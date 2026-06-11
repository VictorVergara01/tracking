'use strict';

// ---- state -----------------------------------------------------------------
const state = {
  token: localStorage.getItem('tf_token') || null,
  user: JSON.parse(localStorage.getItem('tf_user') || 'null'),
  currentView: 'dash',
  lastSig: null,
  refreshTimer: null,
  modalOpen: false,
  editingId: null,
};

// Process templates (mirror of server/process_templates equivalents).
const BLANK = 'Personalizado (en blanco)';
const TEMPLATES = {
  [BLANK]: [],
  'Manufactura estándar': [
    ['Recepción de materiales', 'Almacén'], ['En producción', 'Producción'],
    ['Control de calidad', 'Calidad'], ['Empaque', 'Logística'], ['Finalizado', ''],
  ],
  'Orden de servicio': [
    ['Solicitud recibida', 'Atención al cliente'], ['Diagnóstico', 'Técnico'],
    ['En reparación', 'Técnico'], ['Prueba final', 'Calidad'], ['Entrega', 'Logística'],
  ],
  'Desarrollo de producto': [
    ['Diseño', 'Ingeniería'], ['Prototipo', 'Ingeniería'], ['Validación', 'Calidad'],
    ['Producción piloto', 'Producción'], ['Lanzamiento', ''],
  ],
  'Logística / Envío': [
    ['Preparación de pedido', 'Almacén'], ['En tránsito', 'Transporte'],
    ['En aduana', 'Despacho'], ['Entregado', ''],
  ],
};

// ---- helpers ---------------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function fmtSeconds(seconds) {
  let s = Math.max(Math.floor(seconds), 0);
  const d = Math.floor(s / 86400); s -= d * 86400;
  const h = Math.floor(s / 3600); s -= h * 3600;
  const m = Math.floor(s / 60);
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m`;
  return '<1m';
}

async function api(path, { method = 'GET', body = null } = {}) {
  const headers = {};
  if (state.token) headers['Authorization'] = 'Bearer ' + state.token;
  if (body) headers['Content-Type'] = 'application/json';
  let res;
  try {
    res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : null });
  } catch (e) {
    throw new Error('No se pudo conectar al servidor.');
  }
  if (res.status === 401) { doLogout(); throw new Error('Sesión expirada'); }
  if (!res.ok) {
    let detail;
    try { detail = (await res.json()).detail; } catch (e) { detail = res.statusText; }
    throw new Error(detail || ('Error ' + res.status));
  }
  const txt = await res.text();
  return txt ? JSON.parse(txt) : null;
}

// ---- auth ------------------------------------------------------------------
async function doLogin() {
  $('#loginError').textContent = '';
  const username = $('#loginUser').value.trim();
  const password = $('#loginPass').value;
  if (!username || !password) { $('#loginError').textContent = 'Ingrese usuario y contraseña'; return; }
  try {
    const data = await api('/auth/login', { method: 'POST', body: { username, password } });
    state.token = data.token;
    state.user = data.user;
    localStorage.setItem('tf_token', state.token);
    localStorage.setItem('tf_user', JSON.stringify(state.user));
    enterApp();
  } catch (e) {
    $('#loginError').textContent = e.message;
  }
}

async function doRegister() {
  $('#regError').textContent = '';
  if ($('#regPass').value !== $('#regPass2').value) {
    $('#regError').textContent = 'Las contraseñas no coinciden'; return;
  }
  try {
    await api('/auth/register', { method: 'POST', body: {
      username: $('#regUser').value.trim(), name: $('#regName').value.trim(),
      password: $('#regPass').value, role: $('#regRole').value,
    }});
    $('#registerForm').classList.add('hidden');
    $('#loginForm').classList.remove('hidden');
    $('#loginUser').value = $('#regUser').value.trim();
    $('#loginError').textContent = 'Cuenta creada. Ya puedes iniciar sesión.';
  } catch (e) {
    $('#regError').textContent = e.message;
  }
}

function doLogout() {
  if (state.refreshTimer) clearInterval(state.refreshTimer);
  state.token = null; state.user = null; state.lastSig = null;
  localStorage.removeItem('tf_token'); localStorage.removeItem('tf_user');
  $('#appView').classList.add('hidden');
  $('#loginView').classList.remove('hidden');
  $('#loginPass').value = '';
}

// ---- app shell -------------------------------------------------------------
function enterApp() {
  const isManager = state.user.role === 'manager';
  $('#loginView').classList.add('hidden');
  $('#appView').classList.remove('hidden');
  $('#userLabel').innerHTML = `${esc(state.user.name)} | <b style="color:#e94560">${isManager ? 'Gerente' : 'Cliente'}</b>`;
  $('#tabDash').classList.toggle('hidden', !isManager);
  switchView(isManager ? 'dash' : 'track');
  loadAndRender();
  if (state.refreshTimer) clearInterval(state.refreshTimer);
  state.refreshTimer = setInterval(loadAndRender, 5000);
  if (!state.user.onboarded) openTutorial();
}

function switchView(view) {
  state.currentView = view;
  $('#dashView').classList.toggle('hidden', view !== 'dash');
  $('#trackView').classList.toggle('hidden', view !== 'track');
  state.lastSig = null; // force re-render on tab change
  loadAndRender();
}

// ---- load + render ---------------------------------------------------------
async function loadAndRender() {
  if (state.modalOpen) return; // don't redraw under an open dialog
  let snapshot, bottleneck = null;
  try {
    snapshot = await api('/processes');
    if (state.user.role === 'manager') bottleneck = await api('/metrics/bottleneck');
  } catch (e) {
    return; // transient; keep last render (timer retries)
  }

  if (state.user.role === 'manager') {
    $('#statTotal').textContent = snapshot.length;
    $('#statProgress').textContent = snapshot.filter((p) => p.status === 'in_progress').length;
    $('#statCompleted').textContent = snapshot.filter((p) => p.status === 'completed').length;
    $('#statPending').textContent = snapshot.filter((p) => p.status === 'pending').length;
    renderBottleneck(bottleneck);
  }

  const sig = JSON.stringify(snapshot) + state.currentView;
  if (sig === state.lastSig) return; // anti-flicker: nothing changed
  state.lastSig = sig;

  const listId = state.currentView === 'dash' ? '#dashList' : '#trackList';
  const manager = state.currentView === 'dash';
  $(listId).innerHTML = snapshot.map((p) => processCard(p, manager)).join('') ||
    '<p class="muted">No hay procesos todavía.</p>';
}

function renderBottleneck(stats) {
  const el = $('#bottleneck');
  if (!stats || !stats.length) {
    el.innerHTML = '🔧 <b>Cuello de botella:</b> aún sin datos — completá etapas para medir tiempos.';
    return;
  }
  const top = stats[0];
  el.innerHTML = `🔧 <b>Cuello de botella:</b> “${esc(top.name)}” · promedio ${fmtSeconds(top.avg_seconds)} · ${top.count} medición(es)`;
}

function processCard(p, manager) {
  const overdue = p.overdue ? '<span class="badge overdue">⚠ Atrasado</span>' : '';
  const controls = manager
    ? `<button class="icon-btn edit" onclick="openEdit(${p.id})" title="Editar">✎</button>
       <button class="icon-btn del" onclick="removeProcess(${p.id})" title="Eliminar">✕</button>`
    : '';
  const meta = [];
  if (p.due_text) meta.push(`Entrega: ${p.due_text}`);
  if (p.lead_text) meta.push(`Lead time: ${p.lead_text}`);
  return `
    <div class="process-card">
      <div class="card-head">
        <h3 class="card-title">${esc(p.name)}</h3>
        ${manager ? `<div class="card-actions">${controls}</div>` : ''}
      </div>
      <div class="card-badges">
        <span class="badge ${p.status}">${p.status}</span>
        ${overdue}
      </div>
      <div class="client-line">Cliente: ${esc(p.client_name)}</div>
      ${meta.length ? `<div class="meta-line">${meta.join('   ·   ')}</div>` : ''}
      <div class="progress"><div class="progress-fill" style="width:${Math.max(p.progress, 3)}%"></div><span class="progress-pct">${p.progress}%</span></div>
      ${p.stages.map(stageRow).join('')}
    </div>`;
}

function stageRow(s) {
  const icon = { completed: '✔', in_progress: '●', pending: '○' }[s.status] || '○';
  let action = '';
  if (s.status === 'pending') action = `<button class="btn-stage start" onclick="advance(${s.id})">Iniciar</button>`;
  else if (s.status === 'in_progress') action = `<button class="btn-stage done" onclick="advance(${s.id})">Completar</button>`;
  else action = '<span class="stage-check">✔</span>';
  const sub = [];
  if (s.assigned_to) sub.push(`Responsable: ${esc(s.assigned_to)}`);
  if (s.status === 'completed' && s.duration_text) sub.push(`⏱ ${s.duration_text}`);
  return `
    <div class="stage ${s.status}">
      <span>${icon}</span>
      <div class="stage-info">
        <div class="stage-name">${esc(s.name)}</div>
        ${sub.length ? `<div class="stage-sub">${sub.join(' · ')}</div>` : ''}
      </div>
      ${action}
    </div>`;
}

// ---- actions ---------------------------------------------------------------
async function advance(stageId) {
  try { await api(`/stages/${stageId}/advance`, { method: 'POST' }); }
  catch (e) { alert(e.message); return; }
  state.lastSig = null; loadAndRender();
}

async function removeProcess(id) {
  if (!confirm('¿Eliminar este proceso?')) return;
  try { await api(`/processes/${id}`, { method: 'DELETE' }); }
  catch (e) { alert(e.message); return; }
  state.lastSig = null; loadAndRender();
}

// ---- create / edit modal ---------------------------------------------------
async function openCreate() {
  state.editingId = null;
  $('#modalTitle').textContent = 'Nuevo Proceso';
  $('#modalError').textContent = '';
  $('#pName').value = ''; $('#pDesc').value = '';
  $('#pDueCheck').checked = false; $('#pDue').disabled = true; $('#pDue').value = '';
  $('#templateRow').classList.remove('hidden');
  await fillClients();
  fillTemplateSelect();
  applyTemplate('Manufactura estándar');
  $('#pTemplate').value = 'Manufactura estándar';
  showModal();
}

async function openEdit(id) {
  state.editingId = id;
  $('#modalTitle').textContent = 'Editar Proceso';
  $('#modalError').textContent = '';
  $('#templateRow').classList.add('hidden');
  let p;
  try { await fillClients(); p = await api(`/processes/${id}`); }
  catch (e) { alert(e.message); return; }
  $('#pName').value = p.name;
  $('#pDesc').value = p.description || '';
  $('#pClient').value = p.client_id;
  if (p.due_text) { $('#pDueCheck').checked = true; $('#pDue').disabled = false; $('#pDue').value = p.due_text; }
  else { $('#pDueCheck').checked = false; $('#pDue').disabled = true; $('#pDue').value = ''; }
  setStageRows(p.stages.map((s) => [s.name, s.assigned_to || '', s.id]));
  showModal();
}

async function fillClients() {
  const clients = await api('/clients');
  $('#pClient').innerHTML = clients.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join('');
}

function fillTemplateSelect() {
  $('#pTemplate').innerHTML = Object.keys(TEMPLATES).map((n) => `<option>${esc(n)}</option>`).join('');
}

function applyTemplate(name) {
  const rows = (TEMPLATES[name] || []).map(([n, a]) => [n, a, null]);
  setStageRows(rows.length ? rows : [['', '', null]]);
}

function setStageRows(rows) {
  $('#stageRows').innerHTML = rows.map(stageInputRow).join('');
}

function stageInputRow(row) {
  const [name, assignee, id] = row;
  return `
    <div class="stage-row" data-id="${id ?? ''}">
      <input class="s-name" placeholder="Nombre de la etapa" value="${esc(name)}" />
      <input class="s-assignee" placeholder="Responsable" value="${esc(assignee)}" />
      <button class="s-del" onclick="this.parentElement.remove()" title="Quitar">✕</button>
    </div>`;
}

function collectStages() {
  return [...document.querySelectorAll('#stageRows .stage-row')].map((row) => {
    const idAttr = row.dataset.id;
    return {
      name: row.querySelector('.s-name').value.trim(),
      assigned_to: row.querySelector('.s-assignee').value.trim(),
      stage_id: idAttr ? Number(idAttr) : null,
    };
  }).filter((s) => s.name);
}

async function saveProcess() {
  $('#modalError').textContent = '';
  const payload = {
    name: $('#pName').value.trim(),
    description: $('#pDesc').value.trim(),
    client_id: Number($('#pClient').value),
    due_date: $('#pDueCheck').checked && $('#pDue').value ? $('#pDue').value : null,
    stages: collectStages(),
  };
  if (!payload.name) { $('#modalError').textContent = 'El nombre del proceso es obligatorio'; return; }
  if (!payload.stages.length) { $('#modalError').textContent = 'Agrega al menos una etapa'; return; }
  try {
    if (state.editingId) await api(`/processes/${state.editingId}`, { method: 'PUT', body: payload });
    else await api('/processes', { method: 'POST', body: payload });
  } catch (e) { $('#modalError').textContent = e.message; return; }
  hideModal();
  state.lastSig = null; loadAndRender();
}

function showModal() { state.modalOpen = true; $('#modalOverlay').classList.remove('hidden'); }
function hideModal() { state.modalOpen = false; $('#modalOverlay').classList.add('hidden'); }

// ---- tutorial --------------------------------------------------------------
const TUT_STEPS = {
  manager: [
    ['👋', '¡Bienvenido a TrackFlow!', 'Monitoreá procesos de principio a fin: cada proceso se divide en <b>etapas</b> que avanzan de pendiente → en progreso → completado.'],
    ['📊', 'El Dashboard', 'Ves <b>todos</b> los procesos y un resumen arriba (Total, En Progreso, Completados, Pendientes).'],
    ['➕', 'Crear un proceso', 'Con <b>“+ Nuevo Proceso”</b> elegís una <b>plantilla</b>, el <b>cliente</b> y una <b>fecha límite</b>. El ✎ edita y la ✕ elimina.'],
    ['▶️', 'Avanzar etapas', '<b>“Iniciar”</b> pone una etapa en progreso y <b>“Completar”</b> la termina. Al completar la última, el proceso queda Completado.'],
    ['⏱️', 'Indicadores', 'Se miden tiempos por etapa y el <b>lead time</b> total; el panel <b>Indicadores</b> resalta el <b>cuello de botella</b>. Los atrasos se marcan en rojo.'],
    ['⚙️', 'Ayuda', 'Podés volver a ver este tutorial desde el botón <b>“Tutorial”</b> arriba. ¡Listo para empezar!'],
  ],
  client: [
    ['👋', '¡Bienvenido a TrackFlow!', 'Seguí el avance de tus procesos en tiempo real, etapa por etapa.'],
    ['📋', 'Mis Procesos', 'Ves <b>únicamente los tuyos</b>, con una línea de tiempo y el <b>porcentaje de avance</b>.'],
    ['🔵', 'Leer el estado', '○ gris = pendiente · ● naranja = en progreso · ✔ verde = completada. Al completarse verás <b>cuánto tardó</b> cada etapa.'],
    ['▶️', 'Avanzar tus etapas', '<b>“Iniciar”</b> y <b>“Completar”</b> mueven tus etapas. Solo afecta <b>tus</b> procesos.'],
    ['⚙️', 'Atrasos y ayuda', 'Si un proceso pasa su fecha límite, verás <b>“Atrasado”</b> en rojo. Reabrí este tutorial desde <b>“Tutorial”</b>.'],
  ],
};
let tutIndex = 0;

function openTutorial() {
  tutIndex = 0;
  $('#tutorialOverlay').classList.remove('hidden');
  renderTutStep();
}
function renderTutStep() {
  const steps = TUT_STEPS[state.user.role] || TUT_STEPS.client;
  const [icon, title, body] = steps[tutIndex];
  $('#tutIcon').textContent = icon;
  $('#tutTitle').textContent = title;
  $('#tutBody').innerHTML = body;
  $('#tutStep').textContent = `Paso ${tutIndex + 1} de ${steps.length}`;
  $('#tutBack').disabled = tutIndex === 0;
  const last = tutIndex === steps.length - 1;
  $('#tutNext').textContent = last ? 'Finalizar' : 'Siguiente';
  $('#tutSkip').classList.toggle('hidden', last);
}
async function closeTutorial() {
  $('#tutorialOverlay').classList.add('hidden');
  if (state.user && !state.user.onboarded) {
    try { await api('/me/onboarded', { method: 'POST' }); } catch (e) {}
    state.user.onboarded = true;
    localStorage.setItem('tf_user', JSON.stringify(state.user));
  }
}

// ---- wiring ----------------------------------------------------------------
window.advance = advance;
window.removeProcess = removeProcess;
window.openEdit = openEdit;

function init() {
  $('#loginBtn').onclick = doLogin;
  $('#loginPass').addEventListener('keydown', (e) => { if (e.key === 'Enter') doLogin(); });
  $('#registerBtn').onclick = doRegister;
  $('#toRegister').onclick = (e) => { e.preventDefault(); $('#loginForm').classList.add('hidden'); $('#registerForm').classList.remove('hidden'); };
  $('#toLogin').onclick = (e) => { e.preventDefault(); $('#registerForm').classList.add('hidden'); $('#loginForm').classList.remove('hidden'); };

  $('#logoutBtn').onclick = doLogout;
  $('#tabDash').onclick = () => switchView('dash');
  $('#tabTrack').onclick = () => switchView('track');
  $('#tabHelp').onclick = openTutorial;

  $('#newProcessBtn').onclick = openCreate;
  $('#modalCancel').onclick = hideModal;
  $('#modalSave').onclick = saveProcess;
  $('#addStageBtn').onclick = () => { $('#stageRows').insertAdjacentHTML('beforeend', stageInputRow(['', '', null])); };
  $('#pDueCheck').addEventListener('change', (e) => { $('#pDue').disabled = !e.target.checked; });
  $('#pTemplate').addEventListener('change', (e) => applyTemplate(e.target.value));

  $('#tutBack').onclick = () => { if (tutIndex > 0) { tutIndex--; renderTutStep(); } };
  $('#tutNext').onclick = () => {
    const steps = TUT_STEPS[state.user.role] || TUT_STEPS.client;
    if (tutIndex >= steps.length - 1) closeTutorial();
    else { tutIndex++; renderTutStep(); }
  };
  $('#tutSkip').onclick = (e) => { e.preventDefault(); closeTutorial(); };

  // Auto-resume session if a token is stored.
  if (state.token && state.user) enterApp();
}

document.addEventListener('DOMContentLoaded', init);
