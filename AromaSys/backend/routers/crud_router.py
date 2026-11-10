"""Универсальные CRUD-роуты для сущностей (users, brands, perfumes, ...).
Логика доступа и работы с сессией вынесена сюда как тонкий HTTP-слой;
для продакшена рекомендуется заменить на выделенные сервисы/репозитории.
"""
from datetime import datetime, timezone

from flask import request, jsonify, g
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import User, Brand, Perfume, SKU, Stock, Order, OrderItem
from schemas import (
    UserCreate, UserUpdate, UserOut,
    BrandCreate, BrandUpdate, BrandOut,
    PerfumeCreate, PerfumeUpdate, PerfumeOut,
    SKUCreate, SKUUpdate, SKUOut,
    StockCreate, StockUpdate, StockOut,
    OrderCreate, OrderUpdate, OrderOut,
    OrderItemCreate, OrderItemUpdate, OrderItemOut,
)
from core.auth import require_auth, require_admin
from core.responses import validated, error_response
from core.exceptions import AppError


def _dump(obj, fields):
    return {field: getattr(obj, field) for field in fields}


RESPONSE_SCHEMAS = {
    User: UserOut,
    Brand: BrandOut,
    Perfume: PerfumeOut,
    SKU: SKUOut,
    Stock: StockOut,
    Order: OrderOut,
    OrderItem: OrderItemOut,
}


def _response_dump(obj, fields):
    raw = _dump(obj, fields)
    schema = RESPONSE_SCHEMAS.get(type(obj))
    return schema.model_validate(raw).model_dump(mode="json") if schema else raw


def _commit(session):
    try:
        session.commit()
        return None
    except IntegrityError:
        session.rollback()
        return ("Конфликт данных или нарушение связи между таблицами", 409)


def register_crud_routes(app):
    def crud_routes(
        path,
        model,
        create_schema,
        update_schema,
        fields,
        *,
        admin=True,
        prepare_create=None,
    ):
        auth_decorator = require_admin if admin else require_auth

        def collection_get():
            with SessionLocal() as s:
                stmt = select(model).order_by(model.id)
                if model is Order:
                    stmt = stmt.where(Order.user_id == g.current_user["id"])
                elif model is OrderItem:
                    stmt = stmt.join(Order, Order.id == OrderItem.order_id).where(
                        Order.user_id == g.current_user["id"]
                    )
                rows = s.scalars(stmt).all()
                return jsonify([_response_dump(x, fields) for x in rows]), 200

        def collection_post():
            values, err = validated(create_schema, request.get_json(silent=True) or {})
            if err:
                return err
            with SessionLocal() as s:
                if model is Order and values.get("user_id") != g.current_user["id"]:
                    return error_response(
                        "Нельзя создавать заказ для другого пользователя", 403
                    )
                if model is OrderItem:
                    parent = s.get(Order, values["order_id"])
                    if not parent:
                        return error_response("Заказ не найден", 404)
                    if parent.user_id != g.current_user["id"]:
                        return error_response("Нет доступа к заказу", 403)
                if prepare_create:
                    values = prepare_create(s, values)
                    if isinstance(values, tuple):
                        return error_response(*values)
                obj = model(**values)
                s.add(obj)
                conflict = _commit(s)
                if conflict:
                    return error_response(*conflict)
                s.refresh(obj)
                return jsonify(_response_dump(obj, fields)), 201

        def item_get(item_id):
            with SessionLocal() as s:
                obj = s.get(model, item_id)
                if obj and model is Order and obj.user_id != g.current_user["id"]:
                    return error_response("Нет доступа к заказу", 403)
                if obj and model is OrderItem:
                    parent = s.get(Order, obj.order_id)
                    if not parent or parent.user_id != g.current_user["id"]:
                        return error_response("Нет доступа к позиции заказа", 403)
                if not obj:
                    return error_response("Запись не найдена", 404)
                return jsonify(_response_dump(obj, fields)), 200

        def item_patch(item_id):
            values, err = validated(
                update_schema, request.get_json(silent=True) or {}, partial=True
            )
            if err:
                return err
            with SessionLocal() as s:
                obj = s.get(model, item_id)
                if not obj:
                    return error_response("Запись не найдена", 404)
                if model is Order and obj.user_id != g.current_user["id"]:
                    return error_response("Нет доступа к заказу", 403)
                if model is OrderItem:
                    parent = s.get(Order, obj.order_id)
                    if not parent or parent.user_id != g.current_user["id"]:
                        return error_response("Нет доступа к позиции заказа", 403)
                for k, v in values.items():
                    setattr(obj, k, v)
                conflict = _commit(s)
                if conflict:
                    return error_response(*conflict)
                s.refresh(obj)
                return jsonify(_response_dump(obj, fields)), 200

        def item_delete(item_id):
            with SessionLocal() as s:
                obj = s.get(model, item_id)
                if not obj:
                    return error_response("Запись не найдена", 404)
                if model is Order and obj.user_id != g.current_user["id"]:
                    return error_response("Нет доступа к заказу", 403)
                if model is OrderItem:
                    parent = s.get(Order, obj.order_id)
                    if not parent or parent.user_id != g.current_user["id"]:
                        return error_response("Нет доступа к позиции заказа", 403)
                s.delete(obj)
                conflict = _commit(s)
                if conflict:
                    return error_response(*conflict)
                return "", 204

        # регистрация маршрутов
        app.add_url_rule(
            f"/api/{path}",
            f"{path}_list",
            auth_decorator(collection_get),
            methods=["GET"],
        )
        app.add_url_rule(
            f"/api/{path}",
            f"{path}_create",
            auth_decorator(collection_post),
            methods=["POST"],
        )
        app.add_url_rule(
            f"/api/{path}/<int:item_id>",
            f"{path}_get",
            auth_decorator(item_get),
            methods=["GET"],
        )
        app.add_url_rule(
            f"/api/{path}/<int:item_id>",
            f"{path}_patch",
            auth_decorator(item_patch),
            methods=["PATCH"],
        )
        app.add_url_rule(
            f"/api/{path}/<int:item_id>",
            f"{path}_delete",
            auth_decorator(item_delete),
            methods=["DELETE"],
        )

    # регистрация сущностей
    crud_routes("users", User, UserCreate, UserUpdate, ["id", "username", "email"])
    crud_routes("brands", Brand, BrandCreate, BrandUpdate, ["id", "name"])
    crud_routes(
        "perfumes",
        Perfume,
        PerfumeCreate,
        PerfumeUpdate,
        ["id", "brand_id", "title", "gender", "concentration", "release_year"],
    )
    crud_routes(
        "skus", SKU, SKUCreate, SKUUpdate, ["id", "perfume_id", "volume_ml", "price"]
    )
    crud_routes(
        "stock", Stock, StockCreate, StockUpdate, ["id", "sku_id", "quantity"]
    )
    crud_routes(
        "orders",
        Order,
        OrderCreate,
        OrderUpdate,
        ["id", "user_id", "status", "total_amount", "created_at"],
        admin=False,
        prepare_create=lambda s, v: {
            **v,
            "created_at": datetime.now(timezone.utc),
        },
    )
    crud_routes(
        "order-items",
        OrderItem,
        OrderItemCreate,
        OrderItemUpdate,
        ["id", "order_id", "sku_id", "price", "quantity"],
        admin=False,
    )
