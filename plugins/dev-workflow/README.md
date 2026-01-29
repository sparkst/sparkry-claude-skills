# dev-workflow Plugin

TDD-first development workflow with code review and release management for Claude Code.

## What's Included

### Agents

- **planner** - Transforms inputs into executable plans with REQ IDs and story points
- **pe-reviewer** - Senior PE code review enforcing standards and best practices
- **test-writer** - TDD enforcer who creates failing tests before implementation
- **sde-iii** - Implementation complexity and effort estimation expert
- **release-manager** - Enforces release gates (tests, lint, typecheck)
- **code-quality-auditor** - Standards enforcement and anti-pattern detection
- **debugger** - Minimal repro and root cause isolation specialist
- **requirements-analyst** - REQ management and traceability

### Skills

- **quality/pe-reviewer** - Code review tools and references
  - Cyclomatic complexity analyzer
  - Dependency risk checker
  - Supabase RLS validator
  - MCP security guidelines
  - Function and test best practices checklists

## Installation

### Via Claude Code CLI

```bash
claude plugins install dev-workflow
```

### Manual Installation

1. Clone or download this plugin
2. Copy to your Claude plugins directory:
   ```bash
   cp -r dev-workflow ~/.claude/plugins/dev-workflow
   ```
3. Reload Claude Code

## Quick Start

This plugin follows a TDD-first development workflow. Here's how to use it:

### 1. Planning a Feature (QNEW/QPLAN)

Start with the planner agent to analyze requirements and create a plan:

```
@planner Create a plan for adding user authentication
```

The planner will:
- Extract REQ IDs with acceptance criteria
- Estimate story points
- Generate a phased implementation plan
- Output: `requirements/current.md`, `requirements/requirements.lock.md`

### 2. Writing Tests First (QCODET)

Use the test-writer to create failing tests:

```
@test-writer Generate tests for requirements.lock.md
```

The test-writer will:
- Create test files for each REQ ID
- Ensure ≥1 failing test per requirement
- Generate parallel tests (unit, integration, e2e)
- Output: Test files and `docs/tasks/<task-id>/test-plan.md`

**CRITICAL**: Tests MUST fail before implementation. This enforces TDD.

### 3. Implementing Features (QCODE)

Use the sde-iii agent to implement:

```
@sde-iii Implement authentication feature to pass tests
```

The sde-iii will:
- Analyze implementation complexity
- Identify dependencies and risks
- Make tests pass with minimal code changes

### 4. Code Review (QCHECK/QCHECKF)

Run code review with multiple agents:

```
@pe-reviewer Review authentication implementation
@code-quality-auditor Audit code quality
```

Reviews check:
- CLAUDE.md compliance
- Security vulnerabilities
- Performance issues
- Test coverage
- Best practices

### 5. Release (QGIT)

Use release-manager to verify gates and commit:

```
@release-manager Prepare release for authentication feature
```

The release-manager will:
- Run `npm run lint`
- Run `npm run typecheck`
- Run `npm run test`
- Verify edge function dependencies
- Create Conventional Commit
- Push to repository

## Workflow Integration

### TDD Flow

```
QNEW/QPLAN (planner)
  ↓
QCODET (test-writer) ← Generate failing tests
  ↓
QCHECKT (pe-reviewer, test-writer) ← Review test quality
  ↓
QCODE (sde-iii) ← Implement to pass tests
  ↓
QCHECK/QCHECKF (pe-reviewer, code-quality-auditor) ← Review code
  ↓
QDOC (docs-writer) ← Update documentation
  ↓
QGIT (release-manager) ← Release
```

### Debug Flow

For debugging existing issues:

```
@planner Debug: Users can't login after password reset
```

The planner will coordinate parallel analysis:
- **debugger**: Minimal repro and root cause
- **pe-reviewer**: Security and correctness issues
- **code-quality-auditor**: Technical debt analysis
- **requirements-analyst**: REQ coverage gaps

Output: `docs/tasks/<task-id>/debug-analysis.md`

## Usage Examples

### Example 1: Simple Feature

**Task**: Add cache TTL configuration

```bash
# Step 1: Plan
@planner Create plan for cache TTL configuration

# Step 2: Write tests (TDD)
@test-writer Generate tests for REQ-10

# Step 3: Verify tests fail
npm test  # Should see failing tests

# Step 4: Implement
@sde-iii Implement cache TTL configuration

# Step 5: Review
@pe-reviewer Review cache implementation

# Step 6: Release
@release-manager Create release commit
```

**Estimated effort**: 1-2 SP (0.5-1 hour)

### Example 2: Complex Feature

**Task**: Model selection with fallback logic

```bash
# Step 1: Plan with architecture
@planner Design model selection with fallback (include architecture options)

# Step 2: Parallel test generation
@test-writer Generate unit, integration, and e2e tests for REQ-20, REQ-21, REQ-22

# Step 3: Verify all tests fail
npm test  # Multiple test suites should fail

# Step 4: Implement in phases
@sde-iii Implement backend model selection logic (REQ-20)
@sde-iii Implement fallback mechanism (REQ-21)
@sde-iii Implement cost optimization (REQ-22)

# Step 5: Comprehensive review
@pe-reviewer Review model selection implementation
@code-quality-auditor Audit for performance issues

# Step 6: Release
@release-manager Prepare release with all tests passing
```

**Estimated effort**: 5-8 SP (2-3 days)

### Example 3: Debugging

**Task**: Authentication fails intermittently

```bash
# Step 1: Parallel debug analysis
@planner Debug: Authentication fails intermittently

# This spawns parallel analysis:
# - debugger: Minimal repro
# - pe-reviewer: Security review
# - code-quality-auditor: Race conditions
# - requirements-analyst: REQ coverage

# Step 2: Review analysis
# Read docs/tasks/<task-id>/debug-analysis.md

# Step 3: Implement fix
@debugger Apply minimal fix for race condition in token validation

# Step 4: Verify
npm test  # All tests should pass

# Step 5: Release
@release-manager Create hotfix commit
```

**Estimated effort**: 0.5-1 SP (1-2 hours)

## Configuration

### CLAUDE.md Integration

This plugin expects a `CLAUDE.md` file in your project root with:

- **Core Principles**: Coding standards, TDD requirements
- **Requirements Lock**: REQ ID format and snapshots
- **Planning Poker**: Story point baseline (1 SP = simple authenticated API)
- **Test Failure Tracking**: `.claude/metrics/test-failures.md`
- **Pre-Deployment Gates**: Quality gates before deployment

### Story Point Baseline

**1 SP** = Simple authenticated API endpoint with:
- Key-value operation
- Auth/security validated
- Full test coverage
- Documentation complete
- Deployed and verified

Use Fibonacci scale: 1, 2, 3, 5, 8, 13, 21 (break tasks >13 SP)

### Test Failure Tracking

Enable automatic test failure tracking:

```markdown
# .claude/metrics/test-failures.md

| Date | Test File | Test Name | REQ-ID | Bug | Fix SP | Commit |
|------|-----------|-----------|--------|-----|--------|--------|
| 2026-01-28 | auth.spec.ts | REQ-42 — token expiry | REQ-42 | Timestamp comparison bug | 0.2 | a3f8c2e |
```

## Best Practices

### 1. Always Start with Tests (TDD)

**❌ Don't**:
```bash
@sde-iii Implement authentication  # No tests first!
```

**✅ Do**:
```bash
@test-writer Generate tests for authentication
# Verify failures
npm test
# Then implement
@sde-iii Implement authentication to pass tests
```

### 2. Use Parallel Analysis for Complex Debugging

**❌ Don't**:
```bash
@debugger Fix the login bug  # Single perspective
```

**✅ Do**:
```bash
@planner Debug: Login fails for some users  # Parallel analysis
```

### 3. Review Before Release

**❌ Don't**:
```bash
@release-manager Release immediately  # Skip review
```

**✅ Do**:
```bash
@pe-reviewer Review implementation
@code-quality-auditor Audit code quality
# After reviews pass
@release-manager Release with all gates green
```

### 4. Keep Requirements Traceable

Every feature should have:
- REQ IDs in `requirements/requirements.lock.md`
- Tests citing REQ IDs: `describe('REQ-42 — feature', ...)`
- Code comments for non-obvious REQ mappings
- Design docs referencing REQ IDs

## Troubleshooting

### Tests Not Failing (TDD Violation)

**Problem**: `@test-writer` generates tests but they all pass

**Solution**: Tests don't cover new requirements. Request additional tests:
```bash
@test-writer The tests all pass but REQ-10 requires new cache TTL logic. Add tests that will fail until implementation.
```

### Review Finds Critical Issues (P0)

**Problem**: `@pe-reviewer` reports P0 security vulnerabilities

**Solution**: Fix P0 issues before proceeding:
```bash
# Read the review JSON output
# Fix each P0 issue
@pe-reviewer Review fixes for P0 issues
# Proceed only after P0s resolved
```

### Release Gates Failing

**Problem**: `@release-manager` reports failing gates

**Solution**: Fix each gate in order:
```bash
npm run lint        # Fix linting errors
npm run typecheck   # Fix type errors
npm run test        # Fix failing tests
# After all green
@release-manager Retry release
```

### Story Point Estimation Unclear

**Problem**: Unsure how to estimate story points

**Solution**: Use the baseline and reference table:

| Complexity | Example | Story Points |
|------------|---------|--------------|
| Trivial | Config change, constant update | 0.05-0.1 |
| Simple | Single function, basic logic | 0.2-0.5 |
| Moderate | Multiple functions, some integration | 1-2 |
| Complex | Cross-cutting, architecture changes | 3-5 |
| Major | New subsystem, significant refactor | 8-13 |

Break down tasks >13 SP into smaller chunks.

## Advanced Usage

### Custom Sub-Agents

The planner supports specialized sub-agents for complex planning:

- **requirements-scribe**: Extract and document REQs
- **architecture-advisor**: Design options and trade-offs
- **pe-designer**: Amazon PE design brief and ADR
- **estimator**: Normalize story points
- **synthesis-director**: Consolidate outputs

Invoke via planner:
```bash
@planner Use architecture-advisor to propose 3 design options for real-time notifications
```

### Parallel Test Generation

For large features, generate tests in parallel:

```bash
@test-writer Generate parallel tests for REQ-20, REQ-21, REQ-22
# Generates:
# - Frontend unit tests (0.2 SP)
# - Backend unit tests (0.5 SP)
# - Integration tests (0.3 SP)
# - E2E tests (0.5 SP)
# Total: 1.5 SP
```

### Amazon PE Heuristics

The planner and pe-designer apply Amazon PE principles:

- **Simple-first**: Modular monolith, evolve to microservices
- **One-way vs two-way doors**: Bias reversible choices
- **Risk-first**: Observability, SLOs, kill-switches
- **Data-first**: Consistency model, caching, privacy

Request PE design:
```bash
@planner QDESIGN for distributed task queue (apply Amazon PE heuristics)
```

## Contributing

This plugin is part of the Sparkry.ai Claude Code ecosystem. For issues, enhancements, or questions:

- **Email**: skills@sparkry.ai
- **License**: MIT

## Changelog

### v1.0.0 (2026-01-28)

- Initial release
- 8 core agents (planner, pe-reviewer, test-writer, sde-iii, release-manager, code-quality-auditor, debugger, requirements-analyst)
- 1 skill bundle (quality/pe-reviewer)
- TDD enforcement workflow
- Parallel analysis for debugging
- Story point estimation
- Release gate validation

## License

MIT License - see LICENSE file for details.

---

**Happy coding with TDD-first workflows!**
