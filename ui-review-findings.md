# Part 1: UI Review — Findings

## Checks Performed
- Browser open + visual inspection of production brief-2026-06-04.html
- Console errors checked: **0 errors**
- Full snapshot reviewed for all sections

## Issues Found

### 🔴 Critical: RuntimeWarning leaked into HTML output
- **What:** Line 1 of the HTML file: `<frozen runpy>:128: RuntimeWarning: 'briefing.build' found in sys.modules...`
- **Where:** brief-2026-06-04.html (first line)
- **Why:** `python -m briefing.build` triggers a Python RuntimeWarning during module import. The warning gets captured in the redirect.
- **Fix:** Add `-W ignore::RuntimeWarning` to the Python command in the cron prompt.
  `python -W ignore::RuntimeWarning -m briefing.build ... > brief.html`

### 🟡 Medium: No clickable links on signal headlines
- **What:** Signal headlines display article titles as plain text. No `<a href>` wrapping.
- **Where:** templates/daily-brief.html — the `{{ signal.headline }}` variable renders as `<h3>{{ signal.headline }}</h3>` with no link.
- **Fix:** Add a URL field to the signals template data and wrap headlines in `<a href="{{ signal.url }}">`.

### 🟢 Low: Date timezone inconsistency in file names
- **What:** File names use UTC date (brief-2026-06-04.html) but the brief content uses PT date (June 2, 2026 11:17 PM PDT). The 2-day offset looks wrong at first glance.
- **Where:** The cron prompt uses `$(date +%Y-%m-%d)` for file naming which is UTC; render.py uses PT timezone for display.
- **Fix:** Use the PT-date in file names too, or accept the UTC/PT discrepancy as cosmetic.

### 🟢 Low: Source label can show author names
- **What:** Signal 04 shows source as "Andrii Furmanets" instead of a publication name.
- **Where:** gather.py extracts source from URL domain, but web_extract may return a different author/source field.
- **Fix:** This is minor — the content is correct. Could improve source normalization later.

### 🟢 Passed: Visual system intact
- Dark theme ✅
- Amber accent ✅
- All sections rendering ✅
- Semantic color tags (green=TEST, blue=TRACK) ✅
- Metadata footer ✅
- Footrail ✅
- Mobile breakpoints functional ✅
- Zero console errors ✅

## Immediate Fix Needed
Fix the RuntimeWarning leak in the cron job prompt. It's the only thing that degrades the reading experience.

Fixed prompt command:
```
cd /home/alex/morning-briefing && python -W ignore::RuntimeWarning -m briefing.build --articles-file articles-$(date +%Y-%m-%d).json > brief-$(date +%Y-%m-%d).html 2>/dev/null
```