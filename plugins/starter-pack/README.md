# Starter Pack Plugin

Essential agents for beginners to get started with Claude Code workflows.

## What's Included

This plugin includes three core agents that form the foundation of a professional development workflow:

### 1. Planner (`planner`)
**What it does:** Transforms your ideas into executable plans with requirements and effort estimates.

**When to use:**
- Starting a new feature
- Planning a refactor
- Analyzing a bug

**Command:** `QPLAN`

**Output:**
- `requirements/current.md` - Your requirements document
- `requirements/requirements.lock.md` - Snapshot of requirements
- `plan.md` - Step-by-step implementation plan
- Story point estimates for effort tracking

### 2. PE Reviewer (`pe-reviewer`)
**What it does:** Reviews code for correctness, security, performance, and best practices.

**When to use:**
- Before committing code
- After implementing a feature
- When you want a second opinion

**Command:** `QCHECK`

**Output:**
- JSON review report with findings
- Security analysis
- Test coverage gaps
- Suggested fixes and improvements

### 3. SDE-III (`sde-iii`)
**What it does:** Implements features and provides technical analysis on complexity and dependencies.

**When to use:**
- Implementing planned features
- Estimating build effort
- Analyzing technical feasibility

**Command:** `QCODE`

**Output:**
- Working code implementation
- Position memos on technical decisions
- Effort estimates and risk analysis

## Installation

```bash
# Install the starter pack
claude-code install-plugin starter-pack

# Verify installation
claude-code list-agents
```

You should see `planner`, `pe-reviewer`, and `sde-iii` in your agents list.

## Quick Start

### Your First Workflow

1. **Plan your feature:**
   ```
   QPLAN: Add a login form to my app
   ```

   The planner will create requirements and a step-by-step plan.

2. **Implement the plan:**
   ```
   QCODE: Implement the login form from the plan
   ```

   The SDE-III agent will write the code following the plan.

3. **Review your work:**
   ```
   QCHECK: Review the login form implementation
   ```

   The PE Reviewer will analyze the code and suggest improvements.

### Example Session

```
You: QPLAN: Add user authentication to my app

Claude (planner): I'll create a plan for user authentication...
[Creates requirements/current.md with REQ-001, REQ-002, etc.]
[Creates plan.md with implementation steps]
[Estimates: 8 story points]

You: QCODE: Implement REQ-001 from the plan

Claude (sde-iii): Implementing authentication endpoint...
[Writes auth code]
[Runs tests]
[Documents technical decisions]

You: QCHECK: Review the authentication code

Claude (pe-reviewer): Reviewing authentication implementation...
[Outputs JSON report]
{
  "summary": "Found 2 security concerns and 1 performance issue",
  "findings": [...],
  "security": {...},
  "autofixes": [...]
}
```

## Workflow Pattern

The starter pack follows this basic pattern:

```
QPLAN → QCODE → QCHECK → (repeat if needed) → Done
```

- **QPLAN**: Understand what to build
- **QCODE**: Build it
- **QCHECK**: Verify it's built correctly

## Ready for More?

When you're comfortable with these three agents, upgrade to the full **dev-workflow** plugin which adds:

- Test writer for TDD workflows
- Documentation writer
- Release manager for git commits
- And more specialized agents

```bash
claude-code install-plugin dev-workflow
```

## Configuration

These agents work out of the box with sensible defaults. You can customize them by creating a `.claude/` directory in your project with:

- `agents/` - Override agent behavior
- `settings.json` - Configure tool permissions and preferences

See the [Claude Code documentation](https://docs.anthropic.com/claude-code) for details.

## Support

- **Issues:** Report bugs or request features at the plugin repository
- **Questions:** Join the Claude Code community forums
- **Documentation:** Full guides at https://docs.anthropic.com/claude-code

## License

MIT License - See LICENSE file for details.

## Author

Created by [Sparkry.ai](mailto:skills@sparkry.ai)
