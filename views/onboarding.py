"""First-run interactive walkthrough.

A step-by-step welcome wizard shown the first time each user logs in (and
re-launchable from Configuración). Content adapts to the user's role so a
gerente and a cliente each get instructions relevant to what they can do.

The dialog is intentionally a guided card-by-card wizard rather than spotlight
overlays on live widgets: it is robust across window sizes and easy to keep in
sync with the rest of the UI.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QStackedWidget, QWidget)
from PyQt6.QtCore import Qt


# Each step: (emoji icon, title, HTML body). Steps are tailored per role.
MANAGER_STEPS = [
    ('👋', '¡Bienvenido a TrackFlow!',
     'TrackFlow te ayuda a <b>monitorear procesos</b> de principio a fin: '
     'cada proceso se divide en <b>etapas</b> que avanzan de <i>pendiente</i> '
     '→ <i>en progreso</i> → <i>completado</i>.<br><br>'
     'Este tutorial corto (lo verás solo la primera vez) te muestra todo lo '
     'que podés hacer como <b>Gerente</b>.'),
    ('📊', 'El Dashboard',
     'En <b>Dashboard</b> ves <b>todos</b> los procesos. Arriba, cuatro '
     'tarjetas resumen cuántos hay <b>Total</b>, <b>En Progreso</b>, '
     '<b>Completados</b> y <b>Pendientes</b>.<br><br>'
     'Cada tarjeta de proceso muestra su barra de avance y sus etapas.'),
    ('➕', 'Crear un proceso',
     'Tocá <b>“+ Nuevo Proceso”</b>. Podés partir de una <b>plantilla</b> '
     '(Manufactura, Servicio, etc.) para no escribir las etapas a mano, '
     'elegir el <b>cliente</b> y fijar una <b>fecha límite</b>.<br><br>'
     'El lápiz ✎ edita un proceso y la ✕ lo elimina.'),
    ('▶️', 'Avanzar etapas',
     'En cada etapa usá <b>“Iniciar”</b> para marcarla en progreso y '
     '<b>“Completar”</b> al terminarla. La barra de avance y el estado del '
     'proceso se actualizan solos; al completar la última etapa, el proceso '
     'queda <b>Completado</b>.'),
    ('⏱️', 'Indicadores de ingeniería',
     'TrackFlow mide tiempos automáticamente:<br>'
     '• <b>Tiempo por etapa</b> y <b>lead time</b> total al completar.<br>'
     '• El panel <b>Indicadores</b> resalta el <b>cuello de botella</b> '
     '(la etapa más lenta en promedio).<br>'
     '• Los procesos atrasados se marcan en <b>rojo</b> (“Atrasado”).'),
    ('⚙️', 'Configuración y ayuda',
     'Podés volver a ver este tutorial cuando quieras desde el botón '
     '<b>“Configuración”</b> en la barra superior.<br><br>'
     '¡Listo! Ya podés empezar a gestionar tus procesos.'),
]

CLIENT_STEPS = [
    ('👋', '¡Bienvenido a TrackFlow!',
     'Con TrackFlow podés <b>seguir el avance</b> de tus procesos en tiempo '
     'real, etapa por etapa.<br><br>'
     'Este tutorial corto (lo verás solo la primera vez) te muestra cómo usarlo.'),
    ('📋', 'Mis Procesos',
     'En <b>“Mis Procesos”</b> ves <b>únicamente los tuyos</b>. Cada proceso '
     'muestra una <b>línea de tiempo</b> con sus etapas y una barra con el '
     '<b>porcentaje de avance</b>.'),
    ('🔵', 'Leer el estado',
     'Cada etapa tiene un color e ícono:<br>'
     '• ○ gris = <b>pendiente</b><br>'
     '• ● naranja = <b>en progreso</b><br>'
     '• ✔ verde = <b>completada</b><br><br>'
     'Al completarse, también verás <b>cuánto tardó</b> cada etapa.'),
    ('▶️', 'Avanzar tus etapas',
     'Podés mover el avance de tus propios procesos: <b>“Iniciar”</b> arranca '
     'una etapa y <b>“Completar”</b> la termina. Solo afecta <b>tus</b> '
     'procesos, nunca los de otros clientes.'),
    ('⚙️', 'Atrasos y ayuda',
     'Si un proceso pasa su <b>fecha límite</b>, aparece una marca roja '
     '<b>“Atrasado”</b>.<br><br>'
     'Podés volver a ver este tutorial desde el botón <b>“Configuración”</b> '
     'arriba. ¡Eso es todo!'),
]


def steps_for(role):
    return MANAGER_STEPS if role == 'manager' else CLIENT_STEPS


class WalkthroughDialog(QDialog):
    def __init__(self, role, parent=None):
        super().__init__(parent)
        self.steps = steps_for(role)
        self.setWindowTitle('TrackFlow - Tutorial')
        self.setModal(True)
        self.setFixedSize(540, 460)
        self._setup_ui()
        self._show_step(0)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()
        for icon, title, body in self.steps:
            self.stack.addWidget(self._build_page(icon, title, body))
        layout.addWidget(self.stack, 1)

        footer = QWidget()
        footer.setObjectName('walkFooter')
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 14, 24, 18)

        self.skip_btn = QPushButton('Saltar tutorial')
        self.skip_btn.setObjectName('linkBtn')
        self.skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.skip_btn.clicked.connect(self.accept)
        footer_layout.addWidget(self.skip_btn)

        self.step_label = QLabel()
        self.step_label.setObjectName('walkStep')
        footer_layout.addStretch()
        footer_layout.addWidget(self.step_label)
        footer_layout.addStretch()

        self.back_btn = QPushButton('Anterior')
        self.back_btn.clicked.connect(self._prev)
        footer_layout.addWidget(self.back_btn)

        self.next_btn = QPushButton('Siguiente')
        self.next_btn.setObjectName('primaryBtn')
        self.next_btn.clicked.connect(self._next)
        footer_layout.addWidget(self.next_btn)

        layout.addWidget(footer)

    def _build_page(self, icon, title, body):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(36, 34, 36, 18)
        v.setSpacing(14)

        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet('font-size: 56px;')
        v.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setObjectName('walkTitle')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        v.addWidget(title_label)

        body_label = QLabel(body)
        body_label.setTextFormat(Qt.TextFormat.RichText)
        body_label.setWordWrap(True)
        body_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        body_label.setStyleSheet('font-size: 14px; color: #333; line-height: 150%;')
        v.addWidget(body_label, 1)

        return page

    def _show_step(self, index):
        index = max(0, min(index, len(self.steps) - 1))
        self.stack.setCurrentIndex(index)
        self.step_label.setText(f'Paso {index + 1} de {len(self.steps)}')
        self.back_btn.setEnabled(index > 0)
        is_last = index == len(self.steps) - 1
        self.next_btn.setText('Finalizar' if is_last else 'Siguiente')
        self.skip_btn.setVisible(not is_last)

    def _next(self):
        idx = self.stack.currentIndex()
        if idx >= len(self.steps) - 1:
            self.accept()
        else:
            self._show_step(idx + 1)

    def _prev(self):
        self._show_step(self.stack.currentIndex() - 1)
