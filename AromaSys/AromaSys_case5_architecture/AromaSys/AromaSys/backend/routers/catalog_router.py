"""Роутер каталога — только HTTP-слой, без прямых запросов к БД."""
from flask import Blueprint, request, jsonify

from core.responses import validated, error_response
from core.exceptions import AppError
from core.auth import require_admin
from schemas import CatalogItemCreate, CatalogItemUpdate
from services.catalog_service import CatalogService

catalog_bp = Blueprint("catalog", __name__)
service = CatalogService()


@catalog_bp.get("/catalog")
def catalog():
    try:
        result = service.search(
            gender=request.args.get("gender"),
            query=request.args.get("q", ""),
            sort=request.args.get("sort", "title"),
            direction=request.args.get("order", "asc").lower(),
            page=request.args.get("page", 1, type=int),
            per_page=request.args.get("per_page", 100, type=int),
        )
        return jsonify(result), 200
    except AppError as e:
        return error_response(e.message, e.status_code)


@catalog_bp.get("/catalog/all")
def catalog_all():
    try:
        return jsonify(service.list_all()), 200
    except AppError as e:
        return error_response(e.message, e.status_code)


@catalog_bp.post("/api/catalog-items")
@require_admin
def create_catalog_item():
    values, err = validated(CatalogItemCreate, request.get_json(silent=True) or {})
    if err:
        return err
    try:
        result = service.create_item(values)
        return jsonify(result), 201
    except AppError as e:
        return error_response(e.message, e.status_code)


@catalog_bp.patch("/api/catalog-items/<int:sku_id>")
@require_admin
def update_catalog_item(sku_id):
    values, err = validated(
        CatalogItemUpdate, request.get_json(silent=True) or {}, partial=True
    )
    if err:
        return err
    try:
        result = service.update_item(sku_id, values)
        return jsonify(result), 200
    except AppError as e:
        return error_response(e.message, e.status_code)


@catalog_bp.delete("/api/catalog-items/<int:sku_id>")
@require_admin
def delete_catalog_item(sku_id):
    try:
        service.delete_item(sku_id)
        return "", 204
    except AppError as e:
        return error_response(e.message, e.status_code)
