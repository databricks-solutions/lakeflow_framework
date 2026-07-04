GIT
####

Branching Strategy
------------------

The project uses **trunk-based development** on ``main``. There is no long-lived
``develop`` branch; all changes integrate through pull requests into ``main``.

Primary branches and branch types:

* ``main`` - Production-ready trunk; always deployable
* ``feature/*`` - Short-lived branches for new features or larger changes
* ``fix/*`` - Short-lived branches for bug fixes

Feature Branch Guidelines
^^^^^^^^^^^^^^^^^^^^^^^^^

* Create feature branches from ``main``
* Branch naming: ``feature/descriptive-name`` (e.g. ``feature/add-cdc-support``)
* Keep changes focused and atomic
* Regularly sync with ``main`` to minimize merge conflicts
* Open a pull request to merge into ``main`` when complete

Fix Branch Guidelines
^^^^^^^^^^^^^^^^^^^^^

* Create fix branches from ``main``
* Branch naming: ``fix/issue-description`` (e.g. ``fix/logging-format``)
* Include issue reference in commit messages when applicable
* Keep changes minimal and focused on the bug fix
* Open a pull request to merge into ``main`` when complete

Release and Versioning
----------------------

Version bumps are automated when a pull request is **merged** into ``main`` (see
``.github/workflows/main-build.yml``):

* Branches named ``feature/*`` → **minor** version bump (fix reset to 0)
* Branches named ``fix/*`` → **fix** (patch) version bump
* Other branch names → no automatic version bump (warning in workflow log)

The workflow updates ``VERSION``, commits to ``main``, and creates a ``vX.Y.Z`` tag.

Hotfix Process
^^^^^^^^^^^^^^

For urgent production issues:

1. Create a hotfix branch from ``main`` (e.g. ``fix/critical-data-loss``)
2. Implement and test the fix
3. Merge to ``main`` via pull request (squash merge)
4. Let the version workflow tag ``main`` (``fix/*`` branch → patch bump)

Pull Request Expectations
-------------------------

* Target branch: ``main``
* Prefer **squash and merge** for a linear history
* Ensure **CI** passes (``.github/workflows/ci.yml``) before merge
* Delete the feature branch after merge
