"""Идемпотентное заполнение каталога демонстрационными данными.

Запуск из папки backend: py seed_demo.py
Существующие аккаунты и заказы не изменяются.
"""
from decimal import Decimal
from sqlalchemy import select, func
from database import SessionLocal
from models import Brand, Perfume, SKU, Stock

PRODUCTS = [
    {"brand": "Chanel", "title": "Bleu de Chanel", "gender": "Мужские", "concentration": "Eau de Parfum", "year": 2014,
     "skus": [(50, Decimal("12500.00")), (100, Decimal("16900.00"))]},
    {"brand": "Dior", "title": "Sauvage", "gender": "Мужские", "concentration": "Eau de Parfum", "year": 2015,
     "skus": [(60, Decimal("11800.00")), (100, Decimal("15400.00"))]},
    {"brand": "Chanel", "title": "Chanel N°5", "gender": "Женские", "concentration": "Eau de Parfum", "year": 1921,
     "skus": [(50, Decimal("14200.00")), (100, Decimal("18900.00"))]},
    {"brand": "Cristiano Ronaldo", "title": "Cristiano Ronaldo", "gender": "Мужские", "concentration": "Eau de Toilette", "year": 2015,
     "skus": [(50, Decimal("4500.00")), (100, Decimal("6900.00"))]},
]


def main():
    created_brands = created_perfumes = created_skus = created_stock = 0
    with SessionLocal() as session:
        for item in PRODUCTS:
            brand = session.scalar(select(Brand).where(func.lower(Brand.name) == item["brand"].lower()))
            if brand is None:
                brand = Brand(name=item["brand"])
                session.add(brand)
                session.flush()
                created_brands += 1

            perfume = session.scalar(select(Perfume).where(
                Perfume.brand_id == brand.id,
                func.lower(Perfume.title) == item["title"].lower(),
            ))
            if perfume is None:
                perfume = Perfume(
                    brand_id=brand.id,
                    title=item["title"],
                    gender=item["gender"],
                    concentration=item["concentration"],
                    release_year=item["year"],
                )
                session.add(perfume)
                session.flush()
                created_perfumes += 1

            for volume, price in item["skus"]:
                sku = session.scalar(select(SKU).where(
                    SKU.perfume_id == perfume.id,
                    SKU.volume_ml == volume,
                ))
                if sku is None:
                    sku = SKU(perfume_id=perfume.id, volume_ml=volume, price=price)
                    session.add(sku)
                    session.flush()
                    created_skus += 1
                has_stock = session.scalar(select(Stock.id).where(Stock.sku_id == sku.id).limit(1))
                if has_stock is None:
                    session.add(Stock(sku_id=sku.id, quantity=15))
                    created_stock += 1
        session.commit()
    print("Демонстрационные данные проверены.")
    print(f"Создано брендов: {created_brands}")
    print(f"Создано парфюмов: {created_perfumes}")
    print(f"Создано SKU: {created_skus}")
    print(f"Создано складских записей: {created_stock}")


if __name__ == "__main__":
    main()
