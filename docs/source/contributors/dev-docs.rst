Write & build docs
##################

Author and build the Lakeflow Framework documentation — reStructuredText and MyST sources, Sphinx, and the hub-based information architecture.

For local setup, see :doc:`dev-env` (``requirements-dev.lock`` includes docs dependencies).
For the contribution workflow and doc CI checks, see :doc:`dev-steps`.

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
     - :doc:`get-started/index` — prose landing with paths to :doc:`get-started/what-is-lakeflow-framework` and :doc:`get-started/quick-start`
   * - **Architecture**
     - :doc:`architecture/index` — operating model, bundles, specs
   * - **Samples**
     - :doc:`samples/index` — feature, pattern, and TPCH samples
   * - **Build**
     - :doc:`build/index` hub — structure, steps, spec reference, patterns
   * - **Deploy**
     - :doc:`deploy/index` hub — before you deploy, :doc:`deploy/framework/index` subsection, pipeline bundle local deploy, :doc:`deploy/ci-cd`
   * - **Features**
     - :doc:`features/index` hub — category sub-hubs and ``feature_*.rst`` pages; :doc:`features/a-z` index
   * - **Contributors**
     - :doc:`contributors/index` hub — env, git/releases, workflow, imports, this page

**Folder convention** (site-wide):

* ``docs/source/{section}/index.rst`` — top tab hub (Get Started, Build, Deploy, Features, …)
* ``docs/source/{section}/{topic}/index.rst`` — nested hub (for example ``deploy/framework/``, ``features/metadata/``)
* ``docs/source/{section}/.../*.rst`` — leaf pages (kebab-case filenames)
* ``docs/source/_*.rst`` — includes/partials only (not standalone nav pages)

**Hub pages** use:

* A short intro paragraph
* An ``lf-feature-grid`` / ``lf-hub-grid`` card block (see ``docs/source/_landing.rst``)
* A **hidden** ``.. toctree::`` listing child pages (and optional ``:caption:`` groups for sidebar sections)

Nested section indexes (for example ``build/spec-reference/index``, ``features/platform/index``) are caption-only in ``docs/conf.py`` — the sidebar title links to the first child page.

**URL redirects:** When a published flat URL changes (RTD-era ``feature_cdc.html``, ``deploy.html``, etc.), add an entry under ``docs/redirects/``. Post-build stubs are written for ``current`` and ``local-branch-preview`` only (see ``docs/scripts/write_redirects.py``).

Writing documentation
=====================

Feature pages
-------------

When you add or change framework behavior:

1. Create or update ``docs/source/features/{category}/{page-name}.rst`` (kebab-case)
2. Include the standard metadata table (**Applies To**, **Configuration Scope**, **Databricks Docs** where relevant)
3. Add the page to the matching category hub ``index.rst`` toctree and to :doc:`features/a-z`
4. Update :doc:`build/spec-reference/index` when the Data Flow Spec schema changes
5. If the page replaces a flat URL already on ``main``, add a redirect in ``docs/redirects/features.yaml``

Deploy and build pages
----------------------

Deploy docs are split by audience:

* **Framework** — :doc:`deploy/framework/options`, :doc:`deploy/framework/local-framework`, :doc:`deploy/framework/wheel` under :doc:`deploy/framework/index`
* **Pipeline bundle** — :doc:`deploy/pipeline-bundle/local`
* **Shared** — :doc:`deploy/before-you-deploy`, :doc:`deploy/ci-cd`

Add new deploy guides to the appropriate hub toctree under ``docs/source/deploy/`` (for example ``deploy/index.rst`` or ``deploy/framework/index.rst``), and add a hub card when the page is a primary entry point.

Build guides live under the :doc:`build/index` hub.

Cross-references
----------------

* RST: ``:doc:`page_name``` or ``:doc:`Title <page_name>```
* MyST (``samples/index.md``): ``{doc}`samples/index```
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

From the repo root (or use ``requirements-dev.lock`` from :doc:`dev-env`):

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

CI runs these when ``docs/`` changes on pull requests. Keep Sphinx **warnings** below the CI threshold documented in :doc:`dev-steps`.

See also
--------

- :doc:`contributors/index` — Contributors hub
- :doc:`dev-steps` — pull request workflow
- ``docs/README.md`` — multiversion builds and GitHub Pages
- ``docs/decisions/`` — architecture decisions for docs and packaging
