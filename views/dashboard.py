from html import escape
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QScrollArea, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from api_client import api, ApiError
from views.process_dialog import ProcessDialog


def _fmt_seconds(seconds):
    """Compact duration text from a number of seconds (for the bottleneck avg)."""
    secs = max(int(seconds), 0)
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
        name = QLabel(f'<b>{escape(stage_data["name"])}</b>')
        name.setTextFormat(Qt.TextFormat.RichText)
        info.addWidget(name)
        if stage_data['assigned_to']:
            info.addWidget(QLabel(f'Responsable: {stage_data["assigned_to"]}'))
        if status == 'completed' and stage_data.get('duration_text'):
            dur = QLabel(f'⏱ {stage_data["duration_text"]}')
            dur.setStyleSheet('color: #1b9c6d; font-size: 11px;')
            info.addWidget(dur)
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
    def __init__(self, process_data, on_advance, on_delete, on_edit, parent=None):
        super().__init__(parent)
        self.process_id = process_data['id']
        self.on_delete = on_delete
        self.on_edit = on_edit
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
        title = QLabel(f'<h3 style="margin:0">{escape(process_data["name"])}</h3>')
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

        if process_data.get('overdue'):
            overdue_badge = QLabel('  ⚠ Atrasado  ')
            overdue_badge.setStyleSheet(
                'background: #fdecea; color: #e94560; border-radius: 10px; '
                'padding: 3px 12px; font-weight: 700; font-size: 12px;')
            header.addWidget(overdue_badge)

        edit_btn = QPushButton('✎')
        edit_btn.setFixedSize(28, 28)
        edit_btn.setToolTip('Editar proceso')
        edit_btn.setStyleSheet(
            'background: transparent; border: 1px solid #0f3460; color: #0f3460; '
            'border-radius: 14px; font-weight: 700;')
        edit_btn.clicked.connect(lambda: self.on_edit(self.process_id))
        header.addWidget(edit_btn)

        del_btn = QPushButton('✕')
        del_btn.setFixedSize(28, 28)
        del_btn.setStyleSheet(
            'background: transparent; border: 1px solid #e94560; color: #e94560; '
            'border-radius: 14px; font-weight: 700;')
        del_btn.clicked.connect(lambda: self.on_delete(self.process_id))
        header.addWidget(del_btn)

        layout.addLayout(header)

        client_label = QLabel(f'Cliente: {escape(process_data["client_name"])}')
        client_label.setStyleSheet('color: #666; font-size: 13px;')
        layout.addWidget(client_label)

        meta_bits = []
        if process_data.get('due_text'):
            meta_bits.append(f'Entrega: {process_data["due_text"]}')
        if process_data.get('lead_text'):
            meta_bits.append(f'Lead time: {process_data["lead_text"]}')
        if meta_bits:
            meta = QLabel('   ·   '.join(meta_bits))
            meta.setStyleSheet('color: #888; font-size: 12px;')
            layout.addWidget(meta)

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
        self._last_snapshot = None
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

        # Industrial-engineering indicator: current bottleneck stage.
        self.indicator_panel = QFrame()
        self.indicator_panel.setObjectName('indicatorPanel')
        self.indicator_panel.setStyleSheet(
            '#indicatorPanel { background: #fff8f0; border: 1px solid #f0d9bf; '
            'border-radius: 10px; }')
        ind_layout = QHBoxLayout(self.indicator_panel)
        ind_layout.setContentsMargins(16, 10, 16, 10)
        self.bottleneck_label = QLabel()
        self.bottleneck_label.setTextFormat(Qt.TextFormat.RichText)
        self.bottleneck_label.setStyleSheet('font-size: 13px; color: #7a5320;')
        ind_layout.addWidget(self.bottleneck_label)
        layout.addWidget(self.indicator_panel)

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
        try:
            snapshot = api.list_processes()
            bottleneck = api.bottleneck()
        except ApiError:
            # The 5s timer drives this; don't spam dialogs on a transient
            # network blip — keep the last rendered state.
            return

        # Stats are cheap label updates that never flicker, so refresh them always.
        self.stat_total.set_value(len(snapshot))
        self.stat_progress.set_value(
            sum(1 for p in snapshot if p['status'] == 'in_progress'))
        self.stat_completed.set_value(
            sum(1 for p in snapshot if p['status'] == 'completed'))
        self.stat_pending.set_value(
            sum(1 for p in snapshot if p['status'] == 'pending'))
        self._update_bottleneck(bottleneck)

        # Only rebuild the cards when the data really changed; otherwise the
        # 5s timer would tear down and recreate every widget, causing flicker
        # and resetting the scroll position on each tick.
        if snapshot == self._last_snapshot:
            return
        self._last_snapshot = snapshot

        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for data in snapshot:
            card = ProcessCard(data, self._advance_stage,
                               self._delete_process, self._edit_process)
            self.scroll_layout.addWidget(card)
        self.scroll_layout.addStretch()

    def _update_bottleneck(self, stats):
        if not stats:
            self.bottleneck_label.setText(
                '🔧 <b>Cuello de botella:</b> aún sin datos — completá etapas '
                'para medir tiempos.')
            return
        top = stats[0]
        avg = _fmt_seconds(top['avg_seconds'])
        self.bottleneck_label.setText(
            f'🔧 <b>Cuello de botella:</b> “{escape(top["name"])}” · '
            f'promedio {avg} · {top["count"]} medición(es) completada(s)')

    def _advance_stage(self, stage_id):
        try:
            api.advance_stage(stage_id)
        except ApiError as exc:
            QMessageBox.warning(self, 'Error', str(exc))
            return
        self._load_data()

    def _delete_process(self, process_id):
        reply = QMessageBox.question(
            self, 'Confirmar', '¿Eliminar este proceso?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                api.delete_process(process_id)
            except ApiError as exc:
                QMessageBox.warning(self, 'Error', str(exc))
                return
            self._load_data()

    def _edit_process(self, process_id):
        dialog = ProcessDialog(self, process_id=process_id)
        if dialog.exec():
            self._load_data()

    def _create_process(self):
        dialog = ProcessDialog(self)
        if dialog.exec():
            self._load_data()
