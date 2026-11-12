"""Pydantic-схемы API AromaSys. Отдельные модели для создания, изменения и ответа."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Gender = Literal['Мужские', 'Женские', 'Унисекс']
Concentration = Literal['Parfum', 'Extrait de Parfum', 'Eau de Parfum', 'Eau de Toilette', 'Eau de Cologne']
OrderStatus = Literal['new', 'processing', 'shipped', 'completed', 'cancelled']

class Schema(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class UserCreate(Schema):
    username: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    @field_validator('email')
    @classmethod
    def valid_email(cls, v):
        if '@' not in v or '.' not in v.rsplit('@', 1)[-1]: raise ValueError('Некорректный email')
        return v.lower()
class UserUpdate(Schema):
    username: str | None = Field(default=None, min_length=2, max_length=80)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    @field_validator('email')
    @classmethod
    def valid_email(cls, v):
        if v is not None and ('@' not in v or '.' not in v.rsplit('@', 1)[-1]): raise ValueError('Некорректный email')
        return v.lower() if v else v
class UserOut(BaseModel):
    id: int; username: str; email: str

class ProfileUpdate(Schema):
    username: str | None = Field(default=None, min_length=2, max_length=80)
    delivery_address: str | None = Field(default=None, max_length=500)
    avatar: Literal['pr1.jpg', 'pr2.jpg', 'pr3.jpg'] | None = None

class ProfileOut(BaseModel):
    id: int
    username: str
    email: str
    delivery_address: str = ""
    avatar: str = "pr1.jpg"

class BrandCreate(Schema): name: str = Field(min_length=1, max_length=120)
class BrandUpdate(Schema): name: str | None = Field(default=None, min_length=1, max_length=120)
class BrandOut(BaseModel): id: int; name: str

class PerfumeCreate(Schema):
    brand_id: int = Field(gt=0); title: str = Field(min_length=1, max_length=180)
    gender: Gender; concentration: Concentration; release_year: int = Field(ge=1900, le=2100)
class PerfumeUpdate(Schema):
    brand_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=180)
    gender: Gender | None = None; concentration: Concentration | None = None
    release_year: int | None = Field(default=None, ge=1900, le=2100)
class PerfumeOut(BaseModel):
    id: int; brand_id: int; title: str; gender: str; concentration: str; release_year: int

class SKUCreate(Schema):
    perfume_id: int = Field(gt=0); volume_ml: int = Field(gt=0, le=1000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
class SKUUpdate(Schema):
    perfume_id: int | None = Field(default=None, gt=0)
    volume_ml: int | None = Field(default=None, gt=0, le=1000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
class SKUOut(BaseModel): id: int; perfume_id: int; volume_ml: int; price: Decimal

class StockCreate(Schema): sku_id: int = Field(gt=0); quantity: int = Field(ge=0, le=1000000)
class StockUpdate(Schema):
    sku_id: int | None = Field(default=None, gt=0)
    quantity: int | None = Field(default=None, ge=0, le=1000000)
class StockOut(BaseModel): id: int; sku_id: int; quantity: int

class FavoriteCreate(Schema): user_id: int = Field(gt=0); sku_id: int = Field(gt=0)
class FavoriteOut(BaseModel): id: int; user_id: int; sku_id: int; created_at: datetime

class OrderCreate(Schema):
    user_id: int = Field(gt=0); status: OrderStatus = 'new'
    total_amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    delivery_address: str = Field(default="", max_length=500)
class OrderUpdate(Schema):
    status: OrderStatus | None = None
    total_amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
class OrderOut(BaseModel):
    id: int
    user_id: int
    status: str
    total_amount: Decimal
    delivery_address: str = ""
    created_at: datetime

class CheckoutCreate(Schema):
    sku_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=99)
    delivery_address: str = Field(min_length=5, max_length=500)

class OrderItemCreate(Schema):
    order_id: int = Field(gt=0); sku_id: int = Field(gt=0)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    quantity: int = Field(gt=0, le=100000)
class OrderItemUpdate(Schema):
    order_id: int | None = Field(default=None, gt=0); sku_id: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    quantity: int | None = Field(default=None, gt=0, le=100000)
class OrderItemOut(BaseModel): id: int; order_id: int; sku_id: int; price: Decimal; quantity: int

class CatalogItemCreate(Schema):
    brand: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=180)
    gender: Gender; concentration: Concentration
    release_year: int = Field(ge=1900, le=2100)
    volume_ml: int = Field(gt=0, le=1000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(ge=0, le=1000000)
class CatalogItemUpdate(Schema):
    brand: str | None = Field(default=None, min_length=1, max_length=120)
    title: str | None = Field(default=None, min_length=1, max_length=180)
    gender: Gender | None = None; concentration: Concentration | None = None
    release_year: int | None = Field(default=None, ge=1900, le=2100)
    volume_ml: int | None = Field(default=None, gt=0, le=1000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0, le=1000000)
