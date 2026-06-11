from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QScrollArea, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from sqlalchemy import select
from database import Process, Stage, User, get_session
from views.process_dialog import ProcessDialog


class StatCard(QFrame):
    def __init__(self, title, initial=0, color='#0f3460'):
        super().__init__()
        self.setObjectName('statCard')
        self.setStyleSheet(f'''
            StatCard {{
                background: white; border-radius: 12px;
                padding: 20px; border: 1px solid #e0e0e0;
            }}
        ''')
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.number_label = QLabel(str(initial))
        self.number_label.setStyleSheet(f'font-size: 36px; font-weight: 700; color: {color};')
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.number_label)
        title_label = QLabel(title)
        title_label.setStyleSheet('font-size: 14px; color: #666;')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

    def set_value(self, value):
        self.number_label.setText(str(value))


class StageWidget(QFrame):
    def __init__(self, stage_data, on_advance):
        super().__init__()
        self.stage_id = stage_data['id']
        self.on_advance = on_advance
        status = stage_data['status']
        colors = {
            'completed': ('#e2f7ed', '#1b9c6d', '✔'),
            'in_progress': ('#fef3e2', '#e67e22', '●'),
            'pending': ('#f8f9fa', '#ccc', '○'),
        }
        bg, dot_color, icon = colors.get(status, colors['pending'])
        self.setStyleSheet(f'''
            StageWidget {{
                background: {bg}; border-radius: 8px;
                padding: 10px 14px; border-left: 3px solid {dot_color};
            }}
        ''')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        dot = QLabel(icon)
        dot.setStyleSheet(f'font-size: 14px; color: {dot_color};')
        layout.addWidget(dot)

        info = QVBoxLayout()
        name = QLabel(f'<b>{stage_data["name"]}</b>')
        name.setTextFormat(Qt.TextFormat.RichText)
        info.addWidget(name)
        if stage_data['assigned_to']:
            info.addWidget(QLabel(f'Responsable: {stage_data["assigned_to"]}'))
        layout.addLayout(info, 1)

        if status == 'pending':
            btn = QPushButton('Iniciar')
            btn.setStyleSheet('background: #0f3460; color: white; border: none; '
                              'border-radius: 6px; padding: 6px 16px; font-weight: 600;')
            btn.clicked.connect(lambda: self.on_advance(self.stage_id))
            layout.addWidget(btn)
        elif status == 'in_progress':
            btn = QPushButton('Completar')
            btn.setStyleSheet('background: #1b9c6d; color: white; border: none; '
                              'border-radius: 6px; padding: 6px 16px; font-weight: 600;')
            btn.clicked.connect(lambda: self.on_advance(self.stage_id))
            layout.addWidget(btn)
        else:
            done = QLabel('✔')
            done.setStyleSheet('font-size: 20px; color: #1b9c6d; font-weight: 700;')
            layout.addWidget(done)


class ProcessCard(QFrame):
    def __init__(self, process_data, on_advance, on_delete, parent=None):
        super().__init__(parent)
        self.process_id = process_data['id']
        self.on_delete = on_delete
        self.setStyleSheet('''
            ProcessCard {
                background: white; border-radius: 12px;
                border: 1px solid #e8e8e8; padding: 18px;
            }
            ProcessCard:hover { border-color: #0f3460; }
        ''')
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel(f'<h3 style="margin:0">{process_data["name"]}</h3>')
        title.setTextFormat(Qt.TextFormat.RichText)
        header.addWidget(title, 1)

        status_colors = {
            'pending': ('#f0f0f0', '#666'),
            'in_progress': ('#fef3e2', '#e67e22'),
            'completed': ('#e2f7ed', '#1b9c6d'),
        }
        sc = status_colors.get(process_data['status'], status_colors['pending'])
        badge = QLabel(f'  {process_data["status"]}  ')
        badge.setStyleSheet(
            f'background: {sc[0]}; color: {sc[1]}; border-radius: 10px; '
            f'padding: 3px 12px; font-weight: 600; font-size: 12px;')
        header.addWidget(badge)

        del_btn = QPushButton('✕')
        del_btn.setFixedSize(28, 28)
        del_btn.setStyleSheet(
            'background: transparent; border: 1px solid #e94560; color: #e94560; '
            'border-radius: 14px; font-weight: 700;')
        del_btn.clicked.connect(lambda: self.on_delete(self.process_id))
        header.addWidget(del_btn)

        layout.addLayout(header)

        client_label = QLabel(f'Cliente: {process_data["client_name"]}')
        client_label.setStyleSheet('color: #666; font-size: 13px;')
        layout.addWidget(client_label)

        progress = process_data['progress']
        bar_container = QFrame()
        bar_container.setStyleSheet(
            'background: #e9ecef; border-radius: 10px; height: 22px;')
        bar_layout = QHBoxLayout(bar_container)
        bar_layout.setContentsMargins(0, 0, 0, 0)

        bar_fill = QFrame()
        bar_fill.setStyleSheet(
            f'background: qlineargradient(x1:0, y1:0, x2:1, y2:0, '
            f'stop:0 #0f3460, stop:1 #1b9c6d); '
            f'border-radius: 10px; min-width: {max(progress, 3)}%;')
        bar_layout.addWidget(bar_fill, 1)

        pct = QLabel(f'{progress}%')
        pct.setStyleSheet('font-size: 11px; font-weight: 700; color: #333;')
        pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bar_layout.addWidget(pct)

        layout.addWidget(bar_container)

        for s in process_data['stages']:
            layout.addWidget(StageWidget(s, on_advance))

        self.setLayout(layout)


class DashboardView(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._load_data)
        self._refresh_timer.start(5000)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)

        header = QHBoxLayout()
        title = QLabel('<h2>Dashboard de Procesos</h2>')
        title.setTextFormat(Qt.TextFormat.RichText)
        header.addWidget(title, 1)

        self.create_btn = QPushButton('+ Nuevo Proceso')
        self.create_btn.setObjectName('primaryBtn')
        self.create_btn.setStyleSheet(
            'background: #0f3460; color: white; border: none; '
            'border-radius: 8px; padding: 10px 22px; font-weight: 600; '
            'font-size: 14px;')
        self.create_btn.clicked.connect(self._create_process)
        header.addWidget(self.create_btn)
        layout.addLayout(header)

        self.stats_grid = QHBoxLayout()
        self.stats_grid.setSpacing(12)
        self.stat_total = StatCard('Total', color='#0f3460')
        self.stat_progress = StatCard('En Progreso', color='#e67e22')
        self.stat_completed = StatCard('Completados', color='#1b9c6d')
        self.stat_pending = StatCard('Pendientes', color='#95a5a6')
        self.stats_grid.addWidget(self.stat_total)
        self.stats_grid.addWidget(self.stat_progress)
        self.stats_grid.addWidget(self.stat_completed)
        self.stats_grid.addWidget(self.stat_pending)
        layout.addLayout(self.stats_grid)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(12)
        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll, 1)

        self._load_data()

    def _load_data(self):
        with get_session() as session:
            result = session.execute(
                select(Process).order_by(Process.created_at.desc()))
            processes = result.scalars().all()

            total = len(processes)
            completed = sum(1 for p in processes if p.status == 'completed')
            in_progress = sum(1 for p in processes if p.status == 'in_progress')
            pending = sum(1 for p in processes if p.status == 'pending')
            self.stat_total.set_value(total)
            self.stat_progress.set_value(in_progress)
            self.stat_completed.set_value(completed)
            self.stat_pending.set_value(pending)

            while self.scroll_layout.count():
                item = self.scroll_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            for p in processes:
                data = {
                    'id': p.id,
                    'name': p.name,
                    'status': p.status,
                    'progress': p.progress(),
                    'client_name': p.client.name if p.client else 'N/A',
                    'stages': [{
                        'id': s.id,
                        'name': s.name,
                        'status': s.status,
                        'assigned_to': s.assigned_to or '',
                    } for s in p.stages],
                }
                card = ProcessCard(data, self._advance_stage, self._delete_process)
                self.scroll_layout.addWidget(card)
            self.scroll_layout.addStretch()

    def _advance_stage(self, stage_id):
        with get_session() as session:
            stage = session.get(Stage, stage_id)
            if not stage:
                return
            if stage.status == 'pending':
                stage.status = 'in_progress'
                stage.started_at = datetime.utcnow()
            elif stage.status == 'in_progress':
                stage.status = 'completed'
                stage.completed_at = datetime.utcnow()
            else:
                return
            process = stage.process
            if all(s.status == 'completed' for s in process.stages):
                process.status = 'completed'
            session.commit()
        self._load_data()

    def _delete_process(self, process_id):
        reply = QMessageBox.question(
            self, 'Confirmar', '¿Eliminar este proceso?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            with get_session() as session:
                process = session.get(Process, process_id)
                if process:
                    for s in process.stages:
                        session.delete(s)
                    session.delete(process)
                    session.commit()
            self._load_data()

    def _create_process(self):
        dialog = ProcessDialog(self)
        if dialog.exec():
            self._load_data()
