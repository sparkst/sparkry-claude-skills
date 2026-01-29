# WCAG 2.1 Quick Reference Checklist

Web Content Accessibility Guidelines (WCAG) 2.1 - Quick reference for UX testing

## Level A (Must Have)

### 1. Perceivable

#### 1.1 Text Alternatives
- [ ] **1.1.1**: Provide text alternatives for non-text content

#### 1.2 Time-based Media
- [ ] **1.2.1**: Provide alternatives for audio-only and video-only content
- [ ] **1.2.2**: Provide captions for videos with audio
- [ ] **1.2.3**: Provide audio description or text alternative for video

#### 1.3 Adaptable
- [ ] **1.3.1**: Info and relationships can be programmatically determined
- [ ] **1.3.2**: Sequence of content is meaningful
- [ ] **1.3.3**: Instructions don't rely solely on shape, size, location, orientation, or sound

#### 1.4 Distinguishable
- [ ] **1.4.1**: Color is not the only way to convey information
- [ ] **1.4.2**: User can pause, stop, or adjust volume of audio

### 2. Operable

#### 2.1 Keyboard Accessible
- [ ] **2.1.1**: All functionality is available via keyboard
- [ ] **2.1.2**: Keyboard focus can be moved away from any component
- [ ] **2.1.4**: Keyboard shortcuts can be disabled or remapped

#### 2.2 Enough Time
- [ ] **2.2.1**: Time limits can be extended or disabled
- [ ] **2.2.2**: Moving, blinking, scrolling content can be paused

#### 2.3 Seizures
- [ ] **2.3.1**: No content flashes more than 3 times per second

#### 2.4 Navigable
- [ ] **2.4.1**: Bypass blocks of repeated content (skip links)
- [ ] **2.4.2**: Pages have descriptive titles
- [ ] **2.4.3**: Focus order is logical
- [ ] **2.4.4**: Link purpose is clear from text or context

#### 2.5 Input Modalities
- [ ] **2.5.1**: Pointer gestures have single-point alternative
- [ ] **2.5.2**: Touch targets can be activated on up-event
- [ ] **2.5.3**: Accessible name matches visible label
- [ ] **2.5.4**: Motion actuation can be disabled

### 3. Understandable

#### 3.1 Readable
- [ ] **3.1.1**: Language of page is specified

#### 3.2 Predictable
- [ ] **3.2.1**: Focus doesn't automatically trigger context change
- [ ] **3.2.2**: Input doesn't automatically trigger context change

#### 3.3 Input Assistance
- [ ] **3.3.1**: Errors are identified in text
- [ ] **3.3.2**: Labels or instructions are provided for inputs

### 4. Robust

#### 4.1 Compatible
- [ ] **4.1.1**: Valid HTML (start/end tags, unique IDs)
- [ ] **4.1.2**: Name, role, value are programmatically determinable

---

## Level AA (Should Have)

### 1. Perceivable

#### 1.2 Time-based Media
- [ ] **1.2.4**: Captions for live audio
- [ ] **1.2.5**: Audio description for video

#### 1.3 Adaptable
- [ ] **1.3.4**: Content orientation is not restricted
- [ ] **1.3.5**: Autocomplete purpose is identified

#### 1.4 Distinguishable
- [ ] **1.4.3**: Text contrast ratio ≥4.5:1 (3:1 for large text)
- [ ] **1.4.4**: Text can be resized to 200% without loss of content
- [ ] **1.4.5**: Images of text are avoided
- [ ] **1.4.10**: Content reflows at 320px width
- [ ] **1.4.11**: UI components and graphical objects have ≥3:1 contrast
- [ ] **1.4.12**: Text spacing can be adjusted
- [ ] **1.4.13**: Hover/focus content is dismissible, hoverable, persistent

### 2. Operable

#### 2.4 Navigable
- [ ] **2.4.5**: Multiple ways to find pages (menu, search, sitemap)
- [ ] **2.4.6**: Headings and labels are descriptive
- [ ] **2.4.7**: Keyboard focus is visible

### 3. Understandable

#### 3.1 Readable
- [ ] **3.1.2**: Language of parts is identified (if different from page)

#### 3.2 Predictable
- [ ] **3.2.3**: Navigation is consistent across pages
- [ ] **3.2.4**: Components are identified consistently

#### 3.3 Input Assistance
- [ ] **3.3.3**: Error suggestions are provided
- [ ] **3.3.4**: Errors are prevented for legal, financial, data submissions

### 4. Robust

#### 4.1 Compatible
- [ ] **4.1.3**: Status messages are programmatically determinable

---

## Level AAA (Nice to Have)

### 1. Perceivable

#### 1.2 Time-based Media
- [ ] **1.2.6**: Sign language for audio
- [ ] **1.2.7**: Extended audio description for video
- [ ] **1.2.8**: Alternative for time-based media
- [ ] **1.2.9**: Audio-only (live) has alternative

#### 1.4 Distinguishable
- [ ] **1.4.6**: Text contrast ratio ≥7:1 (4.5:1 for large text)
- [ ] **1.4.7**: Audio has minimal background noise
- [ ] **1.4.8**: Visual presentation is customizable
- [ ] **1.4.9**: Images of text used only for decoration or logos

### 2. Operable

#### 2.1 Keyboard Accessible
- [ ] **2.1.3**: No keyboard trap

#### 2.2 Enough Time
- [ ] **2.2.3**: Timing is not essential
- [ ] **2.2.4**: Interruptions can be suppressed or postponed
- [ ] **2.2.5**: Re-authentication preserves data
- [ ] **2.2.6**: Timeout warnings are provided

#### 2.3 Seizures
- [ ] **2.3.2**: No content flashes more than 3 times per second (stricter)
- [ ] **2.3.3**: Animations from interactions can be disabled

#### 2.4 Navigable
- [ ] **2.4.8**: Current location is indicated
- [ ] **2.4.9**: Link purpose is clear from text alone
- [ ] **2.4.10**: Section headings organize content

#### 2.5 Input Modalities
- [ ] **2.5.5**: Target size is ≥44x44 CSS pixels
- [ ] **2.5.6**: Concurrent input mechanisms are supported

### 3. Understandable

#### 3.1 Readable
- [ ] **3.1.3**: Unusual words have definitions
- [ ] **3.1.4**: Abbreviations have expansions
- [ ] **3.1.5**: Reading level is lower secondary education or simpler
- [ ] **3.1.6**: Pronunciation is provided for ambiguous words

#### 3.2 Predictable
- [ ] **3.2.5**: Context changes only on user request

#### 3.3 Input Assistance
- [ ] **3.3.5**: Context-sensitive help is available
- [ ] **3.3.6**: Error prevention for all submissions

---

## Common Test Scenarios

### Keyboard Navigation
```
Tab - Move to next focusable element
Shift+Tab - Move to previous focusable element
Enter - Activate button or link
Space - Toggle checkbox, activate button
Arrow keys - Navigate within component (menu, tabs, radio group)
Esc - Close modal or dismiss popover
Home/End - Jump to start/end of list or text
```

### Screen Reader Testing

**NVDA (Windows)**:
- Install: https://www.nvaccess.org/download/
- Start: Ctrl+Alt+N
- Navigate: Arrow keys, Tab
- Read: Insert+Down Arrow (continuous read)

**VoiceOver (Mac)**:
- Start: Cmd+F5
- Navigate: Ctrl+Option+Arrow keys
- Read: Ctrl+Option+A (continuous read)

### Color Contrast Testing

**Tools**:
- Chrome DevTools: Inspect element → Contrast ratio in color picker
- axe DevTools: Browser extension (free)
- WAVE: Browser extension (free)
- Contrast Checker: https://webaim.org/resources/contrastchecker/

**Requirements**:
- Normal text: ≥4.5:1 (AA), ≥7:1 (AAA)
- Large text (18pt+): ≥3:1 (AA), ≥4.5:1 (AAA)
- UI components: ≥3:1 (AA)

---

## Quick Audit Process

1. **Automated Scan**: Run axe DevTools or WAVE
2. **Keyboard Test**: Navigate entire page with keyboard only
3. **Screen Reader Test**: Use NVDA or VoiceOver to navigate
4. **Zoom Test**: Zoom to 200% and verify no content loss
5. **Contrast Test**: Check text and UI component contrast
6. **Focus Test**: Verify visible focus indicators
7. **Form Test**: Submit forms with errors, verify announcements

---

## References

- WCAG 2.1: https://www.w3.org/WAI/WCAG21/quickref/
- WebAIM Checklists: https://webaim.org/standards/wcag/checklist
- A11y Project Checklist: https://www.a11yproject.com/checklist/
