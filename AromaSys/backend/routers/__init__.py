from .auth_router import auth_bp
from .catalog_router import catalog_bp
from .favorite_router import favorite_bp
from .health_router import health_bp
from .crud_router import register_crud_routes

__all__ = [
    "auth_bp",
    "catalog_bp",
    "favorite_bp",
    "health_bp",
    "register_crud_routes",
]
