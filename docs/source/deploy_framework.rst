Deploy the Framework
====================

Deploy the **Lakeflow Framework** to your Databricks workspace. Choose a deployment mode, then follow the guide that matches how your team manages dependencies and configuration.

For deploy order and ownership, see :doc:`deploy_before_you_deploy`.

.. raw:: html

   <div class="lf-feature-grid lf-hub-grid">
     <article class="lf-feature-card">
       <div class="lf-feature-card__header">
         <h3 class="lf-feature-card__title">Deployment options</h3>
       </div>
       <hr class="lf-feature-card__divider" />
       <p class="lf-feature-card__body">Flat DAB deploy, wheel install, or wheel plus local config overlay — choose a framework deployment mode.</p>
       <a class="lf-feature-card__link" href="deploy_framework_options.html">
         <svg class="lf-feature-card__link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 11v2h12l-5.5 5.5 1.42 1.42L20.84 12l-8.92-8.92L10.5 4.5 16 10H4z"/></svg>
         Open guide
       </a>
     </article>
     <article class="lf-feature-card">
       <div class="lf-feature-card__header">
         <h3 class="lf-feature-card__title">Deploy from local machine</h3>
       </div>
       <hr class="lf-feature-card__divider" />
       <p class="lf-feature-card__body">Clone the framework repo, authenticate the CLI, validate, and deploy the Framework Bundle to workspace files.</p>
       <a class="lf-feature-card__link" href="deploy_local_framework.html">
         <svg class="lf-feature-card__link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 11v2h12l-5.5 5.5 1.42 1.42L20.84 12l-8.92-8.92L10.5 4.5 16 10H4z"/></svg>
         Open guide
       </a>
     </article>
     <article class="lf-feature-card">
       <div class="lf-feature-card__header">
         <h3 class="lf-feature-card__title">Install as a wheel</h3>
       </div>
       <hr class="lf-feature-card__divider" />
       <p class="lf-feature-card__body">Install <code>lakeflow-framework</code> via pip and use bundled defaults with optional workspace overlays.</p>
       <a class="lf-feature-card__link" href="deploy_wheel.html">
         <svg class="lf-feature-card__link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 11v2h12l-5.5 5.5 1.42 1.42L20.84 12l-8.92-8.92L10.5 4.5 16 10H4z"/></svg>
         Open guide
       </a>
     </article>
   </div>

.. toctree::
   :maxdepth: 2
   :hidden:

   Deployment options <deploy_framework_options>
   Deploy from local machine <deploy_local_framework>
   Installing as a wheel <deploy_wheel>
