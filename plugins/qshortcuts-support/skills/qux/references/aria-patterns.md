# ARIA Patterns Reference

Common ARIA patterns for accessible UI components

## Overview

ARIA (Accessible Rich Internet Applications) provides semantic meaning to custom UI components for assistive technologies.

**Golden Rule**: Use native HTML elements when possible. Only use ARIA when no native alternative exists.

---

## Common Roles

### Landmarks

```html
<header role="banner">
<nav role="navigation" aria-label="Main navigation">
<main role="main">
<aside role="complementary">
<footer role="contentinfo">
```

### Widgets

```html
<div role="button" tabindex="0">
<div role="checkbox" aria-checked="false">
<div role="radio" aria-checked="false">
<div role="tab" aria-selected="false">
<div role="dialog" aria-modal="true">
<div role="alertdialog">
<div role="menu">
<div role="menuitem">
```

### Live Regions

```html
<div role="alert">
<div role="status" aria-live="polite">
<div role="log" aria-live="polite">
<div aria-live="assertive">
```

---

## Pattern: Button

**When to use**: Custom button (not `<button>`)

```html
<div role="button" tabindex="0"
     onclick="handleClick()"
     onkeydown="handleKeyDown(event)">
  Click me
</div>
```

**Keyboard**:
- Enter or Space activates

**JavaScript**:
```javascript
function handleKeyDown(event) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    handleClick();
  }
}
```

**Best Practice**: Use `<button>` instead.

---

## Pattern: Checkbox

**When to use**: Custom checkbox (not `<input type="checkbox">`)

```html
<div role="checkbox"
     aria-checked="false"
     tabindex="0"
     onclick="toggleCheck()"
     onkeydown="handleKeyDown(event)">
  <span class="checkbox-icon"></span>
  Accept terms
</div>
```

**Keyboard**:
- Space toggles

**JavaScript**:
```javascript
function toggleCheck() {
  const checkbox = event.currentTarget;
  const checked = checkbox.getAttribute('aria-checked') === 'true';
  checkbox.setAttribute('aria-checked', !checked);
}

function handleKeyDown(event) {
  if (event.key === ' ') {
    event.preventDefault();
    toggleCheck();
  }
}
```

**Best Practice**: Use `<input type="checkbox">` instead.

---

## Pattern: Modal Dialog

**When to use**: Overlay that requires user interaction

```html
<div role="dialog"
     aria-modal="true"
     aria-labelledby="dialog-title"
     aria-describedby="dialog-desc">

  <h2 id="dialog-title">Confirm Action</h2>
  <p id="dialog-desc">Are you sure you want to delete this item?</p>

  <button onclick="confirm()">Confirm</button>
  <button onclick="cancel()">Cancel</button>
</div>
```

**Requirements**:
- Trap focus inside modal
- Return focus to trigger element on close
- Escape key closes modal
- `aria-modal="true"` hides background from screen readers

**JavaScript**:
```javascript
const focusableElements = dialog.querySelectorAll(
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
);
const firstElement = focusableElements[0];
const lastElement = focusableElements[focusableElements.length - 1];

// Trap focus
dialog.addEventListener('keydown', (e) => {
  if (e.key === 'Tab') {
    if (e.shiftKey && document.activeElement === firstElement) {
      e.preventDefault();
      lastElement.focus();
    } else if (!e.shiftKey && document.activeElement === lastElement) {
      e.preventDefault();
      firstElement.focus();
    }
  } else if (e.key === 'Escape') {
    closeModal();
  }
});

// Focus first element on open
firstElement.focus();
```

---

## Pattern: Tabs

**When to use**: Tab-based navigation

```html
<div class="tabs">
  <div role="tablist" aria-label="Sample tabs">
    <button role="tab" aria-selected="true" aria-controls="panel1" id="tab1">
      Tab 1
    </button>
    <button role="tab" aria-selected="false" aria-controls="panel2" id="tab2">
      Tab 2
    </button>
  </div>

  <div role="tabpanel" id="panel1" aria-labelledby="tab1">
    Panel 1 content
  </div>
  <div role="tabpanel" id="panel2" aria-labelledby="tab2" hidden>
    Panel 2 content
  </div>
</div>
```

**Keyboard**:
- Arrow keys navigate between tabs
- Tab moves focus into tab panel
- Space or Enter activates tab

**JavaScript**:
```javascript
function handleTabKeyDown(event) {
  const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));
  const currentIndex = tabs.indexOf(event.target);

  if (event.key === 'ArrowRight') {
    const nextIndex = (currentIndex + 1) % tabs.length;
    tabs[nextIndex].focus();
  } else if (event.key === 'ArrowLeft') {
    const prevIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    tabs[prevIndex].focus();
  } else if (event.key === 'Home') {
    tabs[0].focus();
  } else if (event.key === 'End') {
    tabs[tabs.length - 1].focus();
  }
}
```

---

## Pattern: Dropdown Menu

**When to use**: Menu triggered by button

```html
<div>
  <button aria-haspopup="true"
          aria-expanded="false"
          aria-controls="menu1"
          id="menubutton">
    Options
  </button>

  <ul role="menu" id="menu1" aria-labelledby="menubutton" hidden>
    <li role="menuitem">Edit</li>
    <li role="menuitem">Delete</li>
    <li role="separator"></li>
    <li role="menuitem">Settings</li>
  </ul>
</div>
```

**Keyboard**:
- Enter or Space opens menu
- Arrow keys navigate menu items
- Escape closes menu
- First letter jumps to item starting with that letter

**JavaScript**:
```javascript
function toggleMenu() {
  const button = document.getElementById('menubutton');
  const menu = document.getElementById('menu1');
  const isExpanded = button.getAttribute('aria-expanded') === 'true';

  button.setAttribute('aria-expanded', !isExpanded);
  menu.hidden = isExpanded;

  if (!isExpanded) {
    menu.querySelector('[role="menuitem"]').focus();
  }
}
```

---

## Pattern: Form Validation

**When to use**: Inline form error messages

```html
<div>
  <label for="email">Email</label>
  <input type="email"
         id="email"
         aria-describedby="email-error"
         aria-invalid="true">
  <div id="email-error" role="alert" class="error">
    Please enter a valid email address
  </div>
</div>
```

**Live Region for Dynamic Errors**:
```html
<div aria-live="assertive" aria-atomic="true" class="sr-only">
  <!-- Announce errors here -->
</div>
```

**JavaScript**:
```javascript
function showError(input, message) {
  input.setAttribute('aria-invalid', 'true');
  const errorEl = document.getElementById(`${input.id}-error`);
  errorEl.textContent = message;

  // Announce to screen reader
  const announcement = document.querySelector('[aria-live]');
  announcement.textContent = message;
}
```

---

## Pattern: Loading State

**When to use**: Async content loading

```html
<div aria-live="polite" aria-busy="true">
  Loading...
</div>
```

**When loaded**:
```html
<div aria-live="polite" aria-busy="false">
  Content loaded successfully
</div>
```

**For spinners**:
```html
<div role="status" aria-live="polite">
  <span class="spinner"></span>
  <span class="sr-only">Loading...</span>
</div>
```

---

## Pattern: Accordion

**When to use**: Collapsible sections

```html
<div class="accordion">
  <h3>
    <button aria-expanded="false" aria-controls="section1" id="accordion1">
      Section 1
    </button>
  </h3>
  <div id="section1" role="region" aria-labelledby="accordion1" hidden>
    Section 1 content
  </div>

  <h3>
    <button aria-expanded="false" aria-controls="section2" id="accordion2">
      Section 2
    </button>
  </h3>
  <div id="section2" role="region" aria-labelledby="accordion2" hidden>
    Section 2 content
  </div>
</div>
```

**Keyboard**:
- Enter or Space toggles section
- Tab moves to next button

---

## Pattern: Combobox (Autocomplete)

**When to use**: Input with suggestions

```html
<div>
  <label for="search">Search</label>
  <input type="text"
         id="search"
         role="combobox"
         aria-autocomplete="list"
         aria-expanded="false"
         aria-controls="suggestions">

  <ul id="suggestions" role="listbox" hidden>
    <li role="option">Suggestion 1</li>
    <li role="option">Suggestion 2</li>
  </ul>
</div>
```

**Keyboard**:
- Arrow down opens suggestions
- Arrow up/down navigates suggestions
- Enter selects suggestion
- Escape closes suggestions

---

## Pattern: Toast Notification

**When to use**: Brief, auto-dismissing message

```html
<div role="status" aria-live="polite" aria-atomic="true" class="toast">
  Item added to cart
</div>
```

**For errors** (use `aria-live="assertive"`):
```html
<div role="alert" aria-live="assertive" aria-atomic="true" class="toast error">
  Payment failed
</div>
```

---

## ARIA Properties Reference

### States

- `aria-checked`: "true" | "false" | "mixed"
- `aria-disabled`: "true" | "false"
- `aria-expanded`: "true" | "false"
- `aria-hidden`: "true" | "false"
- `aria-invalid`: "true" | "false"
- `aria-pressed`: "true" | "false" | "mixed"
- `aria-selected`: "true" | "false"

### Properties

- `aria-label`: String label for element
- `aria-labelledby`: ID of labeling element
- `aria-describedby`: ID of describing element
- `aria-controls`: ID of controlled element
- `aria-haspopup`: "true" | "menu" | "dialog" | etc.
- `aria-live`: "off" | "polite" | "assertive"
- `aria-atomic`: "true" | "false"
- `aria-modal`: "true" | "false"

---

## Best Practices

1. **Use native HTML first**: `<button>` over `<div role="button">`
2. **Provide labels**: Use `aria-label` or `aria-labelledby`
3. **Manage focus**: Ensure logical focus order
4. **Keyboard support**: All interactions must be keyboard accessible
5. **Live regions**: Announce dynamic content changes
6. **Visible focus**: Always show focus indicators
7. **Test with screen readers**: NVDA (Windows), VoiceOver (Mac)

---

## References

- ARIA Authoring Practices: https://www.w3.org/WAI/ARIA/apg/
- MDN ARIA: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA
- Inclusive Components: https://inclusive-components.design/
