import os
import subprocess
import json
import psycopg2
import winrm
import paramiko
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

class IndicatorSchema(BaseModel):
    indicator: str = Field(..., description="The IP address, domain, hostname, file hash, or CVE ID to investigate.")
    type: str = Field(..., description="The type of indicator (ip, domain, hash, cve).")

class ThreatIntelTool(BaseTool):
    name: str = "threat_intel_enricher"
    description: str = "Enrich an IP, domain, or file hash using multiple threat intelligence sources (VT, GreyNoise, OTX) and get a consensus score."
    args_schema: Type[BaseModel] = IndicatorSchema

    def _run(self, indicator: str, type: str) -> str:
        try:
            # ti-master-enricher supports ip, domain, and hash
            script_path = os.path.join(os.getcwd(), "..", "ti-master-enricher", "scripts", "enrich_master.cjs")
            result = subprocess.run(
                ["node", script_path, type, indicator],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error executing threat intel enricher: {e.stderr}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"

class VulnerabilityValidatorTool(BaseTool):
    name: str = "vulnerability_validator"
    description: str = "Validate a specific CVE or vulnerability against a target asset using active scans."
    args_schema: Type[BaseModel] = IndicatorSchema

    def _run(self, indicator: str, type: str) -> str:
        try:
            # This tool is used when type is 'cve'
            script_path = os.path.join(os.getcwd(), "..", "vulnerability-validator", "scripts", "scan_vuln.cjs")
            # For CVEs, the script might need specific target info; 
            # for now, we pass the indicator as the target to scan for that vuln.
            result = subprocess.run(
                ["node", script_path, indicator],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error executing vulnerability validator: {e.stderr}"
        except Exception as e:
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
            
            return json.dumps(results, indent=2, default=str)
        except Exception as e:
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
        try:
            script_path = os.path.join(os.getcwd(), "..", "asset-email-reporter", "scripts", "send_email.cjs")
            result = subprocess.run(
                ["node", script_path, recipient, subject, content],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error sending email: {e.stderr}"
        except Exception as e:
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
        user = os.getenv("WINRM_USER")
        password = os.getenv("WINRM_PASSWORD")
        transport = os.getenv("WINRM_TRANSPORT", "ntlm")

        if not user or not password:
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
                return f"Successfully executed remediation on {target_ip}:\n{output}"
            else:
                return f"Error executing remediation on {target_ip} (Code: {result.status_code}):\n{error}\nOutput:\n{output}"
                
        except Exception as e:
            return f"An unexpected error occurred during WinRM session: {str(e)}"

class MacOSRemediationSchema(BaseModel):
    target_ip: str = Field(..., description="The IP address or hostname of the macOS asset.")
    update_label: str = Field(..., description="The specific software update label to install.")
    force_reboot: bool = Field(default=False, description="Whether to force a reboot if required (default is False).")

class MacOSRemediationTool(BaseTool):
    name: str = "macos_remediation_tool"
    description: str = "Connect to a remote macOS asset via SSH and install a specific software update using softwareupdate."
    args_schema: Type[BaseModel] = MacOSRemediationSchema

    def _run(self, target_ip: str, update_label: str, force_reboot: bool = False) -> str:
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
                return f"ERROR: Update label '{update_label}' not found in available updates.\nList: {list_output}"
            
            # 2. Execute installation
            # Note: softwareupdate requires sudo for installation. 
            # This logic assumes the user has NOPASSWD sudo access for softwareupdate.
            reboot_flag = "--restart" if force_reboot else ""
            cmd = f"sudo softwareupdate --install \"{update_label}\" {reboot_flag}"
            
            stdin, stdout, stderr = ssh.exec_command(cmd)
            # Paramiko's exec_command doesn't handle interactive sudo well; 
            # if a password is required, this will fail or hang.
            
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8')
            ssh.close()
            
            if "Restart Required" in out or "must be restarted" in out:
                return f"RESTART_REQUIRED: Update installed but asset requires a reboot.\nOutput: {out}"
            
            if exit_status == 0:
                return f"SUCCESS: macOS Update '{update_label}' installed.\nOutput: {out}"
            else:
                return f"FAILED: Exit Status {exit_status}.\nError: {err}\nOutput: {out}"
                
        except Exception as e:
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
            # --only-upgrade ensures we don't install new packages
            cmd = f"sudo apt-get install --only-upgrade -y {package_name}"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8')
            
            if exit_status != 0:
                ssh.close()
                return f"FAILED: Status {exit_status}.\nError: {err}\nOutput: {out}"
            
            # 3. Check for reboot required
            _, stdout_reboot, _ = ssh.exec_command("[ -f /var/run/reboot-required ] && echo 'YES' || echo 'NO'")
            reboot_needed = stdout_reboot.read().decode('utf-8').strip() == 'YES'
            
            if reboot_needed and force_reboot:
                ssh.exec_command("sudo reboot")
                ssh.close()
                return f"SUCCESS: Package '{package_name}' updated and system rebooted."
            
            ssh.close()
            
            if reboot_needed:
                return f"RESTART_REQUIRED: Package '{package_name}' updated but system requires a reboot."
            
            return f"SUCCESS: Package '{package_name}' updated."
                
        except Exception as e:
            return f"ERROR: SSH Connection or Ubuntu execution failed: {str(e)}"
