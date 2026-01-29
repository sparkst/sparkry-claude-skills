# QRALPH Self-Healing Protocol

## Trigger Conditions

Self-healing activates when:
- Test failure
- Type error (tsc --noEmit fails)
- Lint error
- Build failure
- Agent-flagged issue with `auto_fix: true`

## Healing Strategy

### Escalating Model Tiers

| Attempt | Model | Strategy | Token Budget |
|---------|-------|----------|--------------|
| 1-2 | Haiku | Simple fix (imports, typos, formatting) | 5K |
| 3-4 | Sonnet | Context-aware fix (type errors, logic) | 10K |
| 5 | Opus | Deep analysis (architecture, complex bugs) | 20K |

### Algorithm

```python
for attempt in range(1, 6):
    # Select model based on attempt
    if attempt <= 2:
        model = "haiku"
        strategy = "simple_fix"
    elif attempt <= 4:
        model = "sonnet"
        strategy = "context_aware_fix"
    else:
        model = "opus"
        strategy = "deep_analysis_fix"

    # Generate and apply fix
    fix = generate_fix(problem, strategy, model)
    apply_fix(fix)

    # Test the fix
    if tests_pass():
        log_success(attempt, fix)
        git_commit(f"QRALPH: Auto-fix {problem.id}")
        break
    else:
        rollback(fix)
        log_failure(attempt, fix, test_output)
else:
    # All 5 attempts exhausted
    create_deferred_item(problem, all_attempts)
    mark_blocked(problem)
```

## Auto-Fix Categories

### Always Auto-Apply (Whitelist)

| Category | Examples |
|----------|----------|
| Import errors | Missing imports, typos in import paths |
| Formatting | Trailing whitespace, missing semicolons |
| Lint fixes | `eslint --fix` eligible issues |
| Type casts | Simple type assertions |
| Unused variables | Remove or underscore prefix |

### Never Auto-Apply (Blacklist)

| Category | Reason |
|----------|--------|
| Security vulnerabilities | Requires human judgment |
| Database schema changes | Production impact |
| API contract changes | Breaking changes |
| Business logic | Requires domain knowledge |
| Exported interface changes | Downstream impact |

## Logging

### Healing Attempt Log

Location: `projects/NNN/.qralph/healing-attempts/`

```markdown
# Healing Attempt 2/5

**Problem**: Type error in UserService.ts:42
**Strategy**: context_aware_fix
**Model**: sonnet

## Attempted Fix
```diff
- const user = fetchUser(id)
+ const user: User = await fetchUser(id)
```

## Result
- Tests: PASSED
- Applied: Yes
- Commit: abc123
```

### DEFERRED.md Entry

When healing fails:

```markdown
## DEFER-001: Type Mismatch in AuthModule

**Problem**: `AuthToken` type incompatible with `SessionToken`
**Attempts**: 5
**Last Error**: "Property 'refresh' missing in type 'AuthToken'"

### Attempts Summary
1. Haiku: Added type cast (failed - downstream error)
2. Haiku: Added missing property (failed - interface mismatch)
3. Sonnet: Created adapter (failed - circular dependency)
4. Sonnet: Unified types (failed - breaking change)
5. Opus: Recommended architecture change

### Permanent Fix Options
1. Merge AuthToken and SessionToken (3 SP, breaking)
2. Create TokenAdapter interface (2 SP, non-breaking)
3. Use discriminated union (1 SP, refactor)

**Recommended**: Option 2 - TokenAdapter
**Owner**: [Unassigned]
```

## Circuit Breakers

| Condition | Action |
|-----------|--------|
| Same error 3x across problems | HALT - systemic issue |
| Total healing tokens > 50K | Pause, ask to continue |
| File modified > 5 times | Flag for review |
| Healing creates new errors | Rollback all, flag |

## Rollback Protocol

1. Git stash current changes
2. Restore from last good checkpoint
3. Log rollback reason
4. Increment attempt counter
5. Try next strategy

If all rollbacks fail:
1. Hard reset to pre-healing state
2. Create comprehensive DEFERRED entry
3. Continue with other unrelated work
