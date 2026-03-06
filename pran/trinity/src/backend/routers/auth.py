"""
Authentication routes for the Trinity backend.
"""
import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
import redis

from models import Token
from config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    EMAIL_AUTH_ENABLED,
    REDIS_URL,
)
from database import db
from dependencies import authenticate_user, create_access_token

logger = logging.getLogger(__name__)

# Rate limiting configuration for admin login (M-005)
LOGIN_RATE_LIMIT = 5  # Max attempts
LOGIN_RATE_WINDOW = 600  # 10 minutes in seconds

# Redis client for rate limiting
_redis_client = None

def get_redis_client():
    """Get or create Redis client for rate limiting."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis unavailable for rate limiting: {e}")
            return None
    return _redis_client


def check_login_rate_limit(client_ip: str) -> bool:
    """
    Check if login attempts from IP are within rate limit.
    Returns True if allowed, raises HTTPException if rate limited.

    Security fix M-005: Prevents brute force attacks on admin login.
    """
    r = get_redis_client()
    if r is None:
        # Redis unavailable - allow login but log warning
        logger.warning("Rate limiting unavailable - Redis not connected")
        return True

    key = f"login_attempts:{client_ip}"
    try:
        attempts = r.get(key)
        if attempts and int(attempts) >= LOGIN_RATE_LIMIT:
            ttl = r.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts. Try again in {ttl} seconds."
            )
        return True
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")
        return True


def record_login_attempt(client_ip: str, success: bool):
    """
    Record a login attempt. Failed attempts increment counter.
    Successful logins clear the counter.
    """
    r = get_redis_client()
    if r is None:
        return

    key = f"login_attempts:{client_ip}"
    try:
        if success:
            # Clear attempts on successful login
            r.delete(key)
        else:
            # Increment failed attempts
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, LOGIN_RATE_WINDOW)
            pipe.execute()
    except Exception as e:
        logger.warning(f"Failed to record login attempt: {e}")


def is_setup_completed() -> bool:
    """Check if initial setup is completed."""
    return db.get_setting_value('setup_completed', 'false') == 'true'

router = APIRouter()


@router.get("/api/auth/mode")
async def get_auth_mode():
    """
    Get authentication mode configuration.

    This endpoint requires NO authentication - it's called before login
    to determine which login options to show.

    Returns:
        - email_auth_enabled: Whether email-based login is enabled
        - setup_completed: Whether first-time setup is complete
    """
    # Check if email auth is enabled (can be overridden via settings)
    email_auth_setting = db.get_setting_value("email_auth_enabled", str(EMAIL_AUTH_ENABLED).lower())
    email_auth_enabled = email_auth_setting.lower() == "true"

    return {
        "email_auth_enabled": email_auth_enabled,
        "setup_completed": is_setup_completed()
    }


@router.post("/token", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Login with username/password and get JWT token.

    Used for admin login (username 'admin' with password).
    Regular users should use email authentication.

    Rate limited: 5 attempts per 10 minutes per IP (M-005).
    """
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limit before processing (M-005)
    check_login_rate_limit(client_ip)

    # Block login if setup is not completed
    if not is_setup_completed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="setup_required"
        )

    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        # Record failed attempt
        record_login_attempt(client_ip, success=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Record successful login (clears attempt counter)
    record_login_attempt(client_ip, success=True)

    # Update last login timestamp
    db.update_last_login(user["username"])

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=access_token_expires,
        mode="admin"  # Mark as admin login token
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/api/token", response_model=Token)
async def login_api(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Alias for /token endpoint."""
    return await login(request, form_data)


@router.get("/api/auth/validate")
async def validate_token(request: Request):
    """
    Validate JWT token for nginx auth_request.
    Returns 200 if valid, 401 if invalid.

    Accepts token via:
    - Authorization header: Bearer <token>
    - Cookie: token=<token>
    - Query param: ?token=<token>
    """
    token = None

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]

    if not token:
        token = request.cookies.get("token")

    if not token:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user = db.get_user_by_username(username) if username else None
        if username is None or user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return {"status": "valid", "user": username}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )


# =========================================================================
# Email-Based Authentication Endpoints (Phase 12.4)
# =========================================================================

@router.post("/api/auth/email/request")
async def request_email_login_code(request: Request):
    """
    Request a login code via email.

    Unauthenticated endpoint. Sends a 6-digit code to the provided email
    if it's in the whitelist.

    Rate limit: 3 requests per 10 minutes per email.
    """
    from database import EmailLoginRequest
    from services.email_service import EmailService

    # Block if setup is not completed
    if not is_setup_completed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="setup_required"
        )

    # Check if email auth is enabled
    email_auth_setting = db.get_setting_value("email_auth_enabled", str(EMAIL_AUTH_ENABLED).lower())
    if email_auth_setting.lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email authentication is disabled"
        )

    # Parse request
    body = await request.json()
    login_request = EmailLoginRequest(**body)
    email = login_request.email.lower()

    # Check if email is whitelisted
    if not db.is_email_whitelisted(email):
        # For security, return generic message (don't reveal if email is whitelisted)
        # Return success to prevent email enumeration
        return {"success": True, "message": "If your email is registered, you'll receive a code shortly"}

    # Check rate limit
    recent_requests = db.count_recent_code_requests(email, minutes=10)
    if recent_requests >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again in 10 minutes"
        )

    # Generate code
    code_data = db.create_login_code(email, expiry_minutes=10)

    # Send email
    email_service = EmailService()
    success = await email_service.send_verification_code(email, code_data["code"])

    return {
        "success": True,
        "message": "Verification code sent to your email",
        "expires_in_seconds": code_data["expires_in_seconds"]
    }


@router.post("/api/auth/email/verify")
async def verify_email_login_code(request: Request):
    """
    Verify email login code and get JWT token.

    Unauthenticated endpoint. Verifies the code and creates/returns user session.
    """
    from database import EmailLoginVerify, EmailLoginResponse

    # Block if setup is not completed
    if not is_setup_completed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="setup_required"
        )

    # Check if email auth is enabled
    email_auth_setting = db.get_setting_value("email_auth_enabled", str(EMAIL_AUTH_ENABLED).lower())
    if email_auth_setting.lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email authentication is disabled"
        )

    # Parse request
    body = await request.json()
    verify_request = EmailLoginVerify(**body)
    email = verify_request.email.lower()
    code = verify_request.code

    # Verify code
    verification = db.verify_login_code(email, code)
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired verification code"
        )

    # Get or create user
    user = db.get_or_create_email_user(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )

    # Update last login
    db.update_last_login(user["username"])

    # Create JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=access_token_expires,
        mode="email"  # Mark as email auth token
    )

    return EmailLoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "name": user.get("name"),
            "picture": user.get("picture")
        }
    )
