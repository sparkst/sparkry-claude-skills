---
name: Trello Integration
description: Create and manage Trello cards with QRALPH project tracking integration
version: 2.0.0
tools: [trello_api.py, trello_integration.py, trello_config.py, github_repo.py, qralph_trello_orchestrator.py]
references: []
claude_tools: Bash
trigger: QTRELLO
---

# Trello Integration Skill

## Role
You are "Trello Manager", a specialist in creating and managing Trello cards, boards, and lists via the Trello API.

## Prerequisites

### Environment Variables Required
```bash
TRELLO_API_KEY=your_api_key
TRELLO_TOKEN=your_oauth_token
```

**Get API Key**: https://trello.com/app-key
**Get Token**: https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&key=YOUR_API_KEY

## Tools Usage

### scripts/trello_api.py

**Create a Card**:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py create-card \
  --list-id "list_id" \
  --title "Card Title" \
  --description "Card description" \
  [--due "2026-01-25"] \
  [--labels "red,blue"]
```

**List Boards**:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py list-boards
```

**List Lists (on a board)**:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py list-lists --board-id "board_id"
```

**Find Board by Name**:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py find-board --name "Board Name"
```

**Find List by Name**:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py find-list --board-id "board_id" --name "List Name"
```

**Update a Card**:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py update-card \
  --card-id "card_id" \
  [--title "New Title"] \
  [--description "New description"] \
  [--due "2026-01-30"] \
  [--move-to-list "list_id"]
```

**Archive a Card**:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py archive-card --card-id "card_id"
```

**Get Card Details** (REQ-008):
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py get-card --card-id "card_id"
# Returns card data including closed status
```

**Unarchive a Card** (REQ-008):
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py unarchive-card --card-id "card_id"
```

**Search Cards** (REQ-008):
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py search-cards --board-id "board_id" --query "[Q:CH]"
```

**Get All Cards in List** (REQ-008):
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py get-all-cards --list-id "list_id" [--include-archived]
```

## QRALPH Integration (REQ-011)

When used with QRALPH, the skill automatically:

1. Creates Trello cards for new projects with `[Q:{initials}]` prefix
2. Updates cards with run summaries after each QRALPH run
3. Detects closed cards when resuming projects
4. Syncs local project state with Trello

### Configuration

Create `.qralph/trello-config.json`:
```json
{
  "board_id": "your-board-id",
  "list_id": "your-list-id",
  "github_repo": "owner/repo",
  "labels": {
    "Automation": "label-id-1",
    "Content": "label-id-2"
  },
  "cache_ttl_seconds": 60
}
```

### QRALPH Commands

```bash
# New project (creates Trello card automatically)
QRALPH "Build user authentication"

# Resume project (checks if card was closed)
QRALPH resume 012

# View all projects with Trello status
QRALPH status

# Sync local projects with Trello
QRALPH sync

# Close project and archive card
QRALPH close 012
```

## Common Workflows

### Add a Card to a Board

1. **Find the board**:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py find-board --name "My Project Board"
# Returns: {"id": "abc123", "name": "My Project Board"}
```

2. **Find the list**:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py find-list --board-id "abc123" --name "To Do"
# Returns: {"id": "def456", "name": "To Do"}
```

3. **Create the card**:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py create-card \
  --list-id "def456" \
  --title "My New Task" \
  --description "Description of the task"
```

### List All Boards and Lists

```bash
# Get all boards
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py list-boards

# For each board, get lists
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py list-lists --board-id "board_id"
```

## Output Format

All commands return JSON for easy parsing:

**Success**:
```json
{
  "success": true,
  "data": {
    "id": "card_id",
    "name": "Card Title",
    "url": "https://trello.com/c/..."
  }
}
```

**Error**:
```json
{
  "success": false,
  "error": "Error message"
}
```

## Example: Create a Card from Claude Code

```bash
QTRELLO: Create a card on "Content Calendar" board, "Ideas" list:
  Title: "Create Substack Creator's Report"
  Description: "Review how creators are engaging with us and how we are engaging with them. Look for actionable insights to improve engagement or cut bait on low-value relationships. Include: comment response rates, content relevance scores, engagement trends, recommendations."
```

**Claude Code executes**:
```bash
# Step 1: Find board
board_id=$(python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py find-board --name "Content Calendar" | jq -r '.data.id')

# Step 2: Find list
list_id=$(python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py find-list --board-id "$board_id" --name "Ideas" | jq -r '.data.id')

# Step 3: Create card
python3 ${CLAUDE_PLUGIN_ROOT}/skills/trello/scripts/trello_api.py create-card \
  --list-id "$list_id" \
  --title "Create Substack Creator's Report" \
  --description "Review how creators are engaging..."
```

## Story Point Estimation

- **Create a card**: 0.05 SP
- **List boards/lists**: 0.05 SP
- **Update a card**: 0.05 SP
- **Full workflow (find + create)**: 0.1 SP

## Troubleshooting

### Authentication Errors
- Verify TRELLO_API_KEY and TRELLO_TOKEN are set
- Check token hasn't expired (use `expiration=never` when generating)

### Board/List Not Found
- Names are case-sensitive
- Use `list-boards` or `list-lists` to see exact names

### Rate Limits
- Trello allows 300 requests per 10 seconds per token
- Add delays for bulk operations
