import os
import re
import asyncio
from ldap3 import Server, Connection, ALL
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from database.db_helper import db

LDAP_SERVER = os.getenv("LDAP_SERVER")
LDAP_BASE_DN = os.getenv("LDAP_BASE_DN")
LDAP_USER_DN_TEMPLATE = os.getenv("LDAP_USER_DN_TEMPLATE")
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

async def authenticate_user(username: str, password: str) -> Optional[str]:
    # Sanitize username to prevent LDAP injection
    sanitized_username = re.sub(r'[()\*\\/]', '', username)

    # 1. Try Local User Fallback first (highest priority for recovery/local admin)
    local_user = await db.get_local_user(sanitized_username)
    if local_user:
        if pwd_context.verify(password, local_user["hashed_password"]):
            return sanitized_username

    # 2. Try LDAP if configured
    if LDAP_SERVER:
        server = Server(LDAP_SERVER, get_info=ALL)
        user_dn = LDAP_USER_DN_TEMPLATE.format(username=sanitized_username)
        try:
            # Run blocking LDAP call in a thread pool to avoid blocking async loop
            loop = asyncio.get_event_loop()
            bound = await loop.run_in_executor(None, lambda: _ldap_bind(server, user_dn, password))
            if bound:
                return sanitized_username
        except Exception:
            pass

    return None

def _ldap_bind(server, user_dn, password):
    try:
        conn = Connection(server, user=user_dn, password=password, check_names=True, lazy=False, raise_exceptions=True)
        conn.bind()
        return True
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    return username
