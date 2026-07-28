Agent Skills
============

This section introduces `Agent Skills <https://agentskills.io/specification>`_ for **end users of the Lakeflow Framework (LFF)**. Skills follow the open Agent Skills standard and work with AI coding assistants that support it — including **Cursor**, **Claude Code**, **Databricks Genie Code**, and others.

**Self-contained skill packages.** Each skill is a complete folder under ``skills/<skill_name>/`` in the repository. That folder holds everything needed to use and extend the skill: ``SKILL.md`` (what the agent loads), human guides under ``docs/``, agent reference material under ``references/``, plus ``assets/``, ``examples/``, and ``scripts/``. Install the skill folder into your assistant's skills directory — do not rely on this docs site as the full skill package.

.. note::

   The pages here are an **overview and entry point** for agent skills only. Refer to each skill's documentation in the repository for the full story.

**Using a skill:** Install the skill folder from the repository into your assistant's skills directory (see each skill's Getting Started guide for Cursor, Claude Code, Genie Code, and other hosts).

**Contributing a skill:** See :doc:`/contributors/index` and :doc:`/contributors/dev-docs` (Agent Skills section). New skills are added under ``skills/<skill_name>/`` with a ``SKILL.md`` and ``README.md``.

Start with the **Data Flow Spec Builder** — the core LFF skill for generating production-ready pipeline bundles from natural language.

.. raw:: html

   <div class="lf-feature-grid lf-hub-grid">
     <article class="lf-feature-card">
       <div class="lf-feature-card__header">
         <svg class="lf-feature-card__icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a1 1 0 0 1 1 1v1.07a7 7 0 0 1 5.93 5.93H20a1 1 0 1 1 0 2h-1.07A7 7 0 0 1 13 17.93V19a1 1 0 1 1-2 0v-1.07A7 7 0 0 1 5.07 12H4a1 1 0 1 1 0-2h1.07A7 7 0 0 1 11 4.07V3a1 1 0 0 1 1-1m0 5a5 5 0 1 0 0 10 5 5 0 0 0 0-10m0 3a2 2 0 1 1 0 4 2 2 0 0 1 0-4z"/></svg>
         <h3 class="lf-feature-card__title">Data Flow Spec Builder</h3>
       </div>
       <hr class="lf-feature-card__divider" />
       <p class="lf-feature-card__body"><strong>Core LFF skill.</strong> generate production-ready data flow spec pipeline bundles from natural language.</p>
       <a class="lf-feature-card__link" href="dataflowspec-builder/index.html">
         <svg class="lf-feature-card__link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 11v2h12l-5.5 5.5 1.42 1.42L20.84 12l-8.92-8.92L10.5 4.5 16 10H4z"/></svg>
         Open skill documentation
       </a>
     </article>
   </div>

.. toctree::
   :maxdepth: 2
   :hidden:

   Data Flow Spec Builder <dataflowspec-builder/index>
