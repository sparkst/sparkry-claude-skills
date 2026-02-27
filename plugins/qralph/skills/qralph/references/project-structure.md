# QRALPH Project Structure

## Directory Layout

```
projects/
├── INDEX.md                          # Auto-maintained project list
├── .qralph-project-lock              # Prevents numbering race conditions
├── .qralph-templates/                # File templates
│   └── STATUS.md
│
├── 001-feature-name/
│   ├── .qralph/
│   │   ├── state.json                # Current state machine position
│   │   ├── STATUS.md                 # Real-time status (every 30s)
│   │   ├── CONTROL.md                # User intervention commands
│   │   ├── QUESTIONS.md              # Clarifying questions (start)
│   │   ├── ASSUMPTIONS.md            # Logged defaults when no answer
│   │   ├── decisions.log             # All decisions made
│   │   ├── agent-outputs/            # Raw agent reviews
│   │   │   ├── architecture-advisor.md
│   │   │   ├── security-reviewer.md
│   │   │   └── ...
│   │   ├── healing-attempts/         # Self-healing audit trail
│   │   │   ├── attempt-1.md
│   │   │   └── ...
│   │   ├── checkpoints/              # Resumable state snapshots
│   │   │   ├── latest.json
│   │   │   └── ...
│   │   └── custom-personas/          # Generated personas (if any)
│   │
│   ├── requirements/                 # Generated requirements (coding mode)
│   ├── DEFERRED.md                   # Items requiring human decision
│   ├── SUMMARY.md                    # Final execution summary
│   └── UAT.md                        # User Acceptance Test
│
└── 002-next-project/
    └── ...
```

## Project Numbering

### Algorithm
```python
def get_next_project_number():
    # Acquire lock
    with lock_file(".qralph-project-lock"):
        existing = glob("projects/[0-9][0-9][0-9]-*")
        if existing:
            nums = [int(p.name[:3]) for p in existing]
            return max(nums) + 1
        return 1
```

### Naming Convention
- Format: `NNN-short-name`
- NNN: 3-digit zero-padded number (001, 002, ...)
- short-name: First 3 meaningful words, kebab-case, max 30 chars
- Example: `001-dark-mode-toggle`, `002-auth-providers`

## File Purposes

### .qralph/state.json
Current execution state for resume capability.
```json
{
  "state": "REVIEWING",
  "timestamp": "2026-01-27T14:32:01Z",
  "data": {
    "agents": ["architecture-advisor", "security-reviewer", ...],
    "agent_status": {"architecture-advisor": "complete", ...}
  }
}
```

### .qralph/STATUS.md
Real-time status for user visibility.
```markdown
# QRALPH Status: 001-dark-mode

**Phase**: REVIEWING (3/5 complete)
**Elapsed**: 4m 23s

## Agent Progress
- [x] Architecture Advisor: 3 findings
- [x] Security Reviewer: 2 findings
- [ ] Requirements: analyzing...
```

### .qralph/CONTROL.md
User intervention commands (polled every 30s).
```markdown
# Write commands here:
PAUSE
```

### .qralph/QUESTIONS.md
Clarifying questions at start.
```markdown
## Question 1
**Context**: Detected two auth patterns
**Question**: Which approach?

- A) JWT with refresh tokens
- B) Session-based auth
- C) Let me specify...

**Default (10m)**: A
**Asked**: 2026-01-27 14:32:01
```

### SUMMARY.md
Final execution summary.
```markdown
# QRALPH Summary: 001-dark-mode

## Request
Add dark mode toggle to settings

## Outcome
- **State**: COMPLETE
- **Files Changed**: 4
- **Tests Added**: 2
- **Self-Heal Attempts**: 1 (success)

## Findings Addressed
- P1: Added WCAG contrast check
- P1: Fixed theme persistence

## Next Steps
- Review SUMMARY.md
- Run manual UAT if any
```

### DEFERRED.md
Items that couldn't be auto-fixed.
```markdown
# Deferred Items

## DEFER-001: Complex Type Mismatch
**Why**: Self-healing exhausted
**Attempts**: 5
**Recommended**: Architecture review
**Owner**: [Unassigned]
```

### UAT.md
User acceptance test scenarios.
```markdown
# UAT: 001-dark-mode

## Scenarios
### UAT-001: Toggle Switch
1. Navigate to Settings
2. Click dark mode toggle
3. **Expected**: Theme changes

## Results
- [x] UAT-001: PASS
```

## INDEX.md Maintenance

Auto-updated on project create/complete:
```markdown
# QRALPH Projects

## Active
| ID | Name | State | Updated |
|----|------|-------|---------|
| 001 | dark-mode-toggle | REVIEWING | 2026-01-27 |

## Completed
| ID | Name | Outcome | Summary |
|----|------|---------|---------|
| (none yet) |
```
