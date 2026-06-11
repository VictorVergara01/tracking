"""Database models and business logic for the TrackFlow API.

This is the authoritative data layer: the desktop client no longer touches the
database directly, it goes through the HTTP API which calls into here. The
models and metric helpers are the same ones the app used locally, moved
server-side so authorization can no longer be bypassed from the client.
"""

import os
from datetime import datetime, timezone
from sqlalchemy import (create_engine, Column, Integer, String, Text, DateTime,
                        Boolean, ForeignKey, select, text, inspect, event)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

Base = declarative_base()


def utcnow():
    """Timezone-aware UTC timestamp (replaces deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc)


def _as_naive(dt):
    """Normalise a datetime to naive UTC so values read back from SQLite (naive)
    and freshly-created aware values can be compared/subtracted safely."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    name = Column(String(120), nullable=False)
    role = Column(String(20), nullable=False)
    onboarded = Column(Boolean, default=False, nullable=False)
    processes = relationship('Process', back_populates='client')


class Process(Base):
    __tablename__ = 'processes'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default='')
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=utcnow)
    due_date = Column(DateTime, nullable=True)
    client_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    client = relationship('User', back_populates='processes')
    stages = relationship('Stage', back_populates='process', order_by='Stage.order',
                          cascade='all, delete-orphan')

    def progress(self):
        if not self.stages:
            return 0
        completed = sum(1 for s in self.stages if s.status == 'completed')
        return int((completed / len(self.stages)) * 100)


class Stage(Base):
    __tablename__ = 'stages'
    id = Column(Integer, primary_key=True)
    process_id = Column(Integer, ForeignKey('processes.id'), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, default='')
    order = Column(Integer, nullable=False)
    status = Column(String(20), default='pending')
    assigned_to = Column(String(120), default='')
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    process = relationship('Process', back_populates='stages')


# DB lives next to this file by default; in Docker set TRACKFLOW_DB_DIR=/data
# (a mounted volume) so the SQLite file survives container rebuilds.
_DB_DIR = os.environ.get('TRACKFLOW_DB_DIR') or os.path.dirname(os.path.abspath(__file__))
os.makedirs(_DB_DIR, exist_ok=True)
DB_PATH = os.path.join(_DB_DIR, 'app.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False,
                       connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine)


@event.listens_for(engine, 'connect')
def _enable_wal(dbapi_conn, _record):
    """WAL mode lets office and field users read/write concurrently far better
    than SQLite's default rollback journal."""
    cur = dbapi_conn.cursor()
    cur.execute('PRAGMA journal_mode=WAL')
    cur.execute('PRAGMA busy_timeout=5000')
    cur.close()


def ensure_schema():
    """Add columns introduced after the first release to an already-existing
    app.db (SQLite has no native migrations). Idempotent."""
    insp = inspect(engine)
    tables = insp.get_table_names()
    with engine.begin() as conn:
        if 'users' in tables:
            cols = {c['name'] for c in insp.get_columns('users')}
            if 'onboarded' not in cols:
                conn.execute(text(
                    'ALTER TABLE users ADD COLUMN onboarded INTEGER NOT NULL DEFAULT 0'))
        if 'processes' in tables:
            cols = {c['name'] for c in insp.get_columns('processes')}
            if 'due_date' not in cols:
                conn.execute(text('ALTER TABLE processes ADD COLUMN due_date DATETIME'))


def init_db():
    Base.metadata.create_all(engine)
    ensure_schema()
    with Session(engine) as session:
        if not session.query(User).filter_by(username='manager').first():
            from werkzeug.security import generate_password_hash
            session.add_all([
                User(username='manager', password_hash=generate_password_hash('manager123'),
                     name='Gerente General', role='manager'),
                User(username='cliente1', password_hash=generate_password_hash('cliente123'),
                     name='Cliente Demo', role='client'),
                User(username='cliente2', password_hash=generate_password_hash('cliente123'),
                     name='Empresa ABC', role='client'),
            ])
            session.commit()


def get_session():
    return SessionLocal()


# --- Users -------------------------------------------------------------------

def create_user(username, name, password, role):
    """Create a user. Returns (user_dict, None) on success or (None, error)."""
    from werkzeug.security import generate_password_hash
    username = (username or '').strip()
    name = (name or '').strip()
    if not username or not name or not password:
        return None, 'Todos los campos son obligatorios'
    if len(username) < 3:
        return None, 'El usuario debe tener al menos 3 caracteres'
    if len(password) < 6:
        return None, 'La contraseña debe tener al menos 6 caracteres'
    if role not in ('manager', 'client'):
        return None, 'Rol inválido'
    with get_session() as session:
        if session.query(User).filter_by(username=username).first():
            return None, 'Ese nombre de usuario ya existe'
        user = User(username=username, name=name, role=role,
                    password_hash=generate_password_hash(password))
        session.add(user)
        session.commit()
        return user_dict(user), None


def authenticate(username, password):
    """Return a user dict if credentials are valid, else None."""
    from werkzeug.security import check_password_hash
    with get_session() as session:
        user = session.execute(
            select(User).where(User.username == (username or '').strip())
        ).scalar_one_or_none()
        if user and check_password_hash(user.password_hash, password):
            return user_dict(user)
    return None


def user_dict(user):
    return {'id': user.id, 'username': user.username, 'name': user.name,
            'role': user.role, 'onboarded': bool(user.onboarded)}


def mark_onboarded(user_id):
    with get_session() as session:
        user = session.get(User, user_id)
        if user and not user.onboarded:
            user.onboarded = True
            session.commit()


def list_clients():
    with get_session() as session:
        rows = session.execute(select(User).where(User.role == 'client')).scalars()
        return [{'id': u.id, 'name': u.name} for u in rows]


# --- Processes / stages ------------------------------------------------------

def processes_for(session, user):
    """Authorization-aware query: clients only ever see their own processes."""
    stmt = select(Process).order_by(Process.created_at.desc())
    if user['role'] != 'manager':
        stmt = stmt.where(Process.client_id == user['id'])
    return session.execute(stmt).scalars().all()


def list_processes(user):
    with get_session() as session:
        return [process_snapshot(p) for p in processes_for(session, user)]


def get_process_snapshot(process_id, user):
    with get_session() as session:
        process = session.get(Process, process_id)
        if not process:
            return None
        if user['role'] != 'manager' and process.client_id != user['id']:
            return None
        return process_snapshot(process)


def _recompute_status(process):
    stages = process.stages
    if stages and all(s.status == 'completed' for s in stages):
        process.status = 'completed'
    elif any(s.status in ('in_progress', 'completed') for s in stages):
        process.status = 'in_progress'
    else:
        process.status = 'pending'


def _sync_stages(session, process, rows):
    """Update existing stages, add new ones, remove deleted ones; keep status."""
    existing = {s.id: s for s in process.stages}
    keep_ids = set()
    for idx, row in enumerate(rows):
        stage = existing.get(row.get('stage_id'))
        if stage is not None:
            stage.name = row['name']
            stage.assigned_to = row.get('assigned_to', '')
            stage.order = idx + 1
            keep_ids.add(stage.id)
        else:
            session.add(Stage(process_id=process.id, name=row['name'],
                              order=idx + 1, status='pending',
                              assigned_to=row.get('assigned_to', '')))
    for stage in list(process.stages):
        if stage.id is not None and stage.id not in keep_ids:
            session.delete(stage)


def create_process(name, description, client_id, due_date, stages):
    """Create a process with its stages. Returns (snapshot, None) or (None, err)."""
    rows = [s for s in stages if s.get('name', '').strip()]
    if not name.strip():
        return None, 'El nombre del proceso es obligatorio'
    if not rows:
        return None, 'Agrega al menos una etapa'
    with get_session() as session:
        if not session.get(User, client_id):
            return None, 'Cliente inválido'
        process = Process(name=name.strip(), description=description or '',
                          client_id=client_id, status='in_progress',
                          due_date=due_date)
        session.add(process)
        session.flush()
        for idx, s in enumerate(rows):
            session.add(Stage(process_id=process.id, name=s['name'].strip(),
                              order=idx + 1, status='pending',
                              assigned_to=s.get('assigned_to', '').strip()))
        _recompute_status(process)
        session.commit()
        return process_snapshot(process), None


def update_process(process_id, name, description, client_id, due_date, stages):
    rows = [s for s in stages if s.get('name', '').strip()]
    if not name.strip():
        return None, 'El nombre del proceso es obligatorio'
    if not rows:
        return None, 'Agrega al menos una etapa'
    with get_session() as session:
        process = session.get(Process, process_id)
        if not process:
            return None, 'El proceso ya no existe'
        process.name = name.strip()
        process.description = description or ''
        process.client_id = client_id
        process.due_date = due_date
        _sync_stages(session, process, rows)
        _recompute_status(process)
        session.commit()
        return process_snapshot(process), None


def delete_process(process_id):
    with get_session() as session:
        process = session.get(Process, process_id)
        if process:
            session.delete(process)  # stages removed via cascade
            session.commit()
        return True


def advance_stage(stage_id, user):
    """Advance a stage pending -> in_progress -> completed and recompute the
    parent process status. Clients may only advance stages of their own
    processes. Returns True if a change was applied."""
    with get_session() as session:
        stage = session.get(Stage, stage_id)
        if not stage:
            return False
        process = stage.process
        if user['role'] != 'manager' and process.client_id != user['id']:
            return False
        if stage.status == 'pending':
            stage.status = 'in_progress'
            stage.started_at = utcnow()
        elif stage.status == 'in_progress':
            stage.status = 'completed'
            stage.completed_at = utcnow()
        else:
            return False
        if all(s.status == 'completed' for s in process.stages):
            process.status = 'completed'
        else:
            process.status = 'in_progress'
        session.commit()
        return True


# --- Industrial-engineering metrics -----------------------------------------

def format_duration(td):
    """Human-friendly duration: '2d 4h', '3h 12m', '45m', '<1m'. None -> None."""
    if td is None:
        return None
    secs = max(int(td.total_seconds()), 0)
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    if days:
        return f'{days}d {hours}h'
    if hours:
        return f'{hours}h {mins}m'
    if mins:
        return f'{mins}m'
    return '<1m'


def stage_duration(stage):
    if stage.started_at and stage.completed_at:
        return _as_naive(stage.completed_at) - _as_naive(stage.started_at)
    return None


def process_lead_time(process):
    starts = [_as_naive(s.started_at) for s in process.stages if s.started_at]
    ends = [_as_naive(s.completed_at) for s in process.stages if s.completed_at]
    if process.status == 'completed' and starts and ends:
        return max(ends) - min(starts)
    return None


def is_overdue(process):
    if not process.due_date or process.status == 'completed':
        return False
    return _now_naive() > _as_naive(process.due_date)


def bottleneck_stats():
    with get_session() as session:
        stages = session.execute(
            select(Stage).where(Stage.status == 'completed')).scalars().all()
        agg = {}
        for s in stages:
            d = stage_duration(s)
            if d is None:
                continue
            acc = agg.setdefault(s.name, [0.0, 0])
            acc[0] += d.total_seconds()
            acc[1] += 1
        stats = [{'name': name, 'avg_seconds': total / count, 'count': count}
                 for name, (total, count) in agg.items()]
        stats.sort(key=lambda x: x['avg_seconds'], reverse=True)
        return stats


def process_snapshot(process):
    """Plain-dict view of a process + its stages, returned by the API and
    rendered as-is by the client (same shape the app used locally)."""
    lead = process_lead_time(process)
    due = _as_naive(process.due_date)
    return {
        'id': process.id,
        'name': process.name,
        'description': process.description or '',
        'status': process.status,
        'progress': process.progress(),
        'client_id': process.client_id,
        'client_name': process.client.name if process.client else 'N/A',
        'overdue': is_overdue(process),
        'due_text': due.strftime('%Y-%m-%d') if due else None,
        'lead_text': format_duration(lead),
        'stages': [{
            'id': s.id,
            'name': s.name,
            'status': s.status,
            'assigned_to': s.assigned_to or '',
            'duration_text': format_duration(stage_duration(s)),
        } for s in process.stages],
    }
