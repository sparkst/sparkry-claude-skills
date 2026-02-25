# Definition of Done: API / Backend Service

## Code Quality
- [ ] All new code follows existing codebase patterns and conventions
- [ ] No TODO/FIXME comments left unresolved
- [ ] Functions are small, single-purpose, and well-named
- [ ] No dead code or unused imports
- [ ] Type safety enforced (strict types, validated at boundaries)

## Testing [BLOCKER]
- [ ] Unit tests cover all new business logic (>80% branch coverage on new code)
- [ ] Integration tests for all API endpoints (request/response validation)
- [ ] Error path testing (4xx and 5xx responses verified)
- [ ] Edge cases tested (empty payloads, malformed input, boundary values)
- [ ] Database migrations tested (up + down, idempotent)
- [ ] Tests are deterministic (no flaky tests introduced)

## Security [BLOCKER]
- [ ] Input validation on all endpoints (schema validation, sanitization)
- [ ] Authentication enforced on all protected endpoints
- [ ] Authorization verified for resource access (no IDOR, no privilege escalation)
- [ ] Rate limiting configured for public endpoints
- [ ] SQL injection prevention (parameterized queries, ORM usage)
- [ ] No secrets in code or version control
- [ ] CORS configured correctly (no wildcard in production)
- [ ] Dependencies scanned for known vulnerabilities

## Operational Readiness
- [ ] Error responses follow consistent format (error codes, messages)
- [ ] Health check endpoint operational
- [ ] Structured logging with request correlation IDs
- [ ] Graceful shutdown handling
- [ ] Environment configuration externalized
- [ ] Database connection pooling configured

## Documentation
- [ ] API documentation current (OpenAPI spec updated)
- [ ] README updated with setup/run/deploy instructions
- [ ] Architecture decisions documented (ADRs for significant choices)
- [ ] Runbook updated for operational procedures
