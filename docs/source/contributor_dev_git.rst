Branching, versioning & releases
################################

How the Lakeflow Framework repository is branched and versioned. **Read this before** :doc:`contributor_dev_steps`.

For how deployed framework versions are pinned in workspace (``current`` vs ``1.2.3`` paths), see :doc:`feature_versioning_framework`.

Trunk-based development
=======================

The project uses **trunk-based development** on ``main``. There is no long-lived ``develop`` branch — all changes integrate through pull requests into ``main``.

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Branch
     - Purpose
   * - ``main``
     - Production-ready trunk; always deployable
   * - ``feature/*``
     - New features or larger changes
   * - ``fix/*``
     - Bug fixes and hotfixes

Branch naming
=============

Create short-lived branches from ``main``. Keep each branch focused on a single feature or fix.

**Feature branches**

* Name: ``feature/descriptive-name`` (for example ``feature/add-cdc-support``)
* Sync with ``main`` regularly to reduce merge conflicts
* Open a pull request to ``main`` when ready

**Fix branches**

* Name: ``fix/issue-description`` (for example ``fix/logging-format``)
* Keep changes minimal; reference the issue in commit messages when applicable
* Use the same PR → squash merge flow as features

Version format and strategy
===========================

The canonical release version lives in ``VERSION`` at the repository root, formatted ``vMAJOR.MINOR.FIX`` (for example ``v0.20.0``).

**Semantic versioning**

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Component
     - When to increment (manual, in your pull request)
   * - **MAJOR**
     - Breaking changes — team-coordinated (for example the v1.0.0 release)
   * - **MINOR**
     - New features or significant enhancements — typical for ``feature/*`` work; reset **FIX** to ``0``
   * - **FIX** (patch)
     - Bug fixes — typical for ``fix/*`` work

**Examples:** ``v0.20.3`` → ``v0.21.0`` for a feature release; ``v0.20.3`` → ``v0.20.4`` for a patch.

Bumping ``VERSION`` in your pull request
========================================

Until **v1.0.0**, contributors **manually** update ``VERSION`` in the same pull request as the code or documentation change:

1. Read the current value in ``VERSION`` on ``main``
2. Apply the appropriate semver increment (see table above)
3. Write the new value (for example ``v0.21.0``) to ``VERSION``
4. Include that file change in your pull request

.. note::

   **Planned for v1.0.0:** version bumps will be automated from branch names on merge to ``main``, and manual ``VERSION`` edits in pull requests will no longer be required. Until then, every release-bound PR must update ``VERSION`` explicitly.

Hotfixes
========

For urgent production issues:

1. Create a ``fix/*`` branch from ``main``
2. Implement and test the fix locally and on Databricks where applicable
3. Bump ``VERSION`` with a **FIX** (patch) increment in the same pull request
4. Open a pull request and **squash merge** to ``main``

Pull request expectations
=========================

* **Target branch:** ``main``
* **Merge method:** **Squash and merge** (linear history)
* **CI:** must pass (``.github/workflows/ci.yml``) before merge
* **Release-bound changes:** include an updated ``VERSION`` file when the change should ship as a new release
* **After merge:** delete the feature branch; close linked issues

See also
--------

- :doc:`contributor_dev_steps` — development and pull request workflow
- :doc:`feature_versioning_framework` — ``current`` vs pinned paths in workspace deploy
- :doc:`deploy_ci_cd` — promoting framework versions through environments
