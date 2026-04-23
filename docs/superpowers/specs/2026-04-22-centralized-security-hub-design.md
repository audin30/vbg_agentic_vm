# Design Spec: Centralized Security Orchestrator Hub

**Status:** Draft  
**Date:** 2026-04-22  
**Topic:** Centralizing the Security Orchestrator for Multi-User Internal Access

## 1. Executive Summary
The goal is to transition the current local-first Security Orchestrator into a centralized **Internal Security Hub**. This architecture allows multiple security staff members to perform concurrent investigations while centralizing logs, threat intelligence data, and network probes on a single, secured internal server.

## 2. Architecture: The Internal Security Hub
The system will be deployed as a containerized stack using Docker Compose on a central Linux VM.

### 2.1 Component Stack
- **Web Frontend:** A lightweight React or Vue-based portal for staff interaction.
- **FastAPI Gateway (The Brain):** The primary entry point that manages user sessions and orchestrates the CrewAI agents.
- **CrewAI Orchestrator:** Maintains agent personas and handles task delegation.
- **Node.js Skill Runners:** Executes the `.skill` scripts (Nmap, VT, etc.) within the server's network context.
- **Remote Kali Node (The Muscle):** A dedicated, separate Kali Linux instance (VM) used by the Offensive Specialist agent via SSH for heavy lifting (Metasploit, Nikto, etc.).
- **PostgreSQL Database:** Acts as the persistent "Memory" and "Audit Trail" for the entire system.

### 2.2 Data Flow
1. **Request:** Staff member submits an investigation request via the Web UI.
2. **Identification:** FastAPI attaches a `user_id` to the request for auditing.
3. **Orchestration:** CrewAI agents determine the necessary steps (e.g., "Researcher looks up IP", "Specialist runs scan").
4. **Execution:** 
    - Recon/OSINT skills run locally on the Hub.
    - Offensive validation and exploitation tasks are offloaded to the **Remote Kali Node** via SSH.
5. **Persistence:** Findings and agent reasoning are stored in PostgreSQL.
6. **Response:** Results are streamed back to the staff member and archived in the searchable audit log.

## 3. Security & Governance

### 3.1 Credential Management
- **Centralized Keys:** All API keys (VirusTotal, GreyNoise, etc.) are stored as server-side environment variables or Docker secrets. Staff never touch raw keys.
- **Target Access:** WinRM and SSH credentials for remediation targets are managed centrally by the server's vault.

### 3.2 Auditing & Multi-tenancy
- **User Attribution:** Every tool execution and agent decision is tagged with the requesting analyst's ID.
- **Shared Knowledge Base:** PostgreSQL caches results of expensive or rate-limited lookups (like VT) so other analysts can benefit from previous investigations without re-querying.
- **Network Consistency:** All security probes originate from a single, static IP, allowing for precise firewall rule sets.

## 4. Implementation Priorities
1. **Dockerization:** Package the FastAPI backend and Node.js runtime into a unified stack.
2. **Database Schema:** Initialize PostgreSQL with tables for `audit_logs`, `knowledge_cache`, and `user_sessions`.
3. **API Enhancements:** Update `backend/main.py` to support multi-user requests and database logging.
4. **Frontend Portal:** Develop a simple shared interface for investigation management.

## 5. Success Criteria
- Multiple staff can run investigations simultaneously without resource contention.
- A centralized, searchable record exists for every security probe performed by the system.
- All external traffic (TI lookups) and internal probes originate from the central Hub IP.
