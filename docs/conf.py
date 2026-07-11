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

# Ensure sphinx-immaterial registers domain synopses before env init.
from sphinx.domains.python import PythonDomain
import sphinx.domains.std

PythonDomain.initial_data.setdefault("synopses", {})
sphinx.domains.std.StandardDomain.initial_data.setdefault("synopses", {})
import sphinx_immaterial.apidoc.python.synopses  # noqa: F401
import sphinx_immaterial.apidoc.generic_synopses  # noqa: F401

project = 'Lakeflow Framework'
copyright = '2026, Databricks'
author = 'Erik Seefeld, Haille Woldegebriel'

# Site title in the header / <title> — project name only (no version / "documentation").
html_title = project

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
    'sphinx_copybutton',
    'custom_markdown_builder',
    "sphinxcontrib.spelling",
]

autosectionlabel_prefix_document = True

# MyST — task-list checkboxes (Quick Start prerequisites) and fenced directives
myst_enable_extensions = [
    "colon_fence",
    "tasklist",
]
myst_enable_checkboxes = True

templates_path = ['_templates', 'source/_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Code blocks: line numbers in a Cursor/VS Code-style gutter (table layout).
html_codeblock_linenos_style = 'table'

# Copy button — WAF-style command snippets only (not dark spec/code panels)
copybutton_selector = "div.lf-command-block div.highlight pre"
copybutton_prompt_is_regexp = True
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,6}\.\.\. | {5,8}: "
copybutton_only_copy_prompt_lines = False
copybutton_remove_prompts = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

intersphinx_mapping = {
    'rtd': ('https://docs.readthedocs.io/en/stable/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}

html_theme = "sphinx_immaterial"
html_baseurl = "https://databricks-solutions.github.io/lakeflow_framework/"
html_logo = "source/_static/lff-logo.png"
html_favicon = "source/_static/lff-logo.png"

html_theme_options = {
    "site_url": html_baseurl,
    "repo_url": "https://github.com/databricks-solutions/lakeflow_framework",
    "repo_name": "lakeflow_framework",
    "icon": {
        "repo": "fontawesome/brands/github",
    },
    "features": [
        "navigation.instant",
        "navigation.top",
        "navigation.tabs",
        "navigation.tabs.sticky",
        "toc.integrate",
        "toc.follow",
        "search.suggest",
        "content.code.copy",
    ],
    "version_dropdown": True,
    # Parent of each version folder (mike default). Plain "versions.json"
    # resolves inside the version dir and 404s in multiversion layouts.
    "version_json": "../versions.json",
    "palette": [
        {
            "media": "(prefers-color-scheme: light)",
            "scheme": "default",
            "primary": "red",
            "accent": "blue-grey",
            "toggle": {
                "icon": "material/brightness-7",
                "name": "Switch to dark mode",
            },
        },
        {
            "media": "(prefers-color-scheme: dark)",
            "scheme": "slate",
            "primary": "red",
            "accent": "blue-grey",
            "toggle": {
                "icon": "material/brightness-4",
                "name": "Switch to light mode",
            },
        },
    ],
    "font": {
        "text": "Roboto",
        "code": "Roboto Mono",
    },
}

html_static_path = ['source/_static']
html_css_files = [
    'databricks-theme.css',
    'custom.css',
]

# Suppress generic Sphinx "Last updated" text.
html_last_updated_fmt = None

html_context = {
    "docs_current_version": os.environ.get("DOCS_CURRENT_VERSION", "current"),
}


def _patch_landing_nav(app, pagename, templatename, context, doctree):
    """Use index.html as the Home landing page; WAF-style section nav."""
    nav = context.get("nav")
    if nav is None:
        return

    from sphinx_immaterial.nav_adapt import MkdocsNavEntry

    pathto = context["pathto"]
    master = app.config.master_doc
    home_url = pathto(master)
    is_home = pagename == master

    # Section index pages: non-selectable sidebar title, tab lands on first child.
    # Features is a real hub landing (cards + nested groups), so it is not
    # caption-only — the Features tab should open features.html.
    section_index_pages = frozenset({
        "deploy_framework",
        "build_pipeline_bundle",
        "dataflow_spec_reference",
        "contributor",
    })

    def _first_leaf(entry):
        current = entry
        while current.children:
            current = current.children[0]
        return current

    def _docname_from_url(url):
        if not url or url == "#":
            return None
        path = url.split("#", 1)[0]
        if path.endswith(".html"):
            return path[:-5]
        return path

    def apply_section_captions(entries):
        for entry in entries:
            if entry.children:
                apply_section_captions(entry.children)
            docname = _docname_from_url(entry.url)
            if docname in section_index_pages and entry.children:
                leaf = _first_leaf(entry)
                if leaf.url:
                    entry.caption_only = True
                    entry.url = leaf.url

    apply_section_captions(nav)

    def rewrite_home_urls(entries):
        for entry in entries:
            if entry.url:
                path = entry.url.split("#", 1)[0]
                if path == "home.html" or path.endswith("/home.html"):
                    fragment = entry.url[len(path):]
                    entry.url = home_url + fragment
            rewrite_home_urls(entry.children)

    rewrite_home_urls(nav)

    nav[:] = [
        entry
        for entry in nav
        if not (entry.url and entry.url.split("#", 1)[0] == home_url and "Home" in entry.title)
    ]

    nav.insert(
        0,
        MkdocsNavEntry(
            title_text="Home",
            url=home_url,
            children=[],
            active=is_home,
            current=is_home,
            active_or_section_within_active=is_home,
            caption_only=False,
        ),
    )

    if is_home:
        for entry in nav[1:]:
            entry.active = False
            entry.current = False
            entry.active_or_section_within_active = False

        page = context.get("page")
        if page is not None:
            if "hide" not in page["meta"]:
                page["meta"]["hide"] = []
            page["meta"]["hide"].append("navigation")
            page["meta"]["hide"].append("toc")

    context["nav"] = nav


def _enable_codeblock_linenos(app, doctree):
    """Show line numbers on syntax-highlighted code blocks (except command snippets)."""
    from docutils import nodes

    for node in doctree.findall(nodes.literal_block):
        classes = list(node.get('classes', []))
        if 'lf-command-block' in classes:
            continue
        if node.rawsource == node.astext():
            node['linenos'] = True


def _tag_command_blocks(app, doctree):
    """Quick Start console fences → light WAF-style command blocks with copy button."""
    from docutils import nodes

    if app.env.docname != 'quick_start':
        return

    for node in doctree.findall(nodes.literal_block):
        language = node.get('language', '')
        if language not in ('console', 'bash', 'shell', 'text', ''):
            continue
        classes = list(node.get('classes', []))
        if 'lf-command-block' not in classes:
            classes.append('lf-command-block')
            node['classes'] = classes
        node.attributes.pop('linenos', None)


def _table_column_count(table) -> int:
    from docutils import nodes

    for tgroup in table.findall(nodes.tgroup):
        cols = tgroup.get('cols')
        if cols:
            return int(cols)
    return 0


def _is_page_metadata_table(table) -> bool:
    """Feature-page metadata strip: 2 cols, Applies To / Configuration Scope rows."""
    from docutils import nodes

    if _table_column_count(table) != 2:
        return False

    rows = list(table.findall(nodes.row))
    if not rows:
        return False

    entries = list(rows[0].findall(nodes.entry))
    if not entries:
        return False

    first_cell = entries[0].astext()
    return (
        'Applies To' in first_cell
        or 'Configuration Scope' in first_cell
        or 'Databricks Docs' in first_cell
    )


def _mark_content_tables(app, doctree, docname=None):
    """Tag body list-tables for theme CSS (excludes h1 metadata strips)."""
    from docutils import nodes

    for table in doctree.findall(nodes.table):
        if _is_page_metadata_table(table):
            continue

        classes = list(table.get('classes', []))
        if 'lf-content-table' not in classes:
            classes.append('lf-content-table')
        if 'data' not in classes:
            classes.append('data')

        col_count = _table_column_count(table)
        col_class = f'lf-table-cols-{col_count}'
        if 2 <= col_count <= 6 and col_class not in classes:
            classes.append(col_class)

        table['classes'] = classes


def setup(app):
    app.set_translator("markdown", CustomMarkdownTranslator)

    def _init_domain_synopses(app):
        for domain_name in ("py", "std"):
            domain = app.env.get_domain(domain_name)
            if "synopses" not in domain.data:
                domain.data["synopses"] = {}

    app.connect("builder-inited", _init_domain_synopses)
    app.connect("doctree-read", _tag_command_blocks)
    app.connect("doctree-read", _enable_codeblock_linenos)
    app.connect("doctree-read", _mark_content_tables)
    app.connect("html-page-context", _patch_landing_nav, priority=999)
    #app.add_builder(MarkdownBuilder)
