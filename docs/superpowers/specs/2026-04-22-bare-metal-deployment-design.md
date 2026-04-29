# Spec: Bare Metal Deployment for Centralized Security Hub

**Date:** 2026-04-22  
**Status:** Approved  
**Topic:** Transitioning from Docker to Bare Metal/Systemd deployment on Host A (Hub).

## 1. Overview
The Centralized Security Hub will be deployed directly on a dedicated virtual server (Host A). It will communicate with a separate PostgreSQL server (Host B) managed by another agent.

## 2. Goals
- Deploy the FastAPI backend and Node.js skills without containerization.
- Use `systemd` for process management, logging, and automatic restarts.
- Isolate Python dependencies using a virtual environment (`venv`).
- Ensure all services run under a dedicated service account for security.

## 3. Architecture
- **Host A (Hub):**
  - **OS:** Linux (Debian/Ubuntu assumed for package management).
  - **Runtime:** Python 3.12, Node.js 20.x.
  - **Service Manager:** `systemd`.
  - **User:** Dedicated service account (e.g., `vbg-hub`).
- **Host B (Database):**
  - **Service:** PostgreSQL 16 (external).

## 4. Components

### 4.1 Dependency Setup Script (`setup_host.sh`)
A shell script to automate host preparation:
- Install system libraries for LDAP (`libldap2-dev`, `libsasl2-dev`).
- Install Node.js 20.x from NodeSource.
- Install Python 3.12 and `venv`.
- Create the dedicated service account if it doesn't exist.

### 4.2 Systemd Service (`vbg-hub.service`)
```ini
[Unit]
Description=VBG Centralized Security Hub
After=network.target

[Service]
User=vbg-hub
Group=vbg-hub
WorkingDirectory=/opt/vbg-hub
EnvironmentFile=/opt/vbg-hub/backend/.env
ExecStart=/opt/vbg-hub/backend/venv/bin/python main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 4.3 Data Flow & Access
- **SSO/JWT:** FastAPI handles JWT generation after LDAP bind.
- **Auditing:** Logs are sent to `stdout`/`stderr` and captured by `journald`, which will later sync with PostgreSQL for identity-linked auditing.
- **Skills:** Node.js skills are executed locally via `child_process` by the Python backend.

## 5. Security Constraints
- **Least Privilege:** The service account will only have read/execute permissions on the application directory.
- **Environment:** Secrets (`JWT_SECRET_KEY`, API keys) must be stored in a secured `.env` file on Host A.

## 6. Verification Plan
- **Pre-flight:** Run `setup_host.sh` and verify all binaries (`node`, `python3.12`) are present.
- **Manual Start:** Run the FastAPI server manually as the service user to confirm connectivity to Host B (PostgreSQL).
- **Service Validation:** Start the `systemd` service and verify it stays active using `systemctl status vbg-hub`.
