-- Демонстрационные данные для каталога AromaSys.
-- Запускай один раз. Скрипт добавляет товары, только если каталог пуст.
-- Картинки лежат в backend/static/ и отдаются по /static/<filename>.

BEGIN;

INSERT INTO brands (name)
SELECT v.name
FROM (VALUES ('Chanel'), ('Dior'), ('Cristiano Ronaldo')) AS v(name)
WHERE NOT EXISTS (SELECT 1 FROM brands WHERE lower(name) = lower(v.name));

INSERT INTO perfumes (brand_id, title, gender, concentration, release_year)
SELECT b.id, v.title, v.gender, v.concentration, v.release_year
FROM (VALUES
    ('Chanel', 'Bleu de Chanel', 'Мужские', 'Eau de Parfum', 2014),
    ('Dior', 'Sauvage', 'Мужские', 'Eau de Parfum', 2015),
    ('Chanel', 'Chanel N°5', 'Женские', 'Eau de Parfum', 1921),
    ('Cristiano Ronaldo', 'Cristiano Ronaldo', 'Мужские', 'Eau de Toilette', 2015)
) AS v(brand_name, title, gender, concentration, release_year)
JOIN brands b ON b.name = v.brand_name
WHERE NOT EXISTS (SELECT 1 FROM perfumes p JOIN brands b2 ON b2.id = p.brand_id
                      WHERE lower(p.title) = lower(v.title) AND lower(b2.name) = lower(v.brand_name));

INSERT INTO skus (perfume_id, volume_ml, price)
SELECT p.id, v.volume_ml, v.price
FROM (VALUES
    ('Bleu de Chanel', 50, 12500.00),
    ('Bleu de Chanel', 100, 16900.00),
    ('Sauvage', 60, 11800.00),
    ('Sauvage', 100, 15400.00),
    ('Chanel N°5', 50, 14200.00),
    ('Chanel N°5', 100, 18900.00),
    ('Cristiano Ronaldo', 50, 4500.00),
    ('Cristiano Ronaldo', 100, 6900.00)
) AS v(title, volume_ml, price)
JOIN perfumes p ON p.title = v.title
WHERE NOT EXISTS (
    SELECT 1 FROM skus s
    WHERE s.perfume_id = p.id AND s.volume_ml = v.volume_ml
);

INSERT INTO stock (sku_id, quantity)
SELECT s.id, 15
FROM skus s
WHERE NOT EXISTS (SELECT 1 FROM stock st WHERE st.sku_id = s.id);

COMMIT;
