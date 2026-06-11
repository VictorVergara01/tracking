from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QLineEdit, QTextEdit, QComboBox, QPushButton,
                              QScrollArea, QWidget, QMessageBox)
from PyQt6.QtCore import Qt
from sqlalchemy import select
from database import User, Process, Stage, get_session


class ProcessDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Nuevo Proceso de Manufactura')
        self.setMinimumSize(500, 450)
        self.setModal(True)
        self._stage_rows = []
        self._setup_ui()
        self._load_clients()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel('Nombre del Proceso:'))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('Ej: Fabricación de pieza X')
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel('Descripción:'))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText('Descripción del proceso')
        self.desc_input.setMaximumHeight(60)
        layout.addWidget(self.desc_input)

        layout.addWidget(QLabel('Cliente:'))
        self.client_combo = QComboBox()
        layout.addWidget(self.client_combo)

        layout.addWidget(QLabel('Etapas del Proceso:'))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.stages_widget = QWidget()
        self.stages_layout = QVBoxLayout(self.stages_widget)
        self.stages_layout.setSpacing(6)
        scroll.setWidget(self.stages_widget)
        layout.addWidget(scroll, 1)

        self._add_stage_row('Recepción de materiales', '')
        self._add_stage_row('En producción', '')
        self._add_stage_row('Control de calidad', '')
        self._add_stage_row('Finalizado', '')

        add_btn = QPushButton('+ Agregar Etapa')
        add_btn.clicked.connect(lambda: self._add_stage_row('', ''))
        layout.addWidget(add_btn)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton('Cancelar')
        cancel_btn.clicked.connect(self.reject)
        self.create_btn = QPushButton('Crear Proceso')
        self.create_btn.setObjectName('primaryBtn')
        self.create_btn.clicked.connect(self._create)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.create_btn)
        layout.addLayout(btn_layout)

    def _add_stage_row(self, name='', assignee=''):
        row = QHBoxLayout()
        name_edit = QLineEdit()
        name_edit.setPlaceholderText('Nombre de la etapa')
        name_edit.setText(name)
        assignee_edit = QLineEdit()
        assignee_edit.setPlaceholderText('Responsable')
        assignee_edit.setText(assignee)
        row.addWidget(name_edit, 2)
        row.addWidget(assignee_edit, 1)
        self.stages_layout.addLayout(row)
        self._stage_rows.append((name_edit, assignee_edit))

    def _load_clients(self):
        with get_session() as session:
            result = session.execute(select(User).where(User.role == 'client'))
            for client in result.scalars():
                self.client_combo.addItem(client.name, client.id)

    def _create(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, 'Error', 'El nombre del proceso es obligatorio')
            return
        if self.client_combo.count() == 0:
            QMessageBox.warning(self, 'Error', 'No hay clientes disponibles')
            return

        description = self.desc_input.toPlainText().strip()
        client_id = self.client_combo.currentData()
        stages = []
        for name_edit, assignee_edit in self._stage_rows:
            sname = name_edit.text().strip()
            if sname:
                stages.append({'name': sname, 'assigned_to': assignee_edit.text().strip()})

        with get_session() as session:
            process = Process(name=name, description=description,
                              client_id=client_id, status='in_progress')
            session.add(process)
            session.flush()
            for idx, s in enumerate(stages):
                session.add(Stage(
                    process_id=process.id, name=s['name'],
                    order=idx + 1, status='pending',
                    assigned_to=s['assigned_to'],
                ))
            session.commit()
            self.process_id = process.id
        self.accept()
