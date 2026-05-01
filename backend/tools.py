import os
import subprocess
import json
import psycopg2
import winrm
import paramiko
from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from logger_config import logger

class IndicatorSchema(BaseModel):
    indicator: str = Field(..., description="The IP address, domain, hostname, file hash, or CVE ID to investigate.")
    type: str = Field(..., description="The type of indicator (ip, domain, hash, cve).")

import asyncio
from database.db_helper import db

class ThreatIntelTool(BaseTool):
    name: str = "threat_intel_enricher"
    description: str = "Enrich an IP, domain, or file hash using multiple threat intelligence sources (VT, GreyNoise, OTX) and get a consensus score."
    args_schema: Type[BaseModel] = IndicatorSchema

    async def _arun(self, indicator: str, type: str) -> str:
        logger.info(f"TOOL - Running ThreatIntelTool for {type}: {indicator}")
        try:
            # 1. Check Knowledge Cache
            cached = await db.get_cached_indicator(indicator)
            if cached:
                logger.info(f"TOOL - Cache HIT for {indicator}")
                return json.dumps(cached, indent=2)

            # 2. Run external lookup
            # ti-master-enricher supports ip, domain, and hash
            script_path = os.path.join(os.getcwd(), "..", "ti-master-enricher", "scripts", "enrich_master.cjs")
            result = subprocess.run(
                ["node", script_path, type, indicator],
                capture_output=True,
                text=True,
                check=True
            )
            
            output = result.stdout
            try:
                # Attempt to parse as JSON for caching
                result_json = json.loads(output)
                await db.cache_indicator(indicator, type, result_json)
            except Exception as ce:
                logger.warning(f"TOOL - Failed to cache result for {indicator}: {str(ce)}")

            logger.info(f"TOOL - ThreatIntelTool output received for {indicator}")
            return output
        except subprocess.CalledProcessError as e:
            logger.error(f"TOOL - ThreatIntelTool error for {indicator}: {e.stderr}")
            return f"Error executing threat intel enricher: {e.stderr}"
        except Exception as e:
            logger.error(f"TOOL - ThreatIntelTool unexpected error for {indicator}: {str(e)}")
            return f"An unexpected error occurred: {str(e)}"

    def _run(self, indicator: str, type: str) -> str:
        # Fallback for sync execution if needed
        return asyncio.run(self._arun(indicator, type))


class VulnerabilityValidatorTool(BaseTool):
    name: str = "vulnerability_validator"
    description: str = "Validate a specific CVE or vulnerability against a target asset using active scans."
    args_schema: Type[BaseModel] = IndicatorSchema

    def _run(self, indicator: str, type: str) -> str:
        logger.info(f"TOOL - Running VulnerabilityValidatorTool for {indicator}")
        try:
            # This tool is used when type is 'cve'
            script_path = os.path.join(os.getcwd(), "..", "vulnerability-validator", "scripts", "scan_vuln.cjs")
            result = subprocess.run(
                ["node", script_path, indicator],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"TOOL - VulnerabilityValidatorTool output received for {indicator}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"TOOL - VulnerabilityValidatorTool error for {indicator}: {e.stderr}")
            return f"Error executing vulnerability validator: {e.stderr}"
        except Exception as e:
            logger.error(f"TOOL - VulnerabilityValidatorTool unexpected error for {indicator}: {str(e)}")
            return f"An unexpected error occurred: {str(e)}"

class SecurityPrioritizerTool(BaseTool):
    name: str = "security_prioritizer"
    description: str = "Query the PostgreSQL database to get a prioritized list of security findings across Tenable, Wiz, and CISA KEV."

    def _run(self) -> str:
        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST"),
                port=os.getenv("POSTGRES_PORT"),
                database=os.getenv("POSTGRES_DATABASE"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD")
            )
            cur = conn.cursor()
            
            query = """
            WITH 
                all_vulns AS (
                    SELECT 
                        tf.cve as cve_id,
                        ta.hostname,
                        ta.ipv4 as ip_address,
                        'Tenable' as source,
                        tf.cvss_score
                    FROM public.tenable_findings tf
                    JOIN public.tenable_assets ta ON tf.asset_id = ta.id
                    
                    UNION ALL
                    
                    SELECT 
                        wv.cve_id,
                        wi.name as hostname,
                        NULL as ip_address, 
                        'Wiz' as source,
                        wv.cvss_score
                    FROM public.wiz_vulnerabilities wv
                    JOIN public.wiz_inventory wi ON wv.resource_id = wi.id

                    UNION ALL

                    SELECT 
                        UNNEST(iv.cves) as cve_id,
                        ia.hostname,
                        ia.ip_addresses[1] as ip_address,
                        'InsightVM' as source,
                        COALESCE(iv.cvss_v3_score, iv.cvss_v2_score) as cvss_score
                    FROM public.insightvm_findings ifnd
                    JOIN public.insightvm_vulnerabilities iv ON ifnd.vulnerability_id = iv.id
                    JOIN public.insightvm_assets ia ON ifnd.asset_id = ia.id
                ),
                prioritized_findings AS (
                    SELECT 
                        v.cve_id,
                        v.hostname,
                        v.ip_address,
                        MAX(v.cvss_score) as max_cvss,
                        STRING_AGG(DISTINCT v.source, ', ') as sources,
                        EXISTS (SELECT 1 FROM public.cisa_kev ck WHERE ck.cve_id = v.cve_id) as in_cisa_kev,
                        EXISTS (SELECT 1 FROM public.tenable_asm_assets asm WHERE asm.hostname = v.hostname OR asm.ip_address = v.ip_address) as in_asm,
                        EXISTS (SELECT 1 FROM public.rapid7_assets r7 WHERE r7.name = v.hostname OR v.ip_address = ANY(r7.ip_addresses)) as in_insightidr,
                        EXISTS (SELECT 1 FROM public.phpipam_assets ipam WHERE (ipam.hostname = v.hostname OR ipam.ip_address = v.ip_address) AND (ipam.subnet_description ILIKE '%MGMT%' OR ipam.subnet_description ILIKE '%OOB%')) as in_mgmt_subnet,
                        EXISTS (SELECT 1 FROM public.phpipam_assets ipam WHERE (ipam.hostname = v.hostname OR ipam.ip_address = v.ip_address) AND ipam.is_gateway = true) as is_gateway
                    FROM all_vulns v
                    GROUP BY v.cve_id, v.hostname, v.ip_address
                )
            SELECT 
                p.cve_id,
                ck.vulnerability_name,
                p.hostname,
                p.sources,
                p.max_cvss,
                (
                    COALESCE(p.max_cvss, 0) + 
                    (CASE WHEN p.in_cisa_kev THEN 100 ELSE 0 END) + 
                    (CASE WHEN p.in_asm THEN 50 ELSE 0 END) + 
                    (CASE WHEN p.in_insightidr THEN 15 ELSE 0 END) + 
                    (CASE WHEN p.in_mgmt_subnet THEN 30 ELSE 0 END) + 
                    (CASE WHEN p.is_gateway THEN 20 ELSE 0 END) + 
                    (CASE WHEN p.sources LIKE '%,%' THEN 20 ELSE 0 END)
                ) as priority_score
            FROM prioritized_findings p
            LEFT JOIN public.cisa_kev ck ON p.cve_id = ck.cve_id
            ORDER BY priority_score DESC
            LIMIT 20;
            """
            
            cur.execute(query)
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
            
            results = []
            for row in rows:
                results.append(dict(zip(colnames, row)))
            
            cur.close()
            conn.close()
            
            logger.info(f"TOOL - SecurityPrioritizerTool retrieved {len(results)} findings.")
            return json.dumps(results, indent=2, default=str)
        except Exception as e:
            logger.error(f"TOOL - SecurityPrioritizerTool DB Error: {str(e)}")
            return f"Error querying database: {str(e)}"

class EmailReportSchema(BaseModel):
    subject: str = Field(..., description="The subject of the email report.")
    content: str = Field(..., description="The body content of the security report.")
    recipient: str = Field(..., description="The email address of the recipient.")

class EmailReporterTool(BaseTool):
    name: str = "security_email_reporter"
    description: str = "Send a security report via email to a stakeholder."
    args_schema: Type[BaseModel] = EmailReportSchema

    def _run(self, subject: str, content: str, recipient: str) -> str:
        logger.info(f"TOOL - Sending Email Report to {recipient}: {subject}")
        try:
            script_path = os.path.join(os.getcwd(), "..", "asset-email-reporter", "scripts", "send_email.cjs")
            result = subprocess.run(
                ["node", script_path, recipient, subject, content],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"TOOL - Email successfully sent to {recipient}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"TOOL - Email delivery failed for {recipient}: {e.stderr}")
            return f"Error sending email: {e.stderr}"
        except Exception as e:
            logger.error(f"TOOL - Email delivery unexpected error for {recipient}: {str(e)}")
            return f"An unexpected error occurred: {str(e)}"

class RemediationSchema(BaseModel):
    target_ip: str = Field(..., description="The IP address or hostname of the Windows asset.")
    kb_id: str = Field(..., description="The KB article ID to install (e.g., 'KB5041571').")
    reboot_allowed: bool = Field(default=False, description="Whether to allow automatic reboots if required.")

class WindowsRemediationTool(BaseTool):
    name: str = "windows_remediator"
    description: str = "Execute remote patch installation on a Windows asset via WinRM using PSWindowsUpdate."
    args_schema: Type[BaseModel] = RemediationSchema

    def _run(self, target_ip: str, kb_id: str, reboot_allowed: bool = False) -> str:
        logger.info(f"TOOL - Running WindowsRemediationTool for {target_ip} (KB: {kb_id})")
        user = os.getenv("WINRM_USER")
        password = os.getenv("WINRM_PASSWORD")
        transport = os.getenv("WINRM_TRANSPORT", "ntlm")

        if not user or not password:
            logger.error("TOOL - WindowsRemediationTool: Missing WinRM credentials.")
            return "Error: WINRM_USER or WINRM_PASSWORD not set in environment."

        try:
            session = winrm.Session(target_ip, auth=(user, password), transport=transport)
            
            reboot_flag = "-AutoReboot" if reboot_allowed else ""
            
            # PowerShell script logic per design spec
            ps_script = f"""
            $ErrorActionPreference = 'Stop'
            if (-not (Get-Module -ListAvailable -Name PSWindowsUpdate)) {{
                Write-Host "Installing PSWindowsUpdate module..."
                Install-Module -Name PSWindowsUpdate -Force -SkipPublisherCheck -Scope CurrentUser
            }}
            
            Write-Host "Attempting to install patch {kb_id}..."
            Get-WindowsUpdate -KBArticleID "{kb_id}" -Install -AcceptAll {reboot_flag}
            """
            
            result = session.run_ps(ps_script)
            
            output = result.std_out.decode('utf-8')
            error = result.std_err.decode('utf-8')
            
            if result.status_code == 0:
                logger.info(f"TOOL - WindowsRemediationTool SUCCESS for {target_ip}")
                return f"Successfully executed remediation on {target_ip}:\n{output}"
            else:
                logger.error(f"TOOL - WindowsRemediationTool FAILED for {target_ip} (Code {result.status_code})")
                return f"Error executing remediation on {target_ip} (Code: {result.status_code}):\n{error}\nOutput:\n{output}"
                
        except Exception as e:
            logger.error(f"TOOL - WindowsRemediationTool unexpected error for {target_ip}: {str(e)}")
            return f"An unexpected error occurred during WinRM session: {str(e)}"

class MacOSRemediationSchema(BaseModel):
    target_ip: str = Field(..., description="The IP address or hostname of the macOS asset.")
    update_label: str = Field(..., description="The specific software update label to install.")
    force_reboot: bool = Field(default=False, description="Whether to force a reboot if required (default is False).")

import shlex

class MacOSRemediationTool(BaseTool):
    name: str = "macos_remediation_tool"
    description: str = "Connect to a remote macOS asset via SSH and install a specific software update using softwareupdate."
    args_schema: Type[BaseModel] = MacOSRemediationSchema

    def _run(self, target_ip: str, update_label: str, force_reboot: bool = False) -> str:
        logger.info(f"TOOL - Running MacOSRemediationTool for {target_ip} (Update: {update_label})")
        try:
            user = os.getenv("MACOS_SSH_USER")
            key_path = os.getenv("MACOS_SSH_KEY_PATH")
            passphrase = os.getenv("MACOS_SSH_PASSPHRASE")
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Load private key
            key = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
            
            ssh.connect(hostname=target_ip, username=user, pkey=key, timeout=30)
            
            # 1. Pre-check: List updates to verify the label
            _, stdout, _ = ssh.exec_command("softwareupdate --list")
            list_output = stdout.read().decode('utf-8')
            if update_label not in list_output:
                ssh.close()
                logger.error(f"TOOL - MacOSRemediationTool: Update {update_label} not found on {target_ip}")
                return f"ERROR: Update label '{update_label}' not found in available updates.\nList: {list_output}"
            
            # 2. Execute installation
            reboot_flag = "--restart" if force_reboot else ""
            quoted_label = shlex.quote(update_label)
            cmd = f"sudo softwareupdate --install {quoted_label} {reboot_flag}"
            
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8')
            ssh.close()
            
            if exit_status == 0:
                logger.info(f"TOOL - MacOSRemediationTool SUCCESS for {target_ip}")
                if "Restart Required" in out or "must be restarted" in out:
                    return f"RESTART_REQUIRED: Update installed but asset requires a reboot.\nOutput: {out}"
                return f"SUCCESS: macOS Update '{update_label}' installed.\nOutput: {out}"
            else:
                logger.error(f"TOOL - MacOSRemediationTool FAILED for {target_ip} (Status {exit_status})")
                return f"FAILED: Exit Status {exit_status}.\nError: {err}\nOutput: {out}"
                
        except Exception as e:
            logger.error(f"TOOL - MacOSRemediationTool unexpected error for {target_ip}: {str(e)}")
            return f"ERROR: SSH Connection or macOS execution failed: {str(e)}"

class UbuntuRemediationSchema(BaseModel):
    target_ip: str = Field(..., description="The IP address or hostname of the Ubuntu asset.")
    package_name: str = Field(..., description="The name of the package to update (e.g., 'openssl').")
    force_reboot: bool = Field(default=False, description="Whether to force a reboot if required (default is False).")

class UbuntuRemediationTool(BaseTool):
    name: str = "ubuntu_remediation_tool"
    description: str = "Connect to a remote Ubuntu asset via SSH and install a specific package update using apt-get."
    args_schema: Type[BaseModel] = UbuntuRemediationSchema

    def _run(self, target_ip: str, package_name: str, force_reboot: bool = False) -> str:
        logger.info(f"TOOL - Running UbuntuRemediationTool for {target_ip} (Package: {package_name})")
        try:
            user = os.getenv("UBUNTU_SSH_USER")
            key_path = os.getenv("UBUNTU_SSH_KEY_PATH")
            passphrase = os.getenv("UBUNTU_SSH_PASSPHRASE")
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Load private key
            key = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
            
            ssh.connect(hostname=target_ip, username=user, pkey=key, timeout=30)
            
            # 1. Update cache
            ssh.exec_command("sudo apt-get update")
            
            # 2. Execute installation
            quoted_package = shlex.quote(package_name)
            cmd = f"sudo apt-get install --only-upgrade -y {quoted_package}"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8')
            
            if exit_status != 0:
                ssh.close()
                logger.error(f"TOOL - UbuntuRemediationTool FAILED for {target_ip} (Status {exit_status})")
                return f"FAILED: Status {exit_status}.\nError: {err}\nOutput: {out}"
            
            # 3. Check for reboot required
            _, stdout_reboot, _ = ssh.exec_command("[ -f /var/run/reboot-required ] && echo 'YES' || echo 'NO'")
            reboot_needed = stdout_reboot.read().decode('utf-8').strip() == 'YES'
            
            logger.info(f"TOOL - UbuntuRemediationTool SUCCESS for {target_ip}")
            if reboot_needed and force_reboot:
                ssh.exec_command("sudo reboot")
                ssh.close()
                return f"SUCCESS: Package '{package_name}' updated and system rebooted."
            
            ssh.close()
            
            if reboot_needed:
                return f"RESTART_REQUIRED: Package '{package_name}' updated but system requires a reboot."
            
            return f"SUCCESS: Package '{package_name}' updated."
                
        except Exception as e:
            logger.error(f"TOOL - UbuntuRemediationTool unexpected error for {target_ip}: {str(e)}")
            return f"ERROR: SSH Connection or Ubuntu execution failed: {str(e)}"

class KaliCommandSchema(BaseModel):
    command: str = Field(..., description="The full shell command to execute on the Kali Linux host (e.g., 'msfconsole -q -x \"search cve:2024-38140; exit\"').")

class FeedbackQuerySchema(BaseModel):
    target: str = Field(..., description="The target IP, domain, or CVE to check for historical human feedback.")

class FeedbackQueryTool(BaseTool):
    name: str = "feedback_query_tool"
    description: str = "Query the internal database for historical human decisions (approved/denied) and feedback notes for a specific target. ALWAYS check this before proposing remediation."
    args_schema: Type[BaseModel] = FeedbackQuerySchema

    async def _arun(self, target: str) -> str:
        logger.info(f"TOOL - Querying feedback for {target}")
        try:
            feedback = await db.get_feedback_for_target(target)
            if not feedback:
                return f"No historical human feedback found for target: {target}"
            
            summary = [f"Found {len(feedback)} feedback entries for {target}:"]
            for f in feedback:
                summary.append(f"- [{f['created_at']}] {f['username']} DECISION: {f['decision']} | NOTES: {f['feedback_notes']}")
            
            return "\n".join(summary)
        except Exception as e:
            logger.error(f"TOOL - FeedbackQueryTool error for {target}: {str(e)}")
            return f"Error querying feedback database: {str(e)}"

    def _run(self, target: str) -> str:
        return asyncio.run(self._arun(target))

class KaliOffensiveTool(BaseTool):
    name: str = "kali_offensive_tool"
    description: str = "Execute offensive security commands (msfconsole, searchsploit, nikto) on a remote Kali Linux host via SSH."
    args_schema: Type[BaseModel] = KaliCommandSchema

    def _run(self, command: str) -> str:
        logger.info(f"TOOL - Running KaliOffensiveTool command: {command}")
        
        # Security: Validate command starts with authorized tool
        allowed_tools = ["msfconsole", "searchsploit", "nikto", "nmap"]
        parts = shlex.split(command)
        if not parts or parts[0] not in allowed_tools:
            return f"ERROR: Unauthorized tool. Allowed: {', '.join(allowed_tools)}"
        
        # Re-assemble safely
        safe_command = " ".join(shlex.quote(p) for p in parts)
        
        try:
            user = os.getenv("KALI_SSH_USER")
            host = os.getenv("KALI_SSH_HOST")
            key_path = os.getenv("KALI_SSH_KEY_PATH")
            passphrase = os.getenv("KALI_SSH_PASSPHRASE")

            if not user or not host or not key_path:
                logger.error("TOOL - KaliOffensiveTool: Missing SSH configuration.")
                return "ERROR: KALI_SSH_USER, KALI_SSH_HOST, or KALI_SSH_KEY_PATH not set in environment."
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            key = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
            ssh.connect(hostname=host, username=user, pkey=key, timeout=60)
            
            stdin, stdout, stderr = ssh.exec_command(safe_command)
            
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8')
            ssh.close()
            
            logger.info(f"TOOL - KaliOffensiveTool command complete (Status {exit_status})")
            return f"COMMAND_OUTPUT (Exit {exit_status}):\n{out}\nERRORS:\n{err}"
                
        except Exception as e:
            logger.error(f"TOOL - KaliOffensiveTool unexpected error: {str(e)}")
            return f"ERROR: Kali SSH connection or execution failed: {str(e)}"
