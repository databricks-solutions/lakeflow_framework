Contribution workflow
#####################

End-to-end process for contributing features or fixes to the Lakeflow Framework.

**Start with** :doc:`contributor_dev_git` for branch naming and manual ``VERSION`` updates in your pull request.

For environment setup, see :doc:`contributor_dev_env`.
For import rules, see :doc:`contributor_imports`.

Step 1 — Open an issue
======================

Create a GitHub issue before significant work:

* Clearly describe the feature or bug
* Include acceptance criteria
* Add labels (``feature``, ``bug``, ``enhancement``, as appropriate)
* Link related issues when applicable

Step 2 — Create a branch
========================

From an up-to-date ``main``:

.. code-block:: console
   :class: lf-command-block

   git checkout main
   git pull origin main
   git checkout -b feature/my-change

See :doc:`contributor_dev_git` for branching strategy, naming conventions, and semver guidance.

Step 3 — Develop locally
========================

* Format Python with **yapf** (install via workspace recommendations in :doc:`contributor_dev_env`)
* Keep commits atomic with meaningful messages
* Deploy updated framework to Databricks when behavior affects pipelines (see :doc:`deploy_local_framework`)
* Add tests to the test suite when you change the framework code

Step 4 — Run tests
==================

**Unit tests** (from repository root):

.. code-block:: console
   :class: lf-command-block

   pytest tests/ -m "not integration and not spark"

Optional coverage: ``--cov=lakeflow_framework --cov-report=term-missing``. See ``tests/README.md`` for markers and layout. CI runs the same command on every pull request.

**Integration tests** (when you change samples, schemas, or validation logic):

.. code-block:: console
   :class: lf-command-block

   pytest tests/ -m integration

**Validate data flow specs** (prefer per-bundle paths):

.. code-block:: console
   :class: lf-command-block

   python scripts/validate_dataflows.py samples/pattern-samples/
   python scripts/validate_dataflows.py samples/tpch_sample/
   python scripts/validate_dataflows.py samples/feature-samples/

When adding a feature, add or extend samples in ``feature-samples`` (isolated demos) or ``pattern-samples`` (medallion patterns) as appropriate. Deploy and run affected pipelines on Databricks — see :doc:`deploy_samples`.

Step 5 — Update documentation
=============================

* Update docs per :doc:`contributor_dev_docs` (feature pages, spec reference, cross-links)
* Before pushing doc changes:

.. code-block:: console
   :class: lf-command-block

   bash scripts/ci/docs_spelling_check.sh
   bash scripts/ci/docs_html_check.sh

``make -C docs spelling`` runs the same spelling check. CI builds HTML when ``docs/`` changes; keep Sphinx warnings below the CI threshold.

Step 6 — Open and merge a pull request
======================================

1. Push your branch and open a PR **to ``main``**
2. Include an updated ``VERSION`` file when the change should ship as a release (see :doc:`contributor_dev_git`)
3. Complete the PR template; link the issue; request reviewers
4. Address review feedback; ensure **CI passes**
5. **Squash and merge** to ``main`` (see :doc:`contributor_dev_git`)
6. Delete the branch after merge

Step 7 — Verify after merge
===========================

* Confirm ``main`` CI is green
* Check published docs on the next docs deploy if you changed documentation
* Monitor for regressions on ``main``

See also
--------

- :doc:`contributor_dev_git` — branching, versioning, and releases
- :doc:`contributor_dev_env` — local setup
- :doc:`contributor_dev_docs` — documentation authoring
- :doc:`feature_versioning_framework` — framework version paths in workspace deploy
