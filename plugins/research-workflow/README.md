# Research Workflow

Multi-agent research orchestration with fact-checking, source evaluation, and synthesis.

## Installation

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
/plugin install research-workflow@sparkry-claude-skills
```

## What's Included

**Agents:** research-director, fact-checker, source-evaluator, industry-scout, synthesis-writer, dissent-moderator

**Skills:** research/plan, research/fact-check, research/source-policy, research/web-exec, research/options-matrix, research/industry-scout

## Quick Reference

| Agent | Purpose |
|-------|---------|
| research-director | Orchestrates multi-agent research |
| fact-checker | Validates claims with 2+ Tier-1 sources |
| source-evaluator | Classifies sources (Tier 1-4) |
| industry-scout | Discovers trends and signals |
| synthesis-writer | Creates executive summaries |
| dissent-moderator | Resolves conflicting recommendations |

## Source Tiers

| Tier | Type | Examples |
|------|------|----------|
| Tier-1 | Primary/Authoritative | Government, peer-reviewed |
| Tier-2 | Reputable Secondary | WSJ, Bloomberg, IDC |
| Tier-3 | Community | Reddit, HN, blogs |
| Tier-4 | Unverified | Marketing, anonymous |

## Usage

```bash
@research-director Analyze competitive landscape for AI coding tools
@fact-checker Verify market size claims
/research-plan "B2B SaaS pricing strategies"
```

## Documentation

**[Full User Guide →](../../docs/RESEARCH-WORKFLOW-GUIDE.md)**

## License

MIT
