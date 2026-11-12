"""Репозиторий оформления заказа: одна транзакция для заказа, позиции и склада."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import User, SKU, Stock, Order, OrderItem
from core.exceptions import ConflictError, NotFoundError


class OrderRepository:
    def create_checkout(self, user_id: int, sku_id: int, quantity: int, delivery_address: str) -> dict:
        with SessionLocal() as session:
            user = session.get(User, user_id)
            if not user:
                raise NotFoundError("Пользователь не найден")

            sku = session.scalar(select(SKU).where(SKU.id == sku_id).with_for_update())
            if not sku:
                raise NotFoundError("Товар не найден")

            stock = session.scalar(
                select(Stock).where(Stock.sku_id == sku_id).with_for_update()
            )
            if not stock or stock.quantity < quantity:
                available = stock.quantity if stock else 0
                raise ConflictError(f"Недостаточно товара на складе. В наличии: {available}")

            total = sku.price * quantity
            order = Order(
                user_id=user_id,
                status="new",
                total_amount=total,
                delivery_address=delivery_address,
            )
            session.add(order)
            session.flush()
            session.add(OrderItem(
                order_id=order.id,
                sku_id=sku_id,
                price=sku.price,
                quantity=quantity,
            ))

            stock.quantity -= quantity
            user.delivery_address = delivery_address

            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise ConflictError("Не удалось сохранить заказ. Проверь данные товара.") from exc

            session.refresh(order)
            return {
                "id": order.id,
                "user_id": order.user_id,
                "status": order.status,
                "total_amount": float(order.total_amount),
                "delivery_address": order.delivery_address,
                "created_at": order.created_at.isoformat() if order.created_at else None,
            }
