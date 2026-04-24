# Phase 3: PostgreSQL Knowledge Cache and Identity-linked Auditing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement persistent storage for audit logs, shared knowledge cache, and user-linked query state using PostgreSQL.

**Architecture:** Use `asyncpg` or `SQLAlchemy` (check existing usage) for database interactions in the FastAPI backend. Implement a `SensitiveDataFilter` decorator/middleware for all database writes to ensure PII masking. The Knowledge Cache will store results of IP/Domain/Hash lookups with a TTL.

**Tech Stack:** FastAPI, PostgreSQL, asyncpg, JWT, Pydantic.

---

### Task 1: Database Schema Migration

**Files:**
- Create: `backend/database/schema.sql`
- Create: `backend/database/init_db.py`

- [ ] **Step 1: Define the SQL schema**

Create `backend/database/schema.sql`:
```sql
-- Identity-linked Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    action TEXT NOT NULL,
    request_data JSONB,
    response_summary TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge Cache for TI Lookups
CREATE TABLE IF NOT EXISTS knowledge_cache (
    indicator TEXT PRIMARY KEY,
    indicator_type TEXT NOT NULL,
    cached_result JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Persistent User Active Queries (Tabs)
CREATE TABLE IF NOT EXISTS user_active_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    title TEXT NOT NULL,
    query_state JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

- [ ] **Step 2: Create DB initialization script**

Create `backend/database/init_db.py` to run the schema.

- [ ] **Step 3: Run the initialization**

Run: `python backend/database/init_db.py`
Expected: Tables created in PostgreSQL.

- [ ] **Step 4: Commit**

```bash
git add backend/database/
git commit -m "feat: add PostgreSQL schema for audit, cache, and queries"
```

---

### Task 2: Implement Database Helper in Backend

**Files:**
- Create: `backend/database/db_helper.py`

- [ ] **Step 1: Implement async database connection pool**

Use `asyncpg` to manage a connection pool.

- [ ] **Step 2: Implement Audit Logger function**

```python
async def log_audit(username: str, action: str, request_data: dict, response_summary: str):
    # Mask data before logging
    # ... logic here ...
    pass
```

- [ ] **Step 3: Commit**

```bash
git add backend/database/db_helper.py
git commit -m "feat: implement database helper with audit logging"
```

---

### Task 3: Integrate Identity-linked Auditing

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Replace file-based logging with DB auditing in /api/orchestrate**

- [ ] **Step 2: Update /api/queries to persist tabs to user_active_queries**

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: integrate identity-linked DB auditing and persistent tabs"
```

---

### Task 4: Knowledge Cache Implementation

**Files:**
- Modify: `backend/crew.py` or `backend/tools.py`

- [ ] **Step 1: Implement cache lookup before tool execution**

- [ ] **Step 2: Implement cache update after tool execution**

- [ ] **Step 3: Commit**

```bash
git add backend/crew.py
git commit -m "feat: implement TI knowledge cache logic"
```

---

### Task 5: Frontend Persistence Sync

**Files:**
- Modify: `frontend/src/store/useTabStore.ts`
- Modify: `frontend/src/hooks/useStreamingResponse.ts`

- [ ] **Step 1: Update useTabStore to fetch initial state from /api/users/me/tabs**

- [ ] **Step 2: Ensure tab closing updates the DB via DELETE /api/queries/:id**

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "feat: sync frontend tab state with persistent backend"
```
