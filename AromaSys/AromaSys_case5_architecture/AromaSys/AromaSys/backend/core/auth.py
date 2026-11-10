"""Аутентификация и авторизация: токены и декораторы."""
from functools import wraps

from flask import request, g
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import select

from admin_config import ADMIN_EMAIL, API_SECRET
from core.exceptions import UnauthorizedError, ForbiddenError
from core.responses import error_response
from database import SessionLocal
from models import User

serializer = URLSafeTimedSerializer(API_SECRET, salt="aromasys-auth-v1")


def issue_token(user: User) -> str:
    return serializer.dumps({"uid": user.id, "email": user.email})


def bearer_user():
    """Извлекает текущего пользователя из Bearer-токена. Возвращает dict или None."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        data = serializer.loads(header[7:], max_age=60 * 60 * 24 * 7)
    except (BadSignature, SignatureExpired):
        return None
    with SessionLocal() as session:
        user = session.get(User, data.get("uid"))
        if not user or user.email.lower() != data.get("email", "").lower():
            return None
        return {"id": user.id, "email": user.email, "username": user.username}


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        g.current_user = bearer_user()
        if not g.current_user:
            return error_response("Требуется авторизация. Выполни вход заново.", 401)
        return fn(*args, **kwargs)

    return wrapper


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        g.current_user = bearer_user()
        if not g.current_user:
            return error_response("Требуется авторизация", 401)
        if (
            not ADMIN_EMAIL
            or ADMIN_EMAIL == "укажи_email_владельца"
            or g.current_user["email"].lower() != ADMIN_EMAIL
        ):
            return error_response(
                "Недостаточно прав. Операция доступна владельцу каталога.", 403
            )
        return fn(*args, **kwargs)

    return wrapper
