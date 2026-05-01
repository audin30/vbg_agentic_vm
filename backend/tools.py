import os
import subprocess
import json
import psycopg2
import winrm
import paramiko
from langchain_core.tools import BaseTool
from typing import Type, Any
from pydantic import BaseModel, Field
from logger_config import logger
import asyncio
import shlex
from database.db_helper import db

class IndicatorSchema(BaseModel):
    indicator: str = Field(..., description="The IP address, domain, hostname, file hash, or CVE ID to investigate.")
    type: str = Field(..., description="The type of indicator (ip, domain, hash, cve).")

class ThreatIntelTool(BaseTool):
    name: str = "threat_intel_enricher"
    description: str = "Enrich an IP, domain, or file hash using multiple threat intelligence sources (VT, GreyNoise, OTX) and get a consensus score."
    args_schema: Type[BaseModel] = IndicatorSchema
    func: Any = lambda x: x 

    async def _arun(self, indicator: str, type: str) -> str:
        logger.info(f"TOOL - Running ThreatIntelTool for {type}: {indicator}")
        try:
            cached = await db.get_cached_indicator(indicator)
            if cached:
                return json.dumps(cached, indent=2)
            script_path = os.path.join(os.getcwd(), "..", "ti-master-enricher", "scripts", "enrich_master.cjs")
            result = subprocess.run(["node", script_path, type, indicator], capture_output=True, text=True, check=True)
            output = result.stdout
            try:
                result_json = json.loads(output)
                await db.cache_indicator(indicator, type, result_json)
            except: pass
            return output
        except Exception as e:
            return f"Error: {str(e)}"

    def _run(self, indicator: str, type: str) -> str:
        return asyncio.run(self._arun(indicator, type))

class VulnerabilityValidatorTool(BaseTool):
    name: str = "vulnerability_validator"
    description: str = "Validate a specific CVE or vulnerability against a target asset using active scans."
    args_schema: Type[BaseModel] = IndicatorSchema
    func: Any = lambda x: x 

    def _run(self, indicator: str, type: str) -> str:
        try:
            script_path = os.path.join(os.getcwd(), "..", "vulnerability-validator", "scripts", "scan_vuln.cjs")
            result = subprocess.run(["node", script_path, indicator], capture_output=True, text=True, check=True)
            return result.stdout
        except Exception as e:
            return f"Error: {str(e)}"

class SecurityPrioritizerTool(BaseTool):
    name: str = "security_prioritizer"
    description: str = "Query the PostgreSQL database to get a prioritized list of security findings across Tenable, Wiz, and CISA KEV."
    func: Any = lambda x: x 

    def _run(self) -> str:
        try:
            conn = psycopg2.connect(host=os.getenv("POSTGRES_HOST"), port=os.getenv("POSTGRES_PORT"), database=os.getenv("POSTGRES_DATABASE"), user=os.getenv("POSTGRES_USER"), password=os.getenv("POSTGRES_PASSWORD"))
            cur = conn.cursor()
            query = """
            WITH all_vulns AS (
                SELECT tf.cve as cve_id, ta.hostname, ta.ipv4 as ip_address, 'Tenable' as source, tf.cvss_score FROM public.tenable_findings tf JOIN public.tenable_assets ta ON tf.asset_id = ta.id
                UNION ALL
                SELECT wv.cve_id, wi.name as hostname, NULL as ip_address, 'Wiz' as source, wv.cvss_score FROM public.wiz_vulnerabilities wv JOIN public.wiz_inventory wi ON wv.resource_id = wi.id
                UNION ALL
                SELECT UNNEST(iv.cves) as cve_id, ia.hostname, ia.ip_addresses[1] as ip_address, 'InsightVM' as source, COALESCE(iv.cvss_v3_score, iv.cvss_v2_score) as cvss_score FROM public.insightvm_findings ifnd JOIN public.insightvm_vulnerabilities iv ON ifnd.vulnerability_id = iv.id JOIN public.insightvm_assets ia ON ifnd.asset_id = ia.id
            ),
            prioritized_findings AS (
                SELECT v.cve_id, v.hostname, v.ip_address, MAX(v.cvss_score) as max_cvss, STRING_AGG(DISTINCT v.source, ', ') as sources,
                EXISTS (SELECT 1 FROM public.cisa_kev ck WHERE ck.cve_id = v.cve_id) as in_cisa_kev,
                EXISTS (SELECT 1 FROM public.tenable_asm_assets asm WHERE asm.hostname = v.hostname OR asm.ip_address = v.ip_address) as in_asm,
                EXISTS (SELECT 1 FROM public.rapid7_assets r7 WHERE r7.name = v.hostname OR v.ip_address = ANY(r7.ip_addresses)) as in_insightidr,
                EXISTS (SELECT 1 FROM public.phpipam_assets ipam WHERE (ipam.hostname = v.hostname OR ipam.ip_address = v.ip_address) AND (ipam.subnet_description ILIKE '%MGMT%' OR ipam.subnet_description ILIKE '%OOB%')) as in_mgmt_subnet,
                EXISTS (SELECT 1 FROM public.phpipam_assets ipam WHERE (ipam.hostname = v.hostname OR ipam.ip_address = v.ip_address) AND ipam.is_gateway = true) as is_gateway
                FROM all_vulns v GROUP BY v.cve_id, v.hostname, v.ip_address
            )
            SELECT p.cve_id, ck.vulnerability_name, p.hostname, p.sources, p.max_cvss,
            (COALESCE(p.max_cvss, 0) + (CASE WHEN p.in_cisa_kev THEN 100 ELSE 0 END) + (CASE WHEN p.in_asm THEN 50 ELSE 0 END) + (CASE WHEN p.in_insightidr THEN 15 ELSE 0 END) + (CASE WHEN p.in_mgmt_subnet THEN 30 ELSE 0 END) + (CASE WHEN p.is_gateway THEN 20 ELSE 0 END) + (CASE WHEN p.sources LIKE '%,%' THEN 20 ELSE 0 END)) as priority_score
            FROM prioritized_findings p LEFT JOIN public.cisa_kev ck ON p.cve_id = ck.cve_id ORDER BY priority_score DESC LIMIT 20;
            """
            cur.execute(query)
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
            results = [dict(zip(colnames, row)) for row in rows]
            cur.close()
            conn.close()
            return json.dumps(results, indent=2, default=str)
        except Exception as e:
            return f"Error: {str(e)}"

class EmailReportSchema(BaseModel):
    subject: str = Field(..., description="The subject of the email report.")
    content: str = Field(..., description="The body content of the security report.")
    recipient: str = Field(..., description="The email address of the recipient.")

class EmailReporterTool(BaseTool):
    name: str = "security_email_reporter"
    description: str = "Send a security report via email to a stakeholder."
    args_schema: Type[BaseModel] = EmailReportSchema
    func: Any = lambda x: x 

    def _run(self, subject: str, content: str, recipient: str) -> str:
        try:
            script_path = os.path.join(os.getcwd(), "..", "asset-email-reporter", "scripts", "send_email.cjs")
            subprocess.run(["node", script_path, recipient, subject, content], check=True)
            return f"Success: Email sent to {recipient}"
        except Exception as e:
            return f"Error: {str(e)}"

class RemediationSchema(BaseModel):
    target_ip: str = Field(..., description="The IP address or hostname of the Windows asset.")
    kb_id: str = Field(..., description="The KB article ID to install (e.g., 'KB5041571').")
    reboot_allowed: bool = Field(default=False, description="Whether to allow automatic reboots if required.")

class WindowsRemediationTool(BaseTool):
    name: str = "windows_remediator"
    description: str = "Execute remote patch installation on a Windows asset via WinRM using PSWindowsUpdate."
    args_schema: Type[BaseModel] = RemediationSchema
    func: Any = lambda x: x 

    def _run(self, target_ip: str, kb_id: str, reboot_allowed: bool = False) -> str:
        try:
            session = winrm.Session(target_ip, auth=(os.getenv("WINRM_USER"), os.getenv("WINRM_PASSWORD")), transport=os.getenv("WINRM_TRANSPORT", "ntlm"))
            reboot_flag = "-AutoReboot" if reboot_allowed else ""
            ps_script = f"Get-WindowsUpdate -KBArticleID '{kb_id}' -Install -AcceptAll {reboot_flag}"
            result = session.run_ps(ps_script)
            return result.std_out.decode('utf-8') if result.status_code == 0 else result.std_err.decode('utf-8')
        except Exception as e:
            return f"Error: {str(e)}"

class MacOSRemediationSchema(BaseModel):
    target_ip: str = Field(..., description="The IP address or hostname of the macOS asset.")
    update_label: str = Field(..., description="The specific software update label to install.")
    force_reboot: bool = Field(default=False, description="Whether to force a reboot if required (default is False).")

class MacOSRemediationTool(BaseTool):
    name: str = "macos_remediation_tool"
    description: str = "Connect to a remote macOS asset via SSH and install a specific software update using softwareupdate."
    args_schema: Type[BaseModel] = MacOSRemediationSchema
    func: Any = lambda x: x 

    def _run(self, target_ip: str, update_label: str, force_reboot: bool = False) -> str:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            key = paramiko.RSAKey.from_private_key_file(os.getenv("MACOS_SSH_KEY_PATH"), password=os.getenv("MACOS_SSH_PASSPHRASE"))
            ssh.connect(hostname=target_ip, username=os.getenv("MACOS_SSH_USER"), pkey=key, timeout=30)
            reboot_flag = "--restart" if force_reboot else ""
            cmd = f"sudo softwareupdate --install {shlex.quote(update_label)} {reboot_flag}"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode('utf-8')
            ssh.close()
            return out
        except Exception as e:
            return f"Error: {str(e)}"

class UbuntuRemediationSchema(BaseModel):
    target_ip: str = Field(..., description="The IP address or hostname of the Ubuntu asset.")
    package_name: str = Field(..., description="The name of the package to update (e.g., 'openssl').")
    force_reboot: bool = Field(default=False, description="Whether to force a reboot if required (default is False).")

class UbuntuRemediationTool(BaseTool):
    name: str = "ubuntu_remediation_tool"
    description: str = "Connect to a remote Ubuntu asset via SSH and install a specific package update using apt-get."
    args_schema: Type[BaseModel] = UbuntuRemediationSchema
    func: Any = lambda x: x 

    def _run(self, target_ip: str, package_name: str, force_reboot: bool = False) -> str:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            key = paramiko.RSAKey.from_private_key_file(os.getenv("UBUNTU_SSH_KEY_PATH"), password=os.getenv("UBUNTU_SSH_PASSPHRASE"))
            ssh.connect(hostname=target_ip, username=os.getenv("UBUNTU_SSH_USER"), pkey=key, timeout=30)
            cmd = f"sudo apt-get update && sudo apt-get install --only-upgrade -y {shlex.quote(package_name)}"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode('utf-8')
            ssh.close()
            return out
        except Exception as e:
            return f"Error: {str(e)}"

class FeedbackQuerySchema(BaseModel):
    target: str = Field(..., description="The target IP, domain, or CVE to check for historical human feedback.")

class FeedbackQueryTool(BaseTool):
    name: str = "feedback_query_tool"
    description: str = "Query the internal database for historical human decisions (approved/denied) and feedback notes for a specific target. ALWAYS check this before proposing remediation."
    args_schema: Type[BaseModel] = FeedbackQuerySchema
    func: Any = lambda x: x 

    async def _arun(self, target: str) -> str:
        try:
            feedback = await db.get_feedback_for_target(target)
            if not feedback: return f"No historical human feedback found for target: {target}"
            summary = [f"Found {len(feedback)} feedback entries for {target}:"]
            for f in feedback: summary.append(f"- [{f['created_at']}] {f['username']} DECISION: {f['decision']} | NOTES: {f['feedback_notes']}")
            return "\n".join(summary)
        except Exception as e: return f"Error: {str(e)}"

    def _run(self, target: str) -> str:
        return asyncio.run(self._arun(target))

class KaliCommandSchema(BaseModel):
    command: str = Field(..., description="The full shell command to execute on the Kali Linux host (e.g., 'msfconsole -q -x \"search cve:2024-38140; exit\"').")

class KaliOffensiveTool(BaseTool):
    name: str = "kali_offensive_tool"
    description: str = "Execute offensive security commands (msfconsole, searchsploit, nikto) on a remote Kali Linux host via SSH."
    args_schema: Type[BaseModel] = KaliCommandSchema
    func: Any = lambda x: x 

    def _run(self, command: str) -> str:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            key = paramiko.RSAKey.from_private_key_file(os.getenv("KALI_SSH_KEY_PATH"), password=os.getenv("KALI_SSH_PASSPHRASE"))
            ssh.connect(hostname=os.getenv("KALI_SSH_HOST"), username=os.getenv("KALI_SSH_USER"), pkey=key, timeout=60)
            stdin, stdout, stderr = ssh.exec_command(command)
            out = stdout.read().decode('utf-8')
            ssh.close()
            return out
        except Exception as e: return f"Error: {str(e)}"
