import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai import LLM as CrewLLM
from tools import (
    ThreatIntelTool, SecurityPrioritizerTool, EmailReporterTool, 
    VulnerabilityValidatorTool, WindowsRemediationTool, MacOSRemediationTool, 
    UbuntuRemediationTool, KaliOffensiveTool, FeedbackQueryTool
)

from gemini_bridge import GeminiChatCLI

load_dotenv()

# 1. Initialize Gemini LLM using the CLI Bridge (No API key required)
# We instantiate the class directly.
gemini_llm = GeminiChatCLI()

# 2. Define Agents
security_coordinator = Agent(
    role='Security Operations Coordinator',
    goal='Orchestrate the security team to fulfill user requests by delegating tasks to specialists',
    backstory="""You are the lead orchestrator of a high-performance security team. 
    Your job is to understand the user's objective, break it down into logical steps, 
    and delegate those steps to your team of specialists (Researcher, Risk Analyst, 
    Remediation Specialists). You don't execute technical tools yourself; you manage 
    the sub-agents to provide a unified and verified outcome.""",
    llm=gemini_llm,
    verbose=True,
    allow_delegation=True
)

researcher = Agent(
    role='Threat Intelligence Researcher',
    goal='Identify and enrich security indicators (IPs, domains, hashes) to determine their maliciousness',
    backstory="""You are an expert security researcher specializing in threat intelligence. 
    You excel at correlating data from multiple sources like VirusTotal, GreyNoise, and OTX 
    to provide a clear verdict. Before finalized findings, check the feedback_query_tool 
    to see if a human has previously flagged or dismissed specific indicators.""",
    tools=[ThreatIntelTool(), FeedbackQueryTool()],
    llm=gemini_llm,
    verbose=True,
    allow_delegation=True
)

vulnerability_specialist = Agent(
    role='Vulnerability Validation Specialist',
    goal='Validate specific CVEs and vulnerabilities to confirm their exploitability',
    backstory="""You are an elite offensive security specialist. Before performing any 
    active scanning or Kali-based exploitation, you MUST check the feedback_query_tool 
    to see if a human has previously denied testing on a specific target. 
    Respect all previous human decisions.""",
    tools=[VulnerabilityValidatorTool(), KaliOffensiveTool(), FeedbackQueryTool()],
    llm=gemini_llm,
    verbose=True,
    allow_delegation=False
)

prioritizer = Agent(
    role='Security Risk Analyst',
    goal='Prioritize security vulnerabilities from the database and report them to stakeholders',
    backstory="""You are a senior risk analyst. You prioritize issues from Tenable, Wiz, and CISA. 
    Critically, you must check the feedback_query_tool to see if a human has previously 
    accepted a risk or deprioritized a finding, and adjust your list accordingly.""",
    tools=[SecurityPrioritizerTool(), EmailReporterTool(), FeedbackQueryTool()],
    llm=gemini_llm,
    verbose=True,
    allow_delegation=True
)

remediation_specialist = Agent(
    role='Windows Remediation Specialist',
    goal='Execute remote patch installation on Windows assets and verify remediation',
    backstory="""You are a Windows systems engineer. Before applying any patches via WinRM, 
    you MUST check the feedback_query_tool for the target asset. If a human has previously 
    denied a patch or provided specific constraints (e.g., 'no reboots'), you MUST adhere to them.""",
    tools=[WindowsRemediationTool(), FeedbackQueryTool()],
    llm=gemini_llm,
    verbose=True,
    allow_delegation=False
)

macos_remediation_specialist = Agent(
    role='macOS Remediation Specialist',
    goal='Execute remote software updates on macOS assets via SSH and report status',
    backstory="""You are a macOS admin. Before installing updates, check the 
    feedback_query_tool for the target. Adhere strictly to any human feedback regarding 
    reboots or update timing for that asset.""",
    tools=[MacOSRemediationTool(), EmailReporterTool(), FeedbackQueryTool()],
    llm=gemini_llm,
    verbose=True,
    allow_delegation=False
)

ubuntu_remediation_specialist = Agent(
    role='Ubuntu Remediation Specialist',
    goal='Execute remote package updates on Ubuntu assets via SSH and report status',
    backstory="""You are a Linux security engineer. Before running apt-get updates, 
    check the feedback_query_tool for the target IP. You MUST follow historical 
    human decisions regarding package pinning or denied updates.""",
    tools=[UbuntuRemediationTool(), EmailReporterTool(), FeedbackQueryTool()],
    llm=gemini_llm,
    verbose=True,
    allow_delegation=False
)

# 3. Security Crew Orchestrator (Structured)
def create_security_crew(indicator=None, indicator_type=None):
    tasks = []
    
    if indicator and indicator_type:
        if indicator_type == 'cve':
            tasks.append(Task(
                description=f"Validate the CVE '{indicator}'. Use active scanning tools to confirm if this vulnerability is present and exploitable.",
                agent=vulnerability_specialist,
                expected_output="A validation report for the CVE."
            ))
        else:
            tasks.append(Task(
                description=f"Investigate the indicator '{indicator}' of type '{indicator_type}'. Provide a summary of its threat reputation.",
                agent=researcher,
                expected_output="A threat intel report for the indicator."
            ))
    
    tasks.append(Task(
        description="Fetch the top 10 prioritized security findings from the database and explain why they are high risk.",
        agent=prioritizer,
        expected_output="A list of top 10 vulnerabilities with justification."
    ))
    
    return Crew(
        agents=[security_coordinator, researcher, vulnerability_specialist, prioritizer, remediation_specialist, macos_remediation_specialist, ubuntu_remediation_specialist],
        tasks=tasks,
        process=Process.sequential,
        verbose=True
    )

# 4. Chat Crew Orchestrator (Free-form)
def create_chat_crew(question):
    analysis_task = Task(
        description=f"""Answer the following security question from the user: '{question}'
        
        You are the lead coordinator. Use your team of specialists to provide the most accurate answer:
        1. Threat Intelligence Researcher (for IPs, domains, hashes)
        2. Vulnerability Specialist (for scanning CVEs)
        3. Risk Analyst (for querying internal security databases)
        4. Remediation Specialists (for Windows, macOS, and Ubuntu package/patch management)
        
        Analyze the request, delegate sub-tasks to the appropriate specialists, and synthesize their 
        work into a final report.""",
        agent=security_coordinator,
        expected_output="A comprehensive, multi-perspective answer to the user's question, incorporating data from various sub-agents."
    )
    
    return Crew(
        agents=[security_coordinator, researcher, vulnerability_specialist, prioritizer, remediation_specialist, macos_remediation_specialist, ubuntu_remediation_specialist],
        tasks=[analysis_task],
        process=Process.hierarchical,
        manager_llm=gemini_llm,
        verbose=True
    )
