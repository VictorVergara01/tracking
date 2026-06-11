import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QPushButton, QStackedWidget,
                              QMessageBox)
from PyQt6.QtCore import Qt
from database import init_db
from auth import LoginDialog
from views.dashboard import DashboardView
from views.track import TrackView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.user = None
        self.setWindowTitle('TrackFlow - Monitoreo de Procesos')
        self.setMinimumSize(900, 650)
        self.resize(1100, 750)
        self._setup_ui()
        self._show_login()

    def _setup_ui(self):
        self.central = QWidget()
        self.setCentralWidget(self.central)
        layout = QVBoxLayout(self.central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toolbar = QWidget()
        self.toolbar.setFixedHeight(56)
        self.toolbar.setObjectName('toolbar')
        toolbar_layout = QHBoxLayout(self.toolbar)
        toolbar_layout.setContentsMargins(20, 0, 20, 0)

        self.brand = QLabel('<b style="font-size:20px;color:white;">TrackFlow</b>')
        self.brand.setTextFormat(Qt.TextFormat.RichText)
        toolbar_layout.addWidget(self.brand)

        toolbar_layout.addStretch()

        self.user_label = QLabel()
        self.user_label.setStyleSheet('color: #ccc; font-size: 13px;')
        toolbar_layout.addWidget(self.user_label)

        self.dash_btn = QPushButton('Dashboard')
        self.dash_btn.setObjectName('toolBtn')
        self.dash_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        toolbar_layout.addWidget(self.dash_btn)

        self.track_btn = QPushButton('Mis Procesos')
        self.track_btn.setObjectName('toolBtn')
        self.track_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        toolbar_layout.addWidget(self.track_btn)

        self.logout_btn = QPushButton('Cerrar Sesión')
        self.logout_btn.setObjectName('toolBtn')
        self.logout_btn.clicked.connect(self._logout)
        toolbar_layout.addWidget(self.logout_btn)

        layout.addWidget(self.toolbar)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

    def _show_login(self):
        self.setVisible(False)
        dialog = LoginDialog(self)
        if dialog.exec():
            self.user = dialog.user
            self._update_ui()
            self.setVisible(True)
            self.show()
        else:
            sys.exit()

    def _update_ui(self):
        role_text = 'Gerente' if self.user.role == 'manager' else 'Cliente'
        self.user_label.setText(
            f'{self.user.name}  |  <span style="color:#e94560;font-weight:600;">{role_text}</span>')
        self.user_label.setTextFormat(Qt.TextFormat.RichText)

        self.dash_btn.setVisible(self.user.role == 'manager')

        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        if self.user.role == 'manager':
            self.stack.addWidget(DashboardView())
        self.stack.addWidget(TrackView(self.user))

        if self.user.role == 'manager':
            self.stack.setCurrentIndex(0)
        else:
            self.stack.setCurrentIndex(0)

    def _logout(self):
        reply = QMessageBox.question(
            self, 'Cerrar Sesión', '¿Cerrar sesión?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.user = None
            self._show_login()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('TrackFlow')

    style_path = os.path.join(os.path.dirname(__file__), 'resources', 'style.qss')
    if os.path.exists(style_path):
        with open(style_path, 'r') as f:
            app.setStyleSheet(f.read())

    init_db()
    window = MainWindow()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
