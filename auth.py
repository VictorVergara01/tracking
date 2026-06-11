from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                              QPushButton, QFormLayout, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt
from api_client import api, ApiError


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = None
        self.setWindowTitle('TrackFlow - Iniciar Sesión')
        self.setFixedSize(400, 470)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 25, 30, 25)

        title = QLabel('TrackFlow')
        title.setObjectName('loginTitle')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel('Sistema de Monitoreo de Procesos')
        subtitle.setObjectName('loginSubtitle')
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(8)

        self.server_input = QLineEdit(api.base_url)
        self.server_input.setPlaceholderText('http://IP-del-servidor:8000')
        self.server_input.setToolTip('Dirección del servidor TrackFlow. En la '
                                     'oficina usá la IP local; de forma remota, '
                                     'el dominio o IP pública.')
        form.addRow('Servidor:', self.server_input)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Nombre de usuario')
        form.addRow('Usuario:', self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Contraseña')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Contraseña:', self.password_input)

        layout.addLayout(form)

        self.login_btn = QPushButton('Ingresar')
        self.login_btn.setObjectName('loginBtn')
        self.login_btn.clicked.connect(self._do_login)
        layout.addWidget(self.login_btn)

        self.register_btn = QPushButton('¿No tienes cuenta? Crear cuenta')
        self.register_btn.setObjectName('linkBtn')
        self.register_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.register_btn.clicked.connect(self._open_register)
        layout.addWidget(self.register_btn)

        hint = QLabel('Gerente: manager / manager123\nCliente: cliente1 / cliente123')
        hint.setObjectName('loginHint')
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self.password_input.returnPressed.connect(self.login_btn.click)

    def _do_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, 'Error', 'Ingrese usuario y contraseña')
            return
        api.set_base_url(self.server_input.text())
        try:
            self.user = api.login(username, password)
        except ApiError as exc:
            QMessageBox.warning(self, 'Error de inicio de sesión', str(exc))
            return
        self.accept()

    def _open_register(self):
        api.set_base_url(self.server_input.text())
        dialog = RegisterDialog(self)
        if dialog.exec() and dialog.created_username:
            self.username_input.setText(dialog.created_username)
            self.password_input.clear()
            self.password_input.setFocus()
            QMessageBox.information(
                self, 'Cuenta creada',
                'Cuenta creada con éxito. Ya puedes iniciar sesión.')


class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.created_username = None
        self.setWindowTitle('TrackFlow - Crear Cuenta')
        self.setFixedSize(420, 470)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 25, 30, 25)

        title = QLabel('Crear Cuenta')
        title.setObjectName('loginTitle')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('Nombre completo')
        form.addRow('Nombre:', self.name_input)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Mínimo 3 caracteres')
        form.addRow('Usuario:', self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Mínimo 6 caracteres')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Contraseña:', self.password_input)

        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText('Repite la contraseña')
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Confirmar:', self.confirm_input)

        self.role_combo = QComboBox()
        self.role_combo.addItem('Cliente', 'client')
        self.role_combo.addItem('Gerente', 'manager')
        form.addRow('Rol:', self.role_combo)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton('Cancelar')
        cancel_btn.clicked.connect(self.reject)
        create_btn = QPushButton('Crear cuenta')
        create_btn.setObjectName('loginBtn')
        create_btn.clicked.connect(self._do_register)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(create_btn)
        layout.addLayout(btn_layout)

        self.confirm_input.returnPressed.connect(create_btn.click)

    def _do_register(self):
        if self.password_input.text() != self.confirm_input.text():
            QMessageBox.warning(self, 'Error', 'Las contraseñas no coinciden')
            return
        try:
            data = api.register(
                self.username_input.text(), self.name_input.text(),
                self.password_input.text(), self.role_combo.currentData())
        except ApiError as exc:
            QMessageBox.warning(self, 'Error', str(exc))
            return
        self.created_username = data['user']['username']
        self.accept()
