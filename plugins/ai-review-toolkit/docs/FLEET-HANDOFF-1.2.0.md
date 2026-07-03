# Fleet handoff — ai-review-toolkit 1.2.0 (ultracode Workflow rewire)

## Summary

`/qreview` and `/qloop` now run on the ultracode **Workflow** engine instead of hand-driven Python
drivers. The deterministic hot-loop (dedup / convergence / model-tiering / prompt construction) is a JS
library, inlined into one self-contained Workflow script ([`review-loop.workflow.js`][workflow]); the
skills are thin wrappers that resolve the review team via [`team-selector.py`][team-selector], invoke the
Workflow, and run [`scorecard.py`][scorecard] `--workflow` at the end. `/qpipeline` is unchanged (still a
Python driver by design). Legacy driver protocols are preserved as `driver-fallback.md` for one release.

Verified: live `/qloop` converges in 2 rounds end-to-end (fixer + fix-ALL gate + min-2-rounds exercised).

## Coordinates

- **Repo:** `sparkst/sparkry-claude-skills`
- **Version:** **1.2.0** — pinned in both [`plugin.json`][plugin-json] and [`marketplace.json`][marketplace-json]
- **Merged PRs (all CI-green):** [#5][pr5] JS adjudication lib · [#6][pr6] Workflow scorecard ·
  [#7][pr7] `review-loop.workflow.js` · [#8][pr8] smoke fixes · [#9][pr9] skill rewire ·
  [#10][pr10] dup-finding-id gate fix

## FLEET DECISION: plugin update everywhere (chosen 2026-07-01)

Every fleet machine takes the marketplace **plugin** (namespaced skills: `ai-review-toolkit:qreview` /
`:qloop`). No fork gymnastics. Bare `/qreview` only on machines deliberately forked (see "Bare-name fork"
below, kept for reference).

### Path A — plugin update (THE fleet path)

Interactive, in a Claude Code session on each machine:

```
/plugin marketplace update sparkry-claude-skills
```

**Headless / fleet-job equivalent — use the `claude plugin` CLI, NOT a raw git pull.**
A `git pull` of the marketplace clone updates only the *source*. Claude Code loads plugins from a
version-pinned **cache** (`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`) plus the
`installed_plugins.json` records — and a git pull rebuilds *neither*, so the machine keeps loading the
**old** version (the marketplace `plugin.json` will read the new number while `claude plugin list` still
shows the old one). Use the CLI, which refreshes the marketplace **and** rebuilds the cache + install
records:

```sh
claude plugin marketplace update sparkry-claude-skills
claude plugin update  ai-review-toolkit@sparkry-claude-skills --scope user \
  || claude plugin install ai-review-toolkit@sparkry-claude-skills --scope user
# verify — expect the current version at Scope: user:
claude plugin list | grep -A2 ai-review-toolkit
```

- **`--scope user` is required.** Fleet jobs run in a *fresh clone per job* (an arbitrary project path),
  so a **project**-scoped install never covers them — only a user-scoped one does. `update` fails if the
  plugin isn't already installed at that scope, hence the `|| install` fallback. Don't pipe the command
  through `tail`/`grep` when relying on the `||` — a pipe masks the exit code and the fallback won't fire.
- **No "restart" needed for jobs.** Each headless `claude -p` job is a fresh process, so the next job
  picks up the new version automatically (the CLI's "restart to apply" is thus satisfied for the worker).
- **Version-agnostic.** This always converges the machine on whatever is current on `main`; it is not
  specific to 1.2.0. (Verified in practice converging the fleet through 1.3.0 → 1.4.0.)

**Update the account that runs jobs, not the SSH login.** On most hosts these differ: the worker runs as a
service user — `builder` on the macOS/launchd nodes, `claude` on the Linux/systemd node — while `travis`
is only the interactive login. Run the CLI as the worker user:

```sh
sudo -u builder -H bash -lc 'cd "$HOME" 2>/dev/null || cd /tmp
  export PATH="$HOME/.local/bin:$PATH"
  claude plugin marketplace add sparkst/sparkry-claude-skills 2>/dev/null || true
  claude plugin install ai-review-toolkit@sparkry-claude-skills --scope user
  claude plugin list | grep -A2 ai-review-toolkit'
```

Two gotchas doing this: **(1)** `sudo -u builder` inherits your cwd — if that's another user's home,
every `claude` call dies with `getcwd: … Permission denied` (EACCES). `cd "$HOME"` first (with `-H` so
`$HOME` is the worker's). **(2)** A never-provisioned worker has **no marketplace registered at all**, so
`claude plugin marketplace add sparkst/sparkry-claude-skills` must run before the install.

**Prereqs per machine:** the Workflow (ultracode) tool available in Claude Code, and `python3` for the
scorecard. If the Workflow tool isn't available, the skills fall back to the legacy Python-driver protocol
in `driver-fallback.md`.

## What shipped (specific file references, pinned to `8efbe4d`)

Plugin surface:
- [`plugins/ai-review-toolkit/.claude-plugin/plugin.json`][plugin-json] — version 1.2.0
- [`.claude-plugin/marketplace.json`][marketplace-json] — marketplace entry, version 1.2.0
- [`plugins/ai-review-toolkit/CHANGELOG.md`][changelog]

The JS engine ([`plugins/ai-review-toolkit/js/`][js-dir]):
- [`review-loop.workflow.js`][workflow] — the committed, self-contained ultracode Workflow (generated; do not hand-edit)
- [`review-loop.template.js`][template] — orchestration source (meta + loop) with the `@@INLINE@@` marker
- [`build-workflow.mjs`][build] — inlines the libs into the workflow (`--write`/`--check`)
- [`adjudication.mjs`][adjudication] — the 7 drift-locked adjudication functions
- [`prompts.mjs`][prompts] — reviewer/fixer prompt construction
- [`workflow-helpers.mjs`][helpers] — `ensureUniqueIds` (dedup-collision fix)

Python (deterministic, invoked at the Workflow edges):
- [`tools/scorecard.py`][scorecard] — gained `--workflow` (reads a Workflow run's per-agent transcripts + wall-clock)
- [`tools/team-selector.py`][team-selector] — team selection + model tiering (unchanged oracle)

Skills:
- [`skills/qreview/SKILL.md`][qreview-skill] + [`skills/qreview/driver-fallback.md`][qreview-fallback]
- [`skills/qloop/SKILL.md`][qloop-skill] + [`skills/qloop/driver-fallback.md`][qloop-fallback]

## Bare-name fork (reference only — NOT the fleet path)

Only the **primary box** (Travis's interactive machine) is a fork — it runs `/qreview` `/qloop` `/qpipeline`
as USER-level skills with the plugin disabled. (jarvis is **not** a fork: it takes the marketplace plugin
like every other fleet node — verified in the 1.4.0 rollout.) The fork lives at
`~/.claude/skills/{qreview,qloop,qpipeline}/SKILL.md` +
`~/.claude/ai-review-tools/*.py` (flat) + `~/.claude/ai-review-tools/js/review-loop.workflow.js`. The fork
does **not** auto-update — it needs a manual re-sync (copy `js/review-loop.workflow.js`, copy runtime
`tools/*.py` except `test_*.py`/`gen-*.py`, and copy the SKILLs with the tool paths rewritten to absolute).
The one thing that bites: `scorecard.py` **must** be re-synced (it gained `--workflow` this release) or
`/qloop`'s final scorecard step breaks.

<!-- links -->
[plugin-json]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/.claude-plugin/plugin.json
[marketplace-json]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/.claude-plugin/marketplace.json
[changelog]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/CHANGELOG.md
[js-dir]: https://github.com/sparkst/sparkry-claude-skills/tree/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/js
[workflow]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/js/review-loop.workflow.js
[template]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/js/review-loop.template.js
[build]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/js/build-workflow.mjs
[adjudication]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/js/adjudication.mjs
[prompts]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/js/prompts.mjs
[helpers]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/js/workflow-helpers.mjs
[scorecard]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/tools/scorecard.py
[team-selector]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/tools/team-selector.py
[qreview-skill]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/skills/qreview/SKILL.md
[qreview-fallback]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/skills/qreview/driver-fallback.md
[qloop-skill]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/skills/qloop/SKILL.md
[qloop-fallback]: https://github.com/sparkst/sparkry-claude-skills/blob/8efbe4dedd56d611739443f5e12329bef29f2e76/plugins/ai-review-toolkit/skills/qloop/driver-fallback.md
[pr5]: https://github.com/sparkst/sparkry-claude-skills/pull/5
[pr6]: https://github.com/sparkst/sparkry-claude-skills/pull/6
[pr7]: https://github.com/sparkst/sparkry-claude-skills/pull/7
[pr8]: https://github.com/sparkst/sparkry-claude-skills/pull/8
[pr9]: https://github.com/sparkst/sparkry-claude-skills/pull/9
[pr10]: https://github.com/sparkst/sparkry-claude-skills/pull/10
