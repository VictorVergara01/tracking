from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QLineEdit, QTextEdit, QComboBox, QPushButton,
                              QScrollArea, QWidget, QMessageBox, QCheckBox,
                              QDateEdit)
from PyQt6.QtCore import Qt, QDate
from api_client import api, ApiError
from process_templates import template_names, stages_for, BLANK


class ProcessDialog(QDialog):
    def __init__(self, parent=None, process_id=None):
        super().__init__(parent)
        self.process_id = process_id
        self._editing = process_id is not None
        self.setWindowTitle('Editar Proceso' if self._editing
                            else 'Nuevo Proceso de Manufactura')
        self.setMinimumSize(500, 450)
        self.setModal(True)
        self._stage_rows = []
        self._setup_ui()
        self._load_clients()
        if self._editing:
            self._load_process()

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

        # Optional due date (Andon / overdue alerts depend on it).
        due_row = QHBoxLayout()
        self.due_check = QCheckBox('Fecha límite:')
        self.due_check.setToolTip('Si se pasa esta fecha sin completar, el '
                                  'proceso se marca como "Atrasado".')
        self.due_date = QDateEdit()
        self.due_date.setCalendarPopup(True)
        self.due_date.setDisplayFormat('yyyy-MM-dd')
        self.due_date.setDate(QDate.currentDate().addDays(7))
        self.due_date.setEnabled(False)
        self.due_check.toggled.connect(self.due_date.setEnabled)
        due_row.addWidget(self.due_check)
        due_row.addWidget(self.due_date, 1)
        layout.addLayout(due_row)

        # Template selector: only when creating (prefilling would clobber the
        # stages of a process being edited).
        if not self._editing:
            layout.addWidget(QLabel('Plantilla:'))
            self.template_combo = QComboBox()
            self.template_combo.addItems(template_names())
            layout.addWidget(self.template_combo)

        layout.addWidget(QLabel('Etapas del Proceso:'))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.stages_widget = QWidget()
        self.stages_layout = QVBoxLayout(self.stages_widget)
        self.stages_layout.setSpacing(6)
        scroll.setWidget(self.stages_widget)
        layout.addWidget(scroll, 1)

        if not self._editing:
            # Prefill from the default template, then react to user changes.
            self._apply_template('Manufactura estándar')
            self.template_combo.setCurrentText('Manufactura estándar')
            self.template_combo.currentTextChanged.connect(self._apply_template)

        add_btn = QPushButton('+ Agregar Etapa')
        add_btn.clicked.connect(lambda: self._add_stage_row('', ''))
        layout.addWidget(add_btn)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton('Cancelar')
        cancel_btn.clicked.connect(self.reject)
        self.create_btn = QPushButton('Guardar Cambios' if self._editing
                                      else 'Crear Proceso')
        self.create_btn.setObjectName('primaryBtn')
        self.create_btn.clicked.connect(self._create)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.create_btn)
        layout.addLayout(btn_layout)

    def _add_stage_row(self, name='', assignee='', stage_id=None):
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
        self._stage_rows.append((name_edit, assignee_edit, stage_id))

    def _clear_stage_rows(self):
        self._stage_rows = []
        while self.stages_layout.count():
            item = self.stages_layout.takeAt(0)
            sub_layout = item.layout()
            if sub_layout is not None:
                while sub_layout.count():
                    sub = sub_layout.takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
                sub_layout.deleteLater()
            elif item.widget():
                item.widget().deleteLater()

    def _apply_template(self, template_name):
        """Replace the stage rows with the chosen template's stages."""
        self._clear_stage_rows()
        if template_name == BLANK:
            self._add_stage_row('', '')
            return
        for stage_name, assignee in stages_for(template_name):
            self._add_stage_row(stage_name, assignee)

    def _load_clients(self):
        try:
            for client in api.clients():
                self.client_combo.addItem(client['name'], client['id'])
        except ApiError as exc:
            QMessageBox.warning(self, 'Error', str(exc))

    def _load_process(self):
        try:
            process = api.get_process(self.process_id)
        except ApiError as exc:
            QMessageBox.warning(self, 'Error', str(exc))
            self.reject()
            return
        self.name_input.setText(process['name'])
        self.desc_input.setPlainText(process.get('description', ''))
        idx = self.client_combo.findData(process['client_id'])
        if idx >= 0:
            self.client_combo.setCurrentIndex(idx)
        if process.get('due_text'):
            self.due_check.setChecked(True)
            self.due_date.setDate(QDate.fromString(process['due_text'], 'yyyy-MM-dd'))
        for stage in process['stages']:
            self._add_stage_row(stage['name'], stage.get('assigned_to', ''),
                                stage['id'])

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
        if self.due_check.isChecked():
            due_value = self.due_date.date().toString('yyyy-MM-dd')
        else:
            due_value = None
        rows = []
        for name_edit, assignee_edit, stage_id in self._stage_rows:
            sname = name_edit.text().strip()
            if sname:
                rows.append({'name': sname,
                             'assigned_to': assignee_edit.text().strip(),
                             'stage_id': stage_id})
        if not rows:
            QMessageBox.warning(self, 'Error', 'Agrega al menos una etapa')
            return

        payload = {'name': name, 'description': description,
                   'client_id': client_id, 'due_date': due_value,
                   'stages': rows}
        try:
            if self._editing:
                result = api.update_process(self.process_id, payload)
            else:
                result = api.create_process(payload)
        except ApiError as exc:
            QMessageBox.warning(self, 'Error', str(exc))
            return
        self.process_id = result['id']
        self.accept()
