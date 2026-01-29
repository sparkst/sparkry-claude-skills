# Starter Pack Plugin Manifest

## Plugin Information
- **Name:** starter-pack
- **Version:** 1.0.0
- **Type:** Agent Bundle
- **Target Audience:** Beginners

## Contents

### Agents (3)
1. **planner.md** - Planning and requirements orchestrator
2. **pe-reviewer.md** - Code review and quality assurance
3. **sde-iii.md** - Implementation and technical analysis

### Documentation
- **README.md** - Installation and quick start guide
- **LICENSE** - MIT License
- **MANIFEST.md** - This file

### Configuration
- **plugin.json** - Plugin metadata and schema

## File Structure
```
starter-pack/
├── .claude-plugin/
│   ├── plugin.json          # Plugin metadata
│   ├── MANIFEST.md          # This file
│   └── agents/
│       ├── planner.md       # Planning orchestrator
│       ├── pe-reviewer.md   # Code reviewer
│       └── sde-iii.md       # Implementation agent
├── README.md                # User documentation
└── LICENSE                  # MIT License
```

## Scrubbing Applied

The following items were removed from the original agents:
- Project-specific file paths
- Internal tool references
- Company-specific workflows
- Sensitive configuration details

All agents are now generic and ready for public distribution.

## Validation Checklist

- [x] All agents have valid frontmatter
- [x] All agents specify required tools
- [x] No sensitive data in agent files
- [x] README.md provides clear installation instructions
- [x] LICENSE file included
- [x] plugin.json follows schema
- [x] No project-specific paths or references

## Quality Metrics

- **Total Files:** 7
- **Agents:** 3
- **Total Lines:** ~600 (across all agents)
- **Documentation Coverage:** 100%

## Usage Pattern

```
User Input → QPLAN (planner) → requirements + plan
Plan → QCODE (sde-iii) → implementation
Implementation → QCHECK (pe-reviewer) → review + fixes
```

## Upgrade Path

Users can upgrade to the full **dev-workflow** plugin for:
- Test-driven development (test-writer)
- Documentation automation (docs-writer)
- Git workflow automation (release-manager)
- Additional specialized agents

## Support

- **Issues:** GitHub repository
- **Questions:** Claude Code forums
- **Email:** skills@sparkry.ai
