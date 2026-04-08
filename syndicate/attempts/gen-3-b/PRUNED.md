# gen-3-b: pruned

Variant B (invert) introduced a new `engine/markdown_view.py` module with a pure `as_prose()` function and routed the scanner through it. Functionally equivalent to A on all criteria (5.00 avg each, 36 tests pass). Lost the pairwise tie-breaker on complexity: +247 lines across 5 files vs A's +158 across 3, plus a new module with no second caller.

B's architectural separation would be right for a larger rule system with multiple consumers of the preprocessor. For this plugin, it's weight that doesn't earn its keep.

Kept as a reference if the engine ever gains a second input format or if the skill path wants to reuse prose-view logic.
