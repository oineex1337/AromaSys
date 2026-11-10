"""Роутер проверки здоровья."""
from flask import Blueprint, jsonify

from core.exceptions import AppError
from core.responses import error_response
from services.catalog_service import CatalogService

health_bp = Blueprint("health", __name__)
service = CatalogService()


@health_bp.get("/health")
def health():
    try:
        return jsonify(service.health()), 200
    except AppError as e:
        return error_response(e.message, e.status_code)
