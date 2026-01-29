# Strategy Workflow Plugin

A comprehensive strategic planning framework for Claude, featuring Chief of Staff (COS) orchestration and Amazon-style strategic deliverables.

## Overview

This plugin provides a complete strategic planning workflow system that helps teams create rigorous business deliverables:

- **PR-FAQ**: Amazon's "Working Backwards" methodology for product proposals
- **Buy-vs-Build Analysis**: 7-dimension decision framework with TCO calculator
- **PMF Validation**: Product-market fit assessment using JTBD, WTP, activation, and retention
- **Tenets**: Non-negotiable principles that guide decision-making
- **Security Review**: Risk-based framework for evaluating third-party tools

## Key Features

### COS Agent (Chief of Staff)

The COS agent orchestrates specialist teams to produce strategic deliverables:

- Intelligent staffing based on deliverable type
- Parallel specialist coordination
- Dissent management (preserves alternative viewpoints)
- Amazon-style quality standards
- Telemetry tracking

### Strategic Skills

1. **Intake**: Request parsing and specialist staffing
2. **PR-FAQ**: Press release + FAQ for product proposals
3. **Buy-vs-Build**: 7-dimension decision matrix with 3-year TCO calculator
4. **PMF Validation**: Systematic product-market fit assessment
5. **Tenets**: Framework for defining team principles
6. **Security Review**: Third-party skill evaluation process

### Specialist Agents

- **Strategic Advisor**: Market sizing, competitive positioning, GTM strategy
- **Finance Consultant**: Unit economics, CAC/LTV, profitability modeling
- **Product Manager**: JTBD analysis, market research, feature prioritization
- **Legal Expert**: Compliance, data privacy, regulatory requirements

## Installation

```bash
# Install the plugin
claude plugins install strategy-workflow

# Or install from GitHub
claude plugins install github:username/strategy-workflow
```

## Quick Start

### Create a PR-FAQ

```
Use the COS agent to create a PR-FAQ for our new AI-powered analytics dashboard.
```

The COS will:
1. Staff specialists (PM, strategic advisor, finance consultant, UX designer)
2. Coordinate parallel research
3. Synthesize into Amazon-style PR-FAQ
4. Output: `product/pr-faq.md`

### Run Buy-vs-Build Analysis

```
Should we build or buy authentication? Analyze using buy-vs-build framework.
```

The COS will:
1. Staff specialists (PE designer, finance consultant, SDE-III)
2. Evaluate 7 dimensions (strategic fit, TCO, time, risk, control, learning, ecosystem)
3. Calculate 3-year TCO with Python tool
4. Output: `buy_build.json` with recommendation

### Validate Product-Market Fit

```
Create a PMF validation plan for our SaaS platform targeting indie developers.
```

The COS will:
1. Staff specialists (PM, strategic advisor, UX designer)
2. Design validation framework (JTBD interviews, WTP surveys, activation metrics, retention cohorts)
3. Output: `pmf/pmf_plan.md`

### Define Team Tenets

```
Define operating tenets for our engineering team.
```

The COS will:
1. Staff specialists (strategic advisor, legal expert if compliance)
2. Create 3-5 pithy principles with rationale, trade-offs, examples
3. Output: `tenets.md`

## Deliverable Types

| Deliverable | Use Case | Specialists | Output |
|-------------|----------|-------------|--------|
| **PR-FAQ** | New product/feature proposal | PM, Strategic Advisor, Finance, UX | `product/pr-faq.md` |
| **Buy-vs-Build** | Technology decision | PE Designer, Finance, SDE-III | `buy_build.json` |
| **PMF Validation** | Assess product-market fit | PM, Strategic Advisor, UX | `pmf/pmf_plan.md` |
| **Tenets** | Team operating principles | Strategic Advisor, Legal | `tenets.md` |
| **Requirements** | Feature specification | PM, UX, PE Designer, SDE-III | `requirements/*.md` |

## Example Workflows

### Launch Planning

```
1. Create PR-FAQ for new feature
2. Get alignment on vision and customer value
3. Create requirements document
4. Validate PMF assumptions
5. Define launch tenets
```

### Technology Evaluation

```
1. Identify build-vs-buy decision
2. Run 7-dimension analysis
3. Calculate 3-year TCO
4. Review security (if third-party)
5. Create ADR (Architecture Decision Record)
```

## Skills Deep Dive

### PR-FAQ (Amazon Working Backwards)

**Structure:**
- Press Release (1 page): Customer-focused launch announcement
- External FAQ: Customer questions (pricing, setup, privacy)
- Internal FAQ: Strategic, business, technical, operational questions
- Premortem: Failure scenarios and mitigations
- Success Metrics: North Star + KPIs

**Example Use Cases:**
- New product launches
- Major feature proposals
- Strategic pivots
- Stakeholder alignment

### Buy-vs-Build Decision Matrix

**7 Dimensions:**
1. Strategic Fit & Differentiation
2. Total Cost of Ownership (3-year)
3. Time to Market
4. Risk & Uncertainty
5. Control & Flexibility
6. Learning & Capability Building
7. Ecosystem & Community

**TCO Calculator:**
- Inputs: Story points, engineering rate, subscription costs
- Outputs: 3-year build vs buy comparison
- Assumptions: Maintenance burden, infrastructure growth, opportunity cost
- Tool: `skills/cos/buy-vs-build/scripts/tco_3y_calc.py`

### PMF Validation Framework

**4 Pillars:**
1. **JTBD Clarity**: 30 customer interviews for job convergence
2. **Willingness-to-Pay**: Van Westendorp price sensitivity meter
3. **Activation Metrics**: Find the "aha moment" correlated with retention
4. **Retention Cohorts**: Month-1, month-3, month-6 retention curves

**PMF Spectrum:**
- Strong PMF: 60%+ month-3 retention, $75+ WTP, NPS ≥50
- Moderate PMF: 40-60% retention, $50-75 WTP, NPS 40-50
- Weak PMF: 20-40% retention, <$50 WTP, NPS <40
- No PMF: <20% retention, pivot recommended

### Tenets Framework

**Structure:**
- Pithy Statement (1 sentence, opinionated)
- Rationale (Why this matters)
- Trade-Off (What we sacrifice)
- Pass/Fail Examples (Concrete scenarios)
- Measurement (How to verify compliance)

**Best Practices:**
- 3-5 core tenets (not 20)
- Specific, not aspirational
- Acknowledge trade-offs honestly
- Provide concrete examples
- Define measurement criteria

## Advanced Usage

### Custom Specialist Routing

The COS automatically routes to appropriate specialists based on deliverable type. You can override:

```
Use the COS to create a buy-vs-build analysis. Assign strategic-advisor and legal-expert as additional specialists due to regulatory concerns.
```

### Dissent Management

When specialists disagree, the COS preserves dissent rather than forcing consensus:

```
PM recommends $50/month pricing, Finance recommends $99/month.
COS documents both in Internal FAQ, leads with domain owner's recommendation.
```

### Integration with Research Director

For deliverables requiring external research, COS can invoke research-director:

```
1. COS identifies research need (e.g., TAM sizing for PR-FAQ)
2. Invokes research-director: "Research AI support agent market"
3. Research-director produces findings
4. COS integrates into PR-FAQ Internal FAQ
```

## Configuration

### Story Point Calibration

The plugin uses planning poker story points (Fibonacci scale):
- 1 SP = Simple authenticated API (baseline)
- Planning scale: 1, 2, 3, 5, 8, 13, 21
- Coding scale: 0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1, 2, 3, 5

### Engineering Rate

Default: $150/hour. Override in TCO calculator:

```bash
python tco_3y_calc.py --build-sp 13 --eng-rate 200 --buy-monthly 99
```

### Decision Weights (Buy-vs-Build)

Default weights:
- Strategic Fit: 25%
- TCO: 20%
- Time to Market: 20%
- Risk: 15%
- Control: 10%
- Learning: 5%
- Ecosystem: 5%

Customize based on your decision patterns.

## Output Files

The plugin creates structured output:

```
.
├── product/
│   └── pr-faq.md                    # PR-FAQ deliverables
├── buy_build.json                   # Buy-vs-build analysis
├── pmf/
│   ├── pmf_plan.md                  # PMF validation plan
│   ├── jtbd_synthesis.json          # JTBD findings
│   ├── wtp_analysis.json            # Pricing data
│   ├── activation_analysis.json     # Activation metrics
│   └── retention_cohorts.json       # Retention curves
├── tenets.md                        # Team principles
├── requirements/
│   └── *.md                         # Feature specs
├── decisions/
│   └── ADR-*.md                     # Architecture decisions
├── cos/
│   ├── plan.json                    # COS staffing plan
│   └── security-review/
│       └── review-*.md              # Third-party skill reviews
└── telemetry/
    └── run-*.json                   # COS run metadata
```

## Dependencies

- Python ≥3.8 (for TCO calculator)
- No external API keys required
- All tools run locally

## Best Practices

### When to Use PR-FAQ

- Before significant engineering investment (>3 months, >$50K)
- When stakeholder alignment is critical
- For new product launches or major features
- When you need to think backwards from customer value

### When to Use Buy-vs-Build

- Before committing to major platform components
- When evaluating third-party tools vs in-house development
- When opportunity cost is high (small teams, resource constraints)
- For decisions with long-term strategic implications

### When to Use PMF Validation

- Before scaling go-to-market
- When retention is weak (<40% month-2)
- When pivoting product positioning
- Before raising funding (prove PMF exists)

### When to Define Tenets

- When establishing new team culture
- When repeated conflicts signal need for principles
- When scaling requires distributed decision-making
- When you want to prevent re-litigation of decisions

## Comparison with Other Frameworks

| Framework | Focus | Output | Time Investment |
|-----------|-------|--------|-----------------|
| **Strategy Workflow** | Strategic rigor, Amazon-style | Structured docs (PR-FAQ, TCO, PMF) | High (hours to days) |
| **Lean Canvas** | Quick validation | 1-page canvas | Low (30 min) |
| **Business Model Canvas** | Business model design | 9-block canvas | Medium (1-2 hours) |
| **SWOT Analysis** | Situation assessment | 4-quadrant matrix | Low (30 min) |

**Use Strategy Workflow when:**
- Decisions are high-stakes
- Multiple stakeholders need alignment
- You need defensible, data-driven recommendations
- Quality matters more than speed

## Troubleshooting

### COS not routing correctly

Check your request syntax. COS determines deliverable type via keywords:
- "PR-FAQ" or "press release" → PR-FAQ
- "build" AND "buy" → Buy-vs-Build
- "PMF" or "product-market fit" → PMF Validation
- "tenets" or "principles" → Tenets

### TCO calculator errors

Ensure Python ≥3.8 is installed:

```bash
python3 --version
python3 tco_3y_calc.py --build-sp 13 --eng-rate 150 --buy-monthly 99
```

### Specialist disagreements

This is expected! COS preserves dissent. Check:
1. Position memos from each specialist
2. COS synthesis (documents alternatives)
3. Appendices (contains dissenting views)

## Contributing

We welcome contributions! Areas for improvement:
- Additional specialist agents (sales, operations, etc.)
- New strategic frameworks
- Localization (non-US markets)
- Industry-specific templates

## License

MIT License - See LICENSE file

## Support

- Documentation: `/skills/cos/*/SKILL.md`
- Issues: GitHub Issues
- Discussions: GitHub Discussions

## Version History

### v1.0.0 (2025-01-28)
- Initial release
- COS agent with 5 specialist agents
- 6 strategic skills (intake, PR-FAQ, buy-vs-build, PMF, tenets, security-review)
- TCO calculator and decision tracker tools
- Complete documentation

## Acknowledgments

Inspired by:
- Amazon's Working Backwards methodology
- Rahul Vohra's Superhuman PMF Engine
- Clayton Christensen's Jobs-to-be-Done framework
- Lenny Rachitsky's PMF research

## Related Plugins

- **research-workflow**: Deep research with source quality gates
- **content-workflow**: Multi-platform content creation
- **planning-workflow**: TDD-first development planning

---

Built with rigor. Ship with confidence.
