"""Сервис каталога — бизнес-логика поиска, фильтрации и управления товарами."""
import os
from typing import Optional

from repositories.catalog_repository import CatalogRepository
from core.exceptions import ValidationAppError, ServiceUnavailableError

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


def catalog_dict(sku, favorite: bool = False) -> dict:
    perfume = sku.perfume
    stock = sum(x.quantity for x in sku.stock_rows) if sku.stock_rows else 0
    image = CatalogRepository.IMAGE_MAP.get(perfume.title)
    image_url = None
    if image and os.path.isfile(os.path.join(STATIC_DIR, image)):
        image_url = f"/static/{image}"
    return {
        "sku_id": sku.id,
        "perfume_id": perfume.id,
        "title": perfume.title,
        "brand": perfume.brand.name,
        "gender": perfume.gender,
        "concentration": perfume.concentration,
        "release_year": perfume.release_year,
        "volume_ml": sku.volume_ml,
        "price": float(sku.price),
        "stock": stock,
        "is_favorite": favorite,
        "image_url": image_url,
    }


class CatalogService:
    ALLOWED_SORT = {"title", "brand", "price", "year", "volume"}
    ALLOWED_GENDER = {"Мужские", "Женские", "Унисекс"}

    def __init__(self):
        self.repo = CatalogRepository()

    def search(
        self,
        gender: Optional[str] = None,
        query: str = "",
        sort: str = "title",
        direction: str = "asc",
        page: int = 1,
        per_page: int = 100,
    ) -> dict:
        if gender and gender not in self.ALLOWED_GENDER:
            raise ValidationAppError("Недопустимое значение gender")
        if sort not in self.ALLOWED_SORT or direction not in ("asc", "desc"):
            raise ValidationAppError("Недопустимая сортировка")
        page = max(page, 1)
        per_page = min(max(per_page, 1), 200)
        rows, total = self.repo.search_catalog(
            gender=gender,
            query=query.strip(),
            sort=sort,
            direction=direction,
            page=page,
            per_page=per_page,
        )
        return {
            "items": [catalog_dict(sku) for sku in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    def list_all(self) -> list:
        return [catalog_dict(sku) for sku in self.repo.list_all_skus()]

    def create_item(self, data: dict) -> dict:
        sku = self.repo.create_catalog_item(data)
        return catalog_dict(sku)

    def update_item(self, sku_id: int, data: dict) -> dict:
        sku = self.repo.update_catalog_item(sku_id, data)
        return catalog_dict(sku)

    def delete_item(self, sku_id: int) -> None:
        self.repo.delete_catalog_item(sku_id)

    def health(self) -> dict:
        try:
            self.repo.health_check()
            return {"status": "ok", "database": "ok"}
        except Exception:
            raise ServiceUnavailableError("База данных недоступна")
