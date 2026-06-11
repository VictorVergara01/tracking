"""Token-based authentication for the API.

Login returns a signed JWT; the client sends it back as `Authorization:
Bearer <token>` on every request. The secret comes from the TRACKFLOW_SECRET
env var (set it in production); a dev fallback keeps local runs frictionless.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import models

SECRET = os.environ.get(
    'TRACKFLOW_SECRET', 'dev-insecure-secret-change-me-in-production-0123456789')
ALGORITHM = 'HS256'
TOKEN_TTL_HOURS = int(os.environ.get('TRACKFLOW_TOKEN_TTL_HOURS', '720'))  # 30 days

_bearer = HTTPBearer(auto_error=True)


def create_token(user):
    """Issue a JWT for a user dict."""
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user['id']),
        'role': user['role'],
        'name': user['name'],
        'username': user['username'],
        'iat': now,
        'exp': now + timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    """FastAPI dependency: decode the bearer token into a user dict, refreshed
    from the DB so role/onboarded are always current."""
    try:
        payload = jwt.decode(creds.credentials, SECRET, algorithms=[ALGORITHM])
        user_id = int(payload['sub'])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Token inválido o expirado')
    with models.get_session() as session:
        user = session.get(models.User, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Usuario no encontrado')
        return models.user_dict(user)


def require_manager(user=Depends(get_current_user)):
    if user['role'] != 'manager':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Requiere rol de gerente')
    return user
