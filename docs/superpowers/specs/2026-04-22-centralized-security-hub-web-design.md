# Spec: React Web Portal for Centralized Security Hub

**Date:** 2026-04-22  
**Status:** Approved  
**Topic:** Implementing a multi-tab, persistent React SPA for the Security Orchestrator.

## 1. Overview
The Web Portal serves as the primary interface for security analysts to interact with the Centralized Security Hub. It prioritizes concurrent investigation management through a persistent multi-tab interface.

## 2. Design Goals
- **Context Persistence:** "Active Queries" (tabs) must persist across browser refreshes and sessions.
- **Real-time Feedback:** Use streaming (SSE) to show agent thoughts and responses as they happen.
- **Effortless Documentation:** Automatically extract and list evidence (IPs, Domains, Hashes) discovered during queries.
- **Enterprise Ready:** Integrated with LDAP/JWT authentication (from Phase 1).

## 3. Architecture

### 3.1 Frontend Stack
- **Framework:** React 18+ with Vite (TypeScript).
- **State Management:** Zustand (handling tabs, message history, and global user state).
- **Routing:** React Router (SPA mode with URLs like `/query/:id`).
- **Styling:** Vanilla CSS (following the dark security theme in `portal_mockup.html`).

### 3.2 Navigation & Layout (Multi-Tab Command Center)
- **Tab Bar:** Top-level navigation showing open "Active Queries". Includes a `+` button for new queries and an `x` to "Close Query".
- **Main Pane:** Full-width streaming chat interface.
  - **Thought Trace:** A separate, styled area for streaming internal agent logic/tool execution steps.
  - **Final Response:** The primary agent answer area.
- **Evidence Drawer:** A collapsible right-hand panel containing the "Evidence Locker" and "Risk Gauge".

## 4. Features & Data Flow

### 4.1 Persistent Tabs
- Tabs are synchronized with a PostgreSQL backend table (`user_active_queries`).
- Opening or closing a tab sends an immediate sync request to the Hub API.
- Deep-linking is supported: navigating to `/query/123` automatically opens that tab if not already present.

### 4.2 Streaming Response (SSE)
- Frontend uses `fetch-event-source` to handle streaming POST requests.
- **Event Types:**
  - `thought`: Updates the Thought Trace UI component.
  - `message`: Appends text to the primary response component.
  - `done`: Signal to stop the cursor animation and finalize the UI state.

### 4.3 Automated Evidence Locker
- A background observer parses incoming text chunks for indicators:
  - IPv4: `\b(?:\d{1,3}\.){3}\d{1,3}\b`
  - Domain: `\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\b`
  - SHA256: `\b[A-Fa-f0-9]{64}\b`
- Extracted items appear in real-time in the Evidence panel.

## 5. Backend Requirements (Hub API)
- **GET** `/api/users/me/tabs`: Returns list of IDs for active tabs.
- **POST** `/api/queries`: Creates a new "Active Query" record.
- **DELETE** `/api/queries/:id`: Marks a query as "Closed" and removes it from the user's active tab list.
- **SSE Endpoint:** `/api/orchestrate` updated to support streaming response.

## 6. Verification Plan
- **Mock Stream:** Create a test script that pushes SSE events to verify the React consumer handles thoughts and messages correctly.
- **Persistence Check:** Open 3 tabs, refresh the browser, and confirm all 3 tabs re-open in the same state.
- **Deep Link Test:** Paste a query URL into a new browser window and verify the specific query loads.
