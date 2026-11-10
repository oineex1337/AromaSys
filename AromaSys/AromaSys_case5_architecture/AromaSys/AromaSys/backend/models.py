"""SQLAlchemy ORM-модели AromaSys. Ограничения БД являются частью модели предметной области."""
from sqlalchemy import (
    String, Integer, Numeric, ForeignKey, UniqueConstraint, CheckConstraint,
    DateTime, Index, func, text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("length(trim(username)) > 0", name="ck_users_username_nonempty"),
        CheckConstraint("length(trim(email)) > 0", name="ck_users_email_nonempty"),
        Index("uq_users_username_lower", text("lower(username)"), unique=True),
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    orders: Mapped[list["Order"]] = relationship(back_populates="user", passive_deletes=True)


class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = (
        UniqueConstraint("name", name="uq_brands_name"),
        CheckConstraint("length(trim(name)) > 0", name="ck_brands_name_nonempty"),
        Index("uq_brands_name_lower", text("lower(name)"), unique=True),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    perfumes: Mapped[list["Perfume"]] = relationship(back_populates="brand", passive_deletes=True)


class Perfume(Base):
    __tablename__ = "perfumes"
    __table_args__ = (
        UniqueConstraint("brand_id", "title", name="uq_perfumes_brand_title"),
        CheckConstraint("length(trim(title)) > 0", name="ck_perfumes_title_nonempty"),
        CheckConstraint("gender IN ('Мужские', 'Женские', 'Унисекс')", name="ck_perfumes_gender"),
        CheckConstraint(
            "concentration IN ('Parfum', 'Extrait de Parfum', 'Eau de Parfum', 'Eau de Toilette', 'Eau de Cologne')",
            name="ck_perfumes_concentration",
        ),
        CheckConstraint("release_year BETWEEN 1900 AND 2100", name="ck_perfumes_release_year"),
        Index("uq_perfumes_brand_title_lower", "brand_id", text("lower(title)"), unique=True),
        Index("ix_perfumes_title", "title"),
        Index("ix_perfumes_gender_year", "gender", "release_year"),
        Index("ix_perfumes_brand_id", "brand_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    gender: Mapped[str] = mapped_column(String, nullable=False)
    concentration: Mapped[str] = mapped_column(String, nullable=False)
    release_year: Mapped[int] = mapped_column(Integer, nullable=False)

    brand: Mapped[Brand] = relationship(back_populates="perfumes")
    skus: Mapped[list["SKU"]] = relationship(back_populates="perfume", passive_deletes=True)


class SKU(Base):
    __tablename__ = "skus"
    __table_args__ = (
        UniqueConstraint("perfume_id", "volume_ml", name="uq_skus_perfume_volume"),
        CheckConstraint("volume_ml BETWEEN 1 AND 1000", name="ck_skus_volume"),
        CheckConstraint("price > 0", name="ck_skus_price_positive"),
        Index("ix_skus_price", "price"),
        Index("ix_skus_perfume_id", "perfume_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    perfume_id: Mapped[int] = mapped_column(ForeignKey("perfumes.id", ondelete="RESTRICT"), nullable=False)
    volume_ml: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    perfume: Mapped[Perfume] = relationship(back_populates="skus")
    stock_rows: Mapped[list["Stock"]] = relationship(
        back_populates="sku", cascade="all, delete-orphan", passive_deletes=True
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="sku", cascade="all, delete-orphan", passive_deletes=True
    )
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="sku", passive_deletes=True)


class Stock(Base):
    __tablename__ = "stock"
    __table_args__ = (
        UniqueConstraint("sku_id", name="uq_stock_sku_id"),
        CheckConstraint("quantity >= 0", name="ck_stock_quantity_nonnegative"),
        Index("ix_stock_sku_id", "sku_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    sku: Mapped[SKU] = relationship(back_populates="stock_rows")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "sku_id", name="uq_favorites_user_sku"),
        Index("ix_favorites_sku_id", "sku_id"),
        Index("ix_favorites_user_created", "user_id", "created_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="favorites")
    sku: Mapped[SKU] = relationship(back_populates="favorites")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("status IN ('new', 'processing', 'shipped', 'completed', 'cancelled')", name="ck_orders_status"),
        CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
        Index("ix_orders_user_created", "user_id", "created_at"),
        Index("ix_orders_status", "status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new", server_default="new")
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", passive_deletes=True
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        UniqueConstraint("order_id", "sku_id", name="uq_order_items_order_sku"),
        CheckConstraint("price > 0", name="ck_order_items_price_positive"),
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        Index("ix_order_items_sku_id", "sku_id"),
        Index("ix_order_items_order_id", "order_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    sku: Mapped[SKU] = relationship(back_populates="order_items")
