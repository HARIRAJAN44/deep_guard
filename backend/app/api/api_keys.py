"""
API Keys management routes.
"""
from typing import Optional

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.api_key import APIKeyCreate, APIKeyResponse
from app.services.api_key_service import (
    create_api_key,
    delete_api_key,
    get_api_key_by_id,
    list_api_keys,
    revoke_api_key,
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api-keys", tags=["API Keys"])
security = HTTPBearer()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description=(
        "Creates a new API key. The full key is returned ONCE — store it securely. "
        "You must explicitly choose a data retention policy and model improvement consent."
    ),
)
async def create_key(
    data: APIKeyCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    user = await get_current_user(credentials.credentials)
    result = await create_api_key(user.id, data)
    return {"success": True, "data": result.model_dump()}


@router.get(
    "/",
    summary="List API keys",
    description="Returns all API keys for the authenticated user. Full keys are never revealed.",
)
async def list_keys(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = await get_current_user(credentials.credentials)
    keys = await list_api_keys(user.id)
    return {"success": True, "data": [k.model_dump() for k in keys]}


@router.get(
    "/{key_id}",
    summary="Get API key details",
)
async def get_key(key_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = await get_current_user(credentials.credentials)
    key = await get_api_key_by_id(key_id, user.id)
    return {"success": True, "data": key.model_dump()}


@router.post(
    "/{key_id}/revoke",
    summary="Revoke an API key",
    description="Permanently disables an API key. Cannot be undone.",
)
async def revoke_key(key_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = await get_current_user(credentials.credentials)
    await revoke_api_key(key_id, user.id)
    return {"success": True, "data": {"message": "API key revoked successfully."}}


@router.delete(
    "/{key_id}",
    summary="Delete an API key",
    description="Permanently removes an API key record.",
)
async def delete_key(key_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = await get_current_user(credentials.credentials)
    await delete_api_key(key_id, user.id)
    return {"success": True, "data": {"message": "API key deleted."}}
