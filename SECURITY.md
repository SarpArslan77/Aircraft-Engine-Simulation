# Security Policy

We take the security of this repository, its toolchain, and its contributors seriously. This policy outlines how to report security vulnerabilities, sensitive data exposures and supply-chain threats responsibly.

---

## 1. Supported Versions

Security patches and dependency updates are applied exclusively to the primary branch:

| Version / Branch | Supported | Notes |
| :--- | :---: | :--- |
| `main` | :white_check_mark: | Actively monitored for security vulnerabilities and dependency updates |
| Feature / Development Branches | :x: | Not officially supported; findings must be reproducible on `main` |

---

## 2. In-Scope Security Vulnerabilities

Please report any finding that poses a cybersecurity, data privacy, or infrastructure risk, including but not limited to:

* **Secret & Credential Exposure:** Accidentally committed API keys, tokens, SSH keys, private certificates, or internal infrastructure credentials.
* **Personally Identifiable Information (PII) / Data Privacy Leaks:** Exposure of private personal data, non-anonymized system paths, local host metadata, or internal organizational identifiers.
* **CI/CD & Infrastructure Exploits:** Remote code execution (RCE), command injection, workflow expression injection, or unauthorized artifact tampering within GitHub Actions pipelines (`.github/workflows/*.yml`).
* **Supply-Chain & Dependency Poisoning:** Malicious packages, compromised dependencies in `requirements.txt` or toolchain scripts, or untrusted binary download vectors.
* **Malicious Payloads & Tainted Test Data:** Vulnerabilities where untrusted input files, test cases, or script arguments could trigger buffer overflows, shell escapes, or arbitrary file overwrites on user or runner machines.

---

## 3. Reporting a Vulnerability

**Please do NOT report security vulnerabilities or sensitive data leaks through public GitHub Issues, Pull Requests, or Discussions.**

Public disclosure exposes users and infrastructure to immediate exploitation before a remediation can be deployed.

### Preferred Reporting Channel: GitHub Private Vulnerability Reporting

Submit your findings privately via GitHub's integrated security advisories:

1. Navigate to the **[Security Advisories](https://github.com/SarpArslan77/fpga-jet-engine-simulator/security/advisories)** page.
2. Click **"Report a vulnerability"** (or **"New draft security advisory"**).
3. Provide details according to the section below.

### Alternative Reporting Channel

If GitHub Private Reporting is unavailable, reach out to the project maintainer directly:
* **Maintainer:** Sarp Arslan ([@SarpArslan77](https://github.com/SarpArslan77))
* **Subject:** `[SECURITY DISCLOSURE] fpga-jet-engine-simulator - <Summary>`

---

## 4. What to Include in a Report

To help us triage and remediate the issue quickly, please provide:

1. **Vulnerability Type:** (e.g., exposed token, CI injection, supply-chain defect, PII leak).
2. **Affected Asset / Location:** File path, commit SHA, workflow name, or dependency reference.
3. **Step-by-Step Proof of Concept (PoC):** Minimal, reproducible steps demonstrating the issue without causing intentional harm or exfiltrating data.
4. **Impact Assessment:** Real-world consequences (e.g., repository hijacking, privilege escalation, credential theft).
5. **Remediation Suggestions:** Recommended fixes, package upgrades, or git history sanitization steps (if known).

---

## 5. Response & Triage Commitments

* **Initial Acknowledgment:** Within **48 hours** of report submission.
* **Triage & Validation:** Within **5 business days**, confirming severity and reproducibility.
* **Remediation & Patching:** High-priority leaks or exploitable flaws will be patched as rapidly as possible, followed by coordinated advisory publication.
* **Git History Scrubbing:** In the event of leaked credentials or PII, git history will be scrubbed immediately using tools like `git-filter-repo` or BFG Repo-Cleaner, and all affected secrets will be revoked immediately.

---

## 6. Responsible Disclosure & Safe Harbor

We consider security research conducted in good faith to be authorized and beneficial. If you make a reasonable effort to avoid privacy violations, data destruction, and service interruption, we will not pursue legal action or report your account to law enforcement or platform operators.