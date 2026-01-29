# Function Best Practices Checklist

> **Source**: Moved from CLAUDE.md § Writing Functions Best Practices
> **Purpose**: Loaded on-demand when PE-Reviewer evaluates function quality

When evaluating whether a function is good, use this checklist:

## 1. Readability Test
**Can you read the function and HONESTLY easily follow what it's doing?**
- If yes, then stop here (function is probably fine)
- If no, continue with remaining checks

## 2. Cyclomatic Complexity
**Does the function have very high cyclomatic complexity?**
- Count independent paths (or number of nested if-else as proxy)
- High complexity is sketchy and needs refactoring
- **Tool**: Run `scripts/cyclomatic-complexity.py` to get objective score
- **Threshold**: Flag if >10

## 3. Data Structures & Algorithms
**Are there common data structures/algorithms that would simplify this?**
- Parsers, trees, stacks/queues, maps, sets
- Often algorithmic approaches are clearer than procedural

## 4. Unused Parameters
**Are there any unused parameters in the function?**
- Remove them (dead code)

## 5. Type Casts
**Are there any unnecessary type casts?**
- Can they be moved to function arguments for better type safety?

## 6. Testability
**Is the function easily testable without mocking core features?**
- SQL queries, redis, external APIs
- If not mockable directly, can it be tested in integration tests?

## 7. Hidden Dependencies
**Are there hidden untested dependencies or values that can be factored out?**
- Only care about non-trivial dependencies that can change/affect the function
- Pass dependencies as arguments for explicit contracts

## 8. Naming
**Brainstorm 3 better function names**
- Is the current name the best?
- Is it consistent with the rest of the codebase?

---

## Refactoring Guidelines

**IMPORTANT**: You SHOULD NOT refactor out a separate function unless there is a compelling need:

### ✅ DO refactor when:
- The refactored function is used in more than one place (DRY principle)
- The refactored function is easily unit testable while the original is not AND you can't test it any other way
- The original function is extremely hard to follow and you resort to putting comments everywhere just to explain it

### ❌ DON'T refactor when:
- Function is only used once
- Function is already testable
- Function is understandable without excessive comments
- Refactoring would create unnecessary abstraction
