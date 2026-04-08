# gen-1-a: pruned

Variant A (decompose) was functionally equivalent to variant B on five of six criteria. B edged ahead on supplement wiring because it supported three kinds (words, phrases, regex) where A supported two (words, phrases). B's data-driven RULES table is also more aligned with the plugin's existing pattern of treating rules.md as a single source of truth.

Both scored 25/25 and 26/26 on pytest respectively. Both kept clean.md silent.

Kept for reference: A's per-category decomposition is a valid future refactor of B's single table if the table ever grows past readable size.
