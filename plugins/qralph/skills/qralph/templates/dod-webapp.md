# Definition of Done: Web Application

## Code Quality
- [ ] All new code follows existing codebase patterns and conventions
- [ ] No TODO/FIXME comments left unresolved
- [ ] Functions are small, single-purpose, and well-named
- [ ] No dead code or unused imports
- [ ] Type safety enforced (TypeScript strict mode, no `any` casts without justification)

## Testing [BLOCKER]
- [ ] Unit tests cover all new business logic (>80% branch coverage on new code)
- [ ] Integration tests for API endpoints and data flows
- [ ] E2E tests for critical user paths (login, checkout, core workflows)
- [ ] Edge cases tested (empty states, error states, boundary values)
- [ ] Tests are deterministic (no flaky tests introduced)

## Security [BLOCKER]
- [ ] Input validation on all user-facing inputs (forms, URLs, query params)
- [ ] Authentication checks on all protected routes
- [ ] Authorization verified for resource access (no IDOR)
- [ ] XSS prevention (output encoding, CSP headers)
- [ ] CSRF protection on state-changing operations
- [ ] No secrets in client-side code or version control
- [ ] Dependencies scanned for known vulnerabilities

## Operational Readiness
- [ ] Error handling provides useful feedback (no raw stack traces to users)
- [ ] Logging captures meaningful events (no PII in logs)
- [ ] Performance acceptable (Core Web Vitals within thresholds)
- [ ] Mobile responsive and accessible (WCAG 2.1 AA)
- [ ] Environment configuration externalized (no hardcoded URLs/keys)

## Documentation
- [ ] README updated with setup/run instructions for new features
- [ ] API documentation current (OpenAPI/Swagger if applicable)
- [ ] Architecture decisions documented (ADRs for significant choices)
