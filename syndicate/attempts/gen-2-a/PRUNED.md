# gen-2-a: pruned

Variant A (constrain) took the narrow path: runtime-only hook test with no production file changes. 3 tests, 29 total pass.

Pruned because criterion 7 explicitly required "both the install flow (templates substitution) and the runtime execution path." A's stance deliberately skipped the install flow, so it scored 3 on that criterion and 4.57 average.

A's approach is still useful as a reference for how to invoke the hook directly in isolation. If install-hook.sh is ever removed or rewritten, A's pattern would become the primary test.
