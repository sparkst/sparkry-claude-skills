# Integrations - Trello

Trello integration for Claude Code with QRALPH project tracking.

## Installation

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
/plugin install integrations-trello@sparkry-claude-skills
```

## Prerequisites

### 1. Get Trello API Credentials

1. **API Key:** https://trello.com/app-key
2. **Token:** After getting your API key, visit:
   ```
   https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&key=YOUR_API_KEY
   ```

### 2. Create Environment File

Create `.env.local` in your project root:

```bash
TRELLO_API_KEY=your_api_key_here
TRELLO_TOKEN=your_oauth_token_here
```

### 3. Find Your Board and List IDs

```bash
# List all your boards
python3 scripts/trello_api.py list-boards

# List all lists on a board
python3 scripts/trello_api.py list-lists --board-id YOUR_BOARD_ID
```

### 4. Create Config (for QRALPH integration)

Create `.qralph/trello-config.json`:

```json
{
  "board_id": "your-board-id",
  "list_id": "your-list-id",
  "github_repo": "owner/repo",
  "labels": {},
  "cache_ttl_seconds": 60
}
```

## What's Included

**Skills:** QTRELLO

**Scripts:**
- `trello_api.py` - Core Trello API client
- `trello_integration.py` - QRALPH-Trello bridge
- `trello_config.py` - Configuration loader
- `github_repo.py` - GitHub repo detection

## Quick Reference

| Command | Purpose |
|---------|---------|
| `list-boards` | List all your Trello boards |
| `list-lists` | List all lists on a board |
| `create-card` | Create a new card |
| `update-card` | Update an existing card |
| `archive-card` | Archive a card |
| `get-card` | Get card details |
| `search-cards` | Search for cards |

## Usage

### Standalone (QTRELLO)

```bash
QTRELLO: Create a card on "My Board", "To Do" list:
  Title: "Build authentication"
  Description: "Implement OAuth2 login flow"
```

### With QRALPH

When configured, QRALPH automatically:
- Creates cards for new projects with `[Q:{initials}]` prefix
- Updates cards with run summaries
- Detects closed cards when resuming

```bash
QRALPH "Add user authentication"  # Auto-creates Trello card
QRALPH resume 012                  # Checks if card was closed
QRALPH close 012                   # Archives the card
```

## Documentation

**[Full User Guide →](../../docs/INTEGRATIONS-TRELLO-GUIDE.md)**

## License

MIT
