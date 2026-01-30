# Dev Workflow - TDD Development Agents

## Overview

Dev Workflow provides a complete TDD-first development team: PE Reviewer for code quality, Test Writer for TDD, Planner for requirements, and Release Manager for deployments. These agents work together to ensure high-quality software delivery.

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

```
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install Dev Workflow

```
/plugin install dev-workflow@sparkry-claude-skills
```

### Step 3: Verify Installation

```
/plugin list
```

------------------------------------------------------------------------

## Included Agents

| Agent | Role | Specialty |
|-------|------|-----------|
| **PE Reviewer** | Principal Engineer | Code quality, architecture, security |
| **Test Writer** | TDD Specialist | Test generation, coverage |
| **Planner** | Requirements Analyst | Task breakdown, estimation |
| **Release Manager** | Deployment Lead | Releases, changelogs, versioning |
| **Requirements Analyst** | Scope Manager | REQ-IDs, acceptance criteria |
| **Debugger** | Issue Resolver | Root cause analysis, minimal fixes |
| **Code Quality Auditor** | Standards Enforcer | Patterns, anti-patterns, tech debt |
| **SDE-III** | Implementation Lead | Complexity analysis, effort estimation |

------------------------------------------------------------------------

## Usage

### Invoke Agents Directly

```
@pe-reviewer Review this pull request for security issues
```

```
@test-writer Generate tests for the authentication module
```

```
@planner Break down this feature into tasks with story points
```

### Use with QShortcuts

The dev-workflow agents power the QShortcuts:

| QShortcut | Primary Agent |
|-----------|---------------|
| QPLAN | planner, requirements-analyst |
| QCODET | test-writer |
| QCODE | sde-iii |
| QCHECK | pe-reviewer, code-quality-auditor |
| QGIT | release-manager |

------------------------------------------------------------------------

## Agent Details

### PE Reviewer

**Purpose:** Senior code review from a Principal Engineer perspective

**Capabilities:**
- Architecture pattern validation
- Security vulnerability detection
- Performance issue identification
- Code smell detection
- Best practice enforcement

**Output format:**
```markdown
## PE Review: [Component]

### P0 - Critical (Must Fix)
- Issue description with line reference

### P1 - Important (Should Fix)
- Issue description

### P2 - Suggestions
- Improvement suggestion
```

------------------------------------------------------------------------

### Test Writer

**Purpose:** TDD-focused test generation

**Capabilities:**
- Unit test generation from requirements
- Integration test scaffolding
- Edge case identification
- Mock/stub setup
- Coverage analysis

**Follows TDD principle:** Tests cite REQ-IDs

```typescript
// REQ-101: User can login with email
test('should authenticate user with valid email', () => {
  // ...
});
```

------------------------------------------------------------------------

### Planner

**Purpose:** Implementation planning and task breakdown

**Capabilities:**
- Codebase analysis for patterns
- Task decomposition
- Story point estimation
- Dependency mapping
- Risk identification

**Output:** Structured plan with SP estimates

------------------------------------------------------------------------

### Release Manager

**Purpose:** Release process management

**Capabilities:**
- Conventional commit formatting
- CHANGELOG generation
- Version bumping (semver)
- Release notes compilation
- Tag management

------------------------------------------------------------------------

## Workflow Example

### Feature Development Flow

```
1. @planner "Plan user authentication feature"
   → Creates requirements, task breakdown, SP estimates

2. @test-writer "Generate tests for auth requirements"
   → Creates failing test files

3. @sde-iii "Implement authentication"
   → Writes code to pass tests

4. @pe-reviewer "Review authentication implementation"
   → Provides P0/P1/P2 feedback

5. @release-manager "Prepare release"
   → Creates commit, updates changelog
```

------------------------------------------------------------------------

## Quality Standards

The PE Reviewer enforces these standards:

### Code Quality
- No TODO/FIXME without issue reference
- Functions under 50 lines
- Cyclomatic complexity under 10
- Type safety (no `any` in TypeScript)

### Security
- Input validation on boundaries
- No secrets in code
- Proper authentication checks
- SQL injection prevention

### Testing
- 80%+ code coverage
- All requirements have tests
- Edge cases covered
- No flaky tests

------------------------------------------------------------------------

## Integration with QRALPH

Dev-workflow agents are part of QRALPH's agent pool:

```
QRALPH "Add payment processing"
→ Spawns: architecture-advisor, security-reviewer, pe-reviewer,
          requirements-analyst, sde-iii
```

------------------------------------------------------------------------

## Related Plugins

- **qshortcuts-core** - QPLAN, QCODE, QCHECK shortcuts
- **orchestration-workflow** - QRALPH multi-agent orchestration

------------------------------------------------------------------------

## Troubleshooting

### Agent not responding

Check that dev-workflow is installed:
```
/plugin list
```

### Review too generic

Provide specific context:
- File paths to review
- Specific concerns to address
- Related requirements

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support at [sparkry.ai/docs](https://sparkry.ai/docs)
