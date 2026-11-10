"""Роутер избранного — только HTTP-слой."""
from flask import Blueprint, request, jsonify, g

from core.responses import validated, error_response
from core.exceptions import AppError
from core.auth import require_auth
from schemas import FavoriteCreate
from services.favorite_service import FavoriteService

favorite_bp = Blueprint("favorites", __name__)
service = FavoriteService()


@favorite_bp.get("/favorites/<int:user_id>")
@require_auth
def get_favorites(user_id):
    try:
        items = service.list_for_user(user_id, g.current_user["id"])
        return jsonify(items), 200
    except AppError as e:
        return error_response(e.message, e.status_code)


@favorite_bp.post("/favorites")
@require_auth
def add_favorite():
    values, err = validated(FavoriteCreate, request.get_json(silent=True) or {})
    if err:
        return err
    try:
        result = service.add(
            values["user_id"], values["sku_id"], g.current_user["id"]
        )
        return jsonify(result), 201
    except AppError as e:
        return error_response(e.message, e.status_code)


@favorite_bp.delete("/favorites/<int:user_id>/<int:sku_id>")
@require_auth
def remove_favorite(user_id, sku_id):
    try:
        result = service.remove(user_id, sku_id, g.current_user["id"])
        return jsonify(result), 200
    except AppError as e:
        return error_response(e.message, e.status_code)


@favorite_bp.get("/api/favorites")
@require_auth
def api_favorites():
    uid = request.args.get("user_id", type=int) or g.current_user["id"]
    try:
        rows = service.list_records(uid, g.current_user["id"])
        return jsonify(rows), 200
    except AppError as e:
        return error_response(e.message, e.status_code)
