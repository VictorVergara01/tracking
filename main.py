import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QPushButton, QStackedWidget,
                              QMessageBox)
from PyQt6.QtCore import Qt
from api_client import api, ApiError
from auth import LoginDialog
from views.dashboard import DashboardView
from views.track import TrackView
from views.onboarding import WalkthroughDialog
from views.settings import SettingsDialog


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

        self.settings_btn = QPushButton('Configuración')
        self.settings_btn.setObjectName('toolBtn')
        self.settings_btn.clicked.connect(self._open_settings)
        toolbar_layout.addWidget(self.settings_btn)

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
            self._maybe_onboard()
        else:
            sys.exit()

    def _maybe_onboard(self):
        """Show the guided walkthrough the first time a user logs in."""
        if self.user and not self.user['onboarded']:
            WalkthroughDialog(self.user['role'], self).exec()
            try:
                api.mark_onboarded()
            except ApiError:
                pass  # non-critical; tutorial just won't be marked seen
            self.user['onboarded'] = True

    def _open_settings(self):
        if self.user:
            SettingsDialog(self.user, self).exec()

    def _update_ui(self):
        role_text = 'Gerente' if self.user['role'] == 'manager' else 'Cliente'
        self.user_label.setText(
            f'{self.user["name"]}  |  <span style="color:#e94560;font-weight:600;">{role_text}</span>')
        self.user_label.setTextFormat(Qt.TextFormat.RichText)

        self.dash_btn.setVisible(self.user['role'] == 'manager')

        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        if self.user['role'] == 'manager':
            self.stack.addWidget(DashboardView())
        self.stack.addWidget(TrackView(self.user))
        self.stack.setCurrentIndex(0)

    def _logout(self):
        reply = QMessageBox.question(
            self, 'Cerrar Sesión', '¿Cerrar sesión?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.user = None
            api.logout()
            self._show_login()


def _resource_path(rel):
    """Resolve a bundled resource both when running from source and when frozen
    by PyInstaller (which unpacks data files under sys._MEIPASS)."""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('TrackFlow')

    style_path = _resource_path(os.path.join('resources', 'style.qss'))
    if os.path.exists(style_path):
        with open(style_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
