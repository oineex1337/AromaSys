"""Роуты оформления заказа."""
from flask import Blueprint, request, jsonify, g

from core.auth import require_auth
from core.responses import validated, error_response
from core.exceptions import AppError
from schemas import CheckoutCreate
from services.order_service import OrderService

orders_bp = Blueprint("orders", __name__)
service = OrderService()


@orders_bp.post("/api/checkout")
@require_auth
def checkout():
    values, err = validated(CheckoutCreate, request.get_json(silent=True) or {})
    if err:
        return err
    try:
        result = service.checkout(g.current_user["id"], values)
        return jsonify(result), 201
    except AppError as exc:
        return error_response(exc.message, exc.status_code)
