# Ransomware Exposure & Priority Remediation Report
**Date:** April 25, 2026
**Scope:** 224 Assets Vulnerable to Ransomware-Linked CVEs

## Executive Summary
Analysis of 14.7 million vulnerabilities across 400,000 assets identifies 224 assets with active "Known Ransomware Use" CVEs (per CISA KEV). Risk is concentrated in the on-premise infrastructure and remote access points.

## 1. High-Priority Infrastructure Exposure
The following servers represent critical entry points and lateral movement hubs.

| Asset Hostname | IP Address | CVE | Vulnerability | Impact |
| :--- | :--- | :--- | :--- | :--- |
| **BETA-EXCHANGE** | 10.219.4.141 | CVE-2021-26855 | ProxyLogon | Initial Access / Data Theft |
| **SPREGEXC2019** | 10.219.19.227 | CVE-2021-26855 | ProxyLogon | Initial Access / Data Theft |
| **O-HV2008R2** | 10.19.100.81 | CVE-2019-0708 | BlueKeep | Wormable Lateral Movement |
| **HV8VM1** | 10.19.99.173 | CVE-2019-0708 | BlueKeep | Lateral Movement to Hosts |

## 2. Direct Public Access Risks
Assets confirmed or inherently public-facing with active ransomware vulnerabilities.

| Asset Name | Primary IP | Exposure Type | Vulnerability |
| :--- | :--- | :--- | :--- |
| **amermacrx37fdw2hd** | 10.0.0.197 | Public IP (Wiz) | Active CVE |
| **carbon.local** | 192.168.1.20 | Public IP (Azure) | Active CVE |
| **Citrix Gateways** | Multiple | Role-Based Public | Citrix Bleed |

## 3. Remediation Recommendations
1. **Isolate & Patch Exchange:** Prioritize the 10.219.x.x subnet.
2. **Secure Remote Access:** Remediation for Citrix Bleed (CVE-2023-4966) is critical to prevent session hijacking.
3. **Legacy Protocol Hardening:** Disable SMBv1/RDP on 10.19.x.x subnet or protect with MFA/VPN.
