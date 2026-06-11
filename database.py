import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    name = Column(String(120), nullable=False)
    role = Column(String(20), nullable=False)
    processes = relationship('Process', back_populates='client')


class Process(Base):
    __tablename__ = 'processes'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default='')
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    client_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    client = relationship('User', back_populates='processes')
    stages = relationship('Stage', back_populates='process', order_by='Stage.order')

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


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)
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
