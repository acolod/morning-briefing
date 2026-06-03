# Morning AI Brief — 3-Part Audit Plan

## Part 1: UI / Visual Fidelity
Check the generated HTML artifact against the v5 mockup design reference.

### Checks
- [ ] **Font loading** — Inter + JetBrains Mono load from Google Fonts
- [ ] **Dark theme** — `#060606` background, amber `#f4a84d` accent
- [ ] **Grid texture** — body::before overlay visible
- [ ] **Top rail** — status dot, path, version, mode, signals count, delivery, assets
- [ ] **Hero section** — mono uppercase headline, lede paragraph, 3 microcards (top/adaptive/delivery)
- [ ] **Side stack** — visual note card, metadata idea, signal shape + sparkline
- [ ] **Signal band** — amber glow border, theme line, "high signal / low drag"
- [ ] **Image treatment section** — rule + placement modules with article image mock slot
- [ ] **Top signals** — 3-5 signals with tags (Test green, Track blue, Ignore red, Learn amber)
- [ ] **Build journey** — bullet list from ranked categories
- [ ] **Rising topic** — adaptive zone card with weighting + effect sidebar
- [ ] **Radar + moves** — two-column: Hermes/agent radar, one move today
- [ ] **Triple footer** — delivery path, visual rules, issue metadata (4-col grid)
- [ ] **Footrail** — version, traits, tags
- [ ] **Mobile responsive** — check `<940px` and `<620px` breakpoints collapse correctly
- [ ] **Console** — zero JS errors, no broken image references
- [ ] **Image handling** — if article images are embedded, are they sized/cropped correctly?

### Tools
- Browser open + visual inspection
- Browser console for errors
- Responsive mode for breakpoints

---

## Part 2: Functional Review — Does It Meet The Goal?

### Goal: Deliver a personalized daily AI/dev briefing that surfaces signal, filters noise, and adapts over time.

### Checks

#### Content Quality
- [ ] **Deduplication** — The `search_index` dict in `gather.py` keys by URL, so same-URL duplicates are handled. But what about same story from different sources? `rank.py` scores each article independently; two articles about the same event could both rank highly. Need a **title-similarity dedup** (e.g., fuzzy match on normalized title) before ranking.
- [ ] **Source diversity** — Does the ranking favor one source too heavily? Should check scoring doesn't cluster.
- [ ] **Link embedding** — Signal headlines in the template (`_signal_tag`, `headline`) are currently plain text. Users can't click through to read more. Each signal should embed the article URL as a clickable link on the headline.
- [ ] **Content source freshness** — `web_extract` pulls full article text. But what if a page is behind a paywall? The `description` from search results may be the only usable content. `gather.py` should handle this gracefully (falls back to description if content_text is empty).
- [ ] **Date accuracy** — `_parse_datetime` in `rank.py` handles ISO 8601. But what if web_extract returns no date? Falls back to `1.0 days old`. Might want to surface the search result date instead.

#### Ranking & Adaptation
- [ ] **Scoring sanity** — Check real article scores make intuitive sense (hermetic_agents articles rank higher than general_ai ones).
- [ ] **Momentum decay** — `0.85x` daily decay means a topic at 1.0 drops to 0.61 after 3 days. Is that the right speed? Check if momentum oscillates sanely.
- [ ] **Category assignment** — `_score_article` assigns one best category per article. If an article matches multiple categories, it only gets the top one. That's fine for v1, but an article about "CLI tools for AI agent development" should arguably contribute to both `dev_tooling` and `hermetic_agents`.

#### Edge Cases
- [ ] **Empty search results** — `gather()` returns `[]`. `rank()` gets an empty list. `render()` should handle gracefully (shows fallback copy).
- [ ] **web_extract fails** — `extract_fn` returns empty dict. `gather.py` should still include the article from search results (title + description).
- [ ] **Momentum file missing/deleted** — `load_momentum()` returns `{}`. Does the build handle this?
- [ ] **JSON articles file malformed** — `_load_articles` will throw. Should wrap in try/except.
- [ ] **Template rendering error** — Jinja2 will throw on missing variables. Each template variable should have a default/fallback.

#### Delivery
- [ ] **Telegram attachment** — Does the HTML file open correctly when delivered via MEDIA:? (We verified this works in mockup phase.)
- [ ] **File naming** — `brief-YYYY-MM-DD.html` is clear. Should older briefs be cleaned up?
- [ ] **Delivery failure** — Does Hermes retry on failed delivery?

### Tools
- Run demo + articles-file modes with real data
- Inspect article counts, scores, categories
- Manually examine a few extracted URLs
- Test edge cases (empty file, bad JSON, no network)

---

## Part 3: Pipeline Robustness & Error Handling

### Checks

#### Failure Modes
- [ ] **Cron agent skips a step** — The current prompt lists 5 steps (gather → save → build → decay → deliver). If the agent gets confused or stops early, we get no briefing. Solution: add step-by-step verification checkpoints in the prompt.
- [ ] **No network access** — What if the cron job runs but web_search/extract are down? Should fall back to demo mode.
- [ ] **Partial failure** — 4 of 6 searches succeed, 2 fail. The brief should still use what it has.
- [ ] **File write permissions** — Articles JSON and output HTML go to `~/morning-briefing/`. If the cron user can't write there, the build silently fails.
- [ ] **Python import resolution** — The `briefing` package uses relative imports. If cwd is wrong, imports break. The cron command uses `cd ~/morning-briefing && python -m briefing.build...` which sets cwd correctly.

#### Monitoring & Observability
- [ ] **No alert on failure** — If the cron job fails (step skipped, build error, delivery error), how do we know? The `last_status` field shows "ok" here, but errors should be visible.
- [ ] **No archive** — Each day overwrites/creates `brief-YYYY-MM-DD.html`. There's no archive index. Should we create an `archive.html` that lists all past briefs?
- [ ] **Momentum drift** — Without conversation-based boosts, momentum only decays. Over a week of no manual intervention, all values approach zero. The brief defaults to general_ai content. Is that desirable?

#### Performance & Cost
- [ ] **Redundant searches** — The 6 search queries overlap. "hermetic agents memory" and "developer tooling cli automation" might both return agent-related articles. The dedup handles URL-level duplicates but wastes search quota.
- [ ] **Redundant extractions** — `web_extract` is called on every search result that has a URL, even if it's the same URL from a different query. The `search_index` dict is built first, then `extract_fn` is called once with all unique URLs. This is actually correct — good.
- [ ] **Cost per run** — Estimate: 6 searches + 6-12 extractions + 1 build script call + 1 delivery. With gpt-5.4, roughly ~$0.10-0.30 per run depending on response length and extraction content size.

#### Improvements to Implement
- [ ] Add **title similarity dedup** before ranking (Levenshtein or TF-IDF cosine similarity)
- [ ] Embed **article URLs as links** on signal headlines in the template
- [ ] Add **fallback demo** mode when network is unavailable
- [ ] Add **archive index** page
- [ ] Add **conversation-based momentum boost** using session_search

---

## Execution Plan
1. Run Part 1 (UI) — open a production brief in browser, visually inspect
2. Run Part 2 (Functional) — run with real article data, check scores, examine edge cases
3. Run Part 3 (Robustness) — review code paths, test failure modes
4. Report issues found and fix them
5. Re-verify fixes