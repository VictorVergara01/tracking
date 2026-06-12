"""TrackFlow API — FastAPI backend.

Run locally:
    uvicorn main:app --reload
Run for office + field access (bind all interfaces):
    uvicorn main:app --host 0.0.0.0 --port 8000

Interactive docs at /docs.
"""

import os
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

import models
import schemas
from auth import create_token, get_current_user, require_manager

app = FastAPI(title='TrackFlow API', version='1.0')

# Desktop clients are not browsers, but CORS keeps the door open for a future
# web client and harmless for native requests.
app.add_middleware(
    CORSMiddleware, allow_origins=['*'], allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
def _startup():
    models.init_db()


def _due_to_datetime(due):
    """Pydantic date -> naive datetime at midnight (matches how the client used
    to store due dates)."""
    if due is None:
        return None
    return datetime(due.year, due.month, due.day)


@app.get('/health')
def health():
    return {'status': 'ok'}


# --- Auth --------------------------------------------------------------------

@app.post('/auth/login', response_model=schemas.LoginResponse)
def login(body: schemas.LoginRequest):
    user = models.authenticate(body.username, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Usuario o contraseña incorrectos')
    return {'token': create_token(user), 'user': user}


@app.post('/auth/register', status_code=status.HTTP_201_CREATED)
def register(body: schemas.RegisterRequest):
    user, error = models.create_user(body.username, body.name, body.password,
                                      body.role)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return {'user': user}


@app.post('/me/onboarded')
def set_onboarded(user=Depends(get_current_user)):
    models.mark_onboarded(user['id'])
    return {'ok': True}


# --- Processes ---------------------------------------------------------------

@app.get('/processes')
def list_processes(user=Depends(get_current_user)):
    return models.list_processes(user)


@app.post('/processes', status_code=status.HTTP_201_CREATED)
def create_process(body: schemas.ProcessInput, _=Depends(require_manager)):
    snapshot, error = models.create_process(
        body.name, body.description, body.client_id,
        _due_to_datetime(body.due_date),
        [s.model_dump() for s in body.stages])
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return snapshot


@app.put('/processes/{process_id}')
def update_process(process_id: int, body: schemas.ProcessInput,
                   _=Depends(require_manager)):
    snapshot, error = models.update_process(
        process_id, body.name, body.description, body.client_id,
        _due_to_datetime(body.due_date),
        [s.model_dump() for s in body.stages])
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return snapshot


@app.get('/processes/{process_id}')
def get_process(process_id: int, user=Depends(get_current_user)):
    snapshot = models.get_process_snapshot(process_id, user)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='Proceso no encontrado')
    return snapshot


@app.delete('/processes/{process_id}')
def delete_process(process_id: int, _=Depends(require_manager)):
    models.delete_process(process_id)
    return {'ok': True}


@app.post('/stages/{stage_id}/advance')
def advance_stage(stage_id: int, user=Depends(require_manager)):
    # Read-only clients: only managers may change stage state. A client calling
    # this directly gets 403 from require_manager.
    changed = models.advance_stage(stage_id, user)
    return {'ok': True, 'changed': changed}


# --- Metrics / helpers -------------------------------------------------------

@app.get('/metrics/bottleneck')
def bottleneck(_=Depends(require_manager)):
    return models.bottleneck_stats()


@app.get('/clients')
def clients(_=Depends(require_manager)):
    return models.list_clients()


# --- Web client (served from the same origin as the API) ---------------------
# Lives at /ui ; "/" redirects there. Because it shares the API's origin, the
# browser app calls endpoints with same-origin relative paths (no CORS, no
# server-URL field). Works on Windows, macOS, Linux and mobile with no install.
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')


@app.get('/')
def root():
    return RedirectResponse(url='/ui/')


app.mount('/ui', StaticFiles(directory=WEB_DIR, html=True), name='ui')
