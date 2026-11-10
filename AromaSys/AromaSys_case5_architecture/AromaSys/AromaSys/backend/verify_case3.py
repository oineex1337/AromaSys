"""Проверка структуры БД для демонстрации кейса 3. Запуск: py verify_case3.py"""
from sqlalchemy import inspect, text
from database import engine

EXPECTED = {"users", "brands", "perfumes", "skus", "stock", "favorites", "orders", "order_items"}

with engine.connect() as connection:
    inspector = inspect(connection)
    tables = set(inspector.get_table_names()) - {"alembic_version"}
    print(f"Таблиц предметной области: {len(tables)}")
    for table in sorted(tables):
        columns = inspector.get_columns(table)
        fks = inspector.get_foreign_keys(table)
        uniques = inspector.get_unique_constraints(table)
        checks = inspector.get_check_constraints(table)
        indexes = inspector.get_indexes(table)
        print(f"\n{table}: {len(columns)} колонок")
        print("  NOT NULL:", ", ".join(c["name"] for c in columns if not c["nullable"]))
        print("  FK:", ", ".join(
            f"{', '.join(fk['constrained_columns'])} -> {fk['referred_table']} ({(fk.get('options') or {}).get('ondelete', 'NO ACTION')})"
            for fk in fks
        ) or "нет")
        print("  UNIQUE:", ", ".join(u.get("name") or str(u.get("column_names")) for u in uniques) or "нет")
        print("  CHECK:", ", ".join(c.get("name") or "без имени" for c in checks) or "нет")
        print("  INDEX:", ", ".join(i["name"] for i in indexes) or "нет")
    version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    print("\nAlembic revision:", version or "не применена")
    if not EXPECTED.issubset(tables):
        raise SystemExit(f"Не хватает таблиц: {', '.join(sorted(EXPECTED - tables))}")
    if not version:
        raise SystemExit("Миграция Alembic ещё не применена")
    print("\nПроверка состава таблиц и версии миграции пройдена.")
