# Sparkry Claude Skills Marketplace

A comprehensive marketplace of enterprise-grade Claude plugins and skills for AI-powered workflows. This collection includes production-ready agents, skills, and tools designed for research, content creation, development, and strategic decision-making.

## Overview

The Sparkry Claude Skills Marketplace provides a curated collection of reusable Claude plugins that extend your AI capabilities. Each plugin includes:

- **Specialized Agents**: Domain experts designed to handle specific tasks
- **Reusable Skills**: Modular components for common operations
- **Python Tools**: Utility scripts for data processing and integrations
- **Complete Documentation**: Implementation guides and API references
- **Production-Ready Code**: Tested and optimized for reliability

## Available Plugins

### 1. Research Workflow Plugin
Comprehensive research orchestration for competitive analysis, market research, and strategic intelligence gathering.

**Includes:**
- Research Director (multi-agent coordinator)
- Fact Checker & Source Evaluator agents
- Web research, industry analysis, and synthesis skills
- Parallel search execution
- Date validation and source policy enforcement

**Use Cases:** Competitive analysis, market research, trend analysis, due diligence

**[View Details →](./plugins/research-workflow/README.md)**

---

### 2. Writing Workflow Plugin
Multi-platform content creation with voice consistency, quality scoring, and automated publishing.

**Includes:**
- Content Director agent
- Quality Scorer & Voice Validator agents
- Multi-platform transformation (LinkedIn, Twitter, Email, Substack)
- Google Docs publishing integration
- Link validation and special content matching

**Use Cases:** Content marketing, thought leadership, blog publishing, social media strategy

**[View Details →](./plugins/writing-workflow/README.md)**

---

### 3. Strategy Workflow Plugin
Strategic decision-making framework for buy-vs-build analysis, product strategy, and executive briefings.

**Includes:**
- Chief of Staff (COS) agent
- PR-FAQ generator
- Buy-vs-Build analyzer
- Executive briefing synthesizer
- Financial ROI calculator

**Use Cases:** Strategic planning, product decisions, executive summaries, go-to-market planning

**[View Details →](./plugins/strategy-workflow/README.md)**

---

### 4. Dev Workflow Plugin
Software development acceleration with code generation, testing, and quality assurance.

**Includes:**
- Development Coordinator agent
- Test Writer & Code Quality Auditor agents
- Schema validators and interface contracts
- TypeScript type safety enforcement
- Automated testing and linting

**Use Cases:** Feature development, test-driven development, code reviews, refactoring

**[View Details →](./plugins/dev-workflow/README.md)**

---

### 5. Starter Pack Plugin
Getting started with Claude plugins - essential agents and tools for first-time users.

**Includes:**
- Onboarding guide
- Basic agent templates
- Simple skill examples
- Integration tutorials

**Use Cases:** Learning Claude plugins, prototyping, proof-of-concepts

**[View Details →](./plugins/starter-pack/README.md)**

---

## Installation

### Prerequisites
- Claude API access (Claude 3 or later)
- Python 3.8+ (for running tools)
- Git

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sparkry/claude-skills-marketplace.git
   cd claude-skills-marketplace
   ```

2. **Choose a plugin:**
   ```bash
   cd plugins/research-workflow  # or any other plugin
   ```

3. **Review the manifest:**
   ```bash
   cat MANIFEST.md
   ```

4. **Import into your Claude setup:**
   - Copy the plugin directory to your `.claude/plugins/` folder
   - Reference agent files in your system prompts
   - Load skills as needed

5. **Configure integrations (if needed):**
   - See individual plugin documentation for API keys
   - Update configuration files with your credentials
   - Run smoke tests to verify setup

### Example: Using Research Workflow

```bash
# Copy to your Claude plugins directory
cp -r plugins/research-workflow ~/.claude/plugins/

# In your Claude conversation:
# "Use the research-workflow plugin to analyze competitors in the SaaS market"
```

## Plugin Structure

Each plugin follows a consistent structure:

```
plugin-name/
├── README.md                 # Plugin overview and usage
├── MANIFEST.md              # Plugin metadata and component listing
├── .claude-plugin/          # Plugin configuration
│   └── plugin.json
├── agents/                  # Agent definitions
│   ├── agent-name.md
│   └── ...
├── skills/                  # Reusable skill components
│   ├── domain/
│   │   ├── skill-name/
│   │   │   ├── SKILL.md
│   │   │   ├── scripts/
│   │   │   └── resources/
│   │   └── ...
├── scripts/                 # Python utility tools
│   ├── tool-name.py
│   └── ...
└── docs/                    # Additional documentation
    ├── INTEGRATION.md
    ├── API.md
    └── ...
```

## Features

✅ **Enterprise-Grade Quality**
- Production-tested implementations
- Comprehensive error handling
- Security and privacy-first design

✅ **Modular & Composable**
- Mix and match agents and skills
- Reuse across multiple workflows
- Minimal dependencies

✅ **Well-Documented**
- Agent behavior specifications
- Skill usage examples
- Integration guides

✅ **Active Maintenance**
- Regular updates and improvements
- Community feedback integration
- Version compatibility tracking

## Documentation

### For Plugin Users
- [Installation Guide](./docs/INSTALLATION.md)
- [Plugin Catalog](./docs/PLUGINS.md)
- [Integration Examples](./docs/EXAMPLES.md)
- [Troubleshooting](./docs/TROUBLESHOOTING.md)

### For Plugin Developers
- [Plugin Development Guide](./docs/PLUGIN-DEVELOPMENT.md)
- [Agent Specification Template](./docs/AGENT-SPEC-TEMPLATE.md)
- [Skill Development Guide](./docs/SKILL-DEVELOPMENT.md)
- [Testing Standards](./docs/TESTING-STANDARDS.md)

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```bash
# Google Docs integration (for writing-workflow)
GOOGLE_DOCS_API_KEY=your_api_key_here

# Web research (for research-workflow)
SERPAPI_KEY=your_serpapi_key

# Email publishing (for writing-workflow)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

See individual plugin docs for complete configuration requirements.

## Usage Examples

### Research Competitive Landscape
```bash
# In Claude with research-workflow loaded
"Analyze the top 5 AI-powered project management tools, comparing features, pricing, and target markets. Use the research-workflow plugin."
```

### Write Multi-Platform Content
```bash
# In Claude with writing-workflow loaded
"Create a LinkedIn post, Twitter thread, and email newsletter about AI productivity tools. Maintain consistent voice across all platforms."
```

### Strategic Analysis
```bash
# In Claude with strategy-workflow loaded
"Should we build an internal tool or use Zapier? Generate a PR-FAQ and financial analysis."
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### Ways to Contribute
- Report bugs and request features via GitHub Issues
- Submit new skills and agents
- Improve documentation
- Share usage examples and case studies
- Integrate new tools and APIs

## Support

- **Documentation**: See `/docs` and individual plugin READMEs
- **Issues**: [GitHub Issues](https://github.com/sparkry/claude-skills-marketplace/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sparkry/claude-skills-marketplace/discussions)
- **Email**: support@sparkry.ai

## License

This project is licensed under the MIT License - see [LICENSE](./LICENSE) file for details.

## Roadmap

### Upcoming Plugins
- [ ] Financial Analysis Workflow
- [ ] Legal Document Review Workflow
- [ ] E-commerce Optimization Workflow
- [ ] Customer Support Automation Workflow
- [ ] Data Analysis & Visualization Workflow

### Planned Enhancements
- [ ] Plugin marketplace web interface
- [ ] One-click installation tool
- [ ] Interactive plugin composition builder
- [ ] Community rating and reviews system
- [ ] Performance benchmarking dashboard

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for version history and updates.

## Citation

If you use Sparkry Claude Skills Marketplace in your research or production system, please cite:

```bibtex
@software{sparkry_claude_plugins,
  author = {Sparkry},
  title = {Claude Skills Marketplace},
  year = {2025},
  url = {https://github.com/sparkry/claude-skills-marketplace}
}
```

## Acknowledgments

Built with support from the Anthropic Claude API and community contributions.

---

**Made with ❤️ by Sparkry**

[Website](https://sparkry.ai) • [Twitter](https://twitter.com/sparkry) • [LinkedIn](https://linkedin.com/company/sparkry)
