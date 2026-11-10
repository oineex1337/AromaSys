"""Базовый репозиторий с общими операциями над сессией."""
from typing import TypeVar, Type, Optional, Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from core.exceptions import ConflictError, NotFoundError

T = TypeVar("T")


class BaseRepository:
    def __init__(self, model: Type[T]):
        self.model = model

    def _session(self):
        return SessionLocal()

    def get_by_id(self, item_id: int) -> Optional[T]:
        with self._session() as session:
            return session.get(self.model, item_id)

    def list_all(self, order_by=None):
        with self._session() as session:
            stmt = select(self.model)
            if order_by is not None:
                stmt = stmt.order_by(order_by)
            else:
                stmt = stmt.order_by(self.model.id)
            return list(session.scalars(stmt).all())

    def create(self, **kwargs) -> T:
        with self._session() as session:
            obj = self.model(**kwargs)
            session.add(obj)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise ConflictError()
            session.refresh(obj)
            return obj

    def update(self, item_id: int, **kwargs) -> T:
        with self._session() as session:
            obj = session.get(self.model, item_id)
            if not obj:
                raise NotFoundError()
            for key, value in kwargs.items():
                setattr(obj, key, value)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise ConflictError()
            session.refresh(obj)
            return obj

    def delete(self, item_id: int) -> None:
        with self._session() as session:
            obj = session.get(self.model, item_id)
            if not obj:
                raise NotFoundError()
            session.delete(obj)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise ConflictError()
