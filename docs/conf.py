# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import json
import os
import subprocess
import sys
from datetime import datetime
sys.path.append(os.path.abspath("."))  # Ensure the script is discoverable
from custom_markdown_builder import CustomMarkdownTranslator

project = 'Lakeflow Framework'
copyright = '2026, Databricks'
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

# Suppress generic Sphinx "Last updated" text; custom version metadata is shown.
html_last_updated_fmt = None


def _head_release_date() -> str:
    try:
        return subprocess.run(
            ["git", "log", "-1", "--format=%cs"],
            cwd=_here,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return ""


def _format_release_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%B %d, %Y")
    except ValueError:
        return date_str


def _fallback_versions() -> list[dict[str, str]]:
    head_release_date = _head_release_date()
    return [
        {
            "name": "current",
            "display_version": release,
            "url": "../current/index.html",
            "is_latest": True,
            "status": "current",
            "release_date": head_release_date,
            "release_date_human": _format_release_date(head_release_date),
        }
    ]


def _load_versions() -> list[dict[str, str]]:
    versions_file = os.environ.get("DOCS_VERSIONS_FILE")
    if not versions_file:
        default_versions_file = os.path.join(_here, "build", "html", "versions.json")
        if os.path.exists(default_versions_file):
            versions_file = default_versions_file

    if not versions_file:
        return _fallback_versions()

    try:
        with open(versions_file, encoding="utf-8") as f:
            versions = json.load(f)
    except FileNotFoundError:
        return _fallback_versions()

    # For per-version pages, switch from site-root links (e.g. "v1.2.3/") to
    # sibling paths (e.g. "../v1.2.3/"), which work under GitHub project pages.
    adapted = []
    for item in versions:
        adapted.append(
            {
                "name": item["name"],
                "display_version": item.get("display_version", item["name"].lstrip("v")),
                "url": f"../{item['name']}/index.html",
                "is_latest": item.get("is_latest", False),
                "status": item.get("status", "release"),
                "release_date": item.get("release_date", ""),
                "release_date_human": _format_release_date(item.get("release_date", "")),
            }
        )
    return adapted


def _current_version_meta(versions: list[dict[str, str]], current: str) -> dict[str, str]:
    for item in versions:
        if item["name"] == current:
            return item
    return {
        "name": current,
        "display_version": current.lstrip("v"),
        "url": f"../{current}/index.html",
        "is_latest": current == "current",
        "status": "current" if current == "current" else "release",
        "release_date": "",
        "release_date_human": "",
    }


_docs_current_version = os.environ.get("DOCS_CURRENT_VERSION", "current")
_docs_versions = _load_versions()

html_context = {
    "docs_current_version": _docs_current_version,
    "docs_versions": _docs_versions,
    "docs_current_version_meta": _current_version_meta(_docs_versions, _docs_current_version),
}

def setup(app):
    app.set_translator("markdown", CustomMarkdownTranslator)
    app.add_css_file('custom.css')
    app.add_css_file('custom.css')
    #app.add_builder(MarkdownBuilder)
