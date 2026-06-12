from html import escape
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QTimer
from api_client import api, ApiError


class TimelineItem(QFrame):
    """Read-only stage row: clients can view progress but not change it."""
    def __init__(self, stage_data):
        super().__init__()
        self.stage_id = stage_data['id']
        status = stage_data['status']
        colors = {
            'completed': ('#1b9c6d', '#e2f7ed', '✔'),
            'in_progress': ('#e67e22', '#fef3e2', '●'),
            'pending': ('#ccc', '#f8f9fa', '○'),
        }
        dot_color, bg, icon = colors.get(status, colors['pending'])

        self.setStyleSheet(f'''
            TimelineItem {{
                background: {bg}; border-radius: 8px;
                padding: 10px 14px; margin-left: 20px;
            }}
        ''')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)

        marker = QLabel(icon)
        marker.setStyleSheet(
            f'font-size: 18px; color: {dot_color}; font-weight: 700;')
        layout.addWidget(marker)

        info = QVBoxLayout()
        name = QLabel(f'<b>{escape(stage_data["name"])}</b>')
        name.setTextFormat(Qt.TextFormat.RichText)
        info.addWidget(name)
        if stage_data['assigned_to']:
            info.addWidget(QLabel(f'Responsable: {stage_data["assigned_to"]}'))
        status_label = QLabel(f'Estado: {stage_data["status"]}')
        status_label.setStyleSheet(f'color: {dot_color}; font-size: 12px;')
        info.addWidget(status_label)
        if status == 'completed' and stage_data.get('duration_text'):
            dur = QLabel(f'⏱ Duró {stage_data["duration_text"]}')
            dur.setStyleSheet('color: #1b9c6d; font-size: 11px;')
            info.addWidget(dur)
        layout.addLayout(info, 1)


class ProcessTrackCard(QFrame):
    def __init__(self, process_data):
        super().__init__()
        self.setStyleSheet('''
            ProcessTrackCard {
                background: white; border-radius: 12px;
                border: 1px solid #e8e8e8; padding: 18px;
            }
        ''')
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

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

        timeline_frame = QFrame()
        timeline_layout = QVBoxLayout(timeline_frame)
        timeline_layout.setSpacing(2)
        timeline_layout.setContentsMargins(0, 0, 0, 0)

        for s in process_data['stages']:
            timeline_layout.addWidget(TimelineItem(s))

        layout.addWidget(timeline_frame)


class TrackView(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._last_snapshot = None
        self._setup_ui()
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._load_data)
        self._refresh_timer.start(5000)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel(f'<h2>Mis Procesos</h2>')
        title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title)

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
            snapshot = api.list_processes()  # scoped to this user by the token
        except ApiError:
            return  # transient network blip; keep last state (5s timer retries)

        # Skip the rebuild when nothing changed so the 5s timer doesn't flicker
        # the cards or reset the scroll position.
        if snapshot == self._last_snapshot:
            return
        self._last_snapshot = snapshot

        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for data in snapshot:
            self.scroll_layout.addWidget(ProcessTrackCard(data))
        self.scroll_layout.addStretch()
