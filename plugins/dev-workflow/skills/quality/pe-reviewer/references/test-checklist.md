# Test Best Practices Checklist

> **Source**: Moved from CLAUDE.md § Writing Tests Best Practices
> **Load when**: PE-Reviewer is reviewing test files

## Mandatory Rules (MUST)

### 1. MUST parameterize inputs
- Never embed unexplained literals (42, "foo") directly in tests
- Use named constants or test fixtures

```typescript
// ❌ Bad
expect(calculateCost(42, "foo")).toBe(3.5);

// ✅ Good
const INPUT_TOKENS = 1000;
const MODEL_NAME = "gpt-4";
expect(calculateCost(INPUT_TOKENS, MODEL_NAME)).toBe(0.03);
```

### 2. MUST ensure tests can fail for real defects
- No trivial asserts like `expect(2).toBe(2)`
- Every test must catch a specific bug if introduced

```typescript
// ❌ Bad (always passes)
test('adds numbers', () => {
  expect(1 + 1).toBe(2);
});

// ✅ Good (catches logic errors)
test('REQ-42 — calculates total with tax', () => {
  expect(calculateTotal(100, 0.08)).toBe(108);
});
```

### 3. MUST align test description with assertion
- Test name must state exactly what the final expect verifies
- If wording and assert don't align, rename or rewrite

```typescript
// ❌ Bad (description doesn't match assertion)
test('validates user input', () => {
  expect(response.statusCode).toBe(200);
});

// ✅ Good
test('returns 200 for valid user input', () => {
  expect(response.statusCode).toBe(200);
});
```

### 4. MUST compare to independent expectations
- Never re-use function output as the oracle
- Use pre-computed values or domain properties

```typescript
// ❌ Bad (circular logic)
const result = calculateHash(input);
expect(calculateHash(input)).toBe(result);

// ✅ Good
const EXPECTED_HASH = "a94a8fe5ccb19ba61c4c...";
expect(calculateHash("hello")).toBe(EXPECTED_HASH);
```

### 5. MUST follow same quality rules as production code
- Prettier, ESLint, strict types apply to tests
- No `any` types without justification
- No disabled linting rules

## Recommended Practices (SHOULD)

### 6. SHOULD express invariants or axioms
- Use property-based testing for algorithmic code
- Test mathematical properties (commutativity, idempotence, round-trip)

```typescript
import fc from 'fast-check';

test('concatenation functoriality', () => {
  fc.assert(
    fc.property(
      fc.string(),
      fc.string(),
      (a, b) =>
        getCharacterCount(a + b) ===
        getCharacterCount(a) + getCharacterCount(b)
    )
  );
});
```

### 7. SHOULD group tests by function
```typescript
describe('calculateCost', () => {
  test('REQ-9 — returns 0 for zero tokens', () => { ... });
  test('REQ-9 — calculates input cost correctly', () => { ... });
  test('REQ-9 — calculates output cost correctly', () => { ... });
});
```

### 8. SHOULD use `expect.any()` for dynamic values
```typescript
// Variable IDs, timestamps, etc.
expect(response).toEqual({
  id: expect.any(String),
  timestamp: expect.any(Number),
  value: 42
});
```

### 9. SHOULD use strong assertions over weak ones
```typescript
// ❌ Weak
expect(x).toBeGreaterThanOrEqual(1);

// ✅ Strong
expect(x).toEqual(1);
```

### 10. SHOULD test edge cases, realistic input, unexpected input
- Boundary values (0, -1, MAX_INT)
- Empty inputs ([], "", null, undefined)
- Invalid types (if not caught by TypeScript)
- Extreme values (very large arrays, long strings)

### 11. SHOULD NOT test type-checker-caught conditions
```typescript
// ❌ Bad (TypeScript catches this)
test('rejects string when number expected', () => {
  expect(() => add("a", "b")).toThrow();
});
```

## REQ-ID Citation

**MUST**: Every test cites the REQ-ID it covers

```typescript
describe('REQ-42 — User authentication flow', () => {
  test('allows login with valid credentials', () => { ... });
  test('rejects invalid passwords', () => { ... });
});
```

## Edge Function Smoke Tests (MANDATORY)

**Template** for every new edge function:

```typescript
// supabase/functions/<name>/__tests__/smoke.test.ts
import { createClient } from '@supabase/supabase-js@2.50.2';

describe('<name> smoke tests', () => {
  it('endpoint exists and responds', async () => {
    const supabase = createClient(/* test config */);
    const { error, status } = await supabase.functions.invoke('<name>');
    expect([200, 400, 401, 500]).toContain(status); // NOT 404
  });
});
```

**MUST verify**:
- Endpoint exists (not 404)
- Auth required (401 without token)
- Basic success path (200 with valid input)
