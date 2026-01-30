# Strategy Workflow

Strategic planning tools for executive decision-making.

## Installation

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
/plugin install strategy-workflow@sparkry-claude-skills
```

## What's Included

**Agents:** cos, strategic-advisor, pm, finance-consultant, legal-expert

**Skills:** cos/intake, cos/prfaq, cos/buy-vs-build, cos/pmf-validation, cos/tenets, cos/security-review

## Quick Reference

| Skill | Purpose |
|-------|---------|
| /prfaq | Amazon-style PR-FAQ documents |
| /buy-vs-build | 7-dimension decision matrix + TCO |
| /pmf-validate | Product-market fit assessment |
| /tenets | Team operating principles |
| @cos | Chief of Staff orchestration |

## Deliverable Types

| Type | Output | Use Case |
|------|--------|----------|
| PR-FAQ | `product/pr-faq.md` | New product proposals |
| Buy-vs-Build | `buy_build.json` | Technology decisions |
| PMF | `pmf/pmf_plan.md` | Market fit validation |
| Tenets | `tenets.md` | Team principles |

## Usage

```bash
/prfaq "Launch AI code review tool"
/buy-vs-build "Customer support chatbot"
/pmf-validate "SaaS for indie developers"
/tenets "Engineering team principles"
@cos "Evaluate European market entry"
```

## Documentation

**[Full User Guide →](../../docs/STRATEGY-WORKFLOW-GUIDE.md)**

## License

MIT
