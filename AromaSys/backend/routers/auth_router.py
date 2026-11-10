"""Роутер аутентификации — только HTTP-слой."""
from flask import Blueprint, request, jsonify

from core.responses import validated, error_response
from core.exceptions import AppError
from schemas import UserCreate
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
