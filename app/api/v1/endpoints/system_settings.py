from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.api.deps import  get_super_admin, check_admin_permission
from app.db.database import get_db
from app.models.system_settings import SystemSettings
from app.schemas.system_settings import (
    SystemSettingsCreate,
    SystemSettingsUpdate,
    SystemSettingsResponse
)
from app.schemas.base import BaseResponse, MessageResponse
from app.services.audit_logger import audit_create

router = APIRouter()


@router.get("/", response_model=BaseResponse[List[SystemSettingsResponse]])
async def get_system_settings(
    category: Optional[str] = None,
    is_public: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_manage_system_settings"))
):
    """Get system settings"""
    query = select(SystemSettings)
    
    if category:
        query = query.where(SystemSettings.category == category)
    
    if is_public is not None:
        query = query.where(SystemSettings.is_public == is_public)
    
    query = query.order_by(SystemSettings.category, SystemSettings.key)
    
    result = await db.execute(query)
    settings = result.scalars().all()
    
    return BaseResponse.success_response(data=settings, message="System settings retrieved successfully")


@router.get("/{key}", response_model=BaseResponse[SystemSettingsResponse])
async def get_system_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_manage_system_settings"))
):
    """Get specific system setting"""
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System setting not found"
        )
    
    return BaseResponse.success_response(data=setting, message="System setting retrieved successfully")


@router.post("/", response_model=BaseResponse[SystemSettingsResponse])
@audit_create("system_settings")
async def create_system_setting(
    setting_data: SystemSettingsCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_super_admin)
):
    """Create new system setting (super admin only)"""
    # Check if setting already exists
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == setting_data.key))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System setting with this key already exists"
        )
    
    setting = SystemSettings(
        key=setting_data.key,
        value=setting_data.value,
        description=setting_data.description,
        category=setting_data.category,
        is_public=setting_data.is_public,
        updated_by=current_admin.id
    )
    
    db.add(setting)
    await db.commit()
    await db.refresh(setting)
    
    return BaseResponse.success_response(data=setting, message="System setting created successfully")


@router.put("/{key}", response_model=BaseResponse[SystemSettingsResponse])
async def update_system_setting(
    key: str,
    setting_update: SystemSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_manage_system_settings"))
):
    """Update system setting"""
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System setting not found"
        )
    
    # Update fields
    for field, value in setting_update.dict(exclude_unset=True).items():
        setattr(setting, field, value)
    
    setting.updated_by = current_admin.id
    
    await db.commit()
    await db.refresh(setting)
    
    return BaseResponse.success_response(data=setting, message="System setting updated successfully")


@router.delete("/{key}", response_model=MessageResponse)
async def delete_system_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_super_admin)
):
    """Delete system setting (super admin only)"""
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System setting not found"
        )
    
    await db.delete(setting)
    await db.commit()
    
    return MessageResponse(message="System setting deleted successfully")


@router.get("/categories/list", response_model=BaseResponse[List[str]])
async def get_setting_categories(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_manage_system_settings"))
):
    """Get all setting categories"""
    result = await db.execute(
        select(SystemSettings.category).distinct().order_by(SystemSettings.category)
    )
    categories = [row[0] for row in result.fetchall()]
    
    return BaseResponse.success_response(data=categories, message="Setting categories retrieved successfully")


@router.post("/bulk-update", response_model=BaseResponse[List[SystemSettingsResponse]])
async def bulk_update_settings(
    settings_data: List[dict],
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_manage_system_settings"))
):
    """Bulk update multiple settings"""
    updated_settings = []
    
    for setting_data in settings_data:
        key = setting_data.get('key')
        value = setting_data.get('value')
        
        if not key:
            continue
            
        result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.value = value
            setting.updated_by = current_admin.id
            updated_settings.append(setting)
    
    await db.commit()
    
    for setting in updated_settings:
        await db.refresh(setting)
    
    return BaseResponse.success_response(data=updated_settings, message="Settings updated successfully")
