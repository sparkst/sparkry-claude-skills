---
name: image-generation
description: Generate AI images for social media articles via Gemini web interface with learnable style guide, creative variation system, and Playwright browser automation
---

# QIMAGE

## Role
You generate compelling hero images for social media articles using Gemini's image generation via Playwright browser automation. You combine Nano Banana Pro prompting, a learnable style guide, and visual psychology research.

## Modes

| Mode | Trigger | What Happens |
|------|---------|-------------|
| **Generate** | `QIMAGE: <concept>` | Build prompt, generate via Gemini, save image |
| **Variations** | `QIMAGE: <concept> --variations 4` | Generate N creative variations |
| **Learn** | `QIMAGE learn: <images>` | Analyze images, update style guide |
| **Refine** | `QIMAGE refine: <feedback>` | Modify last prompt, regenerate |

## Workflow

### Step 1: Run the orchestrator

```bash
python3 .claude/skills/content/image-generation/tools/qimage.py \
  --mode generate \
  --concept "Your concept here" \
  [--variations 4] \
  [--text "OVERLAY TEXT"] \
  [--aspect-ratio "16:9"] \
  [--refine "make it warmer"]
```

For learn mode:
```bash
python3 .claude/skills/content/image-generation/tools/qimage.py \
  --mode learn \
  --images "path1.png,path2.png" \
  [--notes "These got 2x engagement"]
```

The script outputs:
- **Prompts** ready to paste into Gemini (1 per variation)
- **File naming** instructions (date + description)
- **Style guide updates** (learn mode)
- All decisions pre-made — just follow the output

### Step 2: Playwright automation (generate/variations/refine modes)

For each prompt from Step 1:

1. **Open Gemini**:
   ```
   browser_navigate → https://gemini.google.com/app
   ```

2. **Check login**: Take `browser_snapshot` to verify logged in as YOUR_GOOGLE_ACCOUNT. If login page shown, alert user to log in manually in the Playwright browser window.

3. **Find input and type prompt**: Use `browser_snapshot` to find the prompt input element ref, then `browser_type` with the ref and the full prompt as a single line (no newlines — newlines cause auto-submit). Set `submit: true` to send.

4. **Wait for generation**: Wait 20-30 seconds. Use `browser_take_screenshot` to check progress. Look for the generated image in the response.

5. **Save image directly to disk** using `browser_run_code`:
   ```javascript
   async ({ page }) => {
     // Find the generated image element and get its src URL
     const imgSrc = await page.evaluate(() => {
       const imgs = document.querySelectorAll('img[src*="lh3.googleusercontent.com"]');
       return imgs[imgs.length - 1]?.src;
     });
     // Navigate to image URL and save via screenshot or response interception
     const response = await page.goto(imgSrc);
     const buffer = await response.body();
     require('fs').writeFileSync('<output-path>', buffer);
     await page.goBack();
   }
   ```
   Replace `<output-path>` with the path from script output (e.g., `./images/YYYY-MM-DD-concept-v1.png`).

6. **For variations**: Navigate back to Gemini (`browser_navigate`), repeat steps 3-5 for each prompt.

### Step 3: Report

Show user what was generated:
```markdown
## Generated Image(s)
- **File**: images/YYYY-MM-DD-description.png
- **Prompt**: [abbreviated]
- **Concept**: [one-line description]
```

## References (loaded by script automatically)

| Reference | Purpose |
|-----------|---------|
| `references/style-guide.md` | Learnable visual preferences (updated by learn mode) |
| `references/image-psychology.md` | What makes social media images perform |
| `references/creative-angles.md` | Variation ideation angles |
| `references/nano-banana-pro-guide.md` | Gemini prompting best practices (symlinked from QVISUAL) |

## Error Handling

- **Gemini content policy block**: Script provides a sanitized alternative prompt
- **Not logged in**: Alert user to log in via the Playwright browser window, then retry
- **Generation timeout**: Take screenshot to check, wait longer or refresh
- **Image src not found**: Use `browser_snapshot` to inspect page structure, look for alternative image selectors
- **Playwright browser not started**: Run `browser_navigate` to any URL — Playwright auto-launches

## Output Directory

```
./images/
Naming: YYYY-MM-DD-short-description[-vN].png
```
