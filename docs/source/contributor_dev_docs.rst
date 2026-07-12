Write & build docs
##################

Author and build the Lakeflow Framework documentation — reStructuredText and MyST sources, Sphinx, and the hub-based information architecture.

For local setup, see :doc:`contributor_dev_env` (``requirements-dev.lock`` includes docs dependencies).
For the contribution workflow and doc CI checks, see :doc:`contributor_dev_steps`.

Documentation layout
====================

Source files live under ``docs/source/``. Top-level navigation is defined in :doc:`index`.

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Section
     - Role
   * - **Home** (:doc:`index`)
     - Landing page with hero and entry cards (`docs/source/_landing.rst`)
   * - **Get Started**
     - :doc:`get_started` — prose landing with paths to :doc:`what_is_lakeflow_framework` and :doc:`quick_start`
   * - **Architecture**
     - :doc:`concepts` — operating model, bundles, specs
   * - **Samples**
     - :doc:`deploy_samples` — feature, pattern, and TPCH samples
   * - **Build**
     - :doc:`build_pipeline_bundle` hub — structure, steps, spec reference, patterns
   * - **Deploy**
     - :doc:`deploy` hub — before you deploy, :doc:`deploy_framework` subsection, pipeline bundle local deploy, :doc:`deploy_ci_cd`
   * - **Features**
     - :doc:`features` hub — category sub-hubs and ``feature_*.rst`` pages; :doc:`feature_a_z` index
   * - **Contributors**
     - :doc:`contributor` hub — env, git/releases, workflow, imports, this page

**Hub pages** (for example :doc:`deploy`, :doc:`contributor`, :doc:`features`, :doc:`deploy_framework`) use:

* A short intro paragraph
* An ``lf-feature-grid`` / ``lf-hub-grid`` card block (see ``docs/source/_landing.rst`` or :doc:`deploy` for examples)
* A **hidden** ``.. toctree::`` listing child pages (and optional ``:caption:`` groups for sidebar sections)

Only ``dataflow_spec_reference`` is treated as a caption-only section index in ``docs/conf.py`` — other top-level tabs link to their hub page directly.

Writing documentation
=====================

Feature pages
-------------

When you add or change framework behavior:

1. Create or update ``docs/source/feature_<name>.rst``
2. Include the standard metadata table (**Applies To**, **Configuration Scope**, **Databricks Docs** where relevant)
3. Add the page to the matching **Features** sub-hub toctree (for example ``feature_metadata.rst``) and to :doc:`feature_a_z`
4. Update :doc:`dataflow_spec_reference` when the Data Flow Spec schema changes

Deploy and build pages
----------------------

Deploy docs are split by audience:

* **Framework** — :doc:`deploy_framework_options`, :doc:`deploy_local_framework`, :doc:`deploy_wheel` under :doc:`deploy_framework`
* **Pipeline bundle** — :doc:`deploy_local_pipeline_bundle`
* **Shared** — :doc:`deploy_before_you_deploy`, :doc:`deploy_ci_cd`

Add new deploy guides to the appropriate hub toctree in ``deploy.rst`` or ``deploy_framework.rst``, and add a hub card when the page is a primary entry point.

Build guides live under the :doc:`build_pipeline_bundle` hub.

Cross-references
----------------

* RST: ``:doc:`page_name``` or ``:doc:`Title <page_name>```
* MyST (``deploy_samples.md``): ``{doc}`page_name```
* RST: ``:doc:`page_name```
* Sections: ``:ref:`label-name``` (use unique labels; avoid duplicating labels across spec ref pages)

Styling
=======

Theme and HTML
--------------

* Theme and build options: ``docs/conf.py`` (``sphinx_immaterial`` — do not change theme without team agreement)
* Brand CSS: ``docs/source/_static/databricks-theme.css``, ``docs/source/_static/custom.css``
* Landing and hub cards: ``lf-feature-card``, ``lf-hub-grid`` classes in raw HTML blocks

Command-line and code blocks
----------------------------

Shell commands use the WAF-style command snippet pattern:

.. code-block:: console
   :class: lf-command-block

   make -C docs html

* **``console``** + ``:class: lf-command-block`` — terminal commands (copy button enabled via ``conf.py``)
* **``python``**, **``yaml``**, **``toml``** — language blocks without ``lf-command-block`` unless the block is a shell one-liner
* Spec and config examples in body text use normal ``.. code-block:: yaml`` / ``json`` as appropriate

Prerequisites checklists: on ``.md`` use MyST ``- [ ]`` task lists; on ``.rst`` wrap items in sphinx-immaterial ``.. task-list::`` with ``- [ ]`` markers.

Build locally
=============

Install dependencies
--------------------

From the repo root (or use ``requirements-dev.lock`` from :doc:`contributor_dev_env`):

.. code-block:: console
   :class: lf-command-block

   pip install --require-hashes --no-deps -r requirements-docs.lock

.. note::

   ``requirements-dev.lock`` already includes ``requirements-docs.lock`` — a full dev install is enough for doc builds.

Build HTML
----------

From the ``docs/`` directory:

.. code-block:: console
   :class: lf-command-block

   make html

Output: ``docs/build/html/index.html``

Preview with a local HTTP server (recommended for navigation and version UI testing):

.. code-block:: console
   :class: lf-command-block

   cd build/html && python3 -m http.server 8000

Then open ``http://localhost:8000/index.html``.

Other targets
-------------

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Command
     - Purpose
   * - ``make -C docs spelling``
     - Spelling check (fails on misspellings; requires Enchant — ``brew install enchant`` on macOS)
   * - ``make -C docs md``
     - Markdown export to ``docs/build/markdown/``
   * - ``make -C docs html-multiversion-preview``
     - Versioned site under ``docs/build/html/current/`` plus ``local-branch-preview`` for the current branch
   * - ``make -C docs clean``
     - Remove ``docs/build/`` (use after structural IA changes if the build cache misbehaves)

See ``docs/README.md`` for multiversion publishing rules and GitHub Pages layout.

Updating doc dependencies
-------------------------

Edit ``requirements-docs.txt``, then regenerate lockfiles from the repo root:

.. code-block:: console
   :class: lf-command-block

   ./scripts/generate_lockfiles.sh

Commit the updated ``requirements-docs.lock`` (and related ``.lock`` files) in the same pull request.

CI checks
=========

When you change files under ``docs/``, run before pushing:

.. code-block:: console
   :class: lf-command-block

   bash scripts/ci/docs_spelling_check.sh
   bash scripts/ci/docs_html_check.sh

CI runs these when ``docs/`` changes on pull requests. Keep Sphinx **warnings** below the CI threshold documented in :doc:`contributor_dev_steps`.

See also
--------

- :doc:`contributor` — Contributors hub
- :doc:`contributor_dev_steps` — pull request workflow
- ``docs/README.md`` — multiversion builds and GitHub Pages
- ``docs/decisions/`` — architecture decisions for docs and packaging
