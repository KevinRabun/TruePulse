"""
Passkey (WebAuthn/FIDO2) API endpoints.

Provides endpoints for passkey registration, authentication, and management.
All passkey operations require phone verification for credential binding.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from models.user import User
from services.passkey_service import (
    ChallengeExpiredError,
    PasskeyAuthenticationError,
    PasskeyError,
    PasskeyRegistrationError,
    get_passkey_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passkeys", tags=["passkeys"])


# --- Request/Response Models ---


class DeviceInfo(BaseModel):
    """Device information for trust scoring."""

    fingerprint: str | None = Field(None, description="Device fingerprint hash")
    platform: str | None = Field(None, description="Platform (Windows, macOS, iOS, Android)")
    browser: str | None = Field(None, description="Browser name")
    screen_resolution: str | None = Field(None, description="Screen resolution")
    timezone: str | None = Field(None, description="Timezone")


class RegistrationOptionsRequest(BaseModel):
    """Request for passkey registration options."""

    device_info: DeviceInfo | None = None


class RegistrationOptionsResponse(BaseModel):
    """Response with WebAuthn registration options."""

    challenge_id: str = Field(..., alias="challengeId")
    rp: dict
    user: dict
    challenge: str
    pub_key_cred_params: list = Field(..., alias="pubKeyCredParams")
    timeout: int
    attestation: str
    exclude_credentials: list = Field(..., alias="excludeCredentials")
    authenticator_selection: dict = Field(..., alias="authenticatorSelection")

    class Config:
        populate_by_name = True


class RegistrationVerifyRequest(BaseModel):
    """Request to verify passkey registration."""

    challenge_id: str = Field(..., alias="challengeId")
    credential: str = Field(..., description="JSON-encoded WebAuthn credential")
    credential_name: str | None = Field(None, alias="deviceName", description="Friendly name for the passkey")

    class Config:
        populate_by_name = True


class AuthenticationOptionsRequest(BaseModel):
    """Request for passkey authentication options."""

    email: str | None = Field(None, description="Email for non-discoverable flow (optional)")
    device_info: DeviceInfo | None = None


class AuthenticationOptionsResponse(BaseModel):
    """Response with WebAuthn authentication options."""

    challenge_id: str = Field(..., alias="challengeId")
    rp_id: str = Field(..., alias="rpId")
    challenge: str
    timeout: int
    user_verification: str = Field(..., alias="userVerification")
    allow_credentials: list = Field(..., alias="allowCredentials")

    class Config:
        populate_by_name = True


class AuthenticationVerifyRequest(BaseModel):
    """Request to verify passkey authentication."""

    challenge_id: str = Field(..., alias="challengeId")
    credential: str = Field(..., description="JSON-encoded WebAuthn credential")

    class Config:
        populate_by_name = True


class AuthenticationVerifyResponse(BaseModel):
    """Response after successful authentication."""

    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")
    token_type: str = Field(default="bearer", alias="tokenType")
    user: dict

    class Config:
        populate_by_name = True


class PasskeyInfo(BaseModel):
    """Information about a registered passkey."""

    id: str
    credential_name: str = Field(..., alias="deviceName")
    created_at: str = Field(..., alias="createdAt")
    last_used_at: str | None = Field(None, alias="lastUsedAt")
    is_backup_eligible: bool = Field(..., alias="backupEligible")
    is_backed_up: bool = Field(..., alias="backupState")

    class Config:
        populate_by_name = True


class PasskeysListResponse(BaseModel):
    """Response with list of user's passkeys."""

    passkeys: list[PasskeyInfo]


class DeletePasskeyRequest(BaseModel):
    """Request to delete a passkey."""

    passkey_id: str = Field(..., alias="passkeyId")

    class Config:
        populate_by_name = True


# --- Registration Endpoints ---


@router.post("/register/options", response_model=RegistrationOptionsResponse)
async def get_registration_options(
    request: RegistrationOptionsRequest,
    http_request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Get WebAuthn registration options for creating a new passkey.

    Requires:
    - Authenticated user
    - Verified phone number (for credential binding)

    Returns registration options to be passed to `navigator.credentials.create()`.
    """
    try:
        passkey_service = get_passkey_service(db)
        device_info = request.device_info.model_dump() if request.device_info else None

        options = await passkey_service.generate_registration_options(
            user=current_user,
            device_info=device_info,
        )

        return options

    except PasskeyRegistrationError as e:
        logger.warning(f"Registration options error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error generating registration options: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate registration options",
        )


@router.post("/register/verify")
async def verify_registration(
    request: RegistrationVerifyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Verify and store a WebAuthn registration response.

    After the user completes the platform authenticator prompt,
    send the credential response here to complete registration.

    Returns the newly registered passkey information.
    """
    try:
        passkey_service = get_passkey_service(db)

        passkey = await passkey_service.verify_registration(
            user=current_user,
            challenge_id=request.challenge_id,
            credential_json=request.credential,
            credential_name=request.credential_name,
        )

        return {
            "success": True,
            "passkey": {
                "id": passkey.id,
                "deviceName": passkey.credential_name,
                "createdAt": passkey.created_at.isoformat(),
            },
        }

    except ChallengeExpiredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration challenge expired. Please try again.",
        )
    except PasskeyRegistrationError as e:
        logger.warning(f"Registration verification failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error verifying registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify registration",
        )


# --- Authentication Endpoints ---


@router.post("/authenticate/options", response_model=AuthenticationOptionsResponse)
async def get_authentication_options(
    request: AuthenticationOptionsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Get WebAuthn authentication options for signing in with a passkey.

    Can be called in two modes:
    1. With email: Returns options specific to that user's credentials
    2. Without email: Returns options for discoverable credential flow

    Returns authentication options to be passed to `navigator.credentials.get()`.
    """
    from sqlalchemy import select

    try:
        passkey_service = get_passkey_service(db)
        user = None

        # If email provided, look up user's credentials
        if request.email:
            result = await db.execute(select(User).where(User.email == request.email))
            user = result.scalar_one_or_none()
            # Don't reveal if user exists - still return options for security

        device_info = request.device_info.model_dump() if request.device_info else None

        options = await passkey_service.generate_authentication_options(
            user=user,
            device_info=device_info,
        )

        return options

    except Exception as e:
        logger.error(f"Unexpected error generating authentication options: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authentication options",
        )


@router.post("/authenticate/verify", response_model=AuthenticationVerifyResponse)
async def verify_authentication(
    request: AuthenticationVerifyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Verify a WebAuthn authentication response and issue tokens.

    After the user completes the platform authenticator prompt,
    send the credential response here to complete authentication.

    Returns access and refresh tokens on success.
    """
    from core.security import create_access_token, create_refresh_token

    try:
        passkey_service = get_passkey_service(db)

        user, passkey = await passkey_service.verify_authentication(
            challenge_id=request.challenge_id,
            credential_json=request.credential,
        )

        # Update last login
        from datetime import UTC, datetime

        user.last_login_at = datetime.now(UTC)
        await db.commit()

        # Create tokens
        access_token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})

        return {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "tokenType": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "isVerified": user.is_verified,
                "emailVerified": user.email_verified,
                "hasPasskey": True,
                "passkeyOnly": user.passkey_only,
            },
        }

    except ChallengeExpiredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication challenge expired. Please try again.",
        )
    except PasskeyAuthenticationError as e:
        logger.warning(f"Authentication verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Please try again.",
        )
    except Exception as e:
        logger.error(f"Unexpected error verifying authentication: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify authentication",
        )


# --- Management Endpoints ---


@router.get("/", response_model=PasskeysListResponse)
async def list_passkeys(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Get all registered passkeys for the current user.

    Returns a list of passkey information for the management UI.
    """
    try:
        passkey_service = get_passkey_service(db)
        passkeys = await passkey_service.get_user_passkeys(current_user.id)

        return {
            "passkeys": [
                {
                    "id": pk["id"],
                    "deviceName": pk["deviceName"],
                    "createdAt": pk["createdAt"],
                    "lastUsedAt": pk["lastUsedAt"],
                    "backupEligible": pk["backupEligible"],
                    "backupState": pk["backupState"],
                }
                for pk in passkeys
            ]
        }

    except Exception as e:
        logger.error(f"Error listing passkeys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list passkeys",
        )


@router.delete("/{passkey_id}")
async def delete_passkey(
    passkey_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Delete a registered passkey.

    Users cannot delete their last passkey if they are using passkey-only authentication.
    """
    try:
        passkey_service = get_passkey_service(db)

        deleted = await passkey_service.delete_passkey(
            user=current_user,
            passkey_id=passkey_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Passkey not found",
            )

        return {"success": True, "message": "Passkey deleted successfully"}

    except PasskeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting passkey: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete passkey",
        )
