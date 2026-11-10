# Укажи email владельца каталога. Это значение проверяется сервером.
# Для production используй переменную окружения AROMASYS_ADMIN_EMAIL.
import os
ADMIN_EMAIL = os.getenv('AROMASYS_ADMIN_EMAIL', 'укажи_email_владельца').strip().lower()
API_SECRET = os.getenv('AROMASYS_API_SECRET', 'CHANGE_THIS_SECRET_BEFORE_DEPLOYMENT')
