# QRALPH Self-Healing Protocol v4.0

## Trigger Conditions

Self-healing activates when:
- Test failure
- Type error (tsc --noEmit fails)
- Lint error
- Build failure
- Agent-flagged issue with `auto_fix: true`
- Teammate reports error via SendMessage

## Healing Strategy

### Pattern Matching (v4.0)

Before escalating models, the healer checks for known patterns:

1. **Normalize error**: Strip paths, line numbers, timestamps, memory addresses
2. **Hash signature**: SHA-256 of normalized error (first 16 chars)
3. **Lookup**: Check `healing-patterns.json` for matching signature
4. **If known fix exists**: Apply it directly with haiku (cheapest model)
5. **If only failed fixes exist**: Skip them, try new approaches
6. **If novel error**: Proceed with model escalation

### Escalating Model Tiers

| Attempt | Model | Strategy | Token Budget |
|---------|-------|----------|--------------|
| 1-2 | Haiku | Simple fix (imports, typos, formatting) | 5K |
| 3-4 | Sonnet | Context-aware fix (type errors, logic) | 10K |
| 5 | Opus | Deep analysis (architecture, complex bugs) | 20K |

### Catastrophic Rollback (v4.0)

On 3+ consecutive healing failures:
1. Save corrupted state to `healing-attempts/corrupted-state-<timestamp>.json`
2. Find last valid checkpoint (validated via `validate_state`)
3. Restore checkpoint, reset `heal_attempts` to 0, clear `error_counts`
4. Log `CATASTROPHIC ROLLBACK` to `decisions.log`

### Long-term Memory Integration (v4.0)

Before healing:
1. Query SQLite memory store for known resolutions
2. If `successful_workaround` found, apply directly
3. If `failed_approach` found, skip it
4. After healing, record outcome for future reference

### Algorithm

```python
def heal(error_message):
    # Check known patterns first
    known = match_healing_pattern(error_message, project_path)
    if known and known.get("successful_fix"):
        apply_fix(known["successful_fix"], model="haiku")
        return

    # Check long-term memory
    memory_result = memory_store.check(error_message)
    if memory_result.get("tried_before"):
        skip_fixes = [r["description"] for r in memory_result["results"]]

    # Escalating model tiers
    for attempt in range(1, 6):
        context = build_healing_context(state, error_message)
        fix = generate_fix(error_message, context, model)
        apply_fix(fix)

        if tests_pass():
            record_healing_outcome(error_message, fix, "success")
            break
        else:
            record_healing_outcome(error_message, fix, "failed")
            rollback(fix)

        # Catastrophic rollback after 3 consecutive failures
        if attempt >= 3:
            catastrophic_rollback(state, project_path)
```

## Team Integration

1. **Teammate-assisted healing**: If a specific agent flagged the issue, they can propose the fix via SendMessage
2. **Specialist spawning**: For complex fixes, spawn a new teammate with the right `subagent_type` (e.g., `debugger`)
3. **Collaborative diagnosis**: Team lead can broadcast the error to all active teammates for input

## Logging

### Healing Attempt Log

Location: `.qralph/projects/NNN/healing-attempts/`

### Healing Patterns DB (v4.0)

Location: `.qralph/projects/NNN/healing-attempts/healing-patterns.json`

```json
{
  "patterns": [{
    "error_signature": "a1b2c3d4e5f6g7h8",
    "error_type": "import_error",
    "normalized_error": "No module named <PATH>foo",
    "fixes_attempted": [
      {"description": "pip install foo", "result": "failed"},
      {"description": "pip install foo-lib", "result": "success"}
    ],
    "successful_fix": "pip install foo-lib",
    "first_seen": "2025-01-15T10:00:00",
    "last_seen": "2025-01-16T14:30:00"
  }]
}
```

## Circuit Breakers

| Condition | Action |
|-----------|--------|
| Same error 3x across problems | HALT - systemic issue |
| Total healing tokens > 50K | Pause, ask to continue |
| File modified > 5 times | Flag for review |
| Healing creates new errors | Rollback all, flag |
| 3+ orphan processes | Write PAUSE to CONTROL.md |

## Rollback Protocol

1. Git stash current changes
2. Restore from last good checkpoint
3. Log rollback reason
4. Increment attempt counter
5. Try next strategy

Catastrophic rollback (3+ failures):
1. Save corrupted state for forensics
2. Restore last valid checkpoint
3. Reset all counters
4. Log to decisions.log
