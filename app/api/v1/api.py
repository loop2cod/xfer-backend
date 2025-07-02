from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, users, transfers, wallets, admin, admin_wallets, admin_bank_accounts,
    fees, purchases, system_settings, audit_logs, financial_reports
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(transfers.router, prefix="/transfers", tags=["transfers"])
api_router.include_router(wallets.router, prefix="/wallets", tags=["wallets"])

# Admin sub-routes must come before the main admin router to avoid conflicts
api_router.include_router(system_settings.router, prefix="/admin/settings", tags=["system-settings"])
api_router.include_router(audit_logs.router, prefix="/admin/audit-logs", tags=["audit-logs"])
api_router.include_router(financial_reports.router, prefix="/admin/reports", tags=["financial-reports"])

# Main admin router comes after sub-routes
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

api_router.include_router(admin_wallets.router, prefix="/admin-wallets", tags=["admin-wallets"])
api_router.include_router(admin_bank_accounts.router, prefix="/admin-bank-accounts", tags=["admin-bank-accounts"])
api_router.include_router(fees.router, prefix="/fees", tags=["fees"])
api_router.include_router(purchases.router, prefix="/purchases", tags=["purchases"])