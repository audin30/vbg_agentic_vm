# 🤖 Gemini CLI: Security Orchestrator & TI Skills Workspace

This project is a centralized repository for specialized **Gemini CLI Skills** and a **CrewAI-powered Backend Orchestrator** focused on security operations, threat intelligence, and automated remediation.

## 🏗️ Architecture

The system bridges the gap between high-level agentic orchestration and low-level security tools through a modular "Skill" architecture.

```mermaid
graph TD
    subgraph "User Interface / Client"
        User[Security Analyst / User]
        CLI[Gemini CLI]
    end

    subgraph "Backend Orchestration (Python / FastAPI)"
        API[FastAPI Server :8000]
        Crew[CrewAI Orchestrator]
        
        subgraph "Specialized Agents"
            TI_Agent[Threat Intel Researcher]
            VV_Agent[Vuln Validation Specialist]
            RA_Agent[Security Risk Analyst]
            WR_Agent[Windows Remediation Specialist]
            MR_Agent[macOS Remediation Specialist]
            UR_Agent[Ubuntu Remediation Specialist]
        end
    end

    subgraph "Custom Tools & Wrappers (Python)"
        Tool_TI[ThreatIntelTool]
        Tool_VV[VulnerabilityValidatorTool]
        Tool_SP[SecurityPrioritizerTool]
        Tool_ER[EmailReporterTool]
        Tool_WR[WindowsRemediationTool]
        Tool_MR[MacOSRemediationTool]
        Tool_UR[UbuntuRemediationTool]
    end

    subgraph "Gemini CLI Skills (Node.js Scripts)"
        Skill_TI[ti-master-enricher]
        Skill_VV[vulnerability-validator]
        Skill_ER[asset-email-reporter]
    end

    subgraph "External Infrastructure & APIs"
        PG[(PostgreSQL Database)]
        APIs[Security APIs: VT, GreyNoise, OTX]
        WinTarget[[Windows Asset - WinRM]]
        MacTarget[[macOS Asset - SSH]]
        UbuTarget[[Ubuntu Asset - SSH]]
    end

    %% Interactions
    User -->|Inquiry/Directive| CLI
    CLI -->|API Request| API
    API --> Crew
    Crew --> TI_Agent & VV_Agent & RA_Agent & WR_Agent & MR_Agent & UR_Agent

    %% Tool Bindings
    TI_Agent --> Tool_TI
    VV_Agent --> Tool_VV
    RA_Agent --> Tool_SP & Tool_ER
    WR_Agent --> Tool_WR
    MR_Agent --> Tool_MR & Tool_ER
    UR_Agent --> Tool_UR & Tool_ER

    %% Tool Implementations
    Tool_TI -->|subprocess| Skill_TI
    Tool_VV -->|subprocess| Skill_VV
    Tool_ER -->|subprocess| Skill_ER
    
    Tool_SP -->|psycopg2| PG
    Tool_WR -->|winrm| WinTarget
    Tool_MR -->|paramiko/SSH| MacTarget
    Tool_UR -->|paramiko/SSH| UbuTarget
```

---

## 🚀 Featured Skills

| Skill Name | Purpose | Key Data Sources |
| :--- | :--- | :--- |
| **`security-prioritizer`** | Correlates & ranks vulnerabilities based on risk. | Tenable, Wiz, CISA KEV, phpIPAM |
| **`vulnerability-validator`** | Validates vulnerabilities via active scans. | Nuclei, Nmap |
| **`ti-master-enricher`** | Orchestrates multi-source TI lookups (Consensus). | GreyNoise, OTX, VirusTotal |
| **`virustotal-checker`** | Threat reputation for IPs and Domains. | VirusTotal API v3 |
| **`greynoise-community`** | Identifies internet background noise/scanners. | GreyNoise Community API |
| **`alienvault-otx`** | Checks indicators against threat pulses. | AlienVault OTX API |
| **`chronicle-query`** | Queries SIEM events and detections. | Google Chronicle API |
| **`rapid7-siem`** | Queries investigations and logs in InsightIDR. | Rapid7 InsightIDR |
| **`talos-intelligence`** | Reputation lookups from Cisco Talos. | Talos Intelligence |
| **`csv-writer`** | Exports JSON data to CSV files. | Local Node.js Script |

---

## ⚙️ Setup & Installation

### 1. Backend Orchestrator (Python)
Requires Python 3.12+.
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 2. Gemini CLI Skills (Node.js)
Requires Node.js and the Gemini CLI.
```bash
npm install
# Install individual skills into the CLI
gemini skills install ./<skill-name>.skill --scope user
```

### 3. Environment Configuration
Copy `backend/.env.example` to `backend/.env` and provide your API keys:
- `GEMINI_API_KEY`: Core LLM orchestration.
- `VIRUSTOTAL_API_KEY`, `GREYNOISE_API_KEY`, `OTX_API_KEY`: Threat Intelligence.
- `CHRONICLE_CUSTOMER_ID`, `GOOGLE_APPLICATION_CREDENTIALS`: Chronicle SIEM.
- `RAPID7_API_KEY`, `RAPID7_REGION`: Rapid7 InsightIDR.
- `POSTGRES_*`: For the Security Prioritizer database.
- `WINRM_*`, `MACOS_SSH_*`, `UBUNTU_SSH_*`: Credentials for automated remediation.

## 🛠️ Usage

1.  **Direct CLI Interaction**: Use natural language in the Gemini CLI to trigger specific skills (e.g., "Enrich IP 8.8.8.8").
2.  **API-Driven Orchestration**: The backend exposes a `/api/orchestrate` endpoint that uses CrewAI agents to perform multi-step security investigations and remediation.

For detailed development workflows, see [GEMINI.md](GEMINI.md).
