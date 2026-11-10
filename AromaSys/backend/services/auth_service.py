"""Сервис аутентификации — бизнес-логика регистрации и входа."""
from werkzeug.security import generate_password_hash, check_password_hash

from repositories.user_repository import UserRepository
from core.auth import issue_token
from core.exceptions import ConflictError, UnauthorizedError


class AuthService:
    def __init__(self):
        self.users = UserRepository()

    def register(self, username: str, email: str, password: str) -> dict:
        existing = self.users.get_by_email_or_username(email, username)
        if existing:
            raise ConflictError("Email или имя пользователя уже заняты")
        password_hash = generate_password_hash(password)
        user = self.users.create(username, email, password_hash)
        return {
            "message": "Регистрация успешна",
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "token": issue_token(user),
        }

    def login(self, email: str, password: str) -> dict:
        email = (email or "").strip().lower()
        if not email or not isinstance(password, str) or not password:
            raise UnauthorizedError("Укажи email и пароль")
        user = self.users.get_by_email(email)
        if not user or not check_password_hash(user.password, password):
            raise UnauthorizedError("Неверный email или пароль")
        return {
            "message": "Вход выполнен",
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "token": issue_token(user),
        }
