# COE: {{title}}

**Date:** {{date}}
**Severity:** {{severity}}
**Reporter:** {{reporter}}
**Owner:** {{owner}}
**Related COEs:** {{related_coes}}

---

## What Happened
{{narrative — 2-3 paragraphs max}}

---

## Impact
{{what broke, who affected, duration}}

---

## Timeline
| When | What | Source |
|------|------|--------|
| {{timestamp}} | {{event}} | {{source — git commit, user-reported, file mtime}} |

---

## 5 Whys

**Why 1: {{question — what was the direct symptom?}}**
{{answer}}
*Evidence: {{evidence — file path, log entry, commit hash, or timestamp}}*

**Why 2: {{question — why did that happen?}}**
{{answer}}
*Evidence: {{evidence}}*

**Why 3: {{question — why was that possible?}}**
{{answer}}
*Evidence: {{evidence}}*

**Why 4: {{question — why wasn't it caught earlier?}}**
{{answer}}
*Evidence: {{evidence}}*

**Why 5: {{question — what structural gap allowed this?}}**
{{answer}}
*Evidence: {{evidence}}*

---

## Root Cause
{{one paragraph — always structural or boundary-of-control. Never "someone forgot." If the analysis lands on a behavioral cause, push one level deeper to the missing mechanism.}}

---

## Corrective Actions
| # | Action | Owner | Status |
|---|--------|-------|--------|
| 1 | {{action}} | {{owner}} | Done/Pending |

---

## Preventive Mechanisms
### 1. {{mechanism name}} (deterministic)
{{description — what it enforces, why it doesn't rely on behavior, how it's testable}}

---

## Metrics to Watch
| Metric | Target | Current | How to Measure |
|--------|--------|---------|----------------|
| {{metric name}} | {{target value}} | {{current value or "unknown"}} | {{measurement method}} |

---

## Lessons
1. {{actionable lesson — not a platitude}}
2. {{actionable lesson}}

---

<!-- COE-METADATA: {"severity":"{{severity}}","root_cause":"{{root_cause_one_liner}}","action_count":0,"file_path":"{{file_path}}","related_coes":[]} -->
