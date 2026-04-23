# Centralized Security Hub - Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Domain-based authentication (LDAP/AD) and containerize the Security Orchestrator for centralized deployment.

**Architecture:** Use FastAPI middleware for JWT-based authentication linked to an internal LDAP server. The system is containerized via Docker Compose, including the Python backend, Node.js skills runtime, and a PostgreSQL database.

**Tech Stack:** FastAPI, python-jose (JWT), ldap3, Docker, PostgreSQL.

---

### Task 1: Environment & Dependency Setup

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add authentication and LDAP dependencies**

```text
python-jose[cryptography]
passlib[bcrypt]
ldap3
python-multipart
```

- [ ] **Step 2: Install dependencies in the venv**

Run: `source backend/venv/bin/activate && pip install -r backend/requirements.txt`
Expected: Successful installation of new packages.

- [ ] **Step 3: Update .env.example with Auth variables**

Modify `backend/.env.example`:
```env
LDAP_SERVER=ldap://your-domain-controller
LDAP_BASE_DN=dc=example,dc=com
LDAP_USER_DN_TEMPLATE=uid={username},ou=users,dc=example,dc=com
JWT_SECRET_KEY=generate-a-secure-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt backend/.env.example
git commit -m "chore: add auth and ldap dependencies"
```

---

### Task 2: LDAP Authentication Module

**Files:**
- Create: `backend/auth.py`
- Test: `tests/backend/test_auth.py`

- [ ] **Step 1: Write failing test for LDAP authentication**

```python
import pytest
from auth import authenticate_user

def test_authenticate_user_invalid_creds():
    # Mocking would be needed for real LDAP, testing failure for now
    assert authenticate_user("fake_user", "wrong_password") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_auth.py`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement LDAP authentication logic**

```python
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
    # For testing/mocking purposes, we'll implement the structure
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
```

- [ ] **Step 4: Run test to verify it passes (with mocking)**

Run: `pytest tests/backend/test_auth.py` (ensure LDAP_SERVER is mocked or dummy provided)
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/auth.py tests/backend/test_auth.py
git commit -m "feat: implement LDAP authentication and JWT token generation"
```

---

### Task 3: Secure FastAPI Gateway

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add Login endpoint and Security Middleware**

```python
from fastapi import Depends, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from auth import authenticate_user, create_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user})
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Verify JWT and return user
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

- [ ] **Step 2: Update /api/orchestrate to require authentication**

```python
@app.post("/api/orchestrate")
async def orchestrate(request: OrchestrationRequest, current_user: str = Depends(get_current_user)):
    logger.info(f"AUDIT - User [{current_user}] requested orchestration: {request}")
    # ... rest of the logic
```

- [ ] **Step 3: Verify endpoint protection**

Run: `curl -X POST http://localhost:8000/api/orchestrate`
Expected: 401 Unauthorized

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: secure orchestrate endpoint with JWT and identity-linked logging"
```

---

### Task 4: Dockerization of the Hub

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create the Hub Dockerfile**

```dockerfile
FROM python:3.12-slim

# Install Node.js for skills
RUN apt-get update && apt-get install -y nodejs npm curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY alienvault-otx/ ./alienvault-otx/
COPY virustotal-checker/ ./virustotal-checker/
# ... copy other skills needed

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: security_hub
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - backend/.env
    depends_on:
      - db

volumes:
  postgres_data:
```

- [ ] **Step 3: Verify build**

Run: `docker-compose build`
Expected: Successful build of the API image.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: containerize the Security Orchestrator Hub"
```
