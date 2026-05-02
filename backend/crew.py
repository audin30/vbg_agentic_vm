import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from typing import Any
from tools import (
    ThreatIntelTool, SecurityPrioritizerTool, EmailReporterTool, 
    VulnerabilityValidatorTool, WindowsRemediationTool, MacOSRemediationTool, 
    UbuntuRemediationTool, KaliOffensiveTool, FeedbackQueryTool
)
from gemini_bridge import LocalCLIBridge

# --- THE UNIVERSAL PYDANTIC BYPASS ---
# This forces Pydantic to ignore type checking for these fields.
Agent.model_fields['llm'].annotation = Any
Agent.model_fields['tools'].annotation = Any
Agent.model_rebuild(force=True)
Crew.model_fields['manager_llm'].annotation = Any
Crew.model_rebuild(force=True)
# -------------------------------------

load_dotenv()

def get_agents():
    llm = LocalCLIBridge()
    
    coordinator = Agent(
        role='Security Operations Coordinator',
        goal='Orchestrate the security team',
        backstory="Lead orchestrator.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        memory=False
    )

    researcher = Agent(
        role='Threat Intelligence Researcher',
        goal='Investigate indicators',
        backstory="Researcher.",
        tools=[ThreatIntelTool(), FeedbackQueryTool()],
        llm=llm,
        verbose=True,
        allow_delegation=True,
        memory=False
    )

    vuln_spec = Agent(
        role='Vulnerability Specialist',
        goal='Validate CVEs',
        backstory="Specialist.",
        tools=[VulnerabilityValidatorTool(), KaliOffensiveTool(), FeedbackQueryTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=False
    )

    risk_analyst = Agent(
        role='Security Risk Analyst',
        goal='Prioritize findings',
        backstory="Risk analyst.",
        tools=[SecurityPrioritizerTool(), EmailReporterTool(), FeedbackQueryTool()],
        llm=llm,
        verbose=True,
        allow_delegation=True,
        memory=False
    )

    return coordinator, researcher, vuln_spec, risk_analyst

def create_security_crew(indicator=None, indicator_type=None):
    agents = get_agents()
    coordinator, researcher, vuln_spec, risk_analyst = agents
    
    tasks = []
    if indicator and indicator_type:
        tasks.append(Task(description=f"Investigate {indicator}.", agent=researcher if indicator_type != 'cve' else vuln_spec, expected_output="Report."))
    
    tasks.append(Task(description="Fetch top 10 prioritized security findings.", agent=risk_analyst, expected_output="List."))
    
    return Crew(agents=list(agents), tasks=tasks, process=Process.sequential, verbose=True)

def create_chat_crew(question):
    agents = get_agents()
    coordinator = agents[0]
    
    analysis_task = Task(description=f"Answer: '{question}'", agent=coordinator, expected_output="Answer.")
    
    return Crew(agents=list(agents), tasks=[analysis_task], process=Process.sequential, verbose=True)
