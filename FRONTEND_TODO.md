# Frontend Improvement Plan

A prioritized roadmap for improving the Finance Tracker frontend.

---

## Critical: Mobile & Responsive

The app currently has **no mobile breakpoints** — the 250px fixed sidebar and grid layouts will break on smaller screens.

### Responsive CSS Overhaul
- [ ] Add media queries to `static/css/style.css`
  - `@media (max-width: 768px)` — tablets
  - `@media (max-width: 480px)` — mobile
- [ ] Sidebar: Convert to hamburger menu/drawer on mobile
  - Currently: `width: 250px` fixed (line 37)
  - `.content { margin-left: 250px }` (line 83) needs removal on mobile
- [ ] Chart grid: Stack vertically on mobile
  - Currently: `grid-template-columns: 1fr 2fr` (line 162)
- [ ] Summary cards: Single column on small screens
  - Currently: `minmax(240px, 1fr)` (line 111)
- [ ] Filter form: Stack fields vertically on mobile
  - Currently: `minmax(200px, 1fr)` (line 336)
- [ ] Upload area: Reduce padding on mobile
  - Currently: `padding: 3rem` (line 309)

---

## Critical: JavaScript Organization

Large JS blocks are embedded inline in templates — should be extracted to modules.

### Extract Plaid JS
- [ ] Create `static/js/plaid.js`
- [ ] Move from `templates/plaid/connections.html` (lines 102-273):
  - `initiatePlaidLink()`
  - `syncItem()`, `syncAll()`
  - `disconnectItem()`, `reconnectItem()`
- [ ] Remove global scope pollution (`plaidHandler` variable)
- [ ] Initialize via data attributes instead of inline script

### Extract Upload JS
- [ ] Create `static/js/upload.js`
- [ ] Move from `templates/imports/upload.html` (lines 79-137):
  - Drag-drop handlers
  - `showFileName()`, `resetUpload()`
- [ ] Scope functions properly (not global)

### Charts.js Improvements
- [ ] Add error handling for malformed data
- [ ] Make legend position responsive (currently hardcoded 'right')
- [ ] Add empty state / loading skeleton

---

## High Priority: Clean Up Inline Styles

Inline styles scattered throughout templates should move to CSS classes.

### Dashboard (`dashboard.html`)
- [ ] Line 11: `margin-bottom: 2rem` → utility class
- [ ] Line 17: `display: flex; gap: 1rem; flex-wrap: wrap` → `.flex-wrap`
- [ ] Line 19: Bank card styling → `.bank-status-card` class
- [ ] Line 40: Gradient CTA card → `.cta-card` class

### Transactions (`transactions/list.html`)
- [ ] Lines 81, 83: Badge colors hardcoded → use CSS variables

### Plaid Connections (`plaid/connections.html`)
- [ ] Lines 275-285: Move inline `<style>` block to main CSS

### New Utility Classes to Add
```css
.flex { display: flex; }
.flex-wrap { flex-wrap: wrap; }
.gap-4 { gap: 1rem; }
.mb-4 { margin-bottom: 2rem; }
.p-4 { padding: 1rem; }
.text-center { text-align: center; }
```

---

## High Priority: User Feedback

Replace `alert()` calls with proper toast notifications.

### Toast System
- [ ] Create `static/js/toast.js` with API: `showToast(message, type)`
- [ ] Add toast container to `base.html`
- [ ] Add toast CSS styles

### Replace Alerts
- [ ] `connections.html` line 192: Sync success alert
- [ ] `connections.html` line 225: Bulk sync alert
- [ ] `connections.html` line 258: Disconnect alert
- [ ] `upload.html` line 131: Replace page reload with success toast

---

## High Priority: Accessibility

### Base Template (`base.html`)
- [ ] Add skip-to-main-content link
- [ ] Add `role="navigation"` to sidebar
- [ ] Line 16: Add aria-label for emoji logo (`<span aria-label="Finance">💰</span>`)

### Forms
- [ ] `upload.html` line 24: Fix hidden file input accessibility
- [ ] Add `aria-label` to icon-only buttons

### Focus States
- [ ] Add visible focus indicators for all interactive elements
- [ ] Currently only form inputs have focus styles (lines 249-253)

---

## Medium Priority: Loading States

### Button Feedback
- [ ] Add spinner/loading class for buttons during async operations
- [ ] Update button text during loading ("Sync" → "Syncing...")
- [ ] CSS: `.btn:disabled { opacity: 0.6; cursor: not-allowed; }`

### Chart Loading
- [ ] Add skeleton placeholder while charts initialize
- [ ] Show fallback message if chart fails to load

---

## Medium Priority: Form Validation

### Upload Form
- [ ] Add client-side file size validation
- [ ] Add file type validation with user feedback
- [ ] Show validation errors inline

### Category Rules Form
- [ ] Pattern field: Show regex syntax feedback
- [ ] Priority field: Number range validation
- [ ] Prevent duplicate pattern submission

### CSS Error States
```css
.form-group.error input { border-color: var(--danger-color); }
.form-error { color: var(--danger-color); font-size: 0.875rem; }
```

---

## Medium Priority: Table Improvements

### Transactions Table (`transactions/list.html`)
- [ ] Add sticky table headers
- [ ] Add horizontal scroll wrapper for mobile
- [ ] Implement pagination controls (currently shows "first 100 results")
- [ ] Add sort indicators to column headers

### Mobile Alternative
- [ ] Consider card-based layout for transactions on mobile instead of table

---

## Lower Priority: Dark Mode

### CSS Variables
- [ ] Add dark mode color variables to `:root`
- [ ] Support `@media (prefers-color-scheme: dark)`

### Toggle
- [ ] Add dark mode toggle button in sidebar
- [ ] Store preference in localStorage
- [ ] Apply `.dark` class to body

---

## Lower Priority: Component Extraction

Create reusable Jinja2 macros in `templates/components/`:

- [ ] `badge.html` — status badges, category badges
- [ ] `card.html` — basic card wrapper
- [ ] `summary-card.html` — dashboard stat cards
- [ ] `button.html` — button variants (primary, danger, loading state)

---

## Lower Priority: Print Styles

- [ ] Add `@media print` rules to CSS
- [ ] Hide sidebar in print
- [ ] Optimize tables for printing
- [ ] Add page breaks for long content

---

## File Structure After Improvements

```
static/
├── css/
│   └── style.css          # Expanded with responsive, utilities, dark mode
└── js/
    ├── charts.js          # Refactored with error handling
    ├── plaid.js           # NEW - extracted from template
    ├── upload.js          # NEW - extracted from template
    └── toast.js           # NEW - notification system

templates/
├── base.html              # Updated with a11y, toast container
├── components/            # NEW
│   ├── badge.html
│   ├── card.html
│   └── button.html
└── ...                    # Cleaned inline styles
```

---

## Quick Wins

If you want to knock out a few fast improvements:

1. **Add mobile meta viewport** — already present, good
2. **Add utility classes** — 10 min, reduces inline styles
3. **Extract the `<style>` block** from `connections.html` — 5 min
4. **Add basic media query** for sidebar hide on mobile — 15 min
5. **Replace one `alert()` with `console.log`** as interim — 2 min

---

## Notes

- **CSS Framework**: Currently vanilla CSS — could consider Tailwind for utility-first approach, but adds build complexity
- **HTMX**: Already used for some dynamic updates — could expand usage
- **Chart.js**: Working well, just needs responsive legend and error handling
