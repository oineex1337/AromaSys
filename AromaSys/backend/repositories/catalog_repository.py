"""Репозиторий каталога: поиск, SKU, агрегированные операции над товарами."""
from typing import List, Optional, Tuple, Any

from sqlalchemy import select, or_, func
from sqlalchemy.orm import joinedload

from database import SessionLocal
from models import Brand, Perfume, SKU, Stock, Favorite, OrderItem
from core.exceptions import ConflictError, NotFoundError


class CatalogRepository:
    IMAGE_MAP = {
        "Bleu de Chanel": "bleu-de-chanel.jpg",
        "Sauvage": "sauvage.jpg",
        "Chanel N5": "chanel-no.jpg",
        "Chanel N°5": "chanel-no.jpg",
        "Cristiano Ronaldo": "ronaldo.jpg",
    }

    def search_catalog(
        self,
        gender: Optional[str] = None,
        query: str = "",
        sort: str = "title",
        direction: str = "asc",
        page: int = 1,
        per_page: int = 100,
    ) -> Tuple[List[SKU], int]:
        allowed = {
            "title": Perfume.title,
            "brand": Brand.name,
            "price": SKU.price,
            "year": Perfume.release_year,
            "volume": SKU.volume_ml,
        }
        with SessionLocal() as session:
            stmt = (
                select(SKU)
                .join(SKU.perfume)
                .join(Perfume.brand)
                .options(
                    joinedload(SKU.perfume).joinedload(Perfume.brand),
                    joinedload(SKU.stock_rows),
                )
            )
            if gender:
                stmt = stmt.where(Perfume.gender == gender)
            if query:
                pattern = f"%{query}%"
                stmt = stmt.where(
                    or_(Perfume.title.ilike(pattern), Brand.name.ilike(pattern))
                )
            order_col = allowed[sort]
            stmt = stmt.order_by(
                order_col.desc() if direction == "desc" else order_col.asc()
            )
            total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            rows = session.scalars(
                stmt.offset((page - 1) * per_page).limit(per_page)
            ).unique().all()
            return list(rows), total

    def list_all_skus(self) -> List[SKU]:
        with SessionLocal() as session:
            return list(
                session.scalars(
                    select(SKU).options(
                        joinedload(SKU.perfume).joinedload(Perfume.brand),
                        joinedload(SKU.stock_rows),
                    )
                ).unique().all()
            )

    def get_sku(self, sku_id: int) -> Optional[SKU]:
        with SessionLocal() as session:
            return session.scalars(
                select(SKU)
                .where(SKU.id == sku_id)
                .options(
                    joinedload(SKU.perfume).joinedload(Perfume.brand),
                    joinedload(SKU.stock_rows),
                )
            ).unique().first()

    def create_catalog_item(self, data: dict) -> SKU:
        """Создаёт Brand + Perfume + SKU + Stock в одной транзакции."""
        with SessionLocal() as session:
            brand = session.scalar(
                select(Brand).where(func.lower(Brand.name) == data["brand"].lower())
            )
            if not brand:
                brand = Brand(name=data["brand"])
                session.add(brand)
                session.flush()

            perfume = session.scalar(
                select(Perfume).where(
                    Perfume.brand_id == brand.id,
                    func.lower(Perfume.title) == data["title"].lower(),
                )
            )
            if not perfume:
                perfume = Perfume(
                    brand_id=brand.id,
                    title=data["title"],
                    gender=data["gender"],
                    concentration=data["concentration"],
                    release_year=data["release_year"],
                )
                session.add(perfume)
                session.flush()

            sku = SKU(
                perfume_id=perfume.id,
                volume_ml=data["volume_ml"],
                price=data["price"],
            )
            session.add(sku)
            session.flush()
            session.add(Stock(sku_id=sku.id, quantity=data["stock"]))
            try:
                session.commit()
            except Exception:
                session.rollback()
                raise ConflictError()
            session.refresh(sku)
            # перезагружаем связи
            return self.get_sku(sku.id)

    def update_catalog_item(self, sku_id: int, data: dict) -> SKU:
        with SessionLocal() as session:
            sku = session.get(SKU, sku_id)
            if not sku:
                raise NotFoundError("Товар не найден")
            perfume = sku.perfume
            if "brand" in data:
                brand = session.scalar(
                    select(Brand).where(
                        func.lower(Brand.name) == data["brand"].lower()
                    )
                )
                if not brand:
                    brand = Brand(name=data["brand"])
                    session.add(brand)
                    session.flush()
                perfume.brand_id = brand.id
            for field in ("title", "gender", "concentration", "release_year"):
                if field in data:
                    setattr(perfume, field, data[field])
            if "volume_ml" in data:
                sku.volume_ml = data["volume_ml"]
            if "price" in data:
                sku.price = data["price"]
            if "stock" in data:
                stock = session.scalar(select(Stock).where(Stock.sku_id == sku_id))
                if stock:
                    stock.quantity = data["stock"]
                else:
                    session.add(Stock(sku_id=sku_id, quantity=data["stock"]))
            try:
                session.commit()
            except Exception:
                session.rollback()
                raise ConflictError()
            return self.get_sku(sku_id)

    def delete_catalog_item(self, sku_id: int) -> None:
        with SessionLocal() as session:
            sku = session.get(SKU, sku_id)
            if not sku:
                raise NotFoundError("Товар не найден")
            if session.scalar(
                select(OrderItem.id).where(OrderItem.sku_id == sku_id).limit(1)
            ):
                raise ConflictError(
                    "Нельзя удалить товар, который уже входит в заказ"
                )
            session.query(Favorite).filter(Favorite.sku_id == sku_id).delete(
                synchronize_session=False
            )
            session.query(Stock).filter(Stock.sku_id == sku_id).delete(
                synchronize_session=False
            )
            session.delete(sku)
            try:
                session.commit()
            except Exception:
                session.rollback()
                raise ConflictError()

    def health_check(self) -> bool:
        from sqlalchemy import text

        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            return True
