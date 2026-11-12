"""OpenAPI 3 specification and Swagger UI for AromaSys."""
from flask import Blueprint, Response, jsonify

docs_bp = Blueprint('docs', __name__)

BASE = {
 'openapi':'3.0.3',
 'info':{'title':'AromaSys API','version':'2.0.0','description':'REST API магазина AromaSys. CRUD, Pydantic-валидация, поиск, фильтрация, сортировка и авторизация Bearer token.'},
 'servers':[{'url':'http://127.0.0.1:5000','description':'Локальный сервер'}],
 'tags':[{'name':'Auth'},{'name':'Catalog'},{'name':'Users'},{'name':'Brands'},{'name':'Perfumes'},{'name':'SKU'},{'name':'Stock'},{'name':'Orders'},{'name':'Order items'},{'name':'Favorites'},{'name':'System'}],
 'components':{
  'securitySchemes':{'BearerAuth':{'type':'http','scheme':'bearer','bearerFormat':'Signed token'}},
  'schemas':{
   'Error':{'type':'object','properties':{'error':{'type':'string'},'details':{'type':'array','items':{'type':'object'}}}},
   'UserCreate':{'type':'object','required':['username','email','password'],'properties':{'username':{'type':'string','minLength':2},'email':{'type':'string','format':'email'},'password':{'type':'string','minLength':8}}},
   'ProfileUpdate':{'type':'object','properties':{'username':{'type':'string','minLength':2,'maxLength':80},'delivery_address':{'type':'string','maxLength':500},'avatar':{'type':'string','enum':['pr1.jpg','pr2.jpg','pr3.jpg']}}},
   'CheckoutCreate':{'type':'object','required':['sku_id','quantity','delivery_address'],'properties':{'sku_id':{'type':'integer','minimum':1},'quantity':{'type':'integer','minimum':1,'maximum':99},'delivery_address':{'type':'string','minLength':5,'maxLength':500}}},
   'BrandCreate':{'type':'object','required':['name'],'properties':{'name':{'type':'string','minLength':1}}},
   'PerfumeCreate':{'type':'object','required':['brand_id','title','gender','concentration','release_year'],'properties':{'brand_id':{'type':'integer'},'title':{'type':'string'},'gender':{'type':'string','enum':['Мужские','Женские','Унисекс']},'concentration':{'type':'string','enum':['Parfum','Extrait de Parfum','Eau de Parfum','Eau de Toilette','Eau de Cologne']},'release_year':{'type':'integer','minimum':1900,'maximum':2100}}},
   'SKUCreate':{'type':'object','required':['perfume_id','volume_ml','price'],'properties':{'perfume_id':{'type':'integer'},'volume_ml':{'type':'integer','minimum':1,'maximum':1000},'price':{'type':'number','exclusiveMinimum':0}}},
   'StockCreate':{'type':'object','required':['sku_id','quantity'],'properties':{'sku_id':{'type':'integer'},'quantity':{'type':'integer','minimum':0}}},
   'OrderCreate':{'type':'object','required':['user_id','total_amount'],'properties':{'user_id':{'type':'integer'},'status':{'type':'string','enum':['new','processing','shipped','completed','cancelled']},'total_amount':{'type':'number','minimum':0},'delivery_address':{'type':'string','maxLength':500}}},
   'OrderItemCreate':{'type':'object','required':['order_id','sku_id','price','quantity'],'properties':{'order_id':{'type':'integer'},'sku_id':{'type':'integer'},'price':{'type':'number','exclusiveMinimum':0},'quantity':{'type':'integer','minimum':1}}},
   'CatalogItemUpdate':{'type':'object','properties':{'brand':{'type':'string'},'title':{'type':'string'},'gender':{'type':'string','enum':['Мужские','Женские','Унисекс']},'concentration':{'type':'string'},'release_year':{'type':'integer'},'volume_ml':{'type':'integer'},'price':{'type':'number'},'stock':{'type':'integer'}}},
   'CatalogItemCreate':{'type':'object','required':['brand','title','gender','concentration','release_year','volume_ml','price','stock'],'properties':{'brand':{'type':'string'},'title':{'type':'string'},'gender':{'type':'string','enum':['Мужские','Женские','Унисекс']},'concentration':{'type':'string','enum':['Parfum','Extrait de Parfum','Eau de Parfum','Eau de Toilette','Eau de Cologne']},'release_year':{'type':'integer'},'volume_ml':{'type':'integer'},'price':{'type':'number'},'stock':{'type':'integer'}}},
  }
 }
}

def ref(name): return {'$ref':f'#/components/schemas/{name}'}
def body(name): return {'required':True,'content':{'application/json':{'schema':ref(name)}}}
def responses(description='Операция выполнена'):
 return {'200':{'description':description},'201':{'description':'Создано'},'204':{'description':'Удалено'},'401':{'description':'Не авторизован','content':{'application/json':{'schema':ref('Error')}}},'403':{'description':'Недостаточно прав','content':{'application/json':{'schema':ref('Error')}}},'404':{'description':'Не найдено','content':{'application/json':{'schema':ref('Error')}}},'409':{'description':'Конфликт данных','content':{'application/json':{'schema':ref('Error')}}},'422':{'description':'Ошибка валидации','content':{'application/json':{'schema':ref('Error')}}}}

PATHS={
 '/health':{'get':{'tags':['System'],'summary':'Проверка сервера и PostgreSQL','responses':{'200':{'description':'Сервис доступен'},'503':{'description':'База недоступна'}}}},
 '/register':{'post':{'tags':['Auth'],'summary':'Регистрация','requestBody':body('UserCreate'),'responses':{'201':{'description':'Пользователь создан'},'409':{'description':'Email или имя заняты'},'422':{'description':'Ошибка валидации'}}}},
 '/login':{'post':{'tags':['Auth'],'summary':'Вход, возвращает Bearer token','requestBody':{'required':True,'content':{'application/json':{'schema':{'type':'object','required':['email','password'],'properties':{'email':{'type':'string'},'password':{'type':'string'}}}}}},'responses':{'200':{'description':'Вход выполнен'},'401':{'description':'Неверные данные'}}}},
 '/api/profile':{'patch':{'tags':['Auth'],'summary':'Изменить ник, адрес доставки и фото текущего пользователя','security':[{'BearerAuth':[]}],'requestBody':body('ProfileUpdate'),'responses':responses('Профиль сохранён')}},
 '/api/checkout':{'post':{'tags':['Orders'],'summary':'Оформить заказ, добавить позицию и зарезервировать остаток одной транзакцией','security':[{'BearerAuth':[]}],'requestBody':body('CheckoutCreate'),'responses':responses('Заказ оформлен')}},
 '/catalog':{'get':{'tags':['Catalog'],'summary':'Каталог с поиском, фильтром, сортировкой и пагинацией','parameters':[{'name':'q','in':'query','schema':{'type':'string'}},{'name':'gender','in':'query','schema':{'type':'string','enum':['Мужские','Женские','Унисекс']}},{'name':'sort','in':'query','schema':{'type':'string','enum':['title','brand','price','year','volume']}},{'name':'order','in':'query','schema':{'type':'string','enum':['asc','desc']}},{'name':'page','in':'query','schema':{'type':'integer'}},{'name':'per_page','in':'query','schema':{'type':'integer'}}],'responses':{'200':{'description':'Список товаров'},'422':{'description':'Некорректные параметры'}}}},
 '/api/catalog-items':{'post':{'tags':['Catalog'],'summary':'Создать товар каталога вместе с SKU и остатком','security':[{'BearerAuth':[]}],'requestBody':body('CatalogItemCreate'),'responses':responses('Товар создан')}},
 '/api/catalog-items/{sku_id}':{'patch':{'tags':['Catalog'],'summary':'Изменить товар каталога','security':[{'BearerAuth':[]}],'parameters':[{'name':'sku_id','in':'path','required':True,'schema':{'type':'integer'}}],'requestBody':{'required':True,'content':{'application/json':{'schema':{'$ref':'#/components/schemas/CatalogItemUpdate'}}}},'responses':responses()},'delete':{'tags':['Catalog'],'summary':'Удалить SKU каталога','security':[{'BearerAuth':[]}],'parameters':[{'name':'sku_id','in':'path','required':True,'schema':{'type':'integer'}}],'responses':responses()}},
 '/favorites':{'post':{'tags':['Favorites'],'summary':'Добавить товар в избранное','security':[{'BearerAuth':[]}],'requestBody':{'required':True,'content':{'application/json':{'schema':{'type':'object','required':['user_id','sku_id'],'properties':{'user_id':{'type':'integer'},'sku_id':{'type':'integer'}}}}}},'responses':responses()}},
 '/favorites/{user_id}':{'get':{'tags':['Favorites'],'summary':'Получить избранное пользователя','security':[{'BearerAuth':[]}],'parameters':[{'name':'user_id','in':'path','required':True,'schema':{'type':'integer'}}],'responses':{'200':{'description':'Список избранного'},'403':{'description':'Нет доступа'}}}},
 '/favorites/{user_id}/{sku_id}':{'delete':{'tags':['Favorites'],'summary':'Удалить товар из избранного','security':[{'BearerAuth':[]}],'parameters':[{'name':'user_id','in':'path','required':True,'schema':{'type':'integer'}},{'name':'sku_id','in':'path','required':True,'schema':{'type':'integer'}}],'responses':responses()}},
 '/api/favorites':{'get':{'tags':['Favorites'],'summary':'Получить избранное текущего пользователя','security':[{'BearerAuth':[]}],'responses':{'200':{'description':'Избранное'}}}},
}

CRUD=[('users','Users','UserCreate'),('brands','Brands','BrandCreate'),('perfumes','Perfumes','PerfumeCreate'),('skus','SKU','SKUCreate'),('stock','Stock','StockCreate'),('orders','Orders','OrderCreate'),('order-items','Order items','OrderItemCreate')]
for path,tag,schema in CRUD:
 auth=[{'BearerAuth':[]}]
 PATHS[f'/api/{path}']={
  'get':{'tags':[tag],'summary':f'Получить список: {path}','security':auth,'responses':{'200':{'description':'Список записей'},'401':{'description':'Не авторизован'}}},
  'post':{'tags':[tag],'summary':f'Создать запись: {path}','security':auth,'requestBody':body(schema),'responses':responses('Запись создана')}}
 PATHS[f'/api/{path}/{{item_id}}']={
  'get':{'tags':[tag],'summary':f'Получить запись: {path}','security':auth,'parameters':[{'name':'item_id','in':'path','required':True,'schema':{'type':'integer'}}],'responses':responses()},
  'put':{'tags':[tag],'summary':f'Полностью обновить запись: {path}','security':auth,'parameters':[{'name':'item_id','in':'path','required':True,'schema':{'type':'integer'}}],'requestBody':body(schema),'responses':responses()},
  'patch':{'tags':[tag],'summary':f'Частично обновить запись: {path}','security':auth,'parameters':[{'name':'item_id','in':'path','required':True,'schema':{'type':'integer'}}],'requestBody':{'required':True,'content':{'application/json':{'schema':{'type':'object','additionalProperties':True}}}},'responses':responses()},
  'delete':{'tags':[tag],'summary':f'Удалить запись: {path}','security':auth,'parameters':[{'name':'item_id','in':'path','required':True,'schema':{'type':'integer'}}],'responses':responses()}}

OPENAPI_SPEC={**BASE,'paths':PATHS}
SWAGGER_HTML='''<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AromaSys API</title><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"></head><body><div id="swagger-ui"></div><script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script><script>window.onload=()=>SwaggerUIBundle({url:'/openapi.json',dom_id:'#swagger-ui',deepLinking:true,tryItOutEnabled:true,displayRequestDuration:true,persistAuthorization:true});</script></body></html>'''

@docs_bp.get('/openapi.json')
def openapi_json(): return jsonify(OPENAPI_SPEC)
@docs_bp.get('/docs')
def swagger_ui(): return Response(SWAGGER_HTML,mimetype='text/html')
def register_docs(app): app.register_blueprint(docs_bp)
