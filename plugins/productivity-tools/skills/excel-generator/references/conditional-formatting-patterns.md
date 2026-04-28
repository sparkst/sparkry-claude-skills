# Conditional Formatting Patterns

> **Purpose**: Common color patterns for status tracking in Excel
> **Load when**: Setting up new status tracking spreadsheets or customizing color schemes

## Standard Status Colors

### Project Status (6-State)

Use this pattern for general project/task tracking:

```python
color_rules = {
    "Status": {
        "Blocked": "FF0000",      # Red - Cannot proceed
        "Open Issues": "FFFF00",  # Yellow - Has issues but working
        "On Track": "00FF00",     # Green - Proceeding as planned
        "Not Started": "808080",  # Grey - Not yet begun
        "Complete": "0000FF",     # Blue - Finished
        "Canceled": "800080",     # Purple - No longer needed
    }
}
```

### Simple Status (3-State)

For simpler tracking:

```python
color_rules = {
    "Status": {
        "Red": "FF0000",
        "Yellow": "FFFF00",
        "Green": "00FF00",
    }
}
```

### Binary Status

For yes/no tracking:

```python
color_rules = {
    "Complete": {
        "Yes": "00FF00",
        "No": "FFCCCC",
    }
}
```

## Priority Colors

### High/Medium/Low

```python
color_rules = {
    "Priority": {
        "Critical": "FF0000",
        "High": "FF6B6B",
        "Medium": "FFE66D",
        "Low": "4ECDC4",
    }
}
```

### P0-P3 System

```python
color_rules = {
    "Priority": {
        "P0": "FF0000",   # Critical
        "P1": "FF6B6B",   # High
        "P2": "FFE66D",   # Medium
        "P3": "4ECDC4",   # Low
    }
}
```

## Risk Colors

### Impact/Likelihood Matrix

```python
color_rules = {
    "Impact": {
        "Critical": "8B0000",   # Dark red
        "High": "FF0000",       # Red
        "Medium": "FFFF00",     # Yellow
        "Low": "00FF00",        # Green
        "Negligible": "808080", # Grey
    },
    "Likelihood": {
        "Almost Certain": "FF0000",
        "Likely": "FF6B6B",
        "Possible": "FFFF00",
        "Unlikely": "90EE90",
        "Rare": "00FF00",
    }
}
```

## Health Check Colors

### Service Health

```python
color_rules = {
    "Health": {
        "Healthy": "00FF00",
        "Degraded": "FFFF00",
        "Unhealthy": "FF0000",
        "Unknown": "808080",
    }
}
```

### Compliance Status

```python
color_rules = {
    "Compliance": {
        "Compliant": "00FF00",
        "Partial": "FFFF00",
        "Non-Compliant": "FF0000",
        "Not Assessed": "808080",
    }
}
```

## Domain-Specific Patterns

### Software Development

```python
color_rules = {
    "Status": {
        "Backlog": "E0E0E0",
        "Ready": "90CAF9",
        "In Progress": "FFF59D",
        "In Review": "CE93D8",
        "Done": "A5D6A7",
        "Blocked": "EF9A9A",
    }
}
```

### Change Management

```python
color_rules = {
    "Change Status": {
        "Planned": "E0E0E0",
        "Approved": "90CAF9",
        "In Progress": "FFF59D",
        "Implemented": "A5D6A7",
        "Rolled Back": "EF9A9A",
        "Deferred": "808080",
    }
}
```

### Pharmaceutical/Healthcare

```python
color_rules = {
    "Validation Status": {
        "Validated": "00FF00",
        "Pending Validation": "FFFF00",
        "Failed Validation": "FF0000",
        "Not Required": "808080",
    },
    "FDA Status": {
        "Approved": "00FF00",
        "Under Review": "FFFF00",
        "Rejected": "FF0000",
        "Draft": "E0E0E0",
    }
}
```

## Color Accessibility Notes

### High Contrast Alternatives

For colorblind-friendly reports, add patterns or icons alongside colors:

```python
# Use distinct hues that work for most color vision types
color_rules = {
    "Status": {
        "Complete": "0066CC",    # Blue
        "In Progress": "FF9900", # Orange
        "Blocked": "CC0000",     # Dark Red
        "Not Started": "666666", # Grey
    }
}
```

### Best Practices

1. **Avoid red/green only**: Always include a third color option
2. **Use saturation**: Light colors for "good", dark for "bad"
3. **Add text labels**: Don't rely solely on color
4. **Test printing**: Colors should be distinguishable in B&W

## Hex Color Reference

| Color | Hex | Use Case |
|-------|-----|----------|
| Red | FF0000 | Blocked, Critical, Error |
| Orange | FF6B6B | High priority, Warning |
| Yellow | FFFF00 | Medium, Caution, In Progress |
| Green | 00FF00 | On Track, Complete, Success |
| Blue | 0000FF | Complete, Info, Scheduled |
| Purple | 800080 | Canceled, Special status |
| Grey | 808080 | Not Started, N/A, Unknown |
| Light Red | FFCCCC | Soft alert |
| Light Green | 90EE90 | Soft success |
| Light Blue | 90CAF9 | Ready, Queued |

## Multiple Column Example

Apply different rules to different columns:

```python
color_rules = {
    "Status": {
        "Blocked": "FF0000",
        "On Track": "00FF00",
        "Complete": "0000FF",
    },
    "Priority": {
        "High": "FF6B6B",
        "Medium": "FFE66D",
        "Low": "4ECDC4",
    },
    "Risk Level": {
        "High": "FF0000",
        "Medium": "FFFF00",
        "Low": "00FF00",
    }
}

# All three columns will be colored based on their respective rules
```
