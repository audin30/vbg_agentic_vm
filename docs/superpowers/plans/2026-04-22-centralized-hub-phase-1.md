# Centralized Security Hub - Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Domain-based authentication (LDAP/AD) and establish a bare-metal deployment strategy for the Centralized Security Hub.

**Architecture:** Use FastAPI middleware for JWT-based authentication linked to an internal LDAP server. The system is deployed directly on a dedicated Linux host (Host A) using systemd for process management. It connects to an external PostgreSQL server (Host B).

**Tech Stack:** FastAPI, python-jose (JWT), ldap3, systemd, Python 3.12, Node.js 20.x.

---

### Task 1: Environment & Dependency Setup [DONE]
- [x] Step 1: Add authentication and LDAP dependencies to requirements.txt
- [x] Step 2: Install dependencies in the venv
- [x] Step 3: Update .env.example with Auth variables
- [x] Step 4: Commit

### Task 2: LDAP Authentication Module [DONE]
- [x] Step 1: Write failing test for LDAP authentication
- [x] Step 2: Run test to verify it fails
- [x] Step 3: Implement LDAP authentication logic
- [x] Step 4: Run test to verify it passes (with mocking)
- [x] Step 5: Commit

### Task 3: Secure FastAPI Gateway [DONE]
- [x] Step 1: Add Login endpoint and Security Middleware
- [x] Step 2: Update /api/orchestrate to require authentication
- [x] Step 3: Verify endpoint protection (401 response)
- [x] Step 4: Commit

---

### Task 4: Bare Metal Deployment Setup

**Files:**
- Create: `setup_host.sh`
- Create: `vbg-hub.service`

- [ ] **Step 1: Create Host Setup Script**

Create `setup_host.sh` in the root to automate dependency installation for a bare-metal host.

```bash
#!/bin/bash
# setup_host.sh - Prepares Host A for the Security Hub

echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y libldap2-dev libsasl2-dev gcc curl python3.12-venv python3.12-dev

echo "Installing Node.js 20.x..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

echo "Creating service account..."
sudo useradd -r -s /bin/false vbg-hub || echo "User already exists"

echo "Setting up application directory..."
sudo mkdir -p /opt/vbg-hub
sudo chown -R vbg-hub:vbg-hub /opt/vbg-hub

echo "Host setup complete. Manual steps remaining: Copy code to /opt/vbg-hub and configure .env"
```

- [ ] **Step 2: Create systemd service unit**

Create `vbg-hub.service` in the root.

```ini
[Unit]
Description=VBG Centralized Security Hub
After=network.target

[Service]
User=vbg-hub
Group=vbg-hub
WorkingDirectory=/opt/vbg-hub
EnvironmentFile=/opt/vbg-hub/backend/.env
# Use the venv python to ensure dependencies are loaded
ExecStart=/opt/vbg-hub/backend/venv/bin/python backend/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: Verify script and service syntax**

Run: `bash -n setup_host.sh`
Expected: No syntax errors.

- [ ] **Step 4: Commit**

Run: `git add setup_host.sh vbg-hub.service && git commit -m "feat: add bare-metal setup script and systemd service unit"`
