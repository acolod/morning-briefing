# Editorial Renderer Implementation Plan

## Files to create

- `tests/test_renderer.py`: new primary test suite for the editorial JSON renderer, CLI demo mode, malformed JSON fallback, output writing, retired phrase removal, tag rendering, links, metadata, radar, and one-move sections.

## Files to modify

- `briefing/build.py`: replace the gathered/ranked production pipeline with editorial JSON loading. Add `--editorial-json FILE`, keep `--demo`, keep atomic `--output FILE`, expose `_DEMO_EDITORIAL`, and keep optional article-list compatibility by converting articles to editorial-shaped demo content only for tests/backward callers.
- `briefing/render.py`: make `render()` accept editorial dictionaries directly, normalize/fill missing editorial fields, validate action tags, sanitize article URLs, and pass only editorial-rendering context to Jinja.
- `templates/daily-brief.html`: strip all retired/static sections and render only top rail metadata, top story, signals, radar, one move, issue metadata footer, and footrail. Preserve the dark near-black/amber visual system, Google Fonts, grid texture overlay, toprail/footrail, and mobile breakpoints.
- `briefing/config.py`: simplify config to render settings only: timezone, title, issue prefix, footer note, version/source-window style values as needed by the renderer.
- `config.yaml`: remove `search_queries`, `categories`, and `ranking`; keep only `render` settings.
- `briefing/__init__.py`: simplify exports so importing the package no longer depends on ranking/gathering as the main pipeline.
- `tests/test_smoke.py` and `tests/test_pipeline.py`: either remove old ranking/pipeline expectations or reduce them to compatibility checks that do not conflict with the editorial architecture.

## Files to delete or simplify

- `briefing/rank.py`: leave untouched as an optional utility unless old tests force removal; it will no longer be imported by `build.py`.
- `briefing/gather.py`: leave untouched as an optional utility unless old tests force removal; it will no longer be imported by `build.py`.
- `momentum.json`: do not modify or commit; no longer part of the renderer path.

## Test plan

- Write `tests/test_renderer.py` first with the requested 12 tests.
- Run the renderer tests before implementation to verify the old architecture fails the new contract.
- Implement the minimal editorial renderer path.
- Update or remove legacy test assertions that require old sections such as story treatment, read-next delivery, ranking category annotations, or gathered article pipeline behavior.
- Run `python -m pytest tests/ -v` until the full suite passes.

## Verification steps

1. `python -m pytest tests/ -v`
2. `python -m briefing.build --demo`
3. `python -m briefing.build --demo` and confirm output does not contain `RuntimeWarning`
4. `python -m briefing.build --demo | grep -c 'href="#'`
5. Create `test-editorial.json`, then run `python -m briefing.build --editorial-json test-editorial.json`
6. Verify the generated HTML structure starts with `<!DOCTYPE html>`, contains the required sections, and has no retired static phrases or placeholder article links.
7. Check `git status --short`, stage only scoped source/test/config/plan changes, and commit with a message summarizing the architectural shift.
