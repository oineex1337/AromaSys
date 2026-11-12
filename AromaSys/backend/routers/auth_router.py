"""Роутер аутентификации — только HTTP-слой."""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.exc import IntegrityError

from core.auth import require_auth
from database import SessionLocal
from models import User

from core.responses import validated, error_response
from core.exceptions import AppError
from schemas import UserCreate, ProfileUpdate
from services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__)
service = AuthService()


@auth_bp.post("/register")
def register():
    values, err = validated(UserCreate, request.get_json(silent=True) or {})
    if err:
        return err
    try:
        result = service.register(
            values["username"], values["email"], values["password"]
        )
        return jsonify(result), 201
    except AppError as e:
        return error_response(e.message, e.status_code)


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    try:
        result = service.login(data.get("email"), data.get("password"))
        return jsonify(result), 200
    except AppError as e:
        return error_response(e.message, e.status_code)


@auth_bp.patch("/api/profile")
@require_auth
def update_profile():
    values, err = validated(
        ProfileUpdate, request.get_json(silent=True) or {}, partial=True
    )
    if err:
        return err

    with SessionLocal() as session:
        user = session.get(User, g.current_user["id"])
        if not user:
            return error_response("Пользователь не найден", 404)

        if values.get("username") is not None:
            user.username = values["username"].strip()
        if values.get("delivery_address") is not None:
            user.delivery_address = values["delivery_address"].strip()
        if values.get("avatar") is not None:
            user.avatar = values["avatar"]

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return error_response("Такой ник уже занят. Выбери другой.", 409)

        session.refresh(user)
        return jsonify({
            "id": user.id,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "delivery_address": user.delivery_address or "",
            "avatar": user.avatar or "pr1.jpg",
        }), 200
