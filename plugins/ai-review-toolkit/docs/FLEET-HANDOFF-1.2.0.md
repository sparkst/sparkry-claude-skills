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

Headless / fleet-job equivalent (the marketplace is a git-backed clone; updating = pulling it):

```sh
git -C ~/.claude/plugins/marketplaces/sparkry-claude-skills fetch origin --quiet
git -C ~/.claude/plugins/marketplaces/sparkry-claude-skills checkout main
git -C ~/.claude/plugins/marketplaces/sparkry-claude-skills pull --ff-only
# verify the machine now sees 1.2.0:
python3 -c "import json;print(json.load(open('$HOME/.claude/plugins/marketplaces/sparkry-claude-skills/plugins/ai-review-toolkit/.claude-plugin/plugin.json'))['version'])"
```

New sessions pick up 1.2.0 after the pull. (`marketplace.json` was bumped, so the interactive update won't
no-op.)

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

The primary box (and any machine deliberately forked, e.g. jarvis) runs `/qreview` `/qloop` `/qpipeline` as
USER-level skills with the plugin disabled: `~/.claude/skills/{qreview,qloop,qpipeline}/SKILL.md` +
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
