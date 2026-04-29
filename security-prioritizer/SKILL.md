---
name: security-prioritizer
description: Security data correlation and prioritization for Tenable, Wiz, CISA KEV, and phpIPAM data. Use when the user wants to identify the highest risk findings based on exploitation status, visibility, and network context.
---

# Security Prioritizer

This skill enables Gemini CLI to act as a security analyst by correlating vulnerability data from multiple sources (Tenable, Wiz, CISA KEV, phpIPAM) and incorporating human feedback to provide a prioritized action report.

## Prerequisites

- PostgreSQL MCP server connected with the following tables:
  - `public.tenable_findings`, `public.tenable_assets`, `public.tenable_asm_assets`
  - `public.wiz_vulnerabilities`, `public.wiz_inventory`
  - `public.cisa_kev`
  - `public.phpipam_assets`
  - `public.agent_feedback` (HITL Loop)

## Workflows

### Generating a Prioritization Report

When asked to prioritize findings or generate a risk report:

1.  **Check Feedback**: Query the `public.agent_feedback` table to identify findings that have been "Risk Accepted" or "Denied" by an analyst.
2.  **Load Logic**: Reference [references/logic.md](references/logic.md) for the prioritization scoring system.
3.  **Execute Query**: Use the `mcp_postgresql_execute_sql` tool. Ensure results are filtered or sorted based on human feedback (e.g., deprioritize findings marked as 'Risk Accepted').
4.  **Synthesize Results**: Present the top results with a clear explanation of why they are prioritized.

## Scoring Model

- **Base**: CVSS Score (0-10)
- **CISA KEV**: +100
- **External Visibility (ASM)**: +50
- **Cross-Tool Confirmation**: +20
- **Human Override**: -500 (Risk Accepted / Denied)

## Example Requests

- "Give me the top 10 security findings I should work on today."
- "Show me all CISA KEV vulnerabilities that are externally visible."
- "Correlate Tenable and Wiz findings to see what's confirmed by both."
