"""
Точка входа AromaSys Backend.

Слои архитектуры:
  routers/     — HTTP-слой (Flask Blueprints), без бизнес-логики и прямых запросов к БД
  services/    — бизнес-логика
  repositories/— доступ к данным (SQLAlchemy)
  models.py    — ORM-модели
  database.py  — подключение и конфигурация из переменных окружения
  core/        — исключения, ответы, auth-хелперы, журналирование
"""
import os

from flask import Flask, send_from_directory

from core.logging_config import setup_logging
from core.exceptions import AppError
from core.responses import error_response
from openapi_docs import register_docs
from routers import (
    auth_bp,
    catalog_bp,
    favorite_bp,
    health_bp,
    orders_bp,
    register_crud_routes,
)

logger = setup_logging("aromasys")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def create_app() -> Flask:
    app = Flask(__name__)
    register_docs(app)

    # --- Blueprints (роутеры) ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(favorite_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(orders_bp)

    # Универсальные CRUD-роуты
    register_crud_routes(app)

    # Статика
    @app.get("/static/<path:filename>")
    def static_file(filename):
        return send_from_directory(STATIC_DIR, filename)

    # --- Глобальная обработка исключений ---
    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):
        logger.warning("AppError %s: %s", exc.status_code, exc.message)
        return error_response(exc.message, exc.status_code)

    @app.errorhandler(404)
    def not_found(_):
        return error_response("Маршрут или запись не найдены", 404)

    @app.errorhandler(405)
    def method_not_allowed(_):
        return error_response("HTTP-метод не поддерживается для этого маршрута", 405)

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        logger.exception("Необработанное исключение: %s", exc)
        return error_response("Внутренняя ошибка сервера", 500)

    logger.info("AromaSys application created")
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
