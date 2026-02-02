# Trello Integration - Setup & Usage Guide

## Overview

Trello Integration provides Claude Code with the ability to create and manage Trello cards directly from your terminal. When combined with QRALPH, it automatically tracks projects in your Trello board.

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

```
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install Trello Integration

```
/plugin install integrations-trello@sparkry-claude-skills
```

### Step 3: Verify Installation

```
/plugin list
```

------------------------------------------------------------------------

## Setup (Required)

### Step 1: Get Trello API Credentials

1. **Get your API Key:**
   - Go to https://trello.com/app-key
   - Copy your API key

2. **Get your Token:**
   - Replace `YOUR_API_KEY` in this URL and visit it:
   ```
   https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&key=YOUR_API_KEY
   ```
   - Click "Allow" and copy the token

### Step 2: Create Environment File

Create a file called `.env.local` in your project root:

```bash
TRELLO_API_KEY=your_api_key_here
TRELLO_TOKEN=your_token_here
```

**Security Note:** Add `.env.local` to your `.gitignore` to avoid committing secrets.

### Step 3: Find Your Board and List IDs

```bash
# List all your boards
QTRELLO list-boards

# List all lists on a specific board
QTRELLO list-lists --board-id "BOARD_ID_FROM_ABOVE"
```

------------------------------------------------------------------------

## Included Components

### Skills
| Skill | Purpose |
|-------|---------|
| **QTRELLO** | Trello card and board management |

### Python Scripts
| Script | Purpose |
|--------|---------|
| `trello_api.py` | Core Trello API client |
| `trello_integration.py` | QRALPH-Trello bridge |
| `trello_config.py` | Configuration loader |
| `github_repo.py` | GitHub repo detection |

------------------------------------------------------------------------

## Usage

### Basic Commands

#### List Your Boards
```
QTRELLO list-boards
```

#### List Lists on a Board
```
QTRELLO list-lists --board-id "abc123"
```

#### Find a Board by Name
```
QTRELLO find-board --name "My Project Board"
```

#### Create a Card
```
QTRELLO: Create a card on "My Board", "To Do" list:
  Title: "Implement user login"
  Description: "OAuth2 integration with Google"
```

#### Update a Card
```
QTRELLO update-card --card-id "xyz789" --title "New Title"
```

#### Archive a Card
```
QTRELLO archive-card --card-id "xyz789"
```

------------------------------------------------------------------------

## QRALPH Integration

When you have both `orchestration-workflow` and `integrations-trello` installed, QRALPH automatically manages Trello cards.

### Setup for QRALPH Integration

Create `.qralph/trello-config.json` in your project:

```json
{
  "board_id": "your-board-id",
  "list_id": "your-list-id",
  "github_repo": "owner/repo",
  "labels": {
    "Automation": "label-id-1",
    "Bug": "label-id-2"
  },
  "cache_ttl_seconds": 60
}
```

### Automatic Behavior

| Event | Trello Action |
|-------|---------------|
| `QRALPH "new feature"` | Creates card `[Q:XX] 001-new-feature` |
| Run completes | Updates card with summary |
| `QRALPH resume 001` | Checks if card was closed |
| `QRALPH close 001` | Archives the card |
| `QRALPH sync` | Syncs all projects with Trello |

### Card Title Format

Cards are prefixed with `[Q:{initials}]` where initials come from your GitHub repo:
- `sparkst/cardinal-health` → `[Q:CH]`
- `myorg/my-project` → `[Q:MP]`

------------------------------------------------------------------------

## Output Format

All commands return JSON:

**Success:**
```json
{
  "success": true,
  "data": {
    "id": "card123",
    "name": "My Card",
    "url": "https://trello.com/c/abc123"
  }
}
```

**Error:**
```json
{
  "success": false,
  "error": "Board not found: Unknown Board"
}
```

------------------------------------------------------------------------

## Common Workflows

### Create a Card from Claude Code

```
QTRELLO: Create a card on "Sprint Board", "Backlog" list:
  Title: "Add dark mode support"
  Description: "Implement theme toggle with system preference detection"
  Due: "2026-02-15"
```

### Move Card to Different List

```
QTRELLO update-card --card-id "xyz789" --move-to-list "done_list_id"
```

### Search for Cards

```
QTRELLO search-cards --board-id "abc123" --query "[Q:CH]"
```

------------------------------------------------------------------------

## Troubleshooting

### "Missing TRELLO_API_KEY or TRELLO_TOKEN"

Ensure `.env.local` exists in your project root with both variables set.

### "Board not found"

- Board names are case-sensitive
- Use `QTRELLO list-boards` to see exact names
- Try partial matching: `QTRELLO find-board --name "Sprint"`

### "HTTP 401: unauthorized"

- Your token may have expired
- Generate a new token with `expiration=never`
- Verify your API key is correct

### Rate Limits

Trello allows 300 requests per 10 seconds. The API client handles this automatically with exponential backoff.

------------------------------------------------------------------------

## Related Plugins

- **orchestration-workflow** - QRALPH multi-agent swarm (uses Trello automatically)
- **qshortcuts-support** - QGIT for committing changes after Trello updates

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support at [sparkry.ai/docs](https://sparkry.ai/docs)
