# Conventional Commits Reference

Based on: https://www.conventionalcommits.org

## Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Type

**Must be one of**:

- **feat**: New feature for the user
- **fix**: Bug fix for the user
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Performance improvement
- **test**: Add or update tests
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **chore**: Build process, dependencies, tooling
- **ci**: CI/CD configuration changes
- **revert**: Revert previous commit

---

## Scope

**Optional but recommended**. Indicates the area of the codebase affected.

**Common scopes**:
- `auth` - Authentication/authorization
- `api` - API endpoints
- `ui` - UI components
- `core` - Core domain logic
- `db` - Database/migrations
- `cli` - Command-line interface
- `deps` - Dependencies

**Examples**:
- `feat(auth): add OAuth support`
- `fix(api): resolve token refresh race condition`
- `refactor(ui): simplify modal component`

---

## Description

**Rules**:
- Max 50 characters
- Lowercase
- No period at end
- Imperative mood ("add", not "added" or "adds")

**Good**:
- `add password reset flow`
- `fix race condition in token refresh`
- `refactor auth service for testability`

**Bad**:
- `Added password reset flow` (past tense)
- `Adds password reset flow` (present tense)
- `add password reset flow.` (period at end)
- `Add password reset flow with email verification and token expiry handling` (too long)

---

## Body

**Optional**. Explain "why", not "what" (code shows "what").

**Rules**:
- Separate from description with blank line
- Wrap at 72 characters
- Use multiple paragraphs if needed

**Example**:
```
fix(api): resolve race condition in token refresh

Token refresh logic was not thread-safe, causing intermittent
401 errors under high concurrency. Added mutex lock to prevent
concurrent refresh attempts for the same user.

This fixes the issue reported in production where users were
logged out unexpectedly during peak traffic.
```

---

## Footer

**Optional**. Reference issues, REQs, breaking changes.

**REQ References**:
```
REQ-42, REQ-43
```

**Issue References**:
```
Closes #123
Fixes #456
```

**Breaking Changes**:
```
BREAKING CHANGE: Session storage is no longer supported.
Existing sessions will be invalidated on upgrade.

Migration guide: See docs/migration/v2.0.0.md
```

---

## Examples

### Simple Feature

```
feat(auth): add password reset flow

REQ-43

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

### Bug Fix with Context

```
fix(api): resolve race condition in token refresh

Token refresh logic was not thread-safe, causing intermittent
401 errors under high concurrency. Added mutex lock to prevent
concurrent refresh attempts for the same user.

REQ-45

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

### Feature with Multiple REQs

```
feat(auth): add OAuth provider support

Implement Google and GitHub OAuth providers with PKCE flow.
Includes token refresh logic and session management.

REQ-42, REQ-43

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

### Breaking Change

```
feat(auth): migrate from sessions to JWT tokens

BREAKING CHANGE: Session storage is no longer supported.
Existing sessions will be invalidated on upgrade.

Users must log in again after upgrading to v2.0.0.

Migration guide: See docs/migration/v2.0.0.md

REQ-46

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

### Refactor

```
refactor(auth): simplify token validation logic

Extract token validation into separate service for better
testability and reusability across endpoints.

No functional changes.

REQ-50

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

### Performance Improvement

```
perf(api): optimize database queries

Reduced N+1 queries in user profile endpoint by adding
eager loading. Improves response time from 500ms to 50ms.

REQ-52

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

### Chore (Dependencies)

```
chore(deps): update supabase-js to 2.50.2

Updates @supabase/supabase-js across all edge functions for
security patch (CVE-2024-XXXX).

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

### Documentation

```
docs: add OAuth integration guide

REQ-43

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

### Revert

```
revert: revert "feat(auth): add OAuth support"

This reverts commit a3f8c2e.

OAuth integration causing issues in production. Reverting
while we investigate.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Type Selection Guide

### When to use `feat`

- New user-facing feature
- New API endpoint
- New configuration option
- New capability

**Example**: Add OAuth login option

---

### When to use `fix`

- Bug fix (user-visible)
- Regression fix
- Error handling improvement

**Example**: Fix login button not responding

---

### When to use `refactor`

- Code restructuring (no behavior change)
- Extract function/class
- Rename for clarity
- Simplify logic

**Example**: Extract auth logic into service

---

### When to use `perf`

- Performance improvement
- Optimize query
- Reduce bundle size
- Improve load time

**Example**: Optimize database queries

---

### When to use `test`

- Add new tests
- Update existing tests
- Fix flaky tests

**Example**: Add unit tests for auth service

---

### When to use `docs`

- README updates
- Code comments
- Documentation site changes
- CHANGELOG updates

**Example**: Update OAuth setup guide

---

### When to use `style`

- Code formatting
- Whitespace changes
- Linting fixes (no logic change)

**Example**: Fix ESLint warnings

---

### When to use `chore`

- Dependency updates
- Build configuration
- Tooling changes
- Scripts

**Example**: Update npm dependencies

---

### When to use `ci`

- CI/CD pipeline changes
- GitHub Actions updates
- Deployment configuration

**Example**: Add lint check to CI pipeline

---

## Scope Selection Guide

### Common Scopes by Domain

**Authentication/Authorization**:
- `auth` - Login, signup, OAuth
- `session` - Session management
- `token` - JWT, refresh tokens

**API**:
- `api` - General API changes
- `rest` - REST endpoints
- `graphql` - GraphQL schema

**UI**:
- `ui` - General UI changes
- `components` - Component library
- `pages` - Page-level changes

**Database**:
- `db` - Schema changes
- `migrations` - Database migrations
- `seed` - Seed data

**Testing**:
- `test` - Test infrastructure
- `e2e` - End-to-end tests
- `unit` - Unit tests

**Infrastructure**:
- `ci` - CI/CD
- `deploy` - Deployment
- `docker` - Docker configuration

---

## Best Practices

### 1. One Logical Change Per Commit

**❌ Don't**: Mix features and bug fixes
```
feat(auth): add OAuth and fix login bug
```

**✅ Do**: Separate commits
```
feat(auth): add OAuth support
fix(auth): resolve login button issue
```

---

### 2. Write for the CHANGELOG

Your commit messages will generate the CHANGELOG.

**❌ Don't**: Internal implementation details
```
refactor: changed TokenService to use async/await
```

**✅ Do**: User-facing impact
```
perf(auth): improve login performance (50% faster)
```

---

### 3. Use REQ IDs

Always reference REQ IDs for traceability.

**❌ Don't**:
```
feat(auth): add OAuth

Implemented OAuth providers.
```

**✅ Do**:
```
feat(auth): add OAuth support

REQ-42, REQ-43
```

---

### 4. Explain "Why" in Body

**❌ Don't**:
```
fix(api): fix bug
```

**✅ Do**:
```
fix(api): resolve race condition in token refresh

Token refresh logic was not thread-safe, causing intermittent
401 errors under high concurrency.

REQ-45
```

---

### 5. Use Imperative Mood

**❌ Don't**:
- `added OAuth support`
- `adds OAuth support`
- `adding OAuth support`

**✅ Do**:
- `add OAuth support`

---

## Co-Author Attribution

**Always include**:
```
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

This indicates AI assistance in code generation.

---

## Breaking Changes

### When to Mark as Breaking

- API endpoint changes (URL, method, signature)
- Removed features
- Changed behavior that breaks existing usage
- Database schema changes requiring migration
- Configuration changes

---

### How to Document Breaking Changes

```
BREAKING CHANGE: <description>

<migration instructions>
```

**Example**:
```
feat(auth): migrate to JWT tokens

BREAKING CHANGE: Session storage is no longer supported.

All existing sessions will be invalidated on upgrade.
Users must log in again after upgrading to v2.0.0.

Migration:
1. Update frontend to use JWT tokens
2. Run migration script: npm run migrate:sessions-to-jwt
3. Redeploy frontend and backend

See docs/migration/v2.0.0.md for full guide.

REQ-46
```

---

## Tools

### Commitlint

Enforce Conventional Commits format:

```bash
npm install --save-dev @commitlint/cli @commitlint/config-conventional
```

**commitlint.config.js**:
```javascript
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'feat', 'fix', 'refactor', 'perf', 'test',
        'docs', 'style', 'chore', 'ci', 'revert'
      ]
    ],
    'subject-max-length': [2, 'always', 50],
  }
};
```

---

### Husky

Run commitlint on commit:

```bash
npm install --save-dev husky
npx husky install
npx husky add .husky/commit-msg 'npx --no -- commitlint --edit $1'
```

---

## References

- Conventional Commits: https://www.conventionalcommits.org
- Commitlint: https://commitlint.js.org
- Semantic Versioning: https://semver.org
