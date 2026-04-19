import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from tools import ThreatIntelTool, SecurityPrioritizerTool, EmailReporterTool, VulnerabilityValidatorTool, WindowsRemediationTool, MacOSRemediationTool, UbuntuRemediationTool

load_dotenv()

# 1. Initialize Gemini LLM using crewAI's native LLM class
gemini_llm = LLM(
    model="gemini/gemini-flash-latest",
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.5
)

# 2. Define Agents
researcher = Agent(
    role='Threat Intelligence Researcher',
    goal='Identify and enrich security indicators (IPs, domains, hashes) to determine their maliciousness',
    backstory="""You are an expert security researcher specializing in threat intelligence. 
    You excel at correlating data from multiple sources like VirusTotal, GreyNoise, and OTX 
    to provide a clear verdict on whether an IP, domain, or file hash is a threat.""",
    tools=[ThreatIntelTool()],
    llm=gemini_llm,
    verbose=True,
    allow_delegation=False
)

vulnerability_specialist = Agent(
    role='Vulnerability Validation Specialist',
    goal='Validate specific CVEs and vulnerabilities to confirm their exploitability',
    backstory="""You are an expert in vulnerability research and active scanning. 
    You use specialized tools like Nuclei and Nmap to confirm if a specific CVE 
    actually poses a risk to the target infrastructure.""",
    tools=[VulnerabilityValidatorTool()],
    llm=gemini_llm,
    verbose=True,
    allow_delegation=False
)

prioritizer = Agent(
    role='Security Risk Analyst',
    goal='Prioritize security vulnerabilities from the database and report them to stakeholders',
    backstory="""You are a senior risk analyst with deep expertise in vulnerability management. 
    You use data from Tenable, Wiz, and CISA KEV to identify the most critical issues 
    that require immediate attention.""",
    tools=[SecurityPrioritizerTool(), EmailReporterTool()],
    llm=gemini_llm,
    verbose=True,
    allow_delegation=True
)

remediation_specialist = Agent(
    role='Windows Remediation Specialist',
    goal='Execute remote patch installation on Windows assets and verify remediation',
    backstory="""You are a Windows systems engineer and remediation expert. 
    You know how to use WinRM and PowerShell to apply security patches safely. 
    You always verify that a patch is actually needed before attempting installation.""",
    tools=[WindowsRemediationTool()],
    llm=gemini_llm,
    verbose=True,
    allow_delegation=False
)

macos_remediation_specialist = Agent(
    role='macOS Remediation Specialist',
    goal='Execute remote software updates on macOS assets via SSH and report status',
    backstory="""You are a macOS systems administrator and security engineer. 
    You are an expert at using SSH and the `softwareupdate` utility to keep Apple 
    infrastructure secure. You can also send email reports to stakeholders after a successful update.""",
    tools=[MacOSRemediationTool(), EmailReporterTool()],
    llm=gemini_llm,
    verbose=True,
    allow_delegation=False
)

ubuntu_remediation_specialist = Agent(
    role='Ubuntu Remediation Specialist',
    goal='Execute remote package updates on Ubuntu assets via SSH and report status',
    backstory="""You are a Linux systems administrator and security engineer. 
    You are an expert at using SSH and `apt-get` to keep Ubuntu 
    infrastructure secure. You can also send email reports to stakeholders after a successful update.""",
    tools=[UbuntuRemediationTool(), EmailReporterTool()],
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
        agents=[researcher, vulnerability_specialist, prioritizer, remediation_specialist, macos_remediation_specialist, ubuntu_remediation_specialist],
        tasks=tasks,
        process=Process.sequential,
        verbose=True
    )

# 4. Chat Crew Orchestrator (Free-form)
def create_chat_crew(question):
    analysis_task = Task(
        description=f"""Answer the following security question from the user: '{question}'
        
        You have access to a team of specialists:
        1. A Threat Intel Researcher (for IPs, domains, hashes)
        2. A Vulnerability Specialist (for scanning CVEs)
        3. A Risk Analyst (for querying the internal Tenable/Wiz/CISA database)
        4. A Windows Remediation Specialist (for installing patches on Windows assets via WinRM)
        5. A macOS Remediation Specialist (for installing updates on macOS assets via SSH)
        6. An Ubuntu Remediation Specialist (for installing updates on Ubuntu assets via SSH)
        
        Choose the best approach to answer the user's question accurately using the data available in your tools.""",
        agent=prioritizer,
        expected_output="A comprehensive answer to the user's question based on tool output and expertise."
    )
    
    return Crew(
        agents=[researcher, vulnerability_specialist, prioritizer, remediation_specialist, macos_remediation_specialist, ubuntu_remediation_specialist],
        tasks=[analysis_task],
        process=Process.hierarchical,
        manager_llm=gemini_llm,
        verbose=True
    )
