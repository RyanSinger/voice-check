# Plan (variant B, borrow)

1. Refactor `engine/rules.py` to a single data-driven table of rule rows (dataclass or dict). Each row: name, category, kind (regex, phrase, word), pattern, severity, message, scope (line or doc), doc-level trigger threshold.
2. Port the four existing categories (dashes, ai_vocab_cluster, puffery, promotional) into the table.
3. Add rows for hedging, copula avoidance, dangling participles, vague attributions. Use regex kind with word boundaries. Keep clean.md clean by avoiding matches on neutral prose.
4. Add a generic scanner `scan_text(text, extra_rows)` that iterates rows and produces findings; doc-level rules aggregate across the text.
5. Rewrite `engine/voice_check.py` `scan()` to call the new scanner and merge supplement rows via `supplement.find_for()` + `supplement.load_rows()`.
6. Extend `engine/supplement.py` with a `load_rows(path)` parser that reads fenced blocks with info strings `voice-check-phrases`, `voice-check-words`, `voice-check-regex`, each line becoming a supplement rule row tagged `supplement:<category>`.
7. Update tests: keep existing 15 passing (the public API is still `voice_check.scan`). Add new tests for each of the 4 new rule categories (positive and negative) and a supplement integration test.
8. Update `references/rules.md` with engine-vs-skill markers and confirm README is accurate.
9. Verify by running pytest and the CLI against clean.md fixture.
