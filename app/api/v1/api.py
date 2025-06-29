from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, transfers, wallets, admin

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(transfers.router, prefix="/transfers", tags=["transfers"])
api_router.include_router(wallets.router, prefix="/wallets", tags=["wallets"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])