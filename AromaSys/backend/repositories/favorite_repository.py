"""Репозиторий избранного."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from database import SessionLocal
from models import Favorite, SKU, Perfume
from core.exceptions import ConflictError, NotFoundError


class FavoriteRepository:
    def list_for_user(self, user_id: int) -> List[SKU]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(SKU)
                .join(Favorite, Favorite.sku_id == SKU.id)
                .options(
                    joinedload(SKU.perfume).joinedload(Perfume.brand),
                    joinedload(SKU.stock_rows),
                )
                .where(Favorite.user_id == user_id)
                .order_by(Favorite.created_at.desc())
            ).unique().all()
            return list(rows)

    def list_favorite_records(self, user_id: int) -> List[Favorite]:
        with SessionLocal() as session:
            return list(
                session.scalars(
                    select(Favorite).where(Favorite.user_id == user_id)
                ).all()
            )

    def get(self, user_id: int, sku_id: int) -> Optional[Favorite]:
        with SessionLocal() as session:
            return session.scalar(
                select(Favorite).where(
                    Favorite.user_id == user_id, Favorite.sku_id == sku_id
                )
            )

    def add(self, user_id: int, sku_id: int) -> Favorite:
        with SessionLocal() as session:
            existing = session.scalar(
                select(Favorite).where(
                    Favorite.user_id == user_id, Favorite.sku_id == sku_id
                )
            )
            if existing:
                raise ConflictError("Уже в избранном")
            fav = Favorite(user_id=user_id, sku_id=sku_id)
            session.add(fav)
            session.commit()
            session.refresh(fav)
            return fav

    def remove(self, user_id: int, sku_id: int) -> None:
        with SessionLocal() as session:
            obj = session.scalar(
                select(Favorite).where(
                    Favorite.user_id == user_id, Favorite.sku_id == sku_id
                )
            )
            if not obj:
                raise NotFoundError("Запись избранного не найдена")
            session.delete(obj)
            session.commit()
