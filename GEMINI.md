# 🤖 Gemini CLI: Security Prioritizer & TI Skills Workspace

This project is a centralized repository for specialized **Gemini CLI Skills** and the **Internal Security Hub** application. It enables the Gemini CLI to act as a security analyst by correlating data across multiple platforms and providing a persistent web-based orchestration layer.

## 📁 Project Architecture

The workspace is organized into discrete skill directories and a full-stack Hub application.

- **Hub Application**: Located in `backend/` (FastAPI/CrewAI) and `frontend/` (React).
- **Gemini CLI Bridge**: A custom LLM provider in `backend/gemini_bridge.py` that routes agent requests through the local `gemini` CLI session, eliminating the need for `GEMINI_API_KEY` in environment files.
- **Root Skill Directories**: Source directories for individual skills (e.g., `security-prioritizer/`).
- **`.gemini/skills/`**: The local "active" directory where skills are mirrored and loaded by the Gemini CLI.

### Core Components

| Component | Purpose | Key Data Sources |
| :--- | :--- | :--- |
| **Security Hub** | Persistent web portal for agent orchestration. | PostgreSQL, CrewAI |
| **`security-prioritizer`** | Correlates & ranks vulnerabilities based on risk. | Tenable, Wiz, CISA KEV, Feedback |
| **`ti-master-enricher`** | Orchestrates multi-source TI lookups. | GreyNoise, OTX, VirusTotal |
| **`vulnerability-validator`** | Validates vulnerabilities via active scans. | Nuclei, Nmap, Kali |

---

## 🛠️ Development Workflow

### 1. Hub Orchestration
The Hub uses a **Sub-Agent Delegation** architecture. The `SecurityCoordinator` manages user requests and delegates to specialized agents (Researcher, Prioritizer, etc.).
- **HITL**: Agents MUST query the `agent_feedback` table via the `feedback_query_tool` before executing tasks.

### 2. LLM Access (CLI Bridge)
By default, the backend uses the **Gemini CLI Bridge**. Ensure you are authenticated in the CLI:
```bash
gemini --prompt "Verify session"
```
The backend will automatically detect and use this session if `GEMINI_API_KEY` is not set in `backend/.env`.

### 3. Adding/Updating a Skill
1.  Modify logic in the skill's source directory (e.g., `virustotal-checker/scripts/vt_lookup.cjs`).
2.  Repackage the `.skill` zip and mirror to `.gemini/skills/`.
3.  Reload the engine: `/skills reload`.

---

## 🔑 Prerequisites & Configuration

- **PostgreSQL**: Required for the Hub (Auth, Tabs, Audit, Feedback).
- **Gemini CLI**: Required for LLM access via the bridge.
- **Node.js & Python**: Required for runtime scripts and agents.

## 📝 Conventions

- **HITL First**: Always check for historical human decisions before proposing remediation.
- **Identity Awareness**: Every action must be linked to a domain username in audit logs.
- **PII Protection**: Mask sensitive indicators (last octet of IPs, emails) in public logs.
