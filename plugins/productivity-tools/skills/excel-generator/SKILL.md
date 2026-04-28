---
name: Excel Generator
description: Generate Excel files (.xlsx) with advanced formatting including conditional formatting, column sizing, freeze panes, filters, and data validation
version: 1.0.0
tools: [excel_generator.py, test_excel_generator.py]
references: [conditional-formatting-patterns.md]
claude_tools: Read, Grep, Glob, Edit, Write, Bash
trigger: QEXCEL
---

# Excel Generator Skill

## Role
You are "Excel Generator", a specialist in creating professionally formatted Excel spreadsheets from structured data. You automate the creation of .xlsx files with conditional formatting, column sizing, freeze panes, filters, and data validation dropdowns.

## Core Expertise

### 1. Data-to-Excel Conversion
Convert structured data (list of dicts, JSON, markdown tables) into professional Excel workbooks.

**When to load**: `references/conditional-formatting-patterns.md`
- Common conditional formatting patterns
- Color code standards for status tracking

### 2. Conditional Formatting
Apply cell colors based on cell values for visual status tracking.

**Standard Status Colors**:
| Status | Color | Hex |
|--------|-------|-----|
| Blocked | Red | FF0000 |
| Open Issues | Yellow | FFFF00 |
| On Track | Green | 00FF00 |
| Not Started | Grey | 808080 |
| Complete | Blue | 0000FF |
| Canceled | Purple | 800080 |

### 3. Professional Formatting
- Auto-sized or custom column widths
- Frozen header rows for scrolling
- Auto-filters for data exploration
- Dropdown data validation for controlled input

## Tools Usage

### tools/excel_generator.py
**Purpose**: Generate Excel files with full formatting support

**Basic Usage**:
```bash
python3 tools/excel_generator.py \
  --data '[{"Name": "Alice", "Status": "Complete"}, {"Name": "Bob", "Status": "Blocked"}]' \
  --output project_status.xlsx

# Output (JSON):
{
  "status": "success",
  "path": "project_status.xlsx",
  "rows": 2,
  "columns": 2
}
```

**With Conditional Formatting**:
```bash
python3 tools/excel_generator.py \
  --data '[{"Task": "Task 1", "Status": "Blocked"}, {"Task": "Task 2", "Status": "On Track"}]' \
  --output status_report.xlsx \
  --color-rules '{"Status": {"Blocked": "FF0000", "On Track": "00FF00"}}' \
  --freeze-panes A2 \
  --auto-filter \
  --auto-width

# Output (JSON):
{
  "status": "success",
  "path": "status_report.xlsx",
  "rows": 2,
  "columns": 2,
  "conditional_formatting_applied": true
}
```

**Python API (Fluent Builder)**:
```python
from excel_generator import ExcelGenerator

data = [
    {"Project": "Alpha", "Status": "On Track", "Owner": "Alice"},
    {"Project": "Beta", "Status": "Blocked", "Owner": "Bob"},
    {"Project": "Gamma", "Status": "Complete", "Owner": "Charlie"},
]

result = (
    ExcelGenerator(data)
    .with_color_rules({
        "Status": {
            "Blocked": "FF0000",
            "On Track": "00FF00",
            "Complete": "0000FF",
        }
    })
    .with_freeze_panes()
    .with_auto_filter()
    .with_auto_width()
    .save("project_dashboard.xlsx")
)

print(result)  # {"status": "success", "path": "project_dashboard.xlsx", ...}
```

**Python API (Function)**:
```python
from excel_generator import generate_excel

data = [
    {"Task": "Design review", "Status": "Complete", "Priority": "High"},
    {"Task": "Implementation", "Status": "On Track", "Priority": "High"},
    {"Task": "Testing", "Status": "Not Started", "Priority": "Medium"},
]

color_rules = {
    "Status": {
        "Blocked": "FF0000",
        "Open Issues": "FFFF00",
        "On Track": "00FF00",
        "Not Started": "808080",
        "Complete": "0000FF",
        "Canceled": "800080",
    },
    "Priority": {
        "High": "FF6B6B",
        "Medium": "FFE66D",
        "Low": "4ECDC4",
    }
}

result = generate_excel(
    data=data,
    output_path="task_tracker.xlsx",
    color_rules=color_rules,
    freeze_panes=True,
    auto_filter=True,
    auto_width=True,
)
```

**Multiple Sheets**:
```python
from excel_generator import generate_excel

sheets_data = {
    "Summary": [
        {"Project": "Alpha", "Status": "Active", "Budget": 100000},
        {"Project": "Beta", "Status": "Complete", "Budget": 50000},
    ],
    "Tasks": [
        {"Task": "Task 1", "Assignee": "Alice", "Status": "Done"},
        {"Task": "Task 2", "Assignee": "Bob", "Status": "In Progress"},
    ],
    "Risks": [
        {"Risk": "Delay", "Impact": "High", "Mitigation": "Add resources"},
    ],
}

sheet_config = {
    "Summary": {
        "color_rules": {"Status": {"Active": "00FF00", "Complete": "0000FF"}},
        "auto_filter": True,
    },
    "Tasks": {
        "color_rules": {"Status": {"Done": "00FF00", "In Progress": "FFFF00"}},
        "freeze_panes": True,
    },
}

result = generate_excel(
    sheets=sheets_data,
    output_path="project_workbook.xlsx",
    sheet_config=sheet_config,
)
```

**Data Validation (Dropdowns)**:
```python
from excel_generator import generate_excel

data = [
    {"Task": "Review", "Status": "Open"},
    {"Task": "Approve", "Status": "Open"},
]

validation_rules = {
    "Status": ["Open", "In Progress", "Blocked", "Complete", "Canceled"]
}

result = generate_excel(
    data=data,
    output_path="editable_tracker.xlsx",
    validation_rules=validation_rules,
    freeze_panes=True,
)
```

### tools/test_excel_generator.py
**Purpose**: TDD test suite (17 tests covering all features)

```bash
# Run all tests
python3 -m pytest tools/test_excel_generator.py -v

# Run specific test class
python3 -m pytest tools/test_excel_generator.py::TestConditionalFormatting -v
```

## Workflow

### Standard Usage (QEXCEL)

```
QEXCEL: Generate an Excel status report for these projects:
- Alpha: On Track, owner Alice
- Beta: Blocked, owner Bob
- Gamma: Complete, owner Charlie
```

**Output**: Excel file with conditional formatting, frozen headers, and filters.

### Integration with Coaching Skill

Use QEXCEL to generate tracking spreadsheets for coaching engagements:

```python
# After extracting action items with QCOACH
from excel_generator import generate_excel

action_items = [
    {"Action": "Schedule AI training", "Owner": "Veda", "Status": "On Track", "Due": "2026-01-20"},
    {"Action": "Review vendor proposals", "Owner": "Chad", "Status": "Open Issues", "Due": "2026-01-15"},
    {"Action": "Draft change mgmt plan", "Owner": "Adeola", "Status": "Not Started", "Due": "2026-01-25"},
]

generate_excel(
    data=action_items,
    output_path="cardinal-health-action-tracker.xlsx",
    color_rules={
        "Status": {
            "Blocked": "FF0000",
            "Open Issues": "FFFF00",
            "On Track": "00FF00",
            "Not Started": "808080",
            "Complete": "0000FF",
        }
    },
    freeze_panes=True,
    auto_filter=True,
    auto_width=True,
)
```

## Parameters Reference

### generate_excel()

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| data | List[Dict] | None | Single sheet data (list of row dicts) |
| sheets | Dict[str, List[Dict]] | None | Multi-sheet data {name: rows} |
| output_path | str | "output.xlsx" | Output file path |
| color_rules | Dict | None | Conditional formatting {col: {val: "RRGGBB"}} |
| freeze_panes | bool/str | False | True="A2", or cell ref like "B3" |
| auto_filter | bool | False | Enable column filters |
| auto_width | bool | False | Auto-size columns to content |
| column_widths | Dict[str, int] | None | Custom widths {col: width} |
| validation_rules | Dict[str, List] | None | Dropdowns {col: [options]} |
| sheet_config | Dict | None | Per-sheet config for multi-sheet |

### ExcelGenerator (Builder)

```python
ExcelGenerator(data)
    .with_color_rules({...})      # Conditional formatting
    .with_freeze_panes("A2")      # Freeze at cell
    .with_auto_filter()           # Enable filters
    .with_auto_width()            # Auto column widths
    .with_column_widths({...})    # Custom widths
    .with_validation({...})       # Dropdown validation
    .save("output.xlsx")          # Generate file
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "Data is empty" | Empty list passed | Provide at least one row |
| "Invalid JSON" | Malformed JSON input | Check JSON syntax |
| File permission | Can't write to path | Check directory permissions |

## Story Point Estimation

| Task | SP |
|------|-----|
| Simple Excel from JSON (no formatting) | 0.1 |
| Excel with conditional formatting | 0.2 |
| Multi-sheet workbook | 0.3 |
| Full formatting (colors, filters, validation) | 0.3 |
| Custom column widths + styling | 0.2 |

**Reference**: `docs/project/PLANNING-POKER.md`

## References (Load on-demand)

### references/conditional-formatting-patterns.md
Common patterns for status tracking colors. Load when:
- Setting up new status tracking spreadsheets
- Customizing color schemes for different domains

## Dependencies

```bash
pip install openpyxl
```

## Usage Examples

### Example 1: Project Status Dashboard

```bash
QEXCEL: Create a project status dashboard with these columns:
- Project Name
- Status (On Track, At Risk, Blocked, Complete)
- Owner
- Due Date
- Notes

Apply conditional formatting to Status column.
```

### Example 2: Weekly Coaching Tracker

```python
from excel_generator import generate_excel

coaching_data = [
    {"Client": "Cardinal Health", "Session": "2026-01-12", "Focus": "AI Strategy", "Status": "Complete"},
    {"Client": "Cardinal Health", "Session": "2026-01-15", "Focus": "Team Alignment", "Status": "Scheduled"},
    {"Client": "Fascinate", "Session": "2026-01-13", "Focus": "Claude Setup", "Status": "Complete"},
]

generate_excel(
    data=coaching_data,
    output_path="coaching-tracker-2026-w02.xlsx",
    color_rules={
        "Status": {
            "Complete": "00FF00",
            "Scheduled": "FFFF00",
            "Canceled": "808080",
        }
    },
    freeze_panes=True,
    auto_filter=True,
    column_widths={"Client": 20, "Focus": 30, "Notes": 50},
)
```

### Example 3: Risk Register

```python
sheets_data = {
    "Risks": [
        {"ID": "R001", "Risk": "Vendor delay", "Impact": "High", "Status": "Open"},
        {"ID": "R002", "Risk": "Budget overrun", "Impact": "Medium", "Status": "Mitigated"},
    ],
    "Mitigations": [
        {"Risk ID": "R001", "Action": "Identify backup vendor", "Owner": "PM"},
        {"Risk ID": "R002", "Action": "Weekly budget reviews", "Owner": "Finance"},
    ],
}

generate_excel(
    sheets=sheets_data,
    output_path="risk-register.xlsx",
    sheet_config={
        "Risks": {
            "color_rules": {
                "Impact": {"High": "FF0000", "Medium": "FFFF00", "Low": "00FF00"},
                "Status": {"Open": "FF6B6B", "Mitigated": "00FF00", "Closed": "808080"},
            },
            "freeze_panes": True,
            "auto_filter": True,
        },
    },
)
```

## Parallel Work Coordination

When part of QEXCEL task:

1. **Focus**: Generate professionally formatted Excel files
2. **Tools**: excel_generator.py
3. **Output**: .xlsx file path
4. **Format**:
   ```markdown
   ## Excel Generator Results

   ### File Generated
   - **Path**: /path/to/output.xlsx
   - **Rows**: 25
   - **Columns**: 6
   - **Sheets**: 1

   ### Formatting Applied
   - Conditional formatting: Status column (6 color rules)
   - Freeze panes: A2 (header row frozen)
   - Auto-filter: Enabled on all columns
   - Column widths: Auto-sized

   ### Next Steps
   - Open in Excel to verify formatting
   - Share with stakeholders
   ```

---

*Skill created: 2026-01-14*
*Dependencies: openpyxl>=3.1.0*
