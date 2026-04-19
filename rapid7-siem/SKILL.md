# 🔍 Rapid7 SIEM (InsightIDR) Query Skill

This skill allows the Gemini CLI to query Rapid7 InsightIDR for logs and investigations related to specific indicators (IPs, Hostnames, or Users).

## Triggers
- "Check Rapid7 logs for IP 1.2.3.4"
- "Search InsightIDR for host 'workstation-01'"
- "Find Rapid7 investigations for user 'jdoe'"

## Prerequisites
- **RAPID7_API_KEY**: Your InsightIDR API Key.
- **RAPID7_REGION**: The region of your InsightIDR instance (e.g., 'us', 'eu', 'au').

## Usage
The skill uses the InsightIDR REST API to search for log entries or investigations.
