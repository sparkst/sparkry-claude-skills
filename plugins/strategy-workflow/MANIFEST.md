# Strategy Workflow Plugin - Manifest

## Plugin Information

**Name**: strategy-workflow
**Version**: 1.0.0
**Author**: Travis Sparks
**License**: MIT
**Category**: Business Strategy
**Visibility**: Public (Anthropic Marketplace)

## Description

A comprehensive strategic planning framework for Claude featuring Chief of Staff (COS) orchestration and Amazon-style strategic deliverables including PR-FAQ, buy-vs-build analysis, PMF validation, and tenets.

## Components

### Agents (5)

1. **cos** (`agents/cos.md`)
   - Role: Chief of Staff orchestrator
   - Tools: Read, Grep, Glob, Edit, Write, Bash, WebSearch, WebFetch
   - Model: claude-opus-4-5
   - Capabilities: Orchestrates specialists, manages dissent, synthesizes deliverables

2. **strategic-advisor** (`agents/strategic-advisor.md`)
   - Role: Market sizing, competitive positioning, GTM strategy
   - Tools: Read, Grep, Glob, WebSearch, WebFetch
   - Output: Position memos on strategic fit

3. **finance-consultant** (`agents/finance-consultant.md`)
   - Role: Unit economics, CAC/LTV, profitability modeling
   - Tools: Read, Grep, Glob, Edit, Write, Bash
   - Output: Position memos on financial viability

4. **pm** (`agents/pm.md`)
   - Role: Market research, JTBD analysis, feature prioritization
   - Tools: Read, Grep, Glob, WebSearch, WebFetch
   - Output: Position memos on customer needs and competitive landscape

5. **legal-expert** (`agents/legal-expert.md`)
   - Role: Compliance, data privacy, regulatory requirements
   - Tools: Read, Grep, Glob, WebSearch, WebFetch
   - Output: Position memos on legal risks

### Skills (6)

1. **cos-intake** (`skills/cos/intake/`)
   - Description: Request parsing and staffing for COS deliverables
   - Version: 1.0.0
   - Dependencies: None
   - Files: SKILL.md

2. **prfaq** (`skills/cos/prfaq/`)
   - Description: Amazon-style PR-FAQ generator
   - Version: 1.0.0
   - Dependencies: None
   - Files: SKILL.md

3. **buy-vs-build** (`skills/cos/buy-vs-build/`)
   - Description: 7-dimension decision matrix with TCO calculator
   - Version: 1.0.0
   - Dependencies: python>=3.8
   - Files: SKILL.md, scripts/tco_3y_calc.py, scripts/decision_tracker.py

4. **pmf-validation** (`skills/cos/pmf-validation/`)
   - Description: Product-market fit validation framework
   - Version: 1.0.0
   - Dependencies: None
   - Files: SKILL.md

5. **tenets** (`skills/cos/tenets/`)
   - Description: Non-negotiable principles framework
   - Version: 1.0.0
   - Dependencies: None
   - Files: SKILL.md

6. **security-review** (`skills/cos/security-review/`)
   - Description: Third-party skill security review
   - Version: 1.0.0
   - Dependencies: None
   - Files: SKILL.md

### Tools (2)

1. **tco_3y_calc.py**
   - Purpose: 3-year Total Cost of Ownership calculator for build vs buy decisions
   - Language: Python 3.8+
   - Inputs: Story points, engineering rate, subscription costs, infrastructure costs
   - Output: JSON with build vs buy comparison
   - Location: `skills/cos/buy-vs-build/scripts/tco_3y_calc.py`

2. **decision_tracker.py**
   - Purpose: Track build-vs-buy decisions for weight learning
   - Language: Python 3.8+
   - Inputs: Decision history, actual outcomes
   - Output: Suggested weight adjustments for decision matrix
   - Location: `skills/cos/buy-vs-build/scripts/decision_tracker.py`

## File Structure

```
strategy-workflow/
├── .claude-plugin/
│   └── plugin.json                          # Plugin metadata
├── agents/
│   ├── cos.md                               # Chief of Staff orchestrator
│   ├── strategic-advisor.md                 # Market strategy specialist
│   ├── finance-consultant.md                # Financial modeling specialist
│   ├── pm.md                                # Product manager specialist
│   └── legal-expert.md                      # Legal compliance specialist
├── skills/
│   └── cos/
│       ├── intake/
│       │   └── SKILL.md                     # Request parsing
│       ├── prfaq/
│       │   └── SKILL.md                     # PR-FAQ framework
│       ├── buy-vs-build/
│       │   ├── SKILL.md                     # Decision matrix
│       │   └── scripts/
│       │       ├── tco_3y_calc.py           # TCO calculator
│       │       └── decision_tracker.py      # Weight learning
│       ├── pmf-validation/
│       │   └── SKILL.md                     # PMF framework
│       ├── tenets/
│       │   └── SKILL.md                     # Tenets framework
│       └── security-review/
│           └── SKILL.md                     # Security review process
├── README.md                                # Comprehensive documentation
├── CHANGELOG.md                             # Version history
├── LICENSE                                  # MIT License
└── MANIFEST.md                              # This file
```

## Dependencies

- **Python**: ≥3.8 (for TCO calculator and decision tracker)
- **Claude Model**: claude-opus-4-5 (for COS agent)
- **No external API keys required**
- **All tools run locally**

## Deliverable Types Supported

| Type | Description | Specialists | Output File |
|------|-------------|-------------|-------------|
| **PR-FAQ** | Amazon Working Backwards product proposal | PM, Strategic Advisor, Finance, UX | `product/pr-faq.md` |
| **Buy-vs-Build** | 7-dimension technology decision analysis | PE Designer, Finance, SDE-III, Strategic Advisor | `buy_build.json` |
| **PMF Validation** | Product-market fit assessment plan | PM, Strategic Advisor, UX | `pmf/pmf_plan.md` |
| **Tenets** | Non-negotiable team principles | Strategic Advisor, Legal | `tenets.md` |
| **Requirements** | Feature specification document | PM, UX, PE Designer, SDE-III | `requirements/*.md` |
| **Security Review** | Third-party skill evaluation | Legal, PE Designer | `cos/security-review/review-*.md` |

## Quality Standards

### Amazon-Style Rigor
- Proposal-first approach (write before building)
- Depth in appendices (technical details separate from proposal)
- Dissent preservation (alternative viewpoints documented)
- Tier-1 source requirements for high-stakes claims

### Strategic Frameworks
- PR-FAQ: 5-part structure (press release, external FAQ, internal FAQ, premortem, metrics)
- Buy-vs-Build: 7 dimensions with weighted scoring
- PMF Validation: 4 pillars (JTBD, WTP, activation, retention)
- Tenets: 5 components (statement, rationale, trade-off, examples, measurement)

### Testing & Validation
- All calculations verified (TCO calculator tested with known scenarios)
- Framework completeness (all sections required for each deliverable)
- Source quality gates (Tier-1 and Tier-2 sources only)

## Scrubbing Summary

### Business-Specific Content Removed
- **Removed**: All references to internal business entities
- **Removed**: Business routing logic (business-identifier, business-router)
- **Removed**: Business-specific sub-agents
- **Removed**: Business context imports and dependencies

### Generic Replacements
- **COS Agent**: Stripped to core orchestration without business routing
- **Examples**: Replaced business-specific examples with generic scenarios
- **Specialists**: Only included generic specialist agents (not business-specific variants)

### Verification
- ✅ No internal domain references remaining
- ✅ No business-context imports remaining
- ✅ All examples are business-agnostic
- ✅ Framework is fully portable across industries

## Installation

```bash
# Via Claude Marketplace (when published)
claude plugins install strategy-workflow

# Via GitHub (development)
claude plugins install github:sparkst/strategy-workflow
```

## Usage Examples

### Quick Start: PR-FAQ
```
Use the COS agent to create a PR-FAQ for our new AI-powered analytics dashboard.
```

### Quick Start: Buy-vs-Build
```
Should we build or buy authentication? Analyze using buy-vs-build framework.
```

### Quick Start: PMF Validation
```
Create a PMF validation plan for our SaaS platform targeting indie developers.
```

## Telemetry & Tracking

COS agent creates telemetry files at `telemetry/run-<uuid>.json` tracking:
- Specialists assigned
- Token usage
- Latency (time to complete)
- Skill loads (which skills were invoked)
- Deliverable type and outcome

## Success Metrics

- **G1 (Token Efficiency)**: ≥30% reduction vs baseline (32,000 tokens)
- **G2 (Cycle Time)**: Complete COS requests in ≤9.6 minutes (vs 12 min baseline)
- **G3 (Determinism)**: ≥95% success on scripted steps (TCO calc, skill loads)
- **G5 (Governance)**: 100% skills loaded have `trusted: true` in registry

## Known Limitations

1. **Single-business focus**: Plugin assumes single business context (no multi-business portfolio support)
2. **English-only**: All frameworks and examples in English (no localization)
3. **US-centric**: Financial models use USD, legal frameworks reference US regulations
4. **Python 3.8+ required**: TCO calculator requires Python runtime
5. **No external API integrations**: All tools run locally (no cloud data sources)

## Future Enhancements

- Multi-business portfolio support
- Localization (non-US markets)
- Industry-specific templates (SaaS, ecommerce, enterprise)
- Additional strategic frameworks (OKRs, V2MOM, Strategy Maps)
- Integration with external data sources (market research APIs, financial data)
- Enhanced telemetry and analytics dashboards

## Support

- **Documentation**: See skill SKILL.md files in `skills/cos/*/`
- **Examples**: See README.md for detailed usage examples
- **Issues**: Submit via GitHub Issues
- **Discussions**: GitHub Discussions for questions and feedback

## Credits

**Inspired By:**
- Amazon's Working Backwards methodology (PR-FAQ)
- Rahul Vohra's Superhuman PMF Engine (PMF validation)
- Clayton Christensen's Jobs-to-be-Done framework (JTBD)
- Lenny Rachitsky's PMF research (retention cohorts)
- Ray Dalio's Principles (tenets framework)

**Created By:**
Travis Sparks (2025)

## Version History

- **v1.0.0** (2025-01-28): Initial release

---

**Status**: Ready for Anthropic Marketplace submission
**License**: MIT
**Build**: Production
**Quality**: Fully scrubbed, business-agnostic, portable
