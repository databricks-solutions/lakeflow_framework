Installing the Framework as a Wheel
######################################

From v0.20.0 the Lakeflow Framework ships as a proper Python package
(``lakeflow-framework``) with a ``pyproject.toml``.  For a comparison of all
deployment modes, see :doc:`/deploy/framework/options`.

Installing
----------

Core install (no optional extensions):

.. code-block:: console
   :class: lf-command-block

   pip install lakeflow-framework

With community extensions (``contrib``):

.. code-block:: console
   :class: lf-command-block

   pip install "lakeflow-framework[contrib]"

Everything:

.. code-block:: console
   :class: lf-command-block

   pip install "lakeflow-framework[all]"

.. note::
   ``[contrib]`` is currently empty — the ``contrib`` subpackage is a
   scaffold for future community-maintained integrations.  Installing it does
   not add dependencies until a contrib module lands.

Checking the installed version
-------------------------------

From Python:

.. code-block:: python
   :linenos:

   import lakeflow_framework
   print(lakeflow_framework.__version__)

From the command line:

.. code-block:: console
   :class: lf-command-block

   python -c "import lakeflow_framework; print(lakeflow_framework.__version__)"

Config and schema resolution
-----------------------------

When the framework is installed as a wheel, default configuration files and
JSON schemas are bundled inside the package and accessed via
``importlib.resources``.  The resolution order is:

1. **Workspace Files** — ``{framework_path}/lakeflow_framework/config/default/<file>``
   when ``framework.sourcePath`` is configured and the file exists in workspace files.
2. **Package data** — bundled defaults from the wheel (or from
   ``src/lakeflow_framework/`` on ``sys.path`` for flat deploy).
3. **``src/local/config/`` custom override** — deep-merged on top when
   ``framework.sourcePath`` is set and the sparse fragment exists.

See :ref:`config-resolution-order` in :doc:`/features/configuration/framework-configuration`
for the full table.

Using ``src/local/config/`` custom override`` with a wheel
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you install the framework as a wheel but still want per-deployment config
overrides, set ``framework.sourcePath`` in your pipeline resource YAML to point
to a directory that contains ``local/config/``:

.. code-block:: yaml
   :linenos:

   spark_conf:
     framework.sourcePath: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}/files/src

Then place sparse override files under that ``src/local/config/``.  The
framework will load defaults from the wheel and deep-merge your overrides on
top.

Backward compatibility
-----------------------

- **Existing flat-deploy customers** are unaffected.  The workspace files first
  resolution means that if ``framework.sourcePath`` is set and default files
  are in workspace files, they take priority over the wheel — behaviour is identical to
  earlier releases.
- **Compat shims** at the old flat ``src/`` import paths (e.g.
  ``from constants import FrameworkPaths``) remain until v1.0.0.  Prefer
  ``from lakeflow_framework.constants import FrameworkPaths`` in new code.

See also
--------

- :doc:`/deploy/framework/options` — deployment modes overview and flat DAB deploy
- :doc:`/deploy/framework/local-framework` — deploy the framework via DAB from your laptop
- :doc:`/features/configuration/framework-configuration` — full config resolution reference
- :doc:`/features/environments/versioning-framework` — version pinning and rollback
