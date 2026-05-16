# local/init/post/

**Post-init lifecycle scripts** — `.py` files run **after** all SDP table/view declarations
inside `DLTPipelineBuilder.initialize_pipeline()` for **all** pipelines using this framework bundle.

Framework bundle scripts (this directory) run before pipeline bundle `src/init/post/` scripts.

Same execution rules as `local/init/pre/` (sorted order, `_` prefix skipped, `runpy`).

Typical uses: registering org-wide `@dp.on_event_hook` callbacks, post-declaration
monitoring setup, or any logic that must see the fully-assembled SDP graph and should
apply across all pipelines.
