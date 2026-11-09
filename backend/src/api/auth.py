"""Supabase access-token verification for the FastAPI application."""

from dataclasses import dataclass

import requests
from fastapi import Header, HTTPException

from config import SUPABASE_PUBLISHABLE_KEY, SUPABASE_URL


@dataclass(frozen=True)
class AuthenticatedUser:
    """Identity and trusted application role returned by Supabase Auth."""

    user_id: str
    email: str | None
    app_role: str


def get_authenticated_user(
    authorization: str | None = Header(default=None),
) -> AuthenticatedUser:
    """Verify a bearer token with Supabase Auth and return trusted user claims."""
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise HTTPException(
            status_code=503,
            detail="Supabase authentication is not configured on the backend.",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to use this endpoint.")

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Sign in to use this endpoint.")

    try:
        response = requests.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": SUPABASE_PUBLISHABLE_KEY,
                "Authorization": f"Bearer {token}",
            },
            timeout=8,
        )
    except requests.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail="Could not validate the Supabase session.",
        ) from error

    if response.status_code in (401, 403):
        raise HTTPException(status_code=401, detail="Your session is invalid or expired.")
    if not response.ok:
        raise HTTPException(status_code=503, detail="Could not validate the Supabase session.")

    try:
        user = response.json()
    except ValueError as error:
        raise HTTPException(status_code=503, detail="Supabase returned an invalid user record.") from error

    if not isinstance(user, dict) or not user.get("id"):
        raise HTTPException(status_code=401, detail="Your session is invalid or expired.")

    app_metadata = user.get("app_metadata")
    app_role = app_metadata.get("app_role") if isinstance(app_metadata, dict) else None
    if not isinstance(app_role, str) or not app_role.strip():
        app_role = "member"

    return AuthenticatedUser(
        user_id=str(user["id"]),
        email=user.get("email") if isinstance(user.get("email"), str) else None,
        app_role=app_role,
    )
