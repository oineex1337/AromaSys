# AromaSys Backend — Архитектура (Кейс 5)

## Структура проекта

```
backend/
├── app.py                 # Точка входа: создание Flask-приложения, регистрация роутеров,
│                          # глобальные error handlers, логирование
├── database.py            # Подключение к PostgreSQL (параметры из env)
├── models.py              # SQLAlchemy ORM-модели
├── schemas.py             # Pydantic-схемы запросов/ответов
├── admin_config.py        # ADMIN_EMAIL, API_SECRET (из env)
├── openapi_docs.py        # OpenAPI/Swagger документация
│
├── routers/               # HTTP-слой (Flask Blueprints)
│   ├── auth_router.py     # /register, /login
│   ├── catalog_router.py  # /catalog, /api/catalog-items
│   ├── favorite_router.py # /favorites, /api/favorites
│   ├── health_router.py   # /health
│   └── crud_router.py     # универсальные /api/{entity}
│
├── services/              # Бизнес-логика
│   ├── auth_service.py
│   ├── catalog_service.py
│   └── favorite_service.py
│
├── repositories/          # Слой доступа к данным
│   ├── user_repository.py
│   ├── catalog_repository.py
│   ├── favorite_repository.py
│   └── base_repository.py
│
├── core/                  # Общие утилиты
│   ├── exceptions.py      # AppError, NotFoundError, ConflictError, ...
│   ├── responses.py       # error_response, validated
│   ├── auth.py            # issue_token, require_auth, require_admin
│   └── logging_config.py  # Ротация логов в logs/
│
├── alembic/               # Миграции
├── static/                # Изображения каталога
├── .env.example
└── requirements.txt
```

## Принципы разделения слоёв

| Слой            | Ответственность                                      | Что **запрещено**                          |
|-----------------|------------------------------------------------------|--------------------------------------------|
| **routers**     | Приём HTTP, валидация входа, вызов service, ответ    | SQL, SessionLocal, бизнес-правила          |
| **services**    | Бизнес-правила, оркестрация репозиториев             | Прямой HTTP (request/jsonify), сырой SQL   |
| **repositories**| CRUD и запросы к БД через SQLAlchemy                 | HTTP, бизнес-валидация высокого уровня     |
| **models**      | Описание таблиц и связей                             | Логика приложения                          |
| **database**    | Engine, SessionLocal, Base (конфиг из env)           | Бизнес-код                                 |

Основные запросы к БД **не выполняются** в роутерах. Роутер вызывает сервис → сервис вызывает репозиторий.

## Конфигурация (переменные окружения)

Скопируй `.env.example` и задай значения (или экспортируй в shell):

```bash
# .env или export
DATABASE_URL=postgresql+psycopg2://postgres:PASSWORD@localhost:5432/AromaSys
# либо по отдельности:
DB_USER=postgres
DB_PASSWORD=CHANGE_ME
DB_HOST=localhost
DB_PORT=5432
DB_NAME=AromaSys

AROMASYS_ADMIN_EMAIL=owner@example.com
AROMASYS_API_SECRET=длинный_случайный_секрет
SQL_ECHO=false
LOG_LEVEL=INFO
LOG_DIR=logs
```

`database.py` и `admin_config.py` читают только env — секреты не захардкожены в бизнес-логике.

## Обработка исключений и журналирование

- Доменные исключения: `core/exceptions.py` (`AppError`, `NotFoundError`, `ConflictError`, …).
- Глобальные `@app.errorhandler` в `app.py` превращают их в JSON-ответы.
- Логирование (`core/logging_config.py`):
  - консоль + файл `logs/aromasys.log` (ротация);
  - отдельный `logs/aromasys_errors.log` для ERROR+.
- Необработанные исключения логируются с traceback и возвращают 500.

## Запуск

```bash
cd backend
python -m pip install -r requirements.txt

# Миграции
python -m alembic upgrade head

# Демо-данные (опционально)
python seed_demo.py

# Сервер
python app.py
```

Проверка: http://127.0.0.1:5000/health → `{"status":"ok","database":"ok"}`

## Соответствие требованиям кейса 5

1. ✅ Проект разделён на **routers / services / repositories / models / database**.
2. ✅ Логика не сосредоточена в одном файле; основные запросы к БД **не** выполняются в router.
3. ✅ Параметры подключения и конфигурации вынесены в env (`database.py`, `admin_config.py`).
4. ✅* Централизованная обработка исключений + серверное журналирование с ротацией.
