# Editorial Renderer Implementation Plan

## Files to create

- None. The project already has the expected package, template, config, and test files.

## Files to modify

- `briefing/build.py`: keep the editorial JSON entry point as the primary CLI path, preserve `--demo`, preserve atomic `--output`, and keep article-list compatibility as a thin fallback.
- `briefing/render.py`: keep editorial normalization, but harden URL handling so rendered anchors never receive `#` or an empty href. Preserve tag validation for exactly `adopt`, `try`, `track`, and `note`.
- `templates/daily-brief.html`: keep only editorial sections, add the missing issue metadata footer with date, published time, and issue number, keep footrail, and restore both `<940px` and `<620px` responsive breakpoints.
- `briefing/config.py`: keep only render settings plus small compatibility helpers for older callers.
- `config.yaml`: keep render settings only.
- `briefing/rank.py`: simplify into a compatibility utility that no longer depends on removed `ranking` and `categories` config fields.
- `tests/test_renderer.py`: ensure the requested renderer, tag, link, retired-phrase, metadata, malformed JSON, CLI demo, and output-file tests cover the new contract.
- `tests/test_smoke.py` and `tests/test_pipeline.py`: keep only smoke and compatibility assertions aligned with the editorial renderer.

## Files to delete or simplify

- `briefing/gather.py`: keep as an optional utility; it is no longer imported by the build path.
- `briefing/rank.py`: simplify rather than delete, to avoid breaking older imports while removing old keyword/category scoring assumptions.
- `momentum.json`, old briefs, cache files, and pycache: do not modify, stage, or commit.

## Test plan

- Run the renderer tests before implementation to confirm the remaining contract gaps fail.
- Implement the smallest changes needed for issue metadata footer, link hardening, responsive breakpoints, and ranking compatibility.
- Run `python -m pytest tests/ -v` until the full suite passes.
- Run the exact CLI verification commands from the request after tests pass.

## Verification steps

1. `python -m pytest tests/ -v`
2. `python -m briefing.build --demo`
3. `python -m briefing.build --demo` and confirm output does not contain `RuntimeWarning`
4. `python -m briefing.build --demo | grep -c 'href="#'`
5. Create `test-editorial.json`, then run `python -m briefing.build --editorial-json test-editorial.json`
6. Verify the generated HTML structure starts with `<!DOCTYPE html>`, includes top story, signals, radar, one move, issue metadata, and footrail, and contains no retired static phrases or placeholder article links.
7. Check `git status --short`, stage only scoped source/test/config/plan changes, and commit with a message summarizing the architectural shift.
