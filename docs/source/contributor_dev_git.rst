GIT
####

Branching Strategy
------------------

The project follows the Gitflow branching model for version control. This model provides a robust framework for managing larger projects with scheduled releases.

Our repository maintains the following primary branches:

* ``main`` - Contains production-ready code
* ``develop`` - Main integration branch for ongoing development
* ``release`` - Used when preparing a new production release
* ``feature`` - Short-lived branches for new feature development
* ``fix`` - Short-lived branches for bug fixes

Feature Branch Guidelines
^^^^^^^^^^^^^^^^^^^^^^^^

* Create feature branches from ``develop``
* Branch naming: ``feature/descriptive-name`` (e.g. ``feature/add-cdc-support``)
* Keep changes focused and atomic
* Regularly sync with ``develop`` to minimize merge conflicts
* Submit pull request to merge back into ``develop`` when complete

Fix Branch Guidelines
^^^^^^^^^^^^^^^^^^^

* Create fix branches from ``develop`` for non-critical bugs
* Branch naming: ``fix/issue-description`` (e.g. ``fix/logging-format``)
* Include issue reference in commit messages when applicable
* Keep changes minimal and focused on the bug fix
* Submit pull request to merge back into ``develop`` when complete

Release Strategy
---------------

The project follows a structured release process aligned with the GitFlow branching model:

1. **Release Branch Creation**
   
   * When ``develop`` branch contains all features planned for release
   * Create release branch: ``release/vX.Y.Z``
   * Branch naming follows semantic versioning (e.g. ``release/v1.2.0``)

2. **Release Finalization**

   * After thorough testing and stabilization:
     - Merge release branch into ``main``
     - Tag the release in ``main`` with version number
     - Merge release branch back into ``develop``
     - Delete the release branch

4. **Hotfix Process**

   * For critical production issues:
     - Create hotfix branch from ``main`` (e.g. ``hotfix/v1.2.1``)
     - Implement and test the fix
     - Merge hotfix into both ``main`` and ``develop``
     - Tag the new version in ``main``

