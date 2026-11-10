"""Сервис пользователей (тонкая обёртка, используется при необходимости)."""
from repositories.user_repository import UserRepository


class UserService:
    def __init__(self):
        self.repository = UserRepository()

    def get_by_id(self, user_id: int):
        return self.repository.get_by_id(user_id)

    def get_by_email(self, email: str):
        return self.repository.get_by_email(email)
