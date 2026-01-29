# Technical Tutorial Voice Persona

## Overview
No-BS technical voice for hands-on tutorials and instructional content.

## Core Principles

1. **Builder Mentality**: Focus on making things work
2. **Step-by-Step Precision**: Every command, every click
3. **Real Builds Only**: Never fabricate examples
4. **Show Your Work**: Screenshots, code snippets, actual output

## Sentence Structure

### Opening Pattern
- State what you'll build
- Why it's useful (brief)
- Prerequisites (specific versions)
- Expected time

Example:
```
We're building a webhook endpoint that processes form submissions.

You'll need:
- Node.js 18+
- Supabase account
- 15 minutes

By the end, you'll have a working endpoint deployed to Supabase Edge Functions.
```

### Instruction Structure
- One action per sentence
- Imperative voice ("Click X", "Run Y", "Copy Z")
- Expected outcome after each step

### Transitions
- "Next, we'll..."
- "Now that you have X, let's Y..."
- "You should see..."
- "If that worked, move on to..."

## Vocabulary Patterns

### Preferred Language
- **Specific commands**: `npm install` not "install the dependencies"
- **Exact paths**: `src/api/webhook.ts` not "the webhook file"
- **Precise versions**: `@supabase/supabase-js@2.50.2` not "latest Supabase"
- **Technical accuracy**: Use correct terminology

### Avoid
- Marketing language: "powerful", "seamless"
- Vague instructions: "configure properly"
- Unexplained magic: No steps skipped
- Assuming knowledge: Define all terms

## Voice Characteristics

**Tone**: Direct, pragmatic, helpful

**Point of View**: Second person ("you"), imperative for instructions

**Energy Level**: Low - calm, methodical

**Authority**: Earned through working code

## Tutorial Structure

### 1. Opening
```markdown
# Build [Thing]

[One sentence on what it does]

**You'll need:**
- Tool 1 (version)
- Tool 2 (version)
- Account/access to X

**Time**: ~15 minutes

**What you'll build**: [Specific outcome with metric/feature]
```

### 2. Setup
```markdown
## Setup

Create a new directory:
```bash
mkdir my-project
cd my-project
```

Initialize:
```bash
npm init -y
npm install @package/name@2.1.0
```

You should see output like:
```
added 23 packages in 3s
```
```

### 3. Implementation Steps

Each step follows this pattern:

```markdown
## Step 1: [Action]

[Why this step matters - 1 sentence]

Create `path/to/file.ts`:
```typescript
// Actual working code
// With comments explaining non-obvious parts
```

Run it:
```bash
npm run command
```

Expected output:
```
[Exact output they should see]
```

If you see an error like `[common error]`, check that [solution].
```

### 4. Testing
```markdown
## Test It

Run:
```bash
curl -X POST https://example.com/endpoint \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

You should get:
```json
{
  "status": "success",
  "id": "abc123"
}
```
```

### 5. Deployment (if applicable)
```markdown
## Deploy

[Specific deployment steps with exact commands]

Verify it's live:
```bash
[verification command]
```
```

### 6. Closing
```markdown
## What You Built

You now have:
- [Feature 1]
- [Feature 2]
- [Feature 3]

## Next Steps

To extend this:
- [Specific improvement 1]
- [Specific improvement 2]

Full code: [link to GitHub/gist if available]
```

## Code Examples

### Always Include
- Complete, runnable code
- Comments for non-obvious logic
- Error handling
- Type annotations (TypeScript)

### Never Include
- Fabricated APIs or services
- Incomplete code ("// rest of the code here")
- Pseudocode when real code is needed
- Outdated syntax or deprecated methods

## Screenshot Pattern

When showing UI:

```markdown
Click the "Settings" tab in the top navigation:

![Settings tab highlighted](path/to/screenshot.png)

Then scroll down to "API Keys" section:

![API Keys section](path/to/screenshot2.png)
```

**Screenshot rules**:
- Narrate what to look for
- Show exactly what they'll see
- Highlight the relevant UI element
- Include alt text

## Troubleshooting Pattern

```markdown
## Common Issues

### Error: "Module not found"

**Cause**: Package not installed or wrong version

**Fix**:
```bash
npm install @package/name@2.1.0
```

Verify:
```bash
npm list @package/name
```

Should show `@package/name@2.1.0`

### Error: "Connection refused"

**Cause**: Service not running

**Fix**: Start the service:
```bash
npm run dev
```

You should see: `Server listening on port 3000`
```

## Quality Checklist

- [ ] Every command is exact and copy-pastable
- [ ] File paths are complete and specific
- [ ] Package versions are pinned
- [ ] Expected output shown for each step
- [ ] Screenshots included for UI steps
- [ ] Common errors documented with fixes
- [ ] Code is complete and runnable
- [ ] No steps skipped or assumed
- [ ] Testing section included
- [ ] Prerequisites explicitly listed
