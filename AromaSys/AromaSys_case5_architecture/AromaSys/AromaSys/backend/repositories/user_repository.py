"""Репозиторий пользователей — только работа с БД."""
from typing import Optional

from sqlalchemy import select, or_

from database import SessionLocal
from models import User
from core.exceptions import ConflictError


class UserRepository:
    def get_by_id(self, user_id: int) -> Optional[User]:
        with SessionLocal() as session:
            return session.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        with SessionLocal() as session:
            return session.scalar(select(User).where(User.email == email.lower()))

    def get_by_email_or_username(self, email: str, username: str) -> Optional[User]:
        with SessionLocal() as session:
            return session.scalar(
                select(User).where(
                    or_(User.email == email.lower(), User.username == username)
                )
            )

    def create(self, username: str, email: str, password_hash: str) -> User:
        with SessionLocal() as session:
            user = User(
                username=username,
                email=email.lower(),
                password=password_hash,
            )
            session.add(user)
            try:
                session.commit()
            except Exception:
                session.rollback()
                raise ConflictError("Email или имя пользователя уже заняты")
            session.refresh(user)
            return user
