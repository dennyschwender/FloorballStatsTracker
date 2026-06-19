# UI/UX Review Fixes Implementation Plan

> **For agentic workers:** Subagent-driven development recommended.

**Goal:** Fix 13 UI/UX issues identified across all pages of the Floorball Stats Tracker.

**Architecture:** Primarily template+CSS changes to `templates/` and `app/static/css/`. Minor JS additions. No backend logic changes.

**Tech Stack:** Flask (Jinja2), Bootstrap 5, vanilla JS, CSS.

---

### Task 1: Fix collapsed stat sections leaking table headers

**Files:**
- Modify: `templates/stats.html`

When a stat heading is collapsed its table headers (`⇅` sort arrows) are still visible. The `collapse` section needs to hide the entire table, not just the body.

- [ ] **Step 1: Fix the collapse structure in stats.html**

Each stat section looks like:
```html
<h3 data-bs-toggle="collapse" ...>Game Score</h3>
<div class="collapse show" id="...">
  <table>...</table>
</div>
```

The issue is likely that the table within the collapsed div still renders sort arrows outside the collapse boundary. Add `overflow: hidden` to the collapse container, or ensure the `.collapse` class properly hides the table wrapper.

The simplest fix: wrap the table in a container that hides on collapse. Ensure `.collapse:not(.show)` applies `display: none` (Bootstrap default). If the arrows are rendered **outside** the collapse div, move them inside.

- [ ] **Step 2: Run tests**
```
pytest tests/test_stats.py -q
```

- [ ] **Step 3: Commit**
```
git add templates/stats.html
git commit -m "fix: hide stat table headers when section collapsed"
```

---

### Task 2: Remove or fix permanently disabled "Statistics" button

**Files:**
- Modify: `templates/stats.html`

The "Statistics" button on the stats page is always `disabled`. Either remove it or wire it to something useful.

- [ ] **Step 1: Remove the disabled button**

Find and remove the disabled "Statistics" button from `templates/stats.html`. It sits next to "Expand All" / "Collapse All" but serves no function.

- [ ] **Step 2: Commit**
```
git add templates/stats.html
git commit -m "fix: remove unused disabled Statistics button"
```

---

### Task 3: Style danger links differently (Edit JSON, Reset Stats)

**Files:**
- Modify: `templates/game_detail_view.html` or equivalent template

"Edit JSON" and "Reset Stats" are destructive actions but styled as plain links. Change them to `btn btn-outline-danger` or add confirmation dialogs.

- [ ] **Step 1: Find the link group in the game detail template**

Search for `Edit JSON` and `Reset Stats` links. Change their styling to `btn btn-outline-danger btn-sm` and add `onclick="return confirm(...)"` for Reset Stats.

```html
<a href="/game/{{ game.id }}/edit_json" class="btn btn-outline-danger btn-sm">Edit JSON</a>
<a href="#" class="btn btn-outline-danger btn-sm"
   onclick="return confirm('Reset all stats for this game? This cannot be undone.');">Reset Stats</a>
```

- [ ] **Step 2: Commit**
```
git add templates/game_detail_view.html
git commit -m "fix: style destructive links as danger buttons"
```

---

### Task 4: Improve "Switch game" dropdown usability

**Files:**
- Modify: `templates/base.html` or navbar template

20-item dropdown is too long. Options:
- Add `data-bs-auto-close="outside"` and a search input above the dropdown
- Limit to last 5 + "View all games" link

This needs user input on approach. **Ask user.**

---

### Task 5: Mobile stat table — sticky first column + scroll hint

**Files:**
- Modify: `templates/game_detail_view.html` (or inline CSS in the game detail template)

The 12-column stat table needs:
1. Sticky first column (player name + number)
2. A visual scroll hint on the right edge (fade gradient)

```css
#statsTable td:first-child,
#statsTable th:first-child {
  position: sticky;
  left: 0;
  z-index: 2;
  background: var(--bs-table-bg, white);
}
#statsTable-wrapper::after {
  content: '';
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 30px;
  background: linear-gradient(to right, transparent, rgba(0,0,0,0.1));
  pointer-events: none;
}
```

Also add `style="min-width: 900px"` on the table to force horizontal scroll.

- [ ] **Step 1: Apply sticky column and scroll hint CSS**
- [ ] **Step 2: Test on mobile viewport (resize browser)**
- [ ] **Step 3: Commit**
```
git add templates/game_detail_view.html
git commit -m "fix: sticky player column + scroll hint on stat table"
```

---

### Task 6: Add aria-labels to emoji action buttons

**Files:**
- Modify: `templates/game_edit_mode.html` or equivalent

Emoji buttons (⚽, 👍, 🎯) need `aria-label` attributes for screen readers.

```html
<a href="..." aria-label="Add goal">⚽</a>
<a href="..." aria-label="Add assist">👍</a>
<a href="..." aria-label="Add shot on goal">🎯</a>
```

- [ ] **Step 1: Add aria-labels to all action emoji links**
- [ ] **Step 2: Commit**
```
git add templates/game_edit_mode.html
git commit -m "fix: add aria-labels to emoji action buttons"
```

---

### Task 7: Add active nav state

**Files:**
- Modify: `templates/base.html`

Add `aria-current="page"` to the current nav link. The page context can be passed as a Jinja2 variable.

In the route, pass `active_nav='statistics'` etc. to each render call, or use `request.path` comparison.

Simplest approach: compare `request.path` in the template.

```html
<a href="/stats"
   {% if request.path.startswith('/stats') %}aria-current="page" class="active"{% endif %}>
  Statistics
</a>
```

- [ ] **Step 1: Update base.html nav links with active detection**
- [ ] **Step 2: Commit**
```
git add templates/base.html
git commit -m "fix: add active nav state with aria-current"
```

---

### Task 8: Add keyboard shortcuts for edit mode

**Files:**
- Modify: `templates/game_edit_mode.html`

Add JS keyboard listener: `g` = goal, `a` = assist, `s` = SOG for currently focused/selected player row.

This needs a selected-player concept (click row to select, then keyboard applies to that player). **Ask user about scope.**

---

### Task 9: Add tooltip to "⋮" overflow menu

**Files:**
- Modify: `templates/game_edit_mode.html`

Add `title="More actions"` to the kebab button.

```html
<button class="btn btn-sm" title="More actions">⋮</button>
```

- [ ] **Step 1: Add title attribute**
- [ ] **Step 2: Commit**
```
git add templates/game_edit_mode.html
git commit -m "fix: add tooltip to overflow menu button"
```

---

### Task 10: Add brand identity to login page

**Files:**
- Modify: `templates/login.html` or `templates/base.html`

Add a small logo or badge above the PIN input. **Ask user for logo/graphic.**

---

### Task 11: Add pagination to game list

**Files:**
- Modify: `routes/game_routes.py`, `templates/index.html`

Add server-side pagination with page size of ~20. **Ask user.**

---

### Task 12: Add time field to game creation

**Files:**
- Modify: `templates/game_form.html`, `routes/game_routes.py`, `models/game_model.py`

Add a time input next to the date field. **Ask user.**

---

### Task 13: Make create game form mobile-friendly

**Files:**
- Modify: `templates/game_form.html`

Change `col-sm-6` to `col-12` for season/category fields on mobile.

- [ ] **Step 1: Fix column classes**
- [ ] **Step 2: Commit**
```
git add templates/game_form.html
git commit -m "fix: stack season/category fields vertically on mobile"
```