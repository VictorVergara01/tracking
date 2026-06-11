"""HTTP client the desktop app uses to talk to the TrackFlow API.

Replaces the old direct-to-SQLite access. Every method returns the same plain
dictionaries the views already render, so the UI code barely changed. The
server URL is remembered between runs (QSettings); the auth token lives only in
memory and is re-obtained at each login.
"""

import requests
from PyQt6.QtCore import QSettings

DEFAULT_URL = 'http://127.0.0.1:8000'


class ApiError(Exception):
    """Raised on network failure or a non-2xx API response."""
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class ApiClient:
    def __init__(self):
        self._settings = QSettings('TrackFlow', 'TrackFlow')
        self.base_url = self._settings.value('server_url', DEFAULT_URL) or DEFAULT_URL
        self.token = None
        self.user = None

    # --- configuration -------------------------------------------------------
    def set_base_url(self, url):
        self.base_url = (url or '').strip().rstrip('/') or DEFAULT_URL
        self._settings.setValue('server_url', self.base_url)

    def _headers(self):
        return {'Authorization': f'Bearer {self.token}'} if self.token else {}

    def _request(self, method, path, **kwargs):
        url = f'{self.base_url}{path}'
        try:
            resp = requests.request(method, url, headers=self._headers(),
                                    timeout=15, **kwargs)
        except requests.RequestException as exc:
            raise ApiError(f'No se pudo conectar al servidor:\n{self.base_url}\n\n{exc}')
        if resp.status_code >= 400:
            try:
                detail = resp.json().get('detail')
            except ValueError:
                detail = resp.text
            raise ApiError(detail or f'Error {resp.status_code}', resp.status_code)
        return resp.json() if resp.content else None

    # --- auth ----------------------------------------------------------------
    def login(self, username, password):
        data = self._request('POST', '/auth/login',
                             json={'username': username, 'password': password})
        self.token = data['token']
        self.user = data['user']
        return self.user

    def register(self, username, name, password, role):
        return self._request('POST', '/auth/register',
                            json={'username': username, 'name': name,
                                  'password': password, 'role': role})

    def mark_onboarded(self):
        self._request('POST', '/me/onboarded')
        if self.user:
            self.user['onboarded'] = True

    def logout(self):
        self.token = None
        self.user = None

    # --- processes / stages --------------------------------------------------
    def list_processes(self):
        return self._request('GET', '/processes')

    def get_process(self, process_id):
        return self._request('GET', f'/processes/{process_id}')

    def create_process(self, payload):
        return self._request('POST', '/processes', json=payload)

    def update_process(self, process_id, payload):
        return self._request('PUT', f'/processes/{process_id}', json=payload)

    def delete_process(self, process_id):
        return self._request('DELETE', f'/processes/{process_id}')

    def advance_stage(self, stage_id):
        return self._request('POST', f'/stages/{stage_id}/advance')

    # --- metrics / helpers ---------------------------------------------------
    def bottleneck(self):
        return self._request('GET', '/metrics/bottleneck')

    def clients(self):
        return self._request('GET', '/clients')


# Module-level singleton shared by all views (mirrors the old global get_session).
api = ApiClient()
