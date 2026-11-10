"""Сервис избранного."""
from repositories.favorite_repository import FavoriteRepository
from repositories.catalog_repository import CatalogRepository
from core.exceptions import ForbiddenError, NotFoundError
from services.catalog_service import catalog_dict


class FavoriteService:
    def __init__(self):
        self.favorites = FavoriteRepository()
        self.catalog = CatalogRepository()

    def list_for_user(self, user_id: int, current_user_id: int | None = None) -> list:
        if current_user_id is not None and user_id != current_user_id:
            raise ForbiddenError("Нет доступа")
        skus = self.favorites.list_for_user(user_id)
        return [catalog_dict(sku, favorite=True) for sku in skus]

    def list_records(self, user_id: int, current_user_id: int) -> list:
        if user_id != current_user_id:
            raise ForbiddenError("Нет доступа")
        rows = self.favorites.list_favorite_records(user_id)
        return [
            {
                "id": x.id,
                "user_id": x.user_id,
                "sku_id": x.sku_id,
                "created_at": x.created_at.isoformat() if x.created_at else None,
            }
            for x in rows
        ]

    def add(self, user_id: int, sku_id: int, current_user_id: int) -> dict:
        if user_id != current_user_id:
            raise ForbiddenError("Нет доступа")
        # проверяем существование SKU
        if not self.catalog.get_sku(sku_id):
            raise NotFoundError("Товар не найден")
        fav = self.favorites.add(user_id, sku_id)
        return {
            "message": "Добавлено в избранное",
            "id": fav.id,
            "user_id": fav.user_id,
            "sku_id": fav.sku_id,
        }

    def remove(self, user_id: int, sku_id: int, current_user_id: int) -> dict:
        if user_id != current_user_id:
            raise ForbiddenError("Нет доступа")
        self.favorites.remove(user_id, sku_id)
        return {"message": "Удалено из избранного"}
