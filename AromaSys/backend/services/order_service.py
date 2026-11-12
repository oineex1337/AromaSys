"""Сервис оформления заказов."""
from repositories.order_repository import OrderRepository


class OrderService:
    def __init__(self):
        self.repository = OrderRepository()

    def checkout(self, user_id: int, data: dict) -> dict:
        return self.repository.create_checkout(
            user_id=user_id,
            sku_id=data["sku_id"],
            quantity=data["quantity"],
            delivery_address=data["delivery_address"].strip(),
        )
