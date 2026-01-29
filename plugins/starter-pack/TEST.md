# Starter Pack Plugin - Testing Guide

## Pre-Publishing Test Checklist

### 1. File Structure Validation

```bash
# Verify all required files exist
cd ${PROJECT_ROOT}/.qralph/projects/001-package-publish-claude/marketplace/plugins/starter-pack/

# Check structure
ls -la
ls -la .claude-plugin/
ls -la .claude-plugin/agents/
```

Expected output:
```
starter-pack/
├── .claude-plugin/
│   ├── plugin.json
│   ├── MANIFEST.md
│   └── agents/
│       ├── planner.md
│       ├── pe-reviewer.md
│       └── sde-iii.md
├── README.md
├── LICENSE
├── BUNDLE-SUMMARY.md
└── TEST.md (this file)
```

### 2. JSON Validation

```bash
# Validate plugin.json is valid JSON
python3 -m json.tool .claude-plugin/plugin.json
```

Should output formatted JSON without errors.

### 3. Agent Frontmatter Validation

```bash
# Check each agent has valid YAML frontmatter
head -10 .claude-plugin/agents/planner.md
head -10 .claude-plugin/agents/pe-reviewer.md
head -10 .claude-plugin/agents/sde-iii.md
```

Each should have:
- `---` delimiter at start
- `name:` field
- `description:` field
- `tools:` field
- `---` delimiter at end

### 4. Content Validation

```bash
# Check for sensitive data (should return nothing)
grep -r "exec-team" .claude-plugin/agents/
grep -r "SGDrive" .claude-plugin/agents/
grep -r "travis" .claude-plugin/agents/
grep -r "sparkry" .claude-plugin/agents/ | grep -v "Sparkry.ai"
```

### 5. Size Check

```bash
# Check file sizes are reasonable
du -h .claude-plugin/agents/*.md
wc -l .claude-plugin/agents/*.md
```

Expected:
- planner.md: ~115 lines (~5KB)
- pe-reviewer.md: ~200 lines (~7KB)
- sde-iii.md: ~47 lines (~1KB)

### 6. Workflow Test

Manual test of the workflow:

#### Test 1: QPLAN
```
Input: QPLAN: Create a simple REST API endpoint
Expected Output:
- Creates requirements/current.md
- Creates requirements/requirements.lock.md
- Provides story point estimate
- Lists implementation steps
```

#### Test 2: QCODE
```
Input: QCODE: Implement REQ-001 from the plan
Expected Output:
- Creates working code
- Follows plan specifications
- Includes basic error handling
```

#### Test 3: QCHECK
```
Input: QCHECK: Review the API endpoint implementation
Expected Output:
- JSON report with findings
- Security analysis
- Performance recommendations
- Test coverage suggestions
```

### 7. Documentation Test

```bash
# Check README is readable
cat README.md | head -50

# Verify all links work (manual check)
# Check installation instructions are clear
```

### 8. Installation Simulation

```bash
# Simulate installation (when Claude Code CLI is available)
# claude-code install-plugin ./starter-pack

# Verify agents are available
# claude-code list-agents

# Should show:
# - planner
# - pe-reviewer
# - sde-iii
```

### 9. Integration Test

Create a test project and run full workflow:

```bash
# Create test project
mkdir /tmp/starter-pack-test
cd /tmp/starter-pack-test

# Run workflow
QPLAN: Add authentication to a web app
QCODE: Implement basic login form
QCHECK: Review login implementation
```

Verify each step produces expected outputs.

### 10. User Acceptance

Before publishing, get feedback from 2-3 testers:

- [ ] Installation was straightforward
- [ ] README was clear and helpful
- [ ] Workflow pattern made sense
- [ ] Agents worked as expected
- [ ] Error messages were helpful
- [ ] Output quality met expectations

## Test Results Template

```markdown
## Test Results - [Date]

**Tester:** [Name]
**Environment:** [OS, Claude Code version]

### Test Results
- [ ] File structure validation: PASS/FAIL
- [ ] JSON validation: PASS/FAIL
- [ ] Agent frontmatter: PASS/FAIL
- [ ] Content validation: PASS/FAIL
- [ ] Size check: PASS/FAIL
- [ ] Workflow test: PASS/FAIL
- [ ] Documentation test: PASS/FAIL

### Issues Found
1. [Issue description]
2. [Issue description]

### Recommendations
1. [Recommendation]
2. [Recommendation]

### Overall Rating
⭐⭐⭐⭐⭐ (1-5 stars)

### Ready for Publishing?
YES / NO (if no, explain why)
```

## Known Limitations

1. No skills included (minimal bundle)
2. No sub-agents (simplified structure)
3. Generic references (no CLAUDE.md)
4. Basic documentation (not comprehensive)

These are intentional for beginner audience.

## Publishing Readiness Criteria

Before submitting to Anthropic Marketplace:

- [ ] All 10 tests pass
- [ ] At least 2 external testers approve
- [ ] No sensitive data in any file
- [ ] All documentation is clear
- [ ] JSON validates against schema
- [ ] License is correct (MIT)
- [ ] Version number is final (1.0.0)
- [ ] Author information is correct
- [ ] Keywords are appropriate

## Post-Publishing Monitoring

After publishing, monitor:
- Installation success rate
- User feedback/ratings
- Support requests
- Bug reports
- Feature requests
- Upgrade rate to dev-workflow

## Support Process

1. User reports issue via GitHub/email
2. Reproduce locally
3. Document in test results
4. Fix if critical
5. Schedule for next version if minor
6. Communicate fix timeline to user

---

**Testing Status:** Ready for Testing
**Last Updated:** 2026-01-28
**Next Review:** After first round of testing
