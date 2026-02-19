# Sparkry Claude Skills Marketplace

> Distribution repo for Claude Code plugins. Source of truth lives in `exec-team`; this repo is the published artifact at `sparkst/sparkry-claude-skills`.

---

## Marketplace Deployment Process

When a plugin is updated in exec-team, deploy to the marketplace with these steps:

### 1. Copy updated files from exec-team source to the marketplace plugin

Each plugin maps from an exec-team source directory to a marketplace plugin directory:

| Plugin | exec-team source | Marketplace destination |
|--------|-----------------|----------------------|
| **orchestration-workflow** (QRALPH) | `.qralph/tools/` + `.claude/agents/` + `.claude/skills/project-orchestration/qralph/` | `plugins/orchestration-workflow/` |
| **dev-workflow** | `.claude/plugins/dev-workflow/` | `plugins/dev-workflow/` |
| **research-workflow** | `.claude/plugins/research-workflow/` | `plugins/research-workflow/` |
| **writing-workflow** | `.claude/plugins/writing-workflow/` | `plugins/writing-workflow/` |
| **strategy-workflow** | `.claude/plugins/strategy-workflow/` | `plugins/strategy-workflow/` |
| **starter-pack** | `.claude/plugins/starter-pack/` | `plugins/starter-pack/` |
| **qshortcuts-core** | `.claude/plugins/qshortcuts-core/` | `plugins/qshortcuts-core/` |
| **qshortcuts-support** | `.claude/plugins/qshortcuts-support/` | `plugins/qshortcuts-support/` |
| **qshortcuts-ai** | `.claude/plugins/qshortcuts-ai/` | `plugins/qshortcuts-ai/` |
| **qshortcuts-content** | `.claude/plugins/qshortcuts-content/` | `plugins/qshortcuts-content/` |
| **qshortcuts-learning** | `.claude/plugins/qshortcuts-learning/` | `plugins/qshortcuts-learning/` |
| **integrations-trello** | `.claude/plugins/integrations-trello/` | `plugins/integrations-trello/` |

### 2. QRALPH (orchestration-workflow) — Special mapping

QRALPH has a non-standard source layout. The file mapping is:

```
exec-team source                              → marketplace destination
─────────────────────────────────────────────────────────────────────────
.qralph/tools/*.py                            → plugins/orchestration-workflow/skills/qralph/tools/*.py
.qralph/tools/test_*.py                       → plugins/orchestration-workflow/skills/qralph/tools/test_*.py
.claude/agents/qralph-team-lead.md            → plugins/orchestration-workflow/agents/qralph-team-lead.md
.claude/agents/qralph-validator.md            → plugins/orchestration-workflow/agents/qralph-validator.md
.claude/skills/project-orchestration/qralph/SKILL.md → plugins/orchestration-workflow/skills/qralph/SKILL.md
```

Tool files to copy (all from `.qralph/tools/`):
- `qralph-orchestrator.py`
- `qralph-subteam.py`
- `qralph-healer.py`
- `qralph-watchdog.py`
- `qralph-status.py`
- `qralph-state.py`
- `session-state.py`
- `process-monitor.py`
- `test_qralph_orchestrator.py`
- `test_qralph_subteam.py`
- `test_qralph_healer.py`
- `test_qralph_watchdog.py`
- `test_session_state.py`
- `test_work_mode.py`
- `test_process_monitor.py`

### 3. Update plugin metadata (CRITICAL — skipping this breaks marketplace updates)

For each updated plugin:
- Bump `version` in `plugins/<plugin-name>/.claude-plugin/plugin.json`
- Bump `version` in `.claude-plugin/marketplace.json` for the matching plugin entry
- Update the plugin's `README.md` with new features, version, test counts
- Update root `README.md` plugin description if the summary changed

**Both version files MUST be bumped.** The marketplace uses `marketplace.json` to detect updates — if the version there is stale, `/plugin marketplace update` will see no changes and users must delete + reinstall to get updates.

### 4. Commit and push

```bash
cd .qralph/projects/001-package-publish-claude/github-repo
git add plugins/<plugin-name>/
git add README.md  # if root description changed
git commit -m "feat(<plugin-name>): <description>"
git push origin main
```

---

## Repo Structure

```
sparkry-claude-skills/
├── README.md                    # Marketplace catalog (install commands, plugin list)
├── CLAUDE.md                    # This file
├── LICENSE                      # MIT
├── REPOSITORY-STRUCTURE.md      # Detailed structure docs
├── docs/                        # Per-plugin installation guides
│   └── *-GUIDE.md
└── plugins/                     # 12 plugins
    └── <plugin-name>/
        ├── .claude-plugin/
        │   └── plugin.json      # name, version, description, keywords
        ├── README.md            # Plugin-specific docs
        ├── agents/              # Agent definitions (*.md)
        └── skills/              # Skill definitions with tools
            └── <skill>/
                ├── SKILL.md
                ├── tools/       # Python scripts + tests
                └── references/  # Supporting docs
```

## Conventions

- Plugin versions use semver — bump major for breaking changes, minor for features, patch for fixes
- Every plugin has a `.claude-plugin/plugin.json` with `name`, `version`, `description`, `author`, `license`, `keywords`
- Agent definitions are markdown files in `agents/`
- Test files live alongside their source in `tools/` (co-located, not separate test directory)
- Commit messages follow Conventional Commits: `feat(<plugin>):`, `fix(<plugin>):`, `docs(<plugin>):`
- Always run tests in exec-team BEFORE copying to marketplace — this repo has no CI

## Git Details

- **Remote**: `https://github.com/sparkst/sparkry-claude-skills.git`
- **Branch**: `main`
- **Local path**: `.qralph/projects/001-package-publish-claude/github-repo/` (relative to exec-team root)
