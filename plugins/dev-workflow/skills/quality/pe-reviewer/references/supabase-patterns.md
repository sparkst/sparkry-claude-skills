# Supabase Edge Function Patterns

> **Purpose**: Best practices for Supabase Edge Functions (Deno runtime)
> **Load when**: Reviewing edge function code

## Edge Function Pre-Deploy Checklist

**MUST verify before approving edge function changes**:
- [ ] All imports use pinned `@supabase/supabase-js@2.50.2`
- [ ] Function has smoke test in `__tests__/smoke.test.ts`
- [ ] Frontend calls match function signatures (no arg count mismatches)
- [ ] Function appears in `supabase/functions/` directory (not just referenced)
- [ ] CORS headers present if called from browser

**P0 Blockers**:
- Dependency version mismatch across edge functions
- Frontend calling non-existent edge function
- TypeScript signature mismatch (getAllPersonas example)

## CORS Headers (Browser Calls)

```typescript
import { corsHeaders } from '../_shared/cors.ts';

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  return new Response(
    JSON.stringify({ data }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  );
});
```

## Auth Validation

```typescript
const authHeader = req.headers.get('Authorization');
if (!authHeader) {
  return new Response(
    JSON.stringify({ error: 'Missing authorization header' }),
    { status: 401, headers: corsHeaders }
  );
}

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_ANON_KEY')!,
  { global: { headers: { Authorization: authHeader } } }
);

const { data: { user }, error } = await supabase.auth.getUser();
if (error || !user) {
  return new Response(
    JSON.stringify({ error: 'Invalid token' }),
    { status: 401, headers: corsHeaders }
  );
}
```

## Error Handling

```typescript
try {
  // Function logic
} catch (error) {
  console.error('Function error:', error);
  return new Response(
    JSON.stringify({
      error: 'Internal server error',
      // DO NOT leak error details in production
      ...(Deno.env.get('ENVIRONMENT') === 'development' && { details: error.message })
    }),
    { status: 500, headers: corsHeaders }
  );
}
```

## Smoke Test Template

```typescript
// supabase/functions/<name>/__tests__/smoke.test.ts
import { createClient } from '@supabase/supabase-js@2.50.2';

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_ANON_KEY')!
);

Deno.test('endpoint exists and responds', async () => {
  const { data, error, status } = await supabase.functions.invoke('<name>');

  // Verify endpoint exists (not 404)
  expect([200, 400, 401]).toContain(status);
});
```

## Common Anti-Patterns

### ❌ Don't: Hardcode credentials
```typescript
const supabase = createClient(
  'https://xxx.supabase.co',  // ❌ Hardcoded
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'  // ❌ Hardcoded
);
```

### ✅ Do: Use environment variables
```typescript
const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!  // ⚠️ Service role = elevated privileges
);
```

### ❌ Don't: Mix dependency versions
```typescript
// edge-function-1/index.ts
import { createClient } from '@supabase/supabase-js@2.50.2';

// edge-function-2/index.ts
import { createClient } from '@supabase/supabase-js@2.45.0';  // ❌ Version mismatch
```

### ✅ Do: Pin consistent version
```typescript
// ALL edge functions
import { createClient } from '@supabase/supabase-js@2.50.2';
```

## RLS (Row Level Security) Validation

**Tool**: `scripts/supabase-rls-checker.py`

Ensure all tables have RLS enabled:

```sql
-- ❌ Missing RLS
CREATE TABLE personas (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id)
);

-- ✅ RLS enabled
CREATE TABLE personas (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id)
);

ALTER TABLE personas ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access their own personas"
  ON personas FOR ALL
  USING (auth.uid() = user_id);
```
