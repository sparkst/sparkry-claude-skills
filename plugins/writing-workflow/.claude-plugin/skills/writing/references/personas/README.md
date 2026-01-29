# Persona Reference Files

These persona files define voice patterns for different content types. Customize these files to match your own writing voice and style.

## Available Personas

### educational.md
Educational voice patterns for teaching and explaining complex topics.

**Characteristics**:
- Empathy-first communication
- Technical terms with accessible context
- BLUF (Bottom Line Up Front) structure
- Progressive complexity building

**Use for**: Tutorials, explainers, educational content

### strategic.md
Strategic business voice for leadership and decision-making content.

**Characteristics**:
- Systems thinking, second-order effects
- Proof-of-work stories (scale, metrics, impact)
- Physical analogies for abstract concepts
- Stress testing assumptions + upside closing

**Use for**: Strategic plans, business insights, thought leadership

### tutorial.md
Technical tutorial voice for hands-on instructional content.

**Characteristics**:
- Direct, builder mentality
- Step-by-step precision
- Real builds only (no fabrication)
- Narrated screenshots and code examples

**Use for**: How-to guides, technical tutorials, documentation

## Customization

To customize these personas for your voice:

1. **Study your existing content**: Analyze 5-10 of your best pieces
2. **Extract patterns**:
   - Sentence structure (length, complexity)
   - Vocabulary (technical vs accessible, formal vs casual)
   - Transitions (how you connect ideas)
   - Examples (types of analogies, stories you use)
3. **Document patterns**: Update persona files with your specific patterns
4. **Test**: Generate content and validate it matches your voice
5. **Iterate**: Refine patterns based on what works

## Voice Validation

Use `tools/voice-validator.py` to check consistency:

```bash
python tools/voice-validator.py content.md --persona educational
```
