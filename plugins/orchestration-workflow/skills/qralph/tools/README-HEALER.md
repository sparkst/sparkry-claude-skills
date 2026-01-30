# QRALPH Healer Tool

## Overview

The QRALPH Healer is a dedicated self-healing coordinator that analyzes errors, generates healing prompts, tracks healing attempts, and provides rollback capabilities.

## Quick Start

```bash
# Analyze an error
python3 qralph-healer.py analyze "No module named 'requests'"

# Record healing attempt
python3 qralph-healer.py attempt "TypeError: expected str, got int"

# Show healing history
python3 qralph-healer.py history

# Rollback to last checkpoint
python3 qralph-healer.py rollback

# Clear error counts
python3 qralph-healer.py clear

# Show healer status
python3 qralph-healer.py status
```

## Commands

### analyze

Analyze an error and suggest fix strategy without recording an attempt.

**Usage:**
```bash
python3 qralph-healer.py analyze "<error-message>"
```

**Output:**
```json
{
  "status": "analyzed",
  "error_type": "import_error",
  "severity": "recoverable",
  "suggested_model": "haiku",
  "similar_errors": 0,
  "suggested_fix": "Add missing import statement at top of file",
  "heal_prompt": "...",
  "action": "AUTO_FIX: Apply healing prompt with suggested model"
}
```

**Use Cases:**

- Quick error triage before committing to healing attempt
- Understanding error classification
- Getting healing prompt without incrementing counters

### attempt

Record a healing attempt and generate healing prompt.

**Usage:**
```bash
python3 qralph-healer.py attempt "<error-message>"
```

**Output:**
```json
{
  "status": "attempt_recorded",
  "heal_attempt": 1,
  "error_type": "import_error",
  "model": "haiku",
  "severity": "recoverable",
  "attempt_file": "healing-attempts/attempt-01.md",
  "heal_prompt": "...",
  "instruction": "Execute healing using haiku model"
}
```

**Side Effects:**

- Increments `heal_attempts` in state
- Creates `attempt-NN.md` file
- Updates circuit breaker error counts
- Logs to decisions.log

**Use Cases:**

- Recording official healing attempt
- Integrating with orchestrator heal cycle
- Tracking healing history

### history

Show all healing attempts for current project.

**Usage:**
```bash
python3 qralph-healer.py history
```

**Output:**
```json
{
  "status": "history",
  "project_id": "002-tdd-review-qralph",
  "heal_attempts": 5,
  "attempts": [
    {
      "attempt_number": 1,
      "file": "healing-attempts/attempt-01.md",
      "error_type": "import_error",
      "model": "haiku",
      "timestamp": "2026-01-27T23:49:31.041735"
    }
  ]
}
```

**Use Cases:**

- Reviewing what errors occurred
- Checking which model tiers were used
- Understanding healing progression

### rollback

Restore state from last checkpoint.

**Usage:**
```bash
python3 qralph-healer.py rollback
```

**Output:**
```json
{
  "status": "rolled_back",
  "checkpoint_file": "checkpoints/init-234530.json",
  "phase": "INIT",
  "heal_attempts": 0,
  "message": "State restored to last checkpoint"
}
```

**Side Effects:**

- Restores full state from checkpoint JSON
- Logs rollback to decisions.log

**Use Cases:**

- Healing attempt broke something
- Need to restart from known good state
- Circuit breaker tripped unexpectedly

### clear

Clear error counts and reset heal attempts to 0.

**Usage:**
```bash
python3 qralph-healer.py clear
```

**Output:**
```json
{
  "status": "cleared",
  "message": "Error counts cleared and heal attempts reset to 0"
}
```

**Side Effects:**

- Resets `heal_attempts` to 0
- Clears `circuit_breakers.error_counts` to {}
- Logs clear to decisions.log

**Use Cases:**

- Manually fixed issue causing repeated errors
- Need to retry after circuit breaker trips
- Starting fresh healing cycle

### status

Show current healer status and circuit breaker state.

**Usage:**
```bash
python3 qralph-healer.py status
```

**Output:**
```json
{
  "status": "active",
  "project_id": "002-tdd-review-qralph",
  "phase": "REVIEWING",
  "heal_attempts": 0,
  "max_heal_attempts": 5,
  "attempt_files": 5,
  "unique_errors": 0,
  "error_counts": {},
  "healing_dir": ".qralph/projects/002-tdd-review-qralph/healing-attempts"
}
```

**Use Cases:**

- Checking circuit breaker state
- Understanding how many attempts remain
- Monitoring healing progress

## Error Categories

### Recoverable Errors (Auto-Fix)

**ImportError**

- Pattern: `No module named 'X'`, `cannot import name 'Y'`
- Model: haiku
- Fix: Add import statement

**SyntaxError**

- Pattern: `SyntaxError:`, `invalid syntax`, `IndentationError`
- Model: sonnet
- Fix: Correct syntax, indentation, brackets

**TypeError**

- Pattern: `TypeError:`, `expected X but got Y`
- Model: sonnet
- Fix: Add type conversion or validation

**FileNotFoundError**

- Pattern: `No such file or directory`
- Model: haiku
- Fix: Create file or correct path

**JSONDecodeError**

- Pattern: `JSONDecodeError:`, `Invalid JSON`
- Model: haiku
- Fix: Validate and fix JSON formatting

**AttributeError**

- Pattern: `has no attribute 'X'`
- Model: sonnet
- Fix: Add missing attribute or fix reference

### Retry Errors (Wait and Retry)

**NetworkError**

- Pattern: `ConnectionError`, `TimeoutError`, `Connection refused`
- Model: haiku
- Fix: Add retry logic with backoff

### Manual Errors (User Intervention)

**PermissionError**

- Pattern: `Permission denied`, `[Errno 13]`
- Model: opus
- Fix: Manual permission changes required

### Escalate Errors (Expert Analysis)

**UnknownError**

- Pattern: Any unclassified error
- Model: opus
- Fix: Requires expert analysis

## Model Escalation

### By Attempt Number

| Attempt | Model  | Cost/1M | Use Case              |
|---------|--------|---------|------------------------|
| 1-2     | haiku  | $0.25   | Simple fixes          |
| 3-4     | sonnet | $3.00   | Complex fixes         |
| 5       | opus   | $15.00  | Architectural issues  |
| 6+      | manual | N/A     | Deferred (DEFERRED.md)|

### By Error Frequency

- **0-1 similar errors**: Use default model for error type
- **2-3 similar errors**: Escalate to sonnet
- **4+ similar errors**: Escalate to opus

## Integration with Orchestrator

### Orchestrator `cmd_heal()` Flow

1. Error detected during execution
2. Orchestrator increments `heal_attempts`
3. Orchestrator determines model tier (1-2: haiku, 3-4: sonnet, 5: opus)
4. Orchestrator creates basic attempt file
5. Orchestrator returns healing instruction

### Healer Tool Flow

1. **analyze**: Classify error and suggest strategy
2. **attempt**: Record attempt and generate detailed healing prompt
3. Claude executes healing prompt
4. **history**: Review what was tried
5. **clear**: Reset after manual fix
6. **rollback**: Restore if healing broke something

### Complementary Roles

**Orchestrator (qralph-orchestrator.py):**

- State machine management
- Phase transitions
- Circuit breaker enforcement
- Execution coordination

**Healer (qralph-healer.py):**

- Error classification
- Healing prompt generation
- History tracking
- Rollback support

## Workflow Examples

### Example 1: Simple Import Error

```bash
# 1. QRALPH encounters error during execution
# Orchestrator detects: "No module named 'requests'"

# 2. Analyze error
$ python3 qralph-healer.py analyze "No module named 'requests'"
# Output: import_error, haiku model, recoverable

# 3. Record attempt
$ python3 qralph-healer.py attempt "No module named 'requests'"
# Output: attempt-01.md created with healing prompt

# 4. Execute healing prompt using haiku model
# Claude adds: import requests

# 5. Verify fix
# QRALPH continues execution
```

### Example 2: Repeated Error with Escalation

```bash
# Attempt 1: haiku fails
$ python3 qralph-healer.py attempt "TypeError: expected str, got int"
# heal_attempts: 1, model: haiku

# Attempt 2: haiku fails again
$ python3 qralph-healer.py attempt "TypeError: expected str, got int"
# heal_attempts: 2, model: haiku

# Attempt 3: Escalated to sonnet
$ python3 qralph-healer.py attempt "TypeError: expected str, got int"
# heal_attempts: 3, model: sonnet, similar_errors: 2

# Attempt 4: sonnet fails
$ python3 qralph-healer.py attempt "TypeError: expected str, got int"
# heal_attempts: 4, model: sonnet

# Attempt 5: Final attempt with opus
$ python3 qralph-healer.py attempt "TypeError: expected str, got int"
# heal_attempts: 5, model: opus

# Attempt 6: Circuit breaker trips
# Orchestrator creates DEFERRED.md and continues

# Review history
$ python3 qralph-healer.py history
# Shows all 5 attempts with models and timestamps
```

### Example 3: Manual Fix and Clear

```bash
# Circuit breaker trips after 3 same errors
$ python3 qralph-healer.py status
# heal_attempts: 3, error_counts: {"Connection timeout": 3}

# User manually fixes connection issue
# (e.g., fixes network config, API key, etc.)

# Clear error counts to allow retry
$ python3 qralph-healer.py clear
# heal_attempts: 0, error_counts: {}

# QRALPH can now retry without circuit breaker blocking
$ python3 qralph-orchestrator.py resume 002
```

### Example 4: Rollback After Bad Fix

```bash
# Healing attempt #3 applied a fix that broke something
$ python3 qralph-healer.py rollback

# State restored to last checkpoint (before attempt #3)
# heal_attempts restored to 2
# Can try different fix approach
```

## File Locations

### State Files

- **Current state**: `.qralph/current-project.json`
- **Checkpoints**: `project/checkpoints/*.json`

### Healing Files

- **Attempt records**: `project/healing-attempts/attempt-NN.md`
- **Deferred issues**: `project/DEFERRED.md` (created by orchestrator)

### Logs

- **Decisions log**: `project/decisions.log`

## Output Format

All commands output JSON to stdout for Claude integration:

```json
{
  "status": "command_status",
  "key1": "value1",
  "key2": "value2"
}
```

**Status Values:**

- `analyzed`: Error analysis complete
- `attempt_recorded`: Healing attempt recorded
- `history`: Healing history retrieved
- `rolled_back`: State restored from checkpoint
- `cleared`: Error counts cleared
- `active`: Healer status retrieved
- `no_project`: No active QRALPH project

## Error Handling

### No Active Project

```json
{
  "error": "No active project. Run qralph-orchestrator.py init first."
}
```

**Solution:** Initialize QRALPH project first:
```bash
python3 qralph-orchestrator.py init "your request"
```

### Missing Checkpoint

```json
{
  "error": "No checkpoint found"
}
```

**Solution:** Checkpoint doesn't exist yet. Create one:
```bash
python3 qralph-orchestrator.py checkpoint INIT
```

### Invalid JSON

```json
{
  "error": "Failed to load checkpoint: Expecting value: line 1 column 1 (char 0)"
}
```

**Solution:** Checkpoint file corrupted. Reinitialize or use older checkpoint.

## Best Practices

### 1. Analyze Before Attempt

Always analyze errors first to understand classification and suggested model:

```bash
python3 qralph-healer.py analyze "<error>"
# Review output, then record attempt
python3 qralph-healer.py attempt "<error>"
```

### 2. Review History Regularly

Check healing history to identify patterns:

```bash
python3 qralph-healer.py history | jq '.attempts[] | {error_type, model}'
```

### 3. Clear After Manual Fixes

If you manually fix an issue, clear error counts:

```bash
python3 qralph-healer.py clear
```

### 4. Use Rollback Conservatively

Rollback should be last resort. Try clear first:

```bash
# First try: clear and retry
python3 qralph-healer.py clear

# If that fails: rollback
python3 qralph-healer.py rollback
```

### 5. Monitor Circuit Breakers

Check status before long operations:

```bash
python3 qralph-healer.py status | jq '{heal_attempts, unique_errors}'
```

## Troubleshooting

### Healer Not Finding Project

**Problem:** `"error": "No active project"`

**Solution:**
```bash
# Check if QRALPH project is initialized
ls .qralph/current-project.json

# If missing, initialize:
python3 qralph-orchestrator.py init "your request"
```

### Healing Attempts Not Incrementing

**Problem:** Running `attempt` but counter stays at 0

**Solution:**
```bash
# Check state file
cat .qralph/current-project.json | jq '.heal_attempts'

# If state is corrupt, rollback:
python3 qralph-healer.py rollback
```

### Error Classification Wrong

**Problem:** Error classified as "unknown_error" but should be specific type

**Solution:** Error pattern not recognized. Add pattern to `ERROR_PATTERNS` dict in `qralph-healer.py` or open issue for pattern expansion.

### Circuit Breaker Won't Reset

**Problem:** Still getting circuit breaker errors after clear

**Solution:**
```bash
# Check orchestrator state
python3 qralph-orchestrator.py status

# Orchestrator has separate circuit breakers
# Clear healer state:
python3 qralph-healer.py clear

# For orchestrator, may need to edit state file directly or rollback
```

## Version

**Healer Tool:** v1.0
**Compatible Orchestrator:** v2.1+

## Support

For issues or feature requests, see:

- Tool source: `${CLAUDE_PLUGIN_ROOT}/skills/qralph/tools/qralph-healer.py`
- Documentation: `${CLAUDE_PLUGIN_ROOT}/skills/qralph/references/`
- Project: `.qralph/projects/002-tdd-review-qralph/`
