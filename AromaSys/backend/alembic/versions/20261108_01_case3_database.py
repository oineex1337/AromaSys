"""Кейс 3: ограничения, связи, индексы и базовая схема AromaSys.

Миграция совместима с двумя сценариями:
1. Пустая БД: создаёт все таблицы из SQLAlchemy metadata.
2. Существующая БД AromaSys: сохраняет данные и добавляет недостающие ограничения,
   индексы и правила ON DELETE.

Перед применением к существующей БД сделай резервную копию.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261108_01"
down_revision = None
branch_labels = None
depends_on = None


def _has_named(items, name):
    return any(item.get("name") == name for item in items)


def _ensure_check(bind, inspector, table, name, expression):
    if not _has_named(inspector.get_check_constraints(table), name):
        op.create_check_constraint(name, table, expression)


def _ensure_unique(bind, inspector, table, name, columns):
    uniques = inspector.get_unique_constraints(table)
    if not _has_named(uniques, name):
        op.create_unique_constraint(name, table, columns)


def _ensure_fk(inspector, table, name, local_cols, remote_table, remote_cols, ondelete):
    existing = [fk for fk in inspector.get_foreign_keys(table)
                if fk.get("constrained_columns") == local_cols
                and fk.get("referred_table") == remote_table
                and fk.get("referred_columns") == remote_cols]
    desired = (ondelete or "").upper()
    for fk in existing:
        current = ((fk.get("options") or {}).get("ondelete") or "").upper()
        if current == desired:
            return
        if fk.get("name"):
            op.drop_constraint(fk["name"], table, type_="foreignkey")
    op.create_foreign_key(name, table, remote_table, local_cols, remote_cols, ondelete=ondelete)


def upgrade():
    bind = op.get_bind()

    # Создаёт схему на пустой БД и недостающие таблицы на существующей.
    from database import Base
    import models  # noqa: F401
    Base.metadata.create_all(bind=bind)

    inspector = inspect(bind)
    required_not_null = {
        "users": ["username", "email", "password"],
        "brands": ["name"],
        "perfumes": ["brand_id", "title", "gender", "concentration", "release_year"],
        "skus": ["perfume_id", "volume_ml", "price"],
        "stock": ["sku_id", "quantity"],
        "favorites": ["user_id", "sku_id", "created_at"],
        "orders": ["user_id", "status", "total_amount", "created_at"],
        "order_items": ["order_id", "sku_id", "price", "quantity"],
    }
    for table, columns in required_not_null.items():
        actual = {col["name"]: col for col in inspector.get_columns(table)}
        for column in columns:
            if actual[column].get("nullable", True):
                op.alter_column(table, column, existing_type=actual[column]["type"], nullable=False)

    inspector = inspect(bind)
    checks = {
        "users": [
            ("ck_users_username_nonempty", "length(trim(username)) > 0"),
            ("ck_users_email_nonempty", "length(trim(email)) > 0"),
        ],
        "perfumes": [
            ("ck_perfumes_title_nonempty", "length(trim(title)) > 0"),
            ("ck_perfumes_gender", "gender IN ('Мужские', 'Женские', 'Унисекс')"),
            ("ck_perfumes_concentration", "concentration IN ('Parfum', 'Extrait de Parfum', 'Eau de Parfum', 'Eau de Toilette', 'Eau de Cologne')"),
            ("ck_perfumes_release_year", "release_year BETWEEN 1900 AND 2100"),
        ],
        "brands": [("ck_brands_name_nonempty", "length(trim(name)) > 0")],
        "skus": [
            ("ck_skus_volume", "volume_ml BETWEEN 1 AND 1000"),
            ("ck_skus_price_positive", "price > 0"),
        ],
        "stock": [("ck_stock_quantity_nonnegative", "quantity >= 0")],
        "orders": [
            ("ck_orders_status", "status IN ('new', 'processing', 'shipped', 'completed', 'cancelled')"),
            ("ck_orders_total_nonnegative", "total_amount >= 0"),
        ],
        "order_items": [
            ("ck_order_items_price_positive", "price > 0"),
            ("ck_order_items_quantity_positive", "quantity > 0"),
        ],
    }
    for table, items in checks.items():
        for name, expression in items:
            _ensure_check(bind, inspector, table, name, expression)
            inspector = inspect(bind)

    # В старой схеме stock допускал несколько строк на один SKU, хотя отдельного
    # склада/партии нет. Суммируем остатки и оставляем одну строку на SKU.
    # Количество товара сохраняется, дублирующие строки больше не нужны.
    bind.execute(sa.text("""
        WITH grouped AS (
            SELECT sku_id, MIN(id) AS keep_id, SUM(quantity) AS total_quantity
            FROM stock GROUP BY sku_id HAVING COUNT(*) > 1
        )
        UPDATE stock AS target
        SET quantity = grouped.total_quantity
        FROM grouped WHERE target.id = grouped.keep_id
    """))
    bind.execute(sa.text("""
        DELETE FROM stock
        WHERE id NOT IN (SELECT MIN(id) FROM stock GROUP BY sku_id)
    """))

    uniques = {
        "users": [("uq_users_username", ["username"]), ("uq_users_email", ["email"])],
        "brands": [("uq_brands_name", ["name"])],
        "perfumes": [("uq_perfumes_brand_title", ["brand_id", "title"])],
        "skus": [("uq_skus_perfume_volume", ["perfume_id", "volume_ml"])],
        "stock": [("uq_stock_sku_id", ["sku_id"])],
        "favorites": [("uq_favorites_user_sku", ["user_id", "sku_id"])],
        "order_items": [("uq_order_items_order_sku", ["order_id", "sku_id"])],
    }
    for table, items in uniques.items():
        for name, columns in items:
            _ensure_unique(bind, inspector, table, name, columns)
            inspector = inspect(bind)

    # Правила удаления: справочники и проданные позиции защищены от потери истории;
    # избранное и складские строки удаляются вместе с родительской записью.
    foreign_keys = [
        ("perfumes", "fk_perfumes_brand_id_brands", ["brand_id"], "brands", ["id"], "RESTRICT"),
        ("skus", "fk_skus_perfume_id_perfumes", ["perfume_id"], "perfumes", ["id"], "RESTRICT"),
        ("stock", "fk_stock_sku_id_skus", ["sku_id"], "skus", ["id"], "CASCADE"),
        ("favorites", "fk_favorites_user_id_users", ["user_id"], "users", ["id"], "CASCADE"),
        ("favorites", "fk_favorites_sku_id_skus", ["sku_id"], "skus", ["id"], "CASCADE"),
        ("orders", "fk_orders_user_id_users", ["user_id"], "users", ["id"], "RESTRICT"),
        ("order_items", "fk_order_items_order_id_orders", ["order_id"], "orders", ["id"], "CASCADE"),
        ("order_items", "fk_order_items_sku_id_skus", ["sku_id"], "skus", ["id"], "RESTRICT"),
    ]
    inspector = inspect(bind)
    for table, name, local_cols, remote_table, remote_cols, ondelete in foreign_keys:
        _ensure_fk(inspector, table, name, local_cols, remote_table, remote_cols, ondelete)
        inspector = inspect(bind)

    # Индексы для частого поиска, фильтрации, сортировки и JOIN.
    indexes = [
        ("users", "uq_users_username_lower", "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_username_lower ON users (lower(username))"),
        ("users", "uq_users_email_lower", "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_lower ON users (lower(email))"),
        ("brands", "uq_brands_name_lower", "CREATE UNIQUE INDEX IF NOT EXISTS uq_brands_name_lower ON brands (lower(name))"),
        ("perfumes", "uq_perfumes_brand_title_lower", "CREATE UNIQUE INDEX IF NOT EXISTS uq_perfumes_brand_title_lower ON perfumes (brand_id, lower(title))"),
        ("perfumes", "ix_perfumes_title", "CREATE INDEX IF NOT EXISTS ix_perfumes_title ON perfumes (title)"),
        ("perfumes", "ix_perfumes_gender_year", "CREATE INDEX IF NOT EXISTS ix_perfumes_gender_year ON perfumes (gender, release_year)"),
        ("perfumes", "ix_perfumes_brand_id", "CREATE INDEX IF NOT EXISTS ix_perfumes_brand_id ON perfumes (brand_id)"),
        ("skus", "ix_skus_price", "CREATE INDEX IF NOT EXISTS ix_skus_price ON skus (price)"),
        ("skus", "ix_skus_perfume_id", "CREATE INDEX IF NOT EXISTS ix_skus_perfume_id ON skus (perfume_id)"),
        ("stock", "ix_stock_sku_id", "CREATE INDEX IF NOT EXISTS ix_stock_sku_id ON stock (sku_id)"),
        ("favorites", "ix_favorites_sku_id", "CREATE INDEX IF NOT EXISTS ix_favorites_sku_id ON favorites (sku_id)"),
        ("favorites", "ix_favorites_user_created", "CREATE INDEX IF NOT EXISTS ix_favorites_user_created ON favorites (user_id, created_at)"),
        ("orders", "ix_orders_user_created", "CREATE INDEX IF NOT EXISTS ix_orders_user_created ON orders (user_id, created_at)"),
        ("orders", "ix_orders_status", "CREATE INDEX IF NOT EXISTS ix_orders_status ON orders (status)"),
        ("order_items", "ix_order_items_sku_id", "CREATE INDEX IF NOT EXISTS ix_order_items_sku_id ON order_items (sku_id)"),
        ("order_items", "ix_order_items_order_id", "CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON order_items (order_id)"),
    ]
    for _table, _name, statement in indexes:
        bind.execute(sa.text(statement))

    # Старые FK могли быть созданы как NOT VALID. Проверяем их после установки правил.
    if bind.dialect.name == "postgresql":
        inspector = inspect(bind)
        for table, *_rest in foreign_keys:
            for fk in inspector.get_foreign_keys(table):
                if fk.get("name"):
                    bind.execute(sa.text(
                        f'ALTER TABLE "{table}" VALIDATE CONSTRAINT "{fk["name"]}"'
                    ))
            inspector = inspect(bind)


def downgrade():
    # Эта первая миграция добавляет ограничения к существующим пользовательским данным.
    # Автоматический downgrade удалил бы гарантии целостности и потенциально данные,
    # поэтому откат схемы выполняется отдельной миграцией после резервного копирования.
    raise RuntimeError("Безопасный автоматический downgrade отключён. Создай резервную копию и отдельную обратную миграцию.")
