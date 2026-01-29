# QShortcuts Core Plugin

Core TDD development shortcuts for Claude Code. Implements a complete Test-Driven Development workflow from requirements to code review.

## Overview

This plugin provides 7 essential skills for TDD-first development:

- **QNEW** - Initialize new features with requirements analysis
- **QPLAN** - Create implementation plans from codebase patterns
- **QCODET** - Write tests first (TDD red phase)
- **QCODE** - Implement functionality (TDD green phase)
- **QCHECK** - Comprehensive code review (security, quality, architecture)
- **QCHECKF** - Function-focused code review (lightweight)
- **QCHECKT** - Test-focused review (coverage, quality)

## Installation

### Option 1: Clone Plugin Repository

```bash
# Clone to Claude plugins directory
cd ~/.claude/plugins
git clone <plugin-repo-url> qshortcuts-core

# Or copy from local path
cp -r /path/to/qshortcuts-core ~/.claude/plugins/
```

### Option 2: Symlink for Development

```bash
# Link from development location
ln -s /path/to/qshortcuts-core ~/.claude/plugins/qshortcuts-core
```

### Verify Installation

```bash
# Check plugin is recognized
ls ~/.claude/plugins/qshortcuts-core/.claude-plugin/plugin.json

# Should output plugin metadata
cat ~/.claude/plugins/qshortcuts-core/.claude-plugin/plugin.json
```

## Skills Reference

### 1. QNEW - New Feature Initialization

**Purpose:** Start new features by understanding codebase patterns and creating structured requirements.

**Workflow:**
1. Gather requirements from user
2. Analyze codebase for similar patterns
3. Create implementation plan
4. Document requirements in `requirements/current.md`
5. Snapshot to `requirements/requirements.lock.md`

**Usage:**
```
User: QNEW - Add user authentication feature

Claude:
- Analyzes existing auth patterns
- Creates REQ-IDs with acceptance criteria
- Generates implementation plan with SP estimates
- Locks requirements
```

**Output:**
- `requirements/current.md` - Editable requirements
- `requirements/requirements.lock.md` - Frozen snapshot
- Implementation plan with story points

**Agents:** planner, docs-writer

---

### 2. QPLAN - Implementation Planning

**Purpose:** Analyze codebase to create consistent, minimal implementation plans.

**Workflow:**
1. Classify task type (feature, bug, refactor)
2. Extract requirements
3. Analyze codebase for reusable patterns
4. Generate task breakdown with SP estimates
5. Validate interface contracts

**Usage:**
```
User: QPLAN - Implement user registration

Claude:
- Finds similar registration flows
- Identifies reusable validators
- Creates 5 subtasks (0.5-2 SP each)
- Total estimate: 5 SP
```

**Tools:**
- `planning-poker-calc.py` - Calculate story points
- `interface-validator.py` - Validate type contracts

**Output:**
- Task breakdown with SP estimates
- Codebase patterns to reuse
- Dependencies and risks
- Interface contracts

**Agents:** planner, requirements-analyst

---

### 3. QCODET - Test Writing (TDD Red Phase)

**Purpose:** Write failing tests first, referencing REQ-IDs from requirements.lock.

**Workflow:**
1. Extract REQ-IDs from requirements.lock.md
2. Generate test file stubs
3. Implement test cases with assertions
4. Verify tests fail (no implementation yet)
5. Pass quality gates (prettier, typecheck, lint)

**Usage:**
```
User: QCODET - Write tests for user registration

Claude:
- Extracts REQ-101, REQ-102, REQ-103
- Creates auth.service.spec.ts
- Writes 8 failing tests
- All cite REQ-IDs in descriptions
- Quality gates pass (except tests fail as expected)
```

**Tools:**
- `req-id-extractor.py` - Extract requirements
- `test-scaffolder.py` - Generate test stubs
- `coverage-analyzer.py` - Analyze coverage goals

**Output:**
- Co-located test files (`*.spec.ts`)
- Failing tests (red phase)
- Coverage plan (80%+ target)

**Agents:** test-writer

---

### 4. QCODE - Implementation (TDD Green Phase)

**Purpose:** Implement minimal code to make tests pass.

**Workflow:**
1. Read failing tests
2. Plan implementation order
3. Write minimum code per test
4. Run tests iteratively
5. Pass all quality gates
6. Optional refactoring

**Usage:**
```
User: QCODE - Implement user registration

Claude:
- Reads 8 failing tests
- Implements createUser(), validateEmail(), etc.
- Runs tests after each function
- All 8 tests pass
- Quality gates pass
- Coverage: 92%
```

**Principles:**
- Minimal code only
- Domain vocabulary
- Small functions
- Type safety with branded types
- No over-engineering

**Output:**
- Implementation files
- All tests passing (green phase)
- Coverage report (≥80%)
- Quality gates passing

**Agents:** sde-iii, implementation-coordinator

---

### 5. QCHECK - Comprehensive Code Review

**Purpose:** Skeptical review of functions, tests, security, and architecture.

**Workflow:**
1. Run static analysis tools
2. Code quality review
3. Security audit
4. Architecture review
5. Test quality review
6. Generate P0/P1/P2 findings

**Usage:**
```
User: QCHECK - Review authentication implementation

Claude:
- Finds SQL injection risk (P0)
- Missing RLS policy (P0)
- High complexity function (P1)
- Outdated dependency (P1)
- Minor improvements (P2)
- Generates action plan
```

**Tools:**
- `cyclomatic-complexity.py` - Function complexity
- `dependency-risk.py` - Dependency vulnerabilities
- `supabase-rls-checker.py` - RLS policies
- `secret-scanner.py` - Hardcoded secrets

**Output:**
- P0 issues (blocking)
- P1 issues (important)
- P2 issues (nice-to-have)
- Static analysis results
- Actionable recommendations

**Agents:** pe-reviewer, code-quality-auditor, security-reviewer

---

### 6. QCHECKF - Function-Focused Review

**Purpose:** Lightweight review of function quality only (faster than QCHECK).

**Workflow:**
1. Identify functions to review
2. Analyze complexity
3. Review naming, types, parameters
4. Check code patterns
5. Generate P1/P2 findings

**Usage:**
```
User: QCHECKF - Review auth.service.ts functions

Claude:
- createUser() complexity: 12 (P1 - refactor)
- doStuff() unclear name (P1)
- updateProfile() too many params (P1)
- hashPassword() simplify (P2)
```

**When to Use:**
- Small changes (1-3 functions)
- Quick iteration
- Focus on code quality, not security
- Time-sensitive feedback

**Tools:**
- `cyclomatic-complexity.py`
- `dependency-risk.py` (function-level only)

**Output:**
- Function quality report
- P1/P2 issues only (no P0)
- Complexity analysis
- Refactoring suggestions

**Agents:** pe-reviewer, code-quality-auditor

---

### 7. QCHECKT - Test-Focused Review

**Purpose:** Specialized review of test quality and coverage.

**Workflow:**
1. Analyze test coverage
2. Validate REQ-ID mapping
3. Review test quality
4. Check test patterns
5. Generate P1/P2 findings

**Usage:**
```
User: QCHECKT - Review test suite

Claude:
- Coverage: 87.5% (above 80% threshold)
- REQ-104 has no tests (P1)
- Flaky test detected (P1)
- Tests share state (P1)
- Missing Unicode edge cases (P1)
```

**Tools:**
- `coverage-analyzer.py` - Coverage analysis
- `req-id-extractor.py` - REQ-ID mapping

**Output:**
- Coverage report
- REQ-ID coverage matrix
- Test quality issues
- Missing tests identified
- Flaky test detection

**Agents:** pe-reviewer, test-writer

---

## Workflow Example

Complete TDD workflow using all skills:

```bash
# 1. Start new feature
User: QNEW - Add email verification

Output:
- requirements/current.md (REQ-201, REQ-202, REQ-203)
- requirements/requirements.lock.md
- Plan: 8 SP total

# 2. Detailed planning
User: QPLAN - Implement email verification

Output:
- 4 tasks: setup (0.5 SP), logic (2 SP), tests (1.5 SP), integration (1 SP)
- Reuse: EmailService, TokenGenerator
- Dependencies: nodemailer

# 3. Write tests first
User: QCODET - Write tests for email verification

Output:
- email-verification.service.spec.ts (6 failing tests)
- Quality gates pass (except tests)
- Coverage plan: 85%

# 4. Implement functionality
User: QCODE - Implement email verification

Output:
- email-verification.service.ts
- All 6 tests pass
- Coverage: 88%
- Quality gates pass

# 5. Comprehensive review
User: QCHECK - Review email verification

Output:
- P0: Rate limiting missing
- P1: Token expiration edge case
- P2: Extract email template
- Action plan with fixes

# 6. Fix and quick re-check
User: QCHECKF - Review rate limiting function

Output:
- Complexity: 6 (acceptable)
- Naming: clear
- No issues found

# 7. Verify test quality
User: QCHECKT - Review email verification tests

Output:
- Coverage: 92% (above threshold)
- All REQ-IDs covered
- No flaky tests
- Test quality: high
```

## Tools Reference

### Planning Tools

**planning-poker-calc.py**
```bash
python planning-poker-calc.py \
  --files-count 3 \
  --test-files 2 \
  --complexity moderate \
  --integrations 1
```

**interface-validator.py**
```bash
python interface-validator.py \
  --interface-file proposed-interface.ts \
  --codebase-path ./src
```

### Testing Tools

**req-id-extractor.py**
```bash
python req-id-extractor.py \
  --lock-file requirements/requirements.lock.md \
  --output test-checklist.json
```

**test-scaffolder.py**
```bash
python test-scaffolder.py \
  --requirements test-checklist.json \
  --implementation-file src/auth.service.ts \
  --output src/auth.service.spec.ts
```

**coverage-analyzer.py**
```bash
python coverage-analyzer.py \
  --test-results coverage/coverage-summary.json \
  --requirements requirements/requirements.lock.md \
  --threshold 80
```

### Quality Tools

**cyclomatic-complexity.py**
```bash
python cyclomatic-complexity.py \
  --file src/auth.service.ts \
  --threshold 10 \
  --output complexity-report.json
```

**dependency-risk.py**
```bash
python dependency-risk.py \
  --package-json package.json \
  --check-vulnerabilities \
  --check-licenses \
  --output dependency-report.json
```

**secret-scanner.py**
```bash
python secret-scanner.py \
  --path src/ \
  --patterns config/secret-patterns.json \
  --output secrets-report.json
```

**supabase-rls-checker.py**
```bash
python supabase-rls-checker.py \
  --schema-file supabase/schema.sql \
  --check-tables users,posts,comments \
  --output rls-report.json
```

## Agents Used

This plugin leverages agents from `~/.claude/agents/`:

- **planner** - Workflow planning, requirement extraction
- **docs-writer** - Documentation and requirement writing
- **requirements-analyst** - Gap analysis, acceptance criteria
- **test-writer** - TDD test generation, coverage analysis
- **sde-iii** - Implementation, complexity estimation
- **implementation-coordinator** - Parallel task coordination
- **pe-reviewer** - Code review, best practices
- **code-quality-auditor** - Lint, complexity, maintainability
- **security-reviewer** - Vulnerability detection, auth review

## Story Point Reference

**Planning Scale (Fibonacci):** 1, 2, 3, 5, 8, 13, 21...
- Use for initial feature estimation
- Break down tasks >13 SP

**Coding Scale:** 0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1, 2, 3, 5
- Use for implementation tasks
- Break down tasks >5 SP

**Baseline:** 1 SP = simple authenticated API (secured, tested, deployed, documented)

## Best Practices

### TDD Workflow
1. QNEW → QPLAN → QCODET → QCODE → QCHECK
2. Always write tests before implementation
3. Run quality gates frequently
4. Keep functions small and focused

### Requirements Lock
- Lock file prevents scope creep
- Tests reference locked REQ-IDs
- Update lock only when scope formally changes

### Code Quality
- Complexity threshold: 10
- Test coverage threshold: 80%
- Type safety: Use branded types
- Domain vocabulary in naming
- No comments - code explains itself

### Review Strategy
- **Quick iteration:** QCHECKF or QCHECKT
- **Pre-merge:** Full QCHECK
- **Security-sensitive:** Always full QCHECK
- **Small changes:** QCHECKF only

## Troubleshooting

### Tests Won't Pass
1. Verify implementation matches test expectations
2. Check for async/await issues
3. Run single test: `npm test -- -t "test name"`
4. Use QCHECKT to analyze test quality

### Coverage Below Threshold
1. Run coverage-analyzer.py to find gaps
2. Check uncovered lines in report
3. Add missing edge case tests
4. Verify branch coverage

### Complexity Too High
1. Run cyclomatic-complexity.py
2. Extract nested logic to separate functions
3. Use early returns to reduce nesting
4. Apply Arrange-Act-Assert pattern

### Quality Gates Failing
```bash
npm run format      # Fix prettier
npm run typecheck   # Fix type errors
npm run lint        # Fix linting
npm run test        # Fix failing tests
```

## Contributing

To extend this plugin:

1. Add new tools to `skills/<skill-name>/tools/`
2. Update SKILL.md with tool documentation
3. Add tool to dependencies list
4. Update README with examples
5. Test tool independently before integration

## License

MIT

## Author

Sparkry.ai - skills@sparkry.ai

## Version

1.0.0
