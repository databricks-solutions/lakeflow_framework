# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import json
import os
import sys
sys.path.append(os.path.abspath("."))  # Ensure the script is discoverable
from custom_markdown_builder import CustomMarkdownTranslator

project = 'Lakeflow Framework'
copyright = '2025, Databricks'
author = 'Erik Seefeld, Haille Woldegebriel'

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
    "sphinxcontrib.spelling",
]

autosectionlabel_prefix_document = True

templates_path = ['_templates', 'source/_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

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


def _load_versions() -> list[dict[str, str]]:
    versions_file = os.environ.get("DOCS_VERSIONS_FILE")
    if not versions_file:
        return [{"name": "current", "url": "../current/index.html", "is_latest": True}]

    try:
        with open(versions_file, encoding="utf-8") as f:
            versions = json.load(f)
    except FileNotFoundError:
        return [{"name": "current", "url": "../current/index.html", "is_latest": True}]

    # For per-version pages, switch from site-root links (e.g. "v1.2.3/") to
    # sibling paths (e.g. "../v1.2.3/"), which work under GitHub project pages.
    adapted = []
    for item in versions:
        adapted.append(
            {
                "name": item["name"],
                "url": f"../{item['name']}/index.html",
                "is_latest": item.get("is_latest", False),
            }
        )
    return adapted


html_context = {
    "docs_current_version": os.environ.get("DOCS_CURRENT_VERSION", "current"),
    "docs_versions": _load_versions(),
}

def setup(app):
    app.add_css_file('custom.css')
    app.set_translator("markdown", CustomMarkdownTranslator)
    #app.add_builder(MarkdownBuilder)
