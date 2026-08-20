"""Password hashing, JWT issuing, and the dependencies that guard endpoints."""

import os
from datetime import timedelta

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.models import User, get_db, utcnow

load_dotenv()


JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-before-deployment")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain_password):
    return bcrypt.hashpw(
        plain_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(plain_password, password_hash):
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        # A malformed hash in the database must read as "wrong password",
        # never as a server error.
        return False


def create_access_token(user):
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _unauthorized(detail):
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the caller from the Authorization header, or reject with 401."""

    if credentials is None:
        raise _unauthorized("Not authenticated")

    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token has expired")
    except jwt.PyJWTError:
        raise _unauthorized("Invalid token")

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise _unauthorized("Invalid token")

    user = db.get(User, user_id)

    if user is None:
        # The account was deleted after the token was issued.
        raise _unauthorized("Invalid token")

    return user


def require_staff(user: User = Depends(get_current_user)) -> User:
    """Guard for endpoints only Member 5's staff dashboard may call."""

    if user.role != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required",
        )

    return user
