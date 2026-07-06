# src/init/post/

**Post-init lifecycle scripts** — `.py` files run **after** all SDP table/view declarations
inside `DLTPipelineBuilder.initialize_pipeline()`.

Same execution rules as `src/init/pre/` (sorted order, `_` prefix skipped, `runpy`).

Typical uses: registering `@dp.on_event_hook` callbacks, setting up post-declaration
monitoring, or any logic that must see the fully-assembled SDP graph.
