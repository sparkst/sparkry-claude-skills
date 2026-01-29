# SDE-III Position Memo: QShortcuts Content Plugin

**Recommendation:** Build (MVP already scaffolded)

**Effort Estimation:**
- Story Points: 34-55 SP (full implementation)
- Calendar Time: 4-7 weeks (1-2 engineers)
- Confidence: Medium-High

## Implementation Breakdown

### Phase 1: QWRITE (MVP) - 13 SP
1. **Quality Scorer** (quality-scorer.py): 3 SP
   - Implement 5-metric scoring system
   - Priority-based issue detection (P0/P1/P2)
   - Complexity: Moderate (NLP analysis, scoring algorithms)

2. **Voice Validator** (voice-validator.py): 3 SP
   - Persona pattern matching
   - Phrase flagging (corporate speak, hedging)
   - Complexity: Moderate (pattern matching, vocabulary analysis)

3. **Link Validator** (link-validator.py): 2 SP
   - HTTP status checking (BLOCKING gate)
   - URL extraction from markdown
   - Complexity: Simple (HTTP requests, regex)

4. **Special Links Matcher** (special-links-matcher.py): 2 SP
   - Context-aware link suggestion
   - Confidence scoring
   - Complexity: Moderate (NLP context matching)

5. **Platform Constraints** (platform-constraints.py): 2 SP
   - Platform requirement validation
   - Length/format checking
   - Complexity: Simple (rule-based validation)

6. **Template Selector** (template-selector.py): 1 SP
   - Template mapping
   - Structure loading
   - Complexity: Simple (file I/O, JSON parsing)

### Phase 2: QPPT (HTML-First) - 8 SP
1. **Slide Optimizer** (slide-optimizer.py): 2 SP
   - Markdown parsing
   - Text limit enforcement (30 words, 5 lines)
   - Icon suggestion
   - Complexity: Moderate (parsing, keyword matching)

2. **Slide HTML Generator** (slide-html-generator.py): 3 SP
   - HTML template generation
   - Brand styling application
   - Contrast calculation integration
   - Complexity: Moderate (templating, CSS)

3. **Screenshot Generator** (screenshot-generator.py): 2 SP
   - Playwright integration
   - PNG capture (1080×1080)
   - Complexity: Simple (Playwright API wrapper)

4. **Color Contrast Validator** (color-contrast-validator.py): 1 SP
   - WCAG contrast calculation
   - Text color recommendation
   - Complexity: Simple (math algorithm)

### Phase 3: QVISUAL - 5 SP
1. **Generate Hero Image** (generate-hero-image.py): 1 SP
   - Article metadata extraction
   - HTML template injection
   - Complexity: Simple (markdown parsing, templating)

2. **Convert ASCII to Visual** (convert-ascii-to-visual.py): 2 SP
   - ASCII structure parsing
   - HTML/CSS mapping
   - Complexity: Moderate (parsing, layout)

3. **Detect Visual Opportunities** (detect-visual-opportunities.py): 1 SP
   - Pattern detection (ASCII, frameworks)
   - Opportunity categorization
   - Complexity: Simple (regex, pattern matching)

4. **Render HTML to Image** (render-html-to-image.py): 1 SP
   - Playwright wrapper
   - Screenshot capture
   - Complexity: Simple (shared with QPPT)

### Phase 4: QINFOGRAPHIC - 13 SP
1. **Framework Extractor** (framework-extractor.py): 3 SP
   - Article parsing
   - Framework detection (3-10 elements)
   - Supporting quote extraction
   - Complexity: Hard (NLP, structure detection)

2. **Framework Validator** (framework-validator.py): 2 SP
   - Hallucination detection (BLOCKING)
   - Confidence scoring
   - Complexity: Moderate (validation logic)

3. **Pattern Selector** (pattern-selector.py): 2 SP
   - Framework-to-pattern mapping
   - Panel structure generation
   - Complexity: Moderate (mapping logic)

4. **Creativity Orchestrator** (creativity-orchestrator.py): 3 SP
   - Visual metaphor selection
   - Diversity tracking integration
   - Novelty score calculation
   - Complexity: Hard (creative logic, history tracking)

5. **Copy Compressor** (copy-compressor.py): 2 SP
   - Length limit enforcement (BLOCKING)
   - Microcopy generation
   - Complexity: Moderate (compression, validation)

6. **HTML Generator** (html-generator.py): 3 SP
   - Sophisticated HTML/CSS generation
   - Rich visual elements (gradients, shadows, SVG)
   - Accessibility compliance
   - Complexity: Hard (creative core, complex layouts)

7. **Content QA** (content-qa.py): 2 SP
   - Hallucination detection (BLOCKING)
   - Accessibility validation
   - Complexity: Moderate (validation, WCAG checks)

8. **Diversity Tracker** (diversity-tracker.py): 1 SP
   - Creative profile logging
   - Diversity score calculation
   - Complexity: Simple (file I/O, scoring)

### Phase 5: PowerPoint Fallback (Optional) - 8 SP
1. **PPT Generator** (ppt-generator.py): 3 SP
   - python-pptx integration
   - Slide layout application
   - Complexity: Moderate (PowerPoint API)

2. **Icon Fetcher** (icon-fetcher.py): 2 SP
   - Iconify API integration
   - Caching strategy
   - SVG to PNG conversion
   - Complexity: Moderate (API, caching, conversion)

3. **Brand Validator** (brand-validator.py): 2 SP
   - Color palette validation
   - Font compliance checking
   - Logo zone protection
   - Complexity: Simple (rule-based validation)

4. **Integration Testing**: 1 SP

## Dependencies

### External Libraries
- **Playwright** (~200MB): Browser automation for screenshots
  - Risk: Large dependency, requires Chromium
  - Mitigation: Document installation, provide fallbacks

- **python-pptx**: PowerPoint generation (fallback)
  - Risk: Font availability on different platforms
  - Mitigation: Graceful fallback to system fonts

- **Requests**: HTTP for link validation, icon fetching
  - Risk: Network dependency
  - Mitigation: Timeout handling, caching

- **Pillow**: Image processing
  - Risk: None (standard library)

### Internal Services
- **Portfolio RAG** (future): Voice pattern retrieval
  - Current: Load from persona docs directly
  - Risk: Delayed Phase 2 feature
  - Mitigation: Works without RAG (persona docs sufficient)

- **Special Links Configuration**: Link suggestion data
  - Risk: Needs webhook endpoint or local file
  - Mitigation: Support both sources, cached fallback

## Technical Risks

### Risk 1: Playwright Installation Complexity
**Description**: ~200MB Chromium download, platform-specific install
**Impact**: High (blocking for QPPT, QVISUAL)
**Mitigation**:
- Clear documentation in README
- Installation script with error handling
- Fallback to PowerPoint (QPPT) or skip visuals (QVISUAL)

### Risk 2: Hallucination Detection Accuracy
**Description**: False positives in framework validation/content QA
**Impact**: Medium (blocking gates may halt valid content)
**Mitigation**:
- Confidence thresholds (0.7+ for validation pass)
- Manual override option for P1 severity
- Iterative improvement of detection algorithms

### Risk 3: Token Budget Overruns
**Description**: Workflows exceeding 25K token budget
**Impact**: Low (cost concern, not functional)
**Mitigation**:
- Per-agent token allocation
- Overflow strategy (reduce quotes, comments)
- Token usage logging

### Risk 4: Platform-Specific Font Issues
**Description**: Poppins/Inter not available on all systems (PowerPoint fallback)
**Impact**: Low (degraded quality, not broken)
**Mitigation**:
- Web fonts for HTML-first approach (no install needed)
- Graceful fallback to Arial/Helvetica
- Warning in brand validation

### Risk 5: Link Validation False Negatives
**Description**: Valid links flagged as broken due to temporary issues
**Impact**: Medium (BLOCKING gate)
**Mitigation**:
- Retry logic (3 attempts with backoff)
- Timeout configuration (10s default)
- Manual override option

## Build vs Buy

### Build Arguments
1. **Tight Integration**: Needs access to internal voice patterns, brand guidelines, workflow
2. **Customization**: Specific quality metrics, platform constraints, creative diversity logic
3. **No Off-the-Shelf Alternative**: No product combines all 4 workflows (QWRITE, QPPT, QVISUAL, QINFOGRAPHIC)
4. **IP Value**: Quality scoring, persona layering, hallucination prevention are differentiators

### Buy Alternatives (Partial)
- **Grammarly/Hemingway**: Readability scoring (covers 1 of 5 metrics)
- **Canva**: Visual generation (lacks automation, brand enforcement)
- **Copy.ai**: Content generation (lacks quality gates, platform transforms)
- **Beautiful.ai**: Presentation design (lacks content optimization, icon integration)

**Verdict**: Build - No single tool covers all requirements, integration overhead would exceed build cost

## Performance Targets

### Latency
- **QWRITE**: <5 min end-to-end (20K tokens)
- **QPPT**: <45 sec first carousel (no cache), <15 sec subsequent
- **QVISUAL**: <10 sec per article (hero + 2-3 diagrams)
- **QINFOGRAPHIC**: <3 min end-to-end (25K tokens)

### Quality
- **QWRITE**: ≥85/100 quality score, ≥70% voice attribution
- **QPPT**: WCAG AA compliance (4.5:1 contrast), <500KB per slide
- **QVISUAL**: <500KB per image, 2x DPI (retina)
- **QINFOGRAPHIC**: 0% hallucination rate (hard requirement), >0.6 novelty score

### Success Rate
- **QWRITE**: ≥80% complete without human intervention
- **QPPT**: ≥90% successful generation
- **QVISUAL**: ≥95% hero image generation
- **QINFOGRAPHIC**: ≥90% completion for well-structured articles

## Deployment Considerations

### Environment Requirements
- Python 3.8+
- 250MB disk (Playwright Chromium)
- Internet connection (Google Fonts, Iconify CDN)
- 50MB disk (icon cache)

### Configuration
- Brand guidelines (JSON)
- Persona patterns (markdown)
- Platform constraints (JSON)
- Special links (webhook or file)

### Monitoring
- Token usage per workflow
- Quality score distribution
- Success/failure rates
- Generation latency

## Phased Rollout Recommendation

### Week 1-2: QWRITE MVP (13 SP)
- Focus: Quality scoring, link validation (BLOCKING)
- Skip: Special links, platform constraints (nice-to-have)
- Target: 1 engineer

### Week 3-4: QPPT HTML-First (8 SP)
- Focus: HTML generation, screenshots
- Skip: PowerPoint fallback
- Target: 1 engineer

### Week 5: QVISUAL (5 SP)
- Focus: Hero images, ASCII detection
- Skip: Complex ASCII parsing
- Target: 1 engineer

### Week 6-7: QINFOGRAPHIC (13 SP)
- Focus: Framework extraction, rendering
- Risk: Most complex, hallucination detection critical
- Target: 2 engineers

## Confidence: Medium-High

**Why Medium-High, not High:**
1. Hallucination detection is novel (no proven algorithm)
2. Playwright dependency introduces platform-specific risks
3. Token budgeting requires tuning across workflows

**Why not Medium:**
1. Tool stubs already created (reduces unknowns)
2. Reference files provide clear specification
3. Existing writing-workflow plugin provides patterns
4. HTML-first approach proven in carousel generation

## Recommendation

**Build in 4 phases** with MVP focus:
1. QWRITE with quality scoring + link validation (2 weeks)
2. QPPT HTML-first only (2 weeks)
3. QVISUAL hero + basic ASCII (1 week)
4. QINFOGRAPHIC with strict validation gates (2 weeks)

**Total MVP**: 7 weeks, 39 SP

**Skip for v1.0**:
- PowerPoint fallback (use HTML-first only)
- Special links integration (manual for now)
- Advanced ASCII parsing (simple patterns only)
- Portfolio RAG (use persona docs)

**Success Criteria**:
- QWRITE: 1 article published ≥85/100 quality
- QPPT: 1 carousel uploaded to LinkedIn
- QVISUAL: 1 hero image generated
- QINFOGRAPHIC: 1 framework infographic with 0 hallucinations

---

**Prepared by**: SDE-III Agent
**Date**: 2026-01-28
**Status**: Ready for Implementation
