# Starter Pack - Essential Agents for Beginners

## Overview

Starter Pack provides the essential agents to get started with Claude Code plugins: Planner for task breakdown, SDE-III for implementation guidance, and PE Reviewer for code quality. Perfect for learning the plugin system.

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

```
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install Starter Pack

```
/plugin install starter-pack@sparkry-claude-skills
```

### Step 3: Verify Installation

```
/plugin list
```

------------------------------------------------------------------------

## Included Agents

| Agent | Role | Best For |
|-------|------|----------|
| **Planner** | Task breakdown | Planning any implementation |
| **SDE-III** | Implementation | Complexity analysis, effort estimation |
| **PE Reviewer** | Code quality | Code review, best practices |

------------------------------------------------------------------------

## Usage

### Planner

```
@planner Help me plan a user authentication feature
```

**What it does:**
- Breaks down requirements
- Estimates complexity
- Identifies dependencies
- Creates task sequence
- Suggests story points

**Output:**
```markdown
## Plan: User Authentication

### Requirements
- REQ-001: Email/password login
- REQ-002: Password reset flow
- REQ-003: Session management

### Tasks
1. Database schema (1 SP)
2. Auth service (2 SP)
3. API endpoints (2 SP)
4. Frontend forms (2 SP)
5. Tests (1 SP)

**Total: 8 SP**
```

------------------------------------------------------------------------

### SDE-III

```
@sde-iii Analyze the complexity of adding real-time notifications
```

**What it does:**
- Analyzes technical complexity
- Identifies implementation approaches
- Estimates effort
- Flags dependencies
- Suggests architecture patterns

**Output:**
```markdown
## Complexity Analysis: Real-time Notifications

### Complexity: Medium-High

### Approaches
1. WebSockets (recommended)
2. Server-Sent Events
3. Polling (not recommended)

### Effort Estimate
- Backend: 3 SP
- Frontend: 2 SP
- Infrastructure: 2 SP

### Dependencies
- Redis for pub/sub
- WebSocket server
```

------------------------------------------------------------------------

### PE Reviewer

```
@pe-reviewer Review my authentication implementation
```

**What it does:**
- Reviews code quality
- Checks security issues
- Validates patterns
- Identifies improvements
- Prioritizes findings

**Output:**
```markdown
## PE Review: Authentication Module

### P0 - Critical
- Line 45: Password stored in plain text

### P1 - Important
- Line 23: Missing rate limiting
- Line 67: SQL injection risk

### P2 - Suggestions
- Consider adding 2FA support
- Add login attempt logging
```

------------------------------------------------------------------------

## Getting Started Workflow

### Step 1: Plan Your Feature

```
@planner I need to add a comments feature to blog posts
```

### Step 2: Analyze Complexity

```
@sde-iii What's the best approach for the comments feature?
```

### Step 3: Implement

Write your code based on the plan.

### Step 4: Review

```
@pe-reviewer Review my comments implementation
```

### Step 5: Iterate

Fix issues identified, then review again.

------------------------------------------------------------------------

## When to Use Each Agent

| Situation | Agent |
|-----------|-------|
| "How should I approach this?" | @planner |
| "How complex is this?" | @sde-iii |
| "Is my code good?" | @pe-reviewer |
| "Break this into tasks" | @planner |
| "What patterns should I use?" | @sde-iii |
| "Any security issues?" | @pe-reviewer |

------------------------------------------------------------------------

## Story Point Reference

The agents use this baseline:

| SP | Complexity | Example |
|----|------------|---------|
| 1 | Trivial | Fix typo, update config |
| 2 | Simple | Add new field, basic CRUD |
| 3 | Moderate | New endpoint with validation |
| 5 | Complex | Feature with multiple parts |
| 8 | Large | Significant new capability |
| 13+ | Epic | Break down further |

**Baseline:** 1 SP = simple authenticated API endpoint (secured, tested, deployed)

------------------------------------------------------------------------

## Upgrading to Full Workflows

Once comfortable with Starter Pack, consider:

### For More Development Power
```
/plugin install dev-workflow@sparkry-claude-skills
/plugin install qshortcuts-core@sparkry-claude-skills
```

### For Research Capabilities
```
/plugin install research-workflow@sparkry-claude-skills
```

### For Multi-Agent Orchestration
```
/plugin install orchestration-workflow@sparkry-claude-skills
```

------------------------------------------------------------------------

## Tips for Beginners

### Be Specific
Instead of:
```
@planner Help me with my app
```

Try:
```
@planner Help me add email notifications when users receive new messages
```

### Provide Context
```
@pe-reviewer Review my auth code in src/auth/login.ts
```

### Iterate
Don't expect perfect results on first try. Use agent feedback to improve.

------------------------------------------------------------------------

## Common Questions

### Q: Which agent should I start with?
**A:** Start with @planner to break down your task, then use others as needed.

### Q: Can I use multiple agents together?
**A:** Yes! Plan → Implement → Review is a great flow.

### Q: How do I know if my code is ready?
**A:** @pe-reviewer with no P0/P1 issues means you're likely ready.

------------------------------------------------------------------------

## Next Steps

1. Try each agent with a simple task
2. Use them together on a real feature
3. Explore QShortcuts for streamlined workflows
4. Graduate to QRALPH for complex projects

------------------------------------------------------------------------

## Related Plugins

- **qshortcuts-core** - Shortcuts that use these agents
- **dev-workflow** - Full development agent suite
- **orchestration-workflow** - Multi-agent orchestration

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support at [sparkry.ai/docs](https://sparkry.ai/docs)
