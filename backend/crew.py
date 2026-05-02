import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from typing import Any
from tools import (
    ThreatIntelTool, SecurityPrioritizerTool, EmailReporterTool, 
    VulnerabilityValidatorTool, WindowsRemediationTool, MacOSRemediationTool, 
    UbuntuRemediationTool, KaliOffensiveTool, FeedbackQueryTool
)
from gemini_bridge import SecurityHubLLM

# --- THE UNIVERSAL PYDANTIC BYPASS ---
# This forces Pydantic to ignore type checking for custom LLM and Tool fields.
# Essential for using our custom SecurityHubLLM without inheritance conflicts.
Agent.model_fields['llm'].annotation = Any
Agent.model_fields['tools'].annotation = Any
Agent.model_rebuild(force=True)

# Crew in version 0.5.0 doesn't have manager_llm field, so we don't try to bypass it here.
# If using a later version that HAS manager_llm, uncomment below:
# if 'manager_llm' in Crew.model_fields:
#     Crew.model_fields['manager_llm'].annotation = Any
#     Crew.model_rebuild(force=True)
# -------------------------------------

load_dotenv()

def get_agents(llm=None):
    if llm is None:
        llm = SecurityHubLLM()
    
    coordinator = Agent(
        role='Security Operations Coordinator',
        goal='Orchestrate the security team to fulfill user requests by delegating tasks to specialists',
        backstory="You are the lead orchestrator of a high-performance security team.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        memory=False
    )

    researcher = Agent(
        role='Threat Intelligence Researcher',
        goal='Identify and enrich security indicators to determine their maliciousness',
        backstory="Expert security researcher. Correlate data from multi-sources.",
        tools=[ThreatIntelTool(), FeedbackQueryTool()],
        llm=llm,
        verbose=True,
        allow_delegation=True,
        memory=False
    )

    vuln_spec = Agent(
        role='Vulnerability Validation Specialist',
        goal='Validate specific CVEs and vulnerabilities to confirm their exploitability',
        backstory="Elite offensive security specialist.",
        tools=[VulnerabilityValidatorTool(), KaliOffensiveTool(), FeedbackQueryTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=False
    )

    risk_analyst = Agent(
        role='Security Risk Analyst',
        goal='Prioritize security vulnerabilities from the database',
        backstory="Senior risk analyst. Prioritize issues from Tenable, Wiz, and CISA.",
        tools=[SecurityPrioritizerTool(), EmailReporterTool(), FeedbackQueryTool()],
        llm=llm,
        verbose=True,
        allow_delegation=True,
        memory=False
    )

    return (coordinator, researcher, vuln_spec, risk_analyst), llm

def create_security_crew(indicator=None, indicator_type=None):
    agents, llm = get_agents()
    coordinator, researcher, vuln_spec, risk_analyst = agents
    
    tasks = []
    if indicator and indicator_type:
        tasks.append(Task(
            description=f"Investigate the security indicator '{indicator}' of type '{indicator_type}'.",
            agent=researcher if indicator_type != 'cve' else vuln_spec,
            expected_output="A detailed security report."
        ))
    
    tasks.append(Task(
        description="Fetch top 10 prioritized security findings from the database.",
        agent=risk_analyst,
        expected_output="A list of prioritized vulnerabilities."
    ))
    
    # In CrewAI 0.5.0, manager_llm is not a parameter for sequential process.
    return Crew(
        agents=list(agents),
        tasks=tasks,
        process=Process.sequential,
        verbose=True
    )

def create_chat_crew(question):
    agents, llm = get_agents()
    coordinator = agents[0]
    
    analysis_task = Task(
        description=f"Analyze and respond to the following security request: '{question}'",
        agent=coordinator,
        expected_output="A comprehensive security report answering the user's question."
    )
    
    return Crew(
        agents=list(agents),
        tasks=[analysis_task],
        process=Process.sequential,
        verbose=True
    )
