# Progressive Documentation Templates

Templates for three-tier documentation structure

## Root README.md Template

```markdown
# [Project Name]

## Mental Model
[One-paragraph explanation of what this project does and why it exists]

## Entry Points
- `src/auth/` — Authentication and authorization
- `src/api/` — HTTP endpoints and integrations
- `src/core/` — Domain logic and business rules
- `src/ui/` — UI components and pages
- `src/db/` — Database schema and migrations

## Getting Started

### Prerequisites
- Node.js 18+
- PostgreSQL 14+
- [Other dependencies]

### Installation
\`\`\`bash
npm install
cp .env.example .env
# Edit .env with your configuration
npm run db:migrate
npm run dev
\`\`\`

### Development
\`\`\`bash
npm run dev          # Start dev server
npm run test         # Run tests
npm run lint         # Lint code
npm run typecheck    # TypeScript check
\`\`\`

## Architecture
[2-3 sentence high-level architecture overview]

See domain READMEs for detailed documentation:
- [Authentication](src/auth/README.md)
- [API](src/api/README.md)
- [Core Domain](src/core/README.md)

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License
[License type]
```

**Keep it**: ≤200 words

---

## Domain README.md Template

```markdown
# [Domain Name]

## Purpose
[What this domain does and why it exists - 1-2 sentences]

## Boundaries

### In Scope
- [Responsibility 1]
- [Responsibility 2]

### Out of Scope
- [What this domain does NOT handle]

## Key Files

### Core Types
- `types.ts` — Domain types and interfaces
- `schema.ts` — Database schema (if applicable)

### Business Logic
- `service.ts` — Core business logic
- `validators.ts` — Input validation
- `policies.ts` — Business rules and policies

### Integrations
- `api.ts` — External API calls
- `repository.ts` — Database access

### Tests
- `__tests__/service.spec.ts` — Service tests
- `__tests__/integration.spec.ts` — Integration tests

## Patterns

### [Pattern Name]
[Description of idiom or convention to follow]

**Example**:
\`\`\`typescript
// Code example
\`\`\`

### [Another Pattern]
...

## Dependencies

### Upstream Dependencies
- [Domain X] — [Why we depend on it]

### Downstream Consumers
- [Domain Y] — [How they use this domain]

## Common Tasks

### Add New [Entity]
1. Define type in `types.ts`
2. Add schema in `schema.ts`
3. Implement service method in `service.ts`
4. Add tests in `__tests__/service.spec.ts`

### Modify [Process]
...

## Gotchas
- [Common issue 1 and how to avoid it]
- [Common issue 2 and how to avoid it]

## References
- [Design Doc](../../docs/design/[domain].md)
- [ADR](../../docs/adr/[number]-[title].md)
```

**Keep it**: ≤500 words

---

## .claude-context Template

```
Domain: [Feature/Component Name]
Purpose: [One-sentence description]

Key Concepts:
- [Concept 1]: [Brief explanation]
- [Concept 2]: [Brief explanation]

Important Files:
- [file1.ts]: [What it does]
- [file2.ts]: [What it does]

Common Tasks:
- "Add new [thing]": Edit [file.ts], add to [section]
- "Modify [behavior]": Update [file.ts]

Patterns:
- [Pattern 1]: [How to apply it]
- [Pattern 2]: [How to apply it]

Gotchas:
- [Issue 1]: [How to avoid]
- [Issue 2]: [How to avoid]

Dependencies:
- Upstream: [list]
- Downstream: [list]

Testing:
- Unit tests: [location]
- Integration tests: [location]
```

**Keep it**: ≤300 words

---

## CHANGELOG.md Template

Based on **Keep a Changelog** (https://keepachangelog.com)

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- REQ-XX: [New feature description]

### Changed
- REQ-XX: [Change description]

### Fixed
- REQ-XX: [Bug fix description]

## [1.2.0] - 2026-01-28

### Added
- REQ-42: OAuth authentication with Google and GitHub providers
- REQ-43: Password reset flow via email with token expiry

### Changed
- REQ-44: Improved error messages for login failures (now include recovery steps)

### Fixed
- REQ-45: Race condition in token refresh causing intermittent 401 errors

### Deprecated
- REQ-46: Legacy session storage (migrate to JWT tokens by v2.0.0)

## [1.1.0] - 2026-01-15

### Added
- REQ-38: User profile management
- REQ-39: Email verification

### Fixed
- REQ-40: Password validation edge case
- REQ-41: Session timeout not clearing local storage

## [1.0.0] - 2026-01-01

### Added
- REQ-01: Initial release
- REQ-02: User registration and login
- REQ-03: Session management
- REQ-04: Basic user profile
```

---

## Version Numbering Guide

**Semantic Versioning**: MAJOR.MINOR.PATCH

### MAJOR (Breaking Changes)
- Incompatible API changes
- Removed features
- Changed behavior that breaks existing usage

**Example**: v1.x.x → v2.0.0
```markdown
### BREAKING CHANGES
- Session storage replaced with JWT tokens (sessions no longer supported)
- Auth API endpoint changed from `/auth/login` to `/api/v2/auth/login`
```

### MINOR (New Features)
- New features (backward-compatible)
- New capabilities added
- Deprecations (feature marked for removal)

**Example**: v1.1.x → v1.2.0
```markdown
### Added
- REQ-42: OAuth authentication support
```

### PATCH (Bug Fixes)
- Bug fixes (backward-compatible)
- Performance improvements
- Documentation updates

**Example**: v1.1.0 → v1.1.1
```markdown
### Fixed
- REQ-45: Race condition in token refresh
```

---

## CHANGELOG Categories

### Added
New features, capabilities, endpoints, etc.

```markdown
### Added
- REQ-42: OAuth authentication with Google, GitHub, and Microsoft providers
- REQ-43: Password reset flow with email verification
```

### Changed
Changes to existing functionality (non-breaking)

```markdown
### Changed
- REQ-44: Improved error messages for login failures
- REQ-47: Updated password validation to require 12+ characters
```

### Deprecated
Features marked for removal in future versions

```markdown
### Deprecated
- REQ-46: Legacy session storage (will be removed in v2.0.0)
- Use JWT tokens instead
```

### Removed
Features removed (usually causes breaking change)

```markdown
### Removed
- REQ-50: Session-based auth (removed in favor of JWT)
```

### Fixed
Bug fixes, error corrections

```markdown
### Fixed
- REQ-45: Race condition in token refresh causing intermittent logouts
- REQ-48: Memory leak in WebSocket connection cleanup
```

### Security
Security fixes, vulnerability patches

```markdown
### Security
- REQ-51: Patched XSS vulnerability in user profile display
- REQ-52: Updated bcrypt to v5.1.0 (CVE-2024-XXXX)
```

---

## Examples

### Example: New Feature Release

```markdown
## [1.3.0] - 2026-02-15

### Added
- REQ-55: Multi-factor authentication (TOTP)
- REQ-56: Backup codes for MFA recovery
- REQ-57: SMS verification as MFA alternative

### Changed
- REQ-58: Login flow updated to support MFA step

### Fixed
- REQ-59: Edge case in password reset token expiry
```

### Example: Bug Fix Release

```markdown
## [1.2.1] - 2026-02-01

### Fixed
- REQ-60: Race condition in concurrent login attempts
- REQ-61: Incorrect error code for expired tokens (was 500, now 401)
- REQ-62: Memory leak in session cleanup background job
```

### Example: Breaking Change Release

```markdown
## [2.0.0] - 2026-03-01

### BREAKING CHANGES
- Session-based authentication removed (use JWT tokens)
- API endpoints moved from `/auth/*` to `/api/v2/auth/*`
- Minimum Node.js version increased to 20+

### Removed
- REQ-46: Session storage support
- REQ-65: Legacy `/auth/login` endpoint

### Added
- REQ-66: JWT refresh token rotation
- REQ-67: Token introspection endpoint

### Migration Guide
See [docs/migration/v2.0.0.md](docs/migration/v2.0.0.md) for upgrade instructions.
```

---

## Best Practices

### 1. Reference REQ IDs
Always include REQ IDs so changes are traceable to requirements.

❌ Don't: `Added OAuth support`
✅ Do: `REQ-42: OAuth authentication with Google and GitHub providers`

### 2. Write User-Facing Descriptions
CHANGELOG is for users, not developers.

❌ Don't: `Refactored token service to use async/await`
✅ Do: `Improved login performance (50% faster token validation)`

### 3. Group Related Changes
Combine related changes under one entry.

❌ Don't:
```markdown
- REQ-42: Added Google OAuth
- REQ-43: Added GitHub OAuth
```

✅ Do:
```markdown
- REQ-42, REQ-43: OAuth authentication with Google and GitHub providers
```

### 4. Use Unreleased Section
Add changes to `[Unreleased]` during development, then move to versioned section on release.

### 5. Keep Consistent Format
Use past tense, action verbs, and concise descriptions.

❌ Don't: `We are adding OAuth which will allow users to...`
✅ Do: `Added OAuth authentication with Google provider`

---

## Progressive Disclosure Strategy

### Tier 1: Root README
**Audience**: New developers, executives, stakeholders
**Goal**: Answer "What is this?" in 30 seconds
**Content**: Mental model, entry points, getting started

### Tier 2: Domain READMEs
**Audience**: Developers working in domain
**Goal**: Understand boundaries, patterns, dependencies
**Content**: Purpose, key files, patterns, gotchas

### Tier 3: .claude-context
**Audience**: AI assistants (Claude Code)
**Goal**: Provide context for code generation
**Content**: Key concepts, common tasks, domain-specific knowledge

---

## References

- Keep a Changelog: https://keepachangelog.com
- Semantic Versioning: https://semver.org
- Progressive Disclosure: https://www.nngroup.com/articles/progressive-disclosure/
