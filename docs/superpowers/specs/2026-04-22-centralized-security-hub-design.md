# Design Spec: Centralized Security Orchestrator Hub

**Status:** Final Draft  
**Date:** 2026-04-22  
**Topic:** Centralizing the Security Orchestrator for Multi-User Internal Access

## 1. Executive Summary
The goal is to transition the current local-first Security Orchestrator into a centralized **Internal Security Hub**. This architecture allows multiple security staff members to perform concurrent investigations via a Web Portal or a Power-User CLI, utilizing shared logs, threat intelligence data, and a remote Kali Linux node.

## 2. Architecture: The Internal Security Hub
The system is deployed as a containerized stack on a central Linux server, reached via the internal company network.

### 2.1 Component Stack
- **Web Portal (The Interface):** A three-pane React dashboard (History, Chat, Evidence) for general analysts.
- **Power-User CLI (The Proxy):** A local terminal wrapper that uses **SSO (Domain Accounts)** to authenticate and proxy queries to the central Hub.
- **FastAPI Gateway (The Brain):** The central entry point. Handles **JWT-based Authentication** via LDAP/AD and manages CrewAI agent lifecycles.
- **CrewAI Orchestrator:** Maintains agent personas and handles task delegation.
- **Remote Kali Node (The Muscle):** A separate Kali Linux VM accessed via SSH for Metasploit, Nikto, and remediation tasks.
- **PostgreSQL Database:** Stores Identity-linked Audit Logs, Knowledge Cache, and Report Metadata.

### 2.2 User Access & Interaction
#### 2.2.1 Web Portal Experience
Analysts interact with a modern chat UI. Every **Active Query** displays live agent "thoughts" and results in rich result cards. Generated reports are available in a dedicated "Reports & Exports" section.

#### 2.2.2 Power-User CLI Experience
1. **Auth:** User runs `gemini-hub login`, which triggers a browser-based SSO login to the corporate domain.
2. **Session:** A short-lived JWT is stored locally to authorize subsequent queries.
3. **Execution:** Local commands (e.g., `gemini-hub query "Scan IP 10.1.1.5"`) are sent to the Hub API and rendered in the local terminal.

## 3. Security & Governance

### 3.1 Identity & Auditing
- **Domain Integration:** All users are authenticated against the internal Domain Controller (AD/LDAP).
- **Identity-Linked Logs:** Every query, agent decision, and tool execution in PostgreSQL is tagged with the analyst's **Domain Username**.
- **Masking:** All output passes through the `SensitiveDataFilter` to redact PII (masked IPs/Emails) before being stored or displayed.

### 3.2 Credential Isolation
- API Keys for Threat Intel and target credentials (WinRM/SSH) are stored exclusively on the **Central Hub Server** or within the **Remote Kali Node**.

## 4. Implementation Priorities
1. **Authentication:** Implement LDAP middleware in FastAPI and the CLI SSO login flow.
2. **Centralized Hub:** Package the existing CrewAI logic and Node.js skills into a multi-user Docker stack.
3. **Web UI:** Build the three-pane Analyst Portal based on the `portal_mockup.html` design.
4. **Knowledge Cache:** Configure PostgreSQL to serve as a shared result cache for common indicators.

## 5. Success Criteria
- Analysts can choose between Web or CLI interfaces while maintaining a single audit trail.
- No analyst needs to manage local API keys or security toolsets.
- The system scales to support concurrent investigations across the security team.
