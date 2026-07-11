Deploy
======

Deploy the Lakeflow Framework and Pipeline Bundles to a Databricks workspace using Declarative Automation Bundles (DABs) and the Databricks CLI.

Start with :doc:`deploy_before_you_deploy` for deploy order, ownership, and workspace paths — then use the guides below for local or CI/CD deployment.

Browse the guides below, or jump to :doc:`quick_start` for a combined framework + samples path.

.. raw:: html

   <div class="lf-feature-grid lf-hub-grid">
     <article class="lf-feature-card">
       <div class="lf-feature-card__header">
         <h3 class="lf-feature-card__title">Before you deploy</h3>
       </div>
       <hr class="lf-feature-card__divider" />
       <p class="lf-feature-card__body">Deploy order, who deploys what, and service principal workspace paths — read this first.</p>
       <a class="lf-feature-card__link" href="deploy_before_you_deploy.html">
         <svg class="lf-feature-card__link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 11v2h12l-5.5 5.5 1.42 1.42L20.84 12l-8.92-8.92L10.5 4.5 16 10H4z"/></svg>
         Open guide
       </a>
     </article>
     <article class="lf-feature-card">
       <div class="lf-feature-card__header">
         <h3 class="lf-feature-card__title">Deploy the Framework</h3>
       </div>
       <hr class="lf-feature-card__divider" />
       <p class="lf-feature-card__body">Deployment options, local DAB deploy, and wheel install — get the framework into your workspace.</p>
       <a class="lf-feature-card__link" href="deploy_framework.html">
         <svg class="lf-feature-card__link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 11v2h12l-5.5 5.5 1.42 1.42L20.84 12l-8.92-8.92L10.5 4.5 16 10H4z"/></svg>
         Open section
       </a>
     </article>
     <article class="lf-feature-card">
       <div class="lf-feature-card__header">
         <h3 class="lf-feature-card__title">Deploy Pipeline Bundles</h3>
       </div>
       <hr class="lf-feature-card__divider" />
       <p class="lf-feature-card__body">Deploy your Pipeline Bundle after the framework is in place — set <code>framework_source_path</code>, validate, and deploy.</p>
       <a class="lf-feature-card__link" href="deploy_local_pipeline_bundle.html">
         <svg class="lf-feature-card__link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 11v2h12l-5.5 5.5 1.42 1.42L20.84 12l-8.92-8.92L10.5 4.5 16 10H4z"/></svg>
         Open guide
       </a>
     </article>
     <article class="lf-feature-card">
       <div class="lf-feature-card__header">
         <h3 class="lf-feature-card__title">Setting up CI/CD</h3>
       </div>
       <hr class="lf-feature-card__divider" />
       <p class="lf-feature-card__body">Automated deploy for both bundle types, including framework versioning and pinning strategies.</p>
       <a class="lf-feature-card__link" href="deploy_ci_cd.html">
         <svg class="lf-feature-card__link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 11v2h12l-5.5 5.5 1.42 1.42L20.84 12l-8.92-8.92L10.5 4.5 16 10H4z"/></svg>
         Open guide
       </a>
     </article>
   </div>

.. toctree::
   :maxdepth: 2
   :hidden:

   Before you deploy <deploy_before_you_deploy>
   Deploy the Framework <deploy_framework>

.. toctree::
   :caption: Deploy Pipeline Bundle
   :maxdepth: 2
   :hidden:

   Deploy from local machine <deploy_local_pipeline_bundle>

.. toctree::
   :maxdepth: 2
   :hidden:

   Setting up CI/CD <deploy_ci_cd>
