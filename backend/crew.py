import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from tools import (
    ThreatIntelTool, SecurityPrioritizerTool, EmailReporterTool, 
    VulnerabilityValidatorTool, WindowsRemediationTool, MacOSRemediationTool, 
    UbuntuRemediationTool, KaliOffensiveTool, FeedbackQueryTool
)

from gemini_bridge import LocalCLIBridge

load_dotenv()

def get_agents():
    # Use the Pure Local CLI Bridge (No OpenAI dependency)
    llm = LocalCLIBridge()
    
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

    return coordinator, researcher, vuln_spec, risk_analyst

def create_security_crew(indicator=None, indicator_type=None):
    coordinator, researcher, vuln_spec, risk_analyst = get_agents()
    
    tasks = []
    if indicator and indicator_type:
        if indicator_type == 'cve':
            tasks.append(Task(
                description=f"Validate the CVE '{indicator}'.",
                agent=vuln_spec,
                expected_output="A validation report for the CVE."
            ))
        else:
            tasks.append(Task(
                description=f"Investigate the indicator '{indicator}'.",
                agent=researcher,
                expected_output="A threat intel report."
            ))
    
    tasks.append(Task(
        description="Fetch top 10 prioritized security findings.",
        agent=risk_analyst,
        expected_output="A list of top 10 vulnerabilities."
    ))
    
    return Crew(
        agents=[coordinator, researcher, vuln_spec, risk_analyst],
        tasks=tasks,
        process=Process.sequential,
        verbose=True
    )

def create_chat_crew(question):
    coordinator, researcher, vuln_spec, risk_analyst = get_agents()
    
    analysis_task = Task(
        description=f"Analyze and respond to the following security request: '{question}'",
        agent=coordinator,
        expected_output="A detailed security report answering the user's question."
    )
    
    return Crew(
        agents=[coordinator, researcher, vuln_spec, risk_analyst],
        tasks=[analysis_task],
        process=Process.sequential,
        verbose=True
    )
