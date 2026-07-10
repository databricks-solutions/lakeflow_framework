Development Steps
#################

This guide outlines the process for contributing features or fixes to the Lakeflow Framework.

Issue Creation
--------------
1. Create a new issue in the GitHub repository
   
   - Clearly describe the feature or bug
   - Include acceptance criteria
   - Add relevant labels (feature/bug/enhancement)
   - Link to related issues if applicable

Branch Management
-----------------
1. Create a feature branch from ``main``
   
   - Use naming convention: ``feature/[brief-description]``
   - Example: ``feature/add-scd2-support``
2. Keep branches focused on single features/fixes
3. Regularly sync with ``main`` to avoid merge conflicts

Development Process
-------------------
1. Local Development
   
   - Follow coding standards and style guides
       - Ensure the yapf extension is installed and enabled in VS Code (refer to step 2 of :doc:`contributor_dev_env`)
       - Use yapf to format your python code (right click and select 'Format Document With' then select yapf)
   - Stick to solid principles and object oriented design patterns
   - Deploy updated framework to Databricks to ensure it is working as expected
   - Use meaningful commit messages
   - Keep commits atomic and focused

2. Unit Testing
   
   - Install dev dependencies from ``requirements-dev.lock`` (see :doc:`contributor_dev_env`).
   - Run unit tests from the repository root:

     .. code-block:: bash

        pytest tests/ -m "not integration and not spark"

   - See ``tests/README.md`` for layout, fixtures, markers, and conventions.
   - Optional coverage: add ``--cov=src --cov-report=term-missing``.
   - CI runs the same pytest command on every pull request (``.github/workflows/ci.yml``).

3. Integration Testing / Samples

   - Where applicable, add sample pipelines to ``feature-samples`` (for isolated feature demonstrations) or ``pattern-samples`` (for medallion architecture patterns) to show how to use the new feature
   - Run integration tests when you change samples, schemas, or validation logic:

     .. code-block:: bash

        pytest tests/ -m integration

   - Validate data flow specs locally when you change samples or schemas (prefer per-bundle paths):

     .. code-block:: bash

        python scripts/validate_dataflows.py samples/pattern-samples/
        python scripts/validate_dataflows.py samples/tpch_sample/
        python scripts/validate_dataflows.py samples/feature-samples/

   - CI validates sample bundles with ``scripts/validate_dataflows.py samples/`` when files under ``samples/`` change.
   - Deploy and run existing sample pipelines on Databricks to ensure changes are not breaking existing functionality (refer to :doc:`deploy_samples`)

4. Documentation
   - Update documentation per :doc:`contributor_dev_docs`
   - When you change files under ``docs/``, run locally before pushing:

     .. code-block:: bash

        bash scripts/ci/docs_spelling_check.sh
        bash scripts/ci/docs_html_check.sh

   - ``make -C docs spelling`` runs the same spelling check (fails on any misspelled words).
   - CI runs spelling and HTML builds when documentation changes; HTML must stay below 20 Sphinx warnings.

Pull Request Process
--------------------
1. PR Creation
   
   - Create PR from feature branch to ``main``
   - Fill out PR template completely
   - Link related issues
   - Add relevant reviewers

2. PR Review
   
   - Address reviewer comments
   - Update code/docs as needed
   - Get required approvals

3. Merge Process
   
   - **Squash and merge** to ``main``
   - Delete feature branch after merge
   - Close related issues

Post-Merge Steps
----------------
1. Verify Changes
   
   - Confirm changes are working on ``main``
   - Check documentation is published correctly
   - Validate CI/CD pipeline passes

2. Monitor
   
   - Watch for any issues on ``main``
   - Be prepared to address any problems quickly




