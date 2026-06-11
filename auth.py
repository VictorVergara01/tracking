from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                              QPushButton, QFormLayout, QMessageBox)
from PyQt6.QtCore import Qt
from sqlalchemy import select
from werkzeug.security import check_password_hash
from database import User, get_session


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = None
        self.setWindowTitle('TrackFlow - Iniciar Sesión')
        self.setFixedSize(380, 260)
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
        with get_session() as session:
            result = session.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()
            if user and check_password_hash(user.password_hash, password):
                self.user = user
                self.accept()
            else:
                QMessageBox.warning(self, 'Error', 'Usuario o contraseña incorrectos')
