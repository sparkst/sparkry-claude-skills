# Quality Gates Reference

Pre-commit quality gates to ensure code quality

## Default Quality Gates

### 1. Lint

**Command**: `npm run lint`

**What it checks**:
- ESLint rules
- Prettier formatting
- Code style consistency

**Common failures**:
- Unused variables
- Missing semicolons
- Inconsistent formatting
- Console.log statements (in production code)

**How to fix**:
```bash
npm run lint:fix  # Auto-fix most issues
```

---

### 2. Typecheck

**Command**: `npm run typecheck`

**What it checks**:
- TypeScript type errors
- Type safety violations
- Missing type annotations (if strict mode)

**Common failures**:
- `any` type used where specific type expected
- Missing return type annotations
- Type mismatch in function calls
- Null/undefined not handled

**How to fix**:
```bash
# Fix type errors manually
# Add type annotations
# Handle null/undefined cases
```

---

### 3. Test

**Command**: `npm run test`

**What it checks**:
- All tests pass
- No test failures or errors
- Test coverage thresholds (if configured)

**Common failures**:
- Failing unit tests
- Failing integration tests
- Test coverage below threshold

**How to fix**:
```bash
npm test -- --watch  # Run tests in watch mode
# Fix failing tests
# Add tests for new code
```

---

### 4. Edge Function Checks (if applicable)

**Commands**:
```bash
# Check dependency versions
grep -r "@supabase/supabase-js@" supabase/functions/*/index.ts | sort -u

# Should show ONLY: @supabase/supabase-js@2.50.2
```

**What it checks**:
- Dependency version consistency
- Edge functions exist in correct directory
- Smoke tests pass

**Common failures**:
- Mismatched dependency versions
- Frontend calling non-existent edge function
- Missing smoke tests

**How to fix**:
```bash
# Update all edge functions to same version
# Add missing edge functions
# Add smoke tests
```

---

## Custom Quality Gates

### Configuration

Add custom gates in `.qgit.json`:

```json
{
  "quality_gates": [
    {
      "name": "Security Scan",
      "command": "npm audit --production",
      "required": true,
      "fail_on": "high"
    },
    {
      "name": "Bundle Size",
      "command": "npm run build && du -sh dist",
      "required": false
    },
    {
      "name": "Lighthouse Score",
      "command": "npm run lighthouse",
      "required": false,
      "threshold": 90
    }
  ]
}
```

---

### Example: Security Scan

```json
{
  "name": "Security Scan",
  "command": "npm audit --production --audit-level=high",
  "required": true
}
```

**Checks**: High and critical npm vulnerabilities

**Fails if**: High or critical vulnerabilities found

---

### Example: Bundle Size Check

```json
{
  "name": "Bundle Size",
  "command": "npm run build && scripts/check-bundle-size.sh",
  "required": true
}
```

**check-bundle-size.sh**:
```bash
#!/bin/bash
MAX_SIZE=500000  # 500KB
ACTUAL_SIZE=$(du -b dist/bundle.js | cut -f1)

if [ $ACTUAL_SIZE -gt $MAX_SIZE ]; then
  echo "Bundle size $ACTUAL_SIZE exceeds max $MAX_SIZE"
  exit 1
fi

echo "Bundle size OK: $ACTUAL_SIZE bytes"
```

---

### Example: Test Coverage Threshold

```json
{
  "name": "Test Coverage",
  "command": "npm run test:coverage",
  "required": true
}
```

**package.json**:
```json
{
  "scripts": {
    "test:coverage": "jest --coverage --coverageThreshold='{\"global\":{\"lines\":80}}'"
  }
}
```

---

## Gate Execution Order

Gates run in order:

1. **Lint** (fast, fails fast)
2. **Typecheck** (fast, fails fast)
3. **Test** (slow, comprehensive)
4. **Custom gates** (varies)

**Why this order?**:
- Fail fast on simple issues (lint, typecheck)
- Run expensive checks last (tests, builds)

---

## Skipping Gates (Use Sparingly)

### Skip All Gates

```bash
git commit --no-verify -m "wip: work in progress"
```

**⚠️ Warning**: Only use for WIP branches, never for main/master

---

### Skip Specific Gate

```bash
QGIT --skip-lint
```

**⚠️ Warning**: Only skip gates temporarily, fix issues before merging

---

## Troubleshooting

### Issue: Lint Fails with Formatting Errors

**Problem**: Prettier formatting inconsistencies

**Solution**: Auto-fix
```bash
npm run lint:fix
```

---

### Issue: Typecheck Fails with "any" Type Errors

**Problem**: TypeScript strict mode enabled, `any` types not allowed

**Solution**: Add explicit types
```typescript
// Before
function foo(data: any) { ... }

// After
function foo(data: UserData) { ... }
```

---

### Issue: Tests Fail Due to Outdated Snapshots

**Problem**: Component changed, snapshots out of date

**Solution**: Update snapshots
```bash
npm test -- --updateSnapshot
```

---

### Issue: Edge Function Dependency Mismatch

**Problem**: Different `@supabase/supabase-js` versions across functions

**Solution**: Update all to same version
```bash
# Update all edge functions
for dir in supabase/functions/*/; do
  cd "$dir"
  npm install @supabase/supabase-js@2.50.2
  cd -
done
```

---

### Issue: Security Audit Fails

**Problem**: npm audit reports vulnerabilities

**Solution**: Update dependencies
```bash
npm audit fix
# Or manually update specific packages
npm install package@latest
```

---

## Gate Configuration Examples

### Minimal Configuration

```json
{
  "quality_gates": [
    {
      "name": "Lint",
      "command": "npm run lint",
      "required": true
    },
    {
      "name": "Test",
      "command": "npm test",
      "required": true
    }
  ]
}
```

---

### Standard Configuration

```json
{
  "quality_gates": [
    {
      "name": "Lint",
      "command": "npm run lint",
      "required": true
    },
    {
      "name": "Typecheck",
      "command": "npm run typecheck",
      "required": true
    },
    {
      "name": "Test",
      "command": "npm test",
      "required": true
    }
  ]
}
```

---

### Comprehensive Configuration

```json
{
  "quality_gates": [
    {
      "name": "Lint",
      "command": "npm run lint",
      "required": true
    },
    {
      "name": "Typecheck",
      "command": "npm run typecheck",
      "required": true
    },
    {
      "name": "Test",
      "command": "npm test",
      "required": true
    },
    {
      "name": "Test Coverage",
      "command": "npm run test:coverage",
      "required": true
    },
    {
      "name": "Security Scan",
      "command": "npm audit --production --audit-level=high",
      "required": true
    },
    {
      "name": "Bundle Size",
      "command": "npm run build && scripts/check-bundle-size.sh",
      "required": true
    },
    {
      "name": "Edge Functions",
      "command": "scripts/check-edge-functions.sh",
      "required": true
    }
  ]
}
```

---

## Best Practices

### 1. Keep Gates Fast

**❌ Don't**: Run full build and deploy in pre-commit hook
```json
{
  "command": "npm run build && npm run deploy"
}
```

**✅ Do**: Run fast checks only
```json
{
  "command": "npm run lint && npm run typecheck && npm test"
}
```

---

### 2. Fail Fast

**❌ Don't**: Run all gates even if first one fails
**✅ Do**: Stop at first failure (default behavior)

---

### 3. Auto-Fix When Possible

**❌ Don't**: Fail on auto-fixable lint errors
**✅ Do**: Run `lint:fix` before `lint`

```json
{
  "quality_gates": [
    {
      "name": "Lint Fix",
      "command": "npm run lint:fix",
      "required": false
    },
    {
      "name": "Lint",
      "command": "npm run lint",
      "required": true
    }
  ]
}
```

---

### 4. Use CI for Expensive Checks

**Pre-commit** (fast):
- Lint
- Typecheck
- Unit tests

**CI/CD** (slow):
- Integration tests
- E2E tests
- Security scans
- Performance tests
- Bundle analysis

---

## References

- ESLint: https://eslint.org
- TypeScript: https://www.typescriptlang.org
- Jest: https://jestjs.io
- npm audit: https://docs.npmjs.com/cli/v8/commands/npm-audit
