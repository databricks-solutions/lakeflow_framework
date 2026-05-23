# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
sys.path.append(os.path.abspath("."))  # Ensure the script is discoverable
from custom_markdown_builder import CustomMarkdownTranslator

project = 'Lakeflow Framework'
copyright = '2025, Databricks'
author = 'Erik Seefeld, Haille Woldegebriel, Amin Movahed'

# Read version from the VERSION file at the repo root so conf.py never
# needs a manual update when a release is cut.
_here = os.path.dirname(os.path.abspath(__file__))
_version_file = os.path.join(_here, '..', 'VERSION')
try:
    release = open(_version_file).read().strip().lstrip('v')
except FileNotFoundError:
    release = 'dev'

version = '.'.join(release.split('.')[:2])  # e.g. "0.15" from "0.15.3"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autosectionlabel',
    'sphinx_design',
    'myst_parser',
    'sphinx_tabs.tabs',
    'custom_markdown_builder',
    'sphinx_multiversion',
]

templates_path = ['_templates', 'source/_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- sphinx-multiversion -----------------------------------------------------
# Tags to build: set via the SMV_TAG_WHITELIST env var by the CI helper
# script (docs/select_versions.py).  Falls back to matching all semver tags
# so local builds still work without running the helper first.
smv_tag_whitelist = os.environ.get('SMV_TAG_WHITELIST', r'^v\d+\.\d+\.\d+$')

# Always build docs from main as the "dev" version.
smv_branch_whitelist = r'^main$'

# Only consider the upstream remote.
smv_remote_whitelist = r'^origin$'

# Pattern that identifies a ref as a "released" (non-prerelease) version.
smv_released_pattern = r'^v\d+\.\d+\.\d+$'

# The version shown when visitors arrive without an explicit version in the URL.
smv_latest_version = 'main'

# Rebuild all versions together rather than just the latest.
smv_rebuild_tags = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
import sphinx_rtd_theme

intersphinx_mapping = {
    'rtd': ('https://docs.readthedocs.io/en/stable/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}

html_theme = "sphinx_rtd_theme"

# Inject the version switcher into the sidebar.
html_sidebars = {
    '**': [
        'versions.html',
        'globaltoc.html',
        'relations.html',
        'sourcelink.html',
        'searchbox.html',
    ],
}

html_static_path = ['source/_static']
html_css_files = [
    'custom.css',
]

html_last_updated_fmt = "%B %d, %Y"  # Example: January 30, 2025

def setup(app):
    app.add_css_file('custom.css')
    app.set_translator("markdown", CustomMarkdownTranslator)
    #app.add_builder(MarkdownBuilder)
