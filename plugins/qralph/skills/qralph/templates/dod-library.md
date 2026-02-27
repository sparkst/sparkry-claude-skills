# Definition of Done: Library / Package

## Code Quality
- [ ] All new code follows existing codebase patterns and conventions
- [ ] Public API is minimal and well-documented
- [ ] No TODO/FIXME comments left unresolved
- [ ] Functions are small, single-purpose, and well-named
- [ ] No dead code or unused exports
- [ ] Type definitions complete and exported

## Testing [BLOCKER]
- [ ] Unit tests cover all public API functions (>90% branch coverage)
- [ ] Edge cases tested (null inputs, empty collections, boundary values)
- [ ] Error cases tested (invalid inputs produce clear errors)
- [ ] Backward compatibility verified (no breaking changes without major version bump)
- [ ] Tests are deterministic (no flaky tests introduced)

## Security [BLOCKER]
- [ ] No unsafe operations (eval, exec, dynamic require without validation)
- [ ] Input validation on all public functions
- [ ] No bundled secrets or credentials
- [ ] Dependencies scanned for known vulnerabilities
- [ ] Supply chain safety (pinned dependencies, lock file committed)

## Operational Readiness
- [ ] Package builds successfully (clean build from scratch)
- [ ] Bundle size acceptable (no unnecessary dependencies)
- [ ] Tree-shaking supported (ESM exports)
- [ ] Version follows semver correctly
- [ ] CHANGELOG updated

## Documentation
- [ ] README with installation, quick start, and API reference
- [ ] JSDoc/docstrings on all public API functions
- [ ] Examples for common use cases
- [ ] Migration guide if breaking changes
- [ ] Architecture decisions documented (ADRs for significant choices)
