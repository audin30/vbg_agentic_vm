import os
from ldap3 import Server, Connection, ALL
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

LDAP_SERVER = os.getenv("LDAP_SERVER")
LDAP_BASE_DN = os.getenv("LDAP_BASE_DN")
LDAP_USER_DN_TEMPLATE = os.getenv("LDAP_USER_DN_TEMPLATE")
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

def authenticate_user(username: str, password: str) -> Optional[str]:
    # In a real environment, this connects to the Domain Controller
    # For testing/mocking purposes, we'll handle the logic
    if not LDAP_SERVER:
        return None
    server = Server(LDAP_SERVER, get_info=ALL)
    user_dn = LDAP_USER_DN_TEMPLATE.format(username=username)
    try:
        conn = Connection(server, user=user_dn, password=password, check_names=True, lazy=False, raise_exceptions=True)
        conn.bind()
        return username
    except Exception:
        return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
