Framework Deployment Options
############################

The Lakeflow Framework can be deployed to a Databricks workspace in three
ways.  Choose the mode that matches how your team manages dependencies and
configuration.

.. list-table::
   :header-rows: 1
   :widths: 20 42 38

   * - Mode
     - How it works
     - When to use
   * - **Flat DAB deploy** *(default)*
     - The framework repository is cloned and deployed with
       ``databricks bundle deploy``.  ``framework.sourcePath`` points to the
       deployed ``src/`` directory on workspace files; the cluster reads
       Python modules and default config directly from there.
     - Default for all existing customers.  No change to existing pipelines
       required.
   * - **Wheel install**
     - ``pip install lakeflow-framework`` installs the package into the
       cluster Python environment.  Default configs and schemas are bundled
       inside the wheel via ``importlib.resources``.
     - Teams that manage Python dependencies via PyPI, a UC Volume, or an
       internal Artifactory feed.
   * - **Wheel + local overlay**
     - Wheel installed, plus ``framework.sourcePath`` still set so that
       ``src/local/config/`` sparse overrides are deep-merged on top of the
       bundled defaults.
     - Teams that want pip-managed installs but need per-deployment config
       customisation.

.. note::
   For wheel based deployments it is your responsibility to provide
   an entry-point notebook and a location for local config overrides and
   libraries/init scripts when moving away from the default flat deploy.

See also
--------

- :doc:`/deploy/framework/local-framework` — flat DAB deploy from your laptop
- :doc:`/deploy/framework/wheel` — install ``lakeflow-framework`` as a Python wheel