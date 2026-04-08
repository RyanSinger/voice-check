# Gen 3a plan (constrain)

Goal: stop the engine firing false positives on common markdown syntax.

Minimal surgical fix in `plugins/voice-check/engine/rules.py` only.

1. Add `_FENCE_RE`, `_BULLET_RE`, `_INLINE_CODE_RE` module constants.
2. Add `_prepare_line_for_rules(line)`: blank out inline code spans, then blank the leading bullet marker.
3. Add `_strip_code_blocks(text)`: return text with fenced code block contents replaced by blank lines.
4. In `scan_text()`: toggle an in-fence flag per line, skip fenced lines in the line-scope pass, apply `_prepare_line_for_rules` to each surviving line, and feed `_strip_code_blocks(text)` into the doc-scope pass.
5. Update the `check_ai_vocab_cluster` back-compat shim to also scan stripped text.
6. Expand `tests/fixtures/clean.md` with heading, prose, nested bullets, fenced code, inline code, and a table.
7. Add three positive tests plus a fixture-level sanity test in `tests/test_engine.py`.

No changes to rule definitions, supplement format, hook scripts, or skills.
