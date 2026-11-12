"""Сохранённые данные профиля и адрес в заказе.

Revision ID: 20261112_01
Revises: 20261108_01
"""
from alembic import op
import sqlalchemy as sa

revision = "20261112_01"
down_revision = "20261108_01"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in ("users", "orders")
    }

    if "delivery_address" not in existing["users"]:
        op.add_column(
            "users",
            sa.Column("delivery_address", sa.String(length=500), nullable=False, server_default=""),
        )
    if "avatar" not in existing["users"]:
        op.add_column(
            "users",
            sa.Column("avatar", sa.String(length=40), nullable=False, server_default="pr1.jpg"),
        )
    if "delivery_address" not in existing["orders"]:
        op.add_column(
            "orders",
            sa.Column("delivery_address", sa.String(length=500), nullable=False, server_default=""),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in ("users", "orders")
    }
    if "delivery_address" in existing["orders"]:
        op.drop_column("orders", "delivery_address")
    if "avatar" in existing["users"]:
        op.drop_column("users", "avatar")
    if "delivery_address" in existing["users"]:
        op.drop_column("users", "delivery_address")
