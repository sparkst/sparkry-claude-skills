---
name: COS Request Intake
description: Parses COS requests, determines deliverable type (requirements/PR-FAQ/buy-build/PMF/tenets), identifies required specialists, creates staffing plan. Use at start of every COS request.
version: 1.0.0
dependencies: none
---

# COS Request Intake

## Overview

This skill provides the framework for parsing and triaging Chief of Staff (COS) requests, determining the appropriate deliverable type, and creating a staffing plan with the right specialists.

**When to use this skill:**
- At the very start of any COS request
- When the user asks for business/product/strategic work (not coding)
- Before engaging any specialist agents

## Request Types & Deliverable Mapping

| User Request Patterns | Deliverable Type | Template | Specialists Needed |
|----------------------|------------------|----------|-------------------|
| "I need requirements for...", "Spec out...", "Define..." | Requirements Document | `requirements.md` | pm, ux-designer, pe-designer, sde-iii |
| "Create a PR-FAQ for...", "Press release...", "Launch plan..." | PR-FAQ | `product/pr-faq.md` | pm, strategic-advisor, finance-consultant, legal-expert |
| "Should we build or buy...", "Build vs buy analysis..." | Buy-vs-Build Analysis | `buy_build.json` | pe-designer, sde-iii, finance-consultant, strategic-advisor |
| "How do we validate PMF...", "Product-market fit plan..." | PMF Validation Plan | `pmf/pmf_plan.md` | pm, strategic-advisor, ux-designer |
| "Define our tenets...", "Operating principles..." | Tenets Document | `tenets.md` | strategic-advisor, legal-expert (if compliance-related) |
| "Decision record for...", "Document the decision..." | ADR (Architecture Decision Record) | `decisions/ADR-###.md` | Depends on domain |
| "Review this third-party skill..." | Security Review | `cos/security-review/review-<skill-id>.md` | legal-expert, pe-designer |

## Intake Process

### Step 1: Parse the Request

Extract key information:

```json
{
  "raw_request": "I need requirements for a Slack integration feature",
  "parsed": {
    "topic": "Slack integration feature",
    "deliverable_type": "requirements",
    "scope": "feature",
    "domain": "product",
    "urgency": "normal",
    "constraints": [],
    "special_instructions": []
  }
}
```

### Step 2: Determine Deliverable Type

Apply pattern matching:

```python
def determine_deliverable_type(request: str) -> str:
    request_lower = request.lower()

    if any(word in request_lower for word in ["requirements", "spec", "define", "scoping"]):
        return "requirements"

    elif any(word in request_lower for word in ["pr-faq", "prfaq", "press release", "launch"]):
        return "prfaq"

    elif "build" in request_lower and "buy" in request_lower:
        return "buy-vs-build"

    elif any(word in request_lower for word in ["pmf", "product-market fit", "validation plan"]):
        return "pmf-validation"

    elif any(word in request_lower for word in ["tenets", "principles", "operating model"]):
        return "tenets"

    elif any(word in request_lower for word in ["decision", "adr", "decision record"]):
        return "adr"

    elif "review" in request_lower and "skill" in request_lower:
        return "security-review"

    else:
        # Default: requirements (most common)
        return "requirements"
```

### Step 3: Identify Required Specialists

Based on deliverable type and domain:

```json
{
  "deliverable_type": "requirements",
  "domain": "product",
  "specialists": [
    {
      "role": "pm",
      "required": true,
      "rationale": "Owns product strategy and prioritization"
    },
    {
      "role": "ux-designer",
      "required": true,
      "rationale": "Designs user flows and interaction patterns"
    },
    {
      "role": "pe-designer",
      "required": true,
      "rationale": "Defines system architecture and technical approach"
    },
    {
      "role": "sde-iii",
      "required": true,
      "rationale": "Assesses implementation feasibility and complexity"
    },
    {
      "role": "legal-expert",
      "required": false,
      "rationale": "May be needed if Slack integration involves customer data privacy concerns",
      "trigger": "if user data involved"
    }
  ]
}
```

**Specialist Selection Matrix:**

| Deliverable Type | Always Required | Often Required | Sometimes Required |
|------------------|----------------|----------------|-------------------|
| Requirements | pm, ux-designer, pe-designer, sde-iii | legal-expert | finance-consultant, strategic-advisor |
| PR-FAQ | pm, strategic-advisor | finance-consultant | legal-expert, ux-designer |
| Buy-vs-Build | pe-designer, finance-consultant | sde-iii, strategic-advisor | legal-expert |
| PMF Validation | pm, strategic-advisor | ux-designer | finance-consultant |
| Tenets | strategic-advisor | legal-expert (if compliance) | pm |
| Security Review | legal-expert, pe-designer | - | - |

### Step 4: Estimate Effort & Timeline

Based on scope and complexity:

```json
{
  "effort_estimate": {
    "story_points": 5,
    "breakdown": {
      "intake": 0.5,
      "specialist_research": 2,
      "synthesis": 1.5,
      "review_iterations": 1
    },
    "estimated_duration": "2-3 days",
    "confidence": "medium"
  }
}
```

### Step 5: Create Staffing Plan

Output: `cos/plan.json`

```json
{
  "plan_id": "cos_plan_001",
  "created_at": "2025-10-18T16:00:00Z",
  "request": {
    "raw": "I need requirements for a Slack integration feature",
    "parsed_topic": "Slack integration feature",
    "deliverable_type": "requirements",
    "urgency": "normal"
  },
  "staffing": {
    "specialists_assigned": [
      {
        "role": "pm",
        "tasks": ["Market research", "User needs analysis", "Feature prioritization"],
        "effort_sp": 1.5
      },
      {
        "role": "ux-designer",
        "tasks": ["User flow design", "Interaction patterns", "Accessibility review"],
        "effort_sp": 1.5
      },
      {
        "role": "pe-designer",
        "tasks": ["Architecture options (webhooks vs Events API)", "Scalability analysis"],
        "effort_sp": 1
      },
      {
        "role": "sde-iii",
        "tasks": ["Implementation complexity", "Dependency analysis (Slack SDK)", "Effort estimation"],
        "effort_sp": 1
      }
    ],
    "total_effort_sp": 5,
    "coordinator": "cos"
  },
  "deliverables": {
    "primary": "requirements/slack-integration.md",
    "supporting": [
      "research/competitive-analysis.md",
      "research/options_matrix.json",
      "cos/plan.json"
    ]
  },
  "timeline": {
    "estimated_duration_days": 3,
    "milestones": [
      {"day": 1, "deliverable": "Initial research and specialist position memos"},
      {"day": 2, "deliverable": "Options matrix and dissent resolution"},
      {"day": 3, "deliverable": "Final requirements document"}
    ]
  },
  "next_steps": [
    "COS orchestrates specialist fan-out",
    "PM conducts market research on Slack integrations",
    "UX-designer maps user flows",
    "PE-designer evaluates architecture options",
    "SDE-III assesses implementation complexity"
  ]
}
```

## Scope Clarification Questions

If the request is ambiguous, the intake skill should prompt for clarification:

**Example Clarifications:**
- "You asked for 'requirements for Slack integration'. Do you mean:
  - A. Integration to send notifications FROM our app TO Slack?
  - B. Integration to trigger our app actions FROM Slack commands?
  - C. Both directions (bidirectional integration)?"

- "What's the primary use case/JTBD for this integration?"

- "Are there any must-have features or non-negotiable constraints?"

- "What's the urgency? (Needs to ship this month vs exploratory for future roadmap)"

## Output

After intake processing, creates:

1. **`cos/plan.json`** - Staffing plan with specialists, tasks, timeline
2. **Confirmation prompt to user** - "I've created a plan for '{topic}'. This will require {specialists} and take approximately {duration}. The primary deliverable will be {deliverable_type}. Shall I proceed?"

## Quality Checklist

Before proceeding to specialist coordination:

- [ ] Deliverable type clearly determined
- [ ] All required specialists identified
- [ ] Effort estimate provided (SP and days)
- [ ] Timeline includes milestones
- [ ] User confirmation obtained (if request was ambiguous)

## Integration with COS Agent

The `cos` agent workflow:

```
1. User makes request
2. COS loads intake skill
3. Intake skill creates cos/plan.json
4. COS confirms plan with user
5. User approves → COS orchestrates specialists
6. Specialists produce position memos
7. Dissent-moderator (if needed) creates options_matrix.json
8. Synthesis-writer creates final deliverable
```

## References

See `templates/cos-plan.json` for full JSON schema
See `.claude/agents/cos.md` for orchestrator agent details
