"""Доменные и HTTP-ориентированные исключения приложения."""


class AppError(Exception):
    """Базовое исключение приложения с HTTP-статусом."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Запись не найдена"):
        super().__init__(message, 404)


class ConflictError(AppError):
    def __init__(self, message: str = "Конфликт данных или нарушение связи между таблицами"):
        super().__init__(message, 409)


class ValidationAppError(AppError):
    def __init__(self, message: str = "Ошибка валидации", details=None):
        super().__init__(message, 422)
        self.details = details or []


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Требуется авторизация"):
        super().__init__(message, 401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Недостаточно прав"):
        super().__init__(message, 403)


class ServiceUnavailableError(AppError):
    def __init__(self, message: str = "База данных недоступна"):
        super().__init__(message, 503)
