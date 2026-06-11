"""Configuración dialog.

Currently hosts the "replay tutorial" action the user asked for; built as a
small dialog so more preferences can be added later without touching the
toolbar wiring.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFrame)
from PyQt6.QtCore import Qt
from views.onboarding import WalkthroughDialog


class SettingsDialog(QDialog):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle('TrackFlow - Configuración')
        self.setModal(True)
        self.setMinimumWidth(420)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel('Configuración')
        title.setObjectName('loginTitle')
        layout.addWidget(title)

        role_text = 'Gerente' if self.user['role'] == 'manager' else 'Cliente'
        who = QLabel(f'Sesión: <b>{self.user["name"]}</b> · {role_text}')
        who.setTextFormat(Qt.TextFormat.RichText)
        who.setStyleSheet('color: #666;')
        layout.addWidget(who)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet('color: #e0e0e0;')
        layout.addWidget(line)

        help_block = QVBoxLayout()
        help_block.setSpacing(4)
        help_title = QLabel('Ayuda')
        help_title.setStyleSheet('font-weight: 700; font-size: 14px;')
        help_block.addWidget(help_title)
        help_desc = QLabel('¿Olvidaste cómo funciona algo? Volvé a ver el '
                           'tutorial guiado de tu rol.')
        help_desc.setWordWrap(True)
        help_desc.setStyleSheet('color: #666; font-size: 13px;')
        help_block.addWidget(help_desc)
        layout.addLayout(help_block)

        self.tutorial_btn = QPushButton('Ver tutorial nuevamente')
        self.tutorial_btn.setObjectName('primaryBtn')
        self.tutorial_btn.clicked.connect(self._replay_tutorial)
        layout.addWidget(self.tutorial_btn)

        layout.addStretch()

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton('Cerrar')
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def _replay_tutorial(self):
        WalkthroughDialog(self.user['role'], self).exec()
