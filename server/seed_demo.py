"""Carga datos de ejemplo para demos/presentaciones.

Crea procesos realistas (con tiempos por etapa ya medidos) para que el panel de
cuello de botella, los lead times y las alertas de atraso se vean poblados.

Uso:
    cd server
    .venv/bin/python seed_demo.py          # crea/repone los procesos demo
    .venv/bin/python seed_demo.py --clear   # solo borra los procesos demo

Es idempotente: vuelve a generar los mismos procesos sin duplicar (se reconocen
por un prefijo en el nombre). No toca los procesos que crees vos.
"""

import sys
from datetime import timedelta
from sqlalchemy import select

import models

DEMO_PREFIX = '[Demo] '

# (etapa, responsable, estado, horas_inicio_desde_t0, horas_fin_desde_t0)
# Los offsets en horas posicionan started_at/completed_at relativos al arranque
# del proceso, para que las duraciones queden realistas.
DEMO = [
    {
        'name': 'Fabricación lote A-100', 'client': 'cliente1',
        'description': 'Producción de 100 piezas mecanizadas.',
        'due_days': 5, 'start_days_ago': 4,
        'stages': [
            ('Recepción de materiales', 'Almacén',   'completed', 0,  2),
            ('En producción',          'Producción', 'completed', 2,  14),
            ('Control de calidad',     'Calidad',    'in_progress', 14, None),
            ('Empaque',                'Logística',  'pending',    None, None),
            ('Finalizado',             '',           'pending',    None, None),
        ],
    },
    {
        'name': 'Pedido B-205 (terminado)', 'client': 'cliente2',
        'description': 'Orden completa de Empresa ABC.',
        'due_days': None, 'start_days_ago': 6,
        'stages': [
            ('Solicitud recibida', 'Atención al cliente', 'completed', 0,  1),
            ('Diagnóstico',        'Técnico',             'completed', 1,  5),
            ('En reparación',      'Técnico',             'completed', 5,  20),
            ('Prueba final',       'Calidad',             'completed', 20, 22),
            ('Entrega',            'Logística',           'completed', 22, 26),
        ],
    },
    {
        'name': 'Orden urgente C-300', 'client': 'cliente1',
        'description': 'Entrega con fecha vencida (demo de atraso).',
        'due_days': -1, 'start_days_ago': 3,
        'stages': [
            ('Diseño',     'Ingeniería', 'completed',  0,  6),
            ('Prototipo',  'Ingeniería', 'in_progress', 6,  None),
            ('Validación', 'Calidad',    'pending',     None, None),
            ('Lanzamiento','',           'pending',     None, None),
        ],
    },
    {
        'name': 'Desarrollo D-400 (por iniciar)', 'client': 'cliente2',
        'description': 'Aún no arranca.',
        'due_days': 14, 'start_days_ago': 0,
        'stages': [
            ('Diseño',           'Ingeniería', 'pending', None, None),
            ('Prototipo',        'Ingeniería', 'pending', None, None),
            ('Producción piloto','Producción', 'pending', None, None),
        ],
    },
]


def _client_ids():
    with models.get_session() as s:
        ids = {}
        for uname in ('cliente1', 'cliente2'):
            u = s.execute(select(models.User).where(
                models.User.username == uname)).scalar_one_or_none()
            if u:
                ids[uname] = u.id
        return ids


def clear_demo():
    """Borra solo los procesos demo (por prefijo)."""
    with models.get_session() as s:
        rows = s.execute(select(models.Process).where(
            models.Process.name.like(DEMO_PREFIX + '%'))).scalars().all()
        for p in rows:
            s.delete(p)
        s.commit()
        return len(rows)


def seed():
    models.init_db()
    removed = clear_demo()
    ids = _client_ids()
    if not ids:
        print('No hay usuarios cliente; corré el server una vez para sembrarlos.')
        return
    now = models._now_naive()
    created = 0
    with models.get_session() as s:
        for spec in DEMO:
            client_id = ids.get(spec['client'])
            if not client_id:
                continue
            t0 = now - timedelta(days=spec['start_days_ago'])
            due = None
            if spec['due_days'] is not None:
                due = (now + timedelta(days=spec['due_days'])).replace(
                    hour=0, minute=0, second=0, microsecond=0)
            process = models.Process(
                name=DEMO_PREFIX + spec['name'], description=spec['description'],
                client_id=client_id, due_date=due, status='pending')
            s.add(process)
            s.flush()
            for order, (sname, who, status, h0, h1) in enumerate(spec['stages'], 1):
                stage = models.Stage(
                    process_id=process.id, name=sname, assigned_to=who,
                    order=order, status=status)
                if h0 is not None:
                    stage.started_at = t0 + timedelta(hours=h0)
                if h1 is not None:
                    stage.completed_at = t0 + timedelta(hours=h1)
                s.add(stage)
            s.flush()
            models._recompute_status(process)
            created += 1
        s.commit()
    print(f'Procesos demo: {removed} reemplazados, {created} creados.')


if __name__ == '__main__':
    if '--clear' in sys.argv:
        n = clear_demo()
        print(f'{n} procesos demo borrados.')
    else:
        seed()
