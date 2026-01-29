# Feedback Taxonomy

> Standardized categorization system for feedback classification

## Categories

### 1. Enhancement
**Description**: Improvements to existing features or capabilities

**Keywords**: add, improve, enhance, better, optimize, refactor, upgrade, extend

**Examples**:
- "Add pagination to user list"
- "Improve error messages for validation"
- "Enhance performance of search"

**Priority Indicators**:
- P0: Critical enhancement blocking workflows
- P1: Significant value add to users
- P2: Nice to have improvement
- P3: Future consideration

---

### 2. Bug
**Description**: Something broken, incorrect, or not working as intended

**Keywords**: fix, bug, broken, error, crash, issue, wrong, fails, incorrect

**Examples**:
- "Fix null pointer exception in auth"
- "Login button doesn't work on mobile"
- "Data not saving correctly"

**Priority Indicators**:
- P0: Critical bug causing data loss or security issues
- P1: Bug affecting core functionality
- P2: Minor bug with workaround
- P3: Edge case bug

---

### 3. UX (User Experience)
**Description**: User interface, workflow, or usability issues

**Keywords**: ux, user, confusing, unclear, interface, workflow, usability, intuitive

**Examples**:
- "Workflow is confusing for new users"
- "Too many clicks to complete action"
- "Interface layout is unclear"

**Priority Indicators**:
- P0: UX issue blocking user workflows
- P1: Significant friction for users
- P2: Minor usability improvement
- P3: Polish and refinement

---

### 4. Performance
**Description**: Speed, efficiency, or resource optimization

**Keywords**: slow, performance, optimize, speed, efficient, cache, latency, memory

**Examples**:
- "Page takes too long to load"
- "Query is inefficient"
- "Memory usage is too high"

**Priority Indicators**:
- P0: Performance regression or timeout issues
- P1: Noticeable slowness affecting UX
- P2: Optimization opportunity
- P3: Minor efficiency gain

---

### 5. Documentation
**Description**: Missing, unclear, or outdated documentation

**Keywords**: docs, document, readme, comment, explain, example, guide, tutorial

**Examples**:
- "Need example for API usage"
- "README is outdated"
- "Missing comments for complex logic"

**Priority Indicators**:
- P0: Critical documentation for production features
- P1: Documentation for commonly used features
- P2: Helpful documentation addition
- P3: Nice to have documentation

---

### 6. Architecture
**Description**: System design, structure, or technical debt

**Keywords**: architecture, design, structure, pattern, refactor, decouple, modular

**Examples**:
- "Should use event-driven architecture"
- "Too much coupling between modules"
- "Need to refactor for scalability"

**Priority Indicators**:
- P0: Architectural blocker for critical features
- P1: Technical debt impacting velocity
- P2: Refactoring opportunity
- P3: Long-term architectural improvement

---

## Priority Levels

### P0 - Critical
**When to Use**:
- Blocking production deployment
- Security vulnerability
- Data loss risk
- Major user workflow broken
- System outage

**Response Time**: Immediate (same day)

**Examples**:
- "FIXME: Critical SQL injection vulnerability"
- "TODO: Urgent - users can't checkout"

---

### P1 - Important
**When to Use**:
- Significant impact on productivity
- Core feature improvement needed
- High-value enhancement
- Common user pain point

**Response Time**: Within 1-2 sprints

**Examples**:
- "TODO: Add error handling - users are confused"
- "FIXME: Performance is impacting UX"

---

### P2 - Nice to Have
**When to Use**:
- Minor improvement
- Quality of life enhancement
- Technical debt with workaround
- Low-frequency issue

**Response Time**: Backlog prioritization

**Examples**:
- "TODO: Consider adding dark mode"
- "NOTE: Could optimize this query"

---

### P3 - Future
**When to Use**:
- Long-term consideration
- Low impact
- Nice to have, not needed
- Future feature idea

**Response Time**: No specific timeline

**Examples**:
- "TODO: Someday add export feature"
- "NOTE: Future - consider microservices"

---

## Domain Classification

### Testing
**Indicators**: test, spec, coverage, assert, mock, unit, integration, e2e

### Security
**Indicators**: security, auth, permission, vulnerability, encrypt, token, access

### API
**Indicators**: api, endpoint, route, request, response, rest, graphql

### Database
**Indicators**: database, query, sql, schema, migration, index, constraint

### Frontend
**Indicators**: ui, component, render, view, page, react, vue, angular

### Backend
**Indicators**: server, service, handler, controller, middleware, business logic

### DevOps
**Indicators**: deploy, ci, cd, build, pipeline, docker, kubernetes, infrastructure

### General
**Default**: When no specific domain matches

---

## Extraction Rules

### Comment Type Mapping

| Comment Type | Default Priority | Notes |
|--------------|------------------|-------|
| **TODO** | P2 | General task or improvement |
| **FIXME** | P1 | Something broken or needs fixing |
| **NOTE** | P3 | Observation or future consideration |
| **FEEDBACK** | P1 | Explicit user or reviewer feedback |

### Context Enhancement

When extracting feedback, always capture:
1. **Source**: File path and line number
2. **Context**: Surrounding function/class name
3. **Type**: Comment type (TODO, FIXME, etc.)
4. **Content**: The actual feedback text
5. **Timestamp**: When extracted

---

## Integration Patterns

### Pattern 1: Direct Append
**When**: Feedback is clearly related to existing learning

**Action**: Add to Evidence section with timestamp and source

**Example**:
```markdown
## Evidence
- [2026-01-28] [auth.ts:42]: Need better error messages
```

---

### Pattern 2: Create New Learning
**When**: Feedback represents new insight or pattern

**Action**: Create new learning file with full structure

**Example**: New file `learnings/testing/error-handling.md`

---

### Pattern 3: Update Insight
**When**: Feedback refines or contradicts existing insight

**Action**: Update Insight section and add to Evidence with note

**Example**:
```markdown
## Insight
Error handling should be user-friendly AND developer-friendly
(Updated 2026-01-28 based on user feedback)

## Evidence
- [2026-01-28] [auth.ts:42]: Users confused by technical error messages
```

---

### Pattern 4: Cross-Reference
**When**: Feedback relates to multiple learnings

**Action**: Add evidence to primary learning and cross-references to related

**Example**:
```markdown
## Related
- [learnings/ux/error-messages.md] - User-facing error patterns
- [learnings/security/error-disclosure.md] - Security considerations
```

---

## Quality Checks

### Before Categorization
- [ ] Source and context captured
- [ ] Content is clear and actionable
- [ ] Type correctly identified
- [ ] Timestamp present

### After Categorization
- [ ] Category matches content
- [ ] Priority is justified
- [ ] Domain is accurate
- [ ] Related learnings identified
- [ ] Action items are specific

### After Integration
- [ ] Learning file updated or created
- [ ] Evidence properly formatted
- [ ] Cross-references added
- [ ] Timestamp included
- [ ] Source is traceable
