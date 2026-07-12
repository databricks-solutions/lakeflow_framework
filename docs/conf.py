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

# sphinx-immaterial ``.. task-list::`` (RST) — interactive like MyST checkboxes
clickable_checkbox = True

templates_path = ['_templates', 'source/_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Code blocks: when :linenos: is set, use Cursor/VS Code-style gutter (table layout).
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
    # Architecture / Deploy / Samples / Features / Build / Contributors / Get Started
    # are real top-level hub links.
    section_index_pages = frozenset({
        "build/spec-reference/index",
        "build/patterns/index",
        "deploy/framework/index",
        "features/metadata/index",
        "features/authoring/index",
        "features/configuration/index",
        "features/sources-targets/index",
        "features/platform/index",
        "features/python/index",
        "features/data-quality/index",
        "features/environments/index",
        "features/migrations/index",
    })

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
                first_child = entry.children[0]
                if first_child.url:
                    entry.caption_only = True
                    entry.url = first_child.url

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


def _flatten_mermaid_diagrams(app, doctree):
    """Emit plain diagram source for md-mermaid (no Pygments wrapper inside <pre>)."""
    from docutils import nodes

    from sphinx_immaterial.mermaid_diagrams import mermaid_node

    for diagram in doctree.findall(mermaid_node):
        content = diagram.get('content', '')
        if not content:
            for child in diagram.children:
                if isinstance(child, nodes.literal_block):
                    content = child.astext()
                    break
        diagram.children[:] = [nodes.Text(content)]


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


def _upgrade_mermaid_dist(app, env=None):
    """Replace theme mermaid (11.12) with vendored 11.16 for treeView-beta support."""
    from pathlib import Path
    import shutil

    import sphinx_immaterial
    from sphinx.builders.html import StandaloneHTMLBuilder

    if not isinstance(app.builder, StandaloneHTMLBuilder):
        return

    if env is None:
        env = app.env
    if not getattr(env, "sphinx_immaterial_copy_mermaid_dist", False):
        return

    vendor = Path(_here) / "source" / "_static" / "vendor" / "mermaid.min.js"
    if not vendor.is_file():
        return

    dst_dir = Path(app.outdir) / "_static" / "mermaid"
    dst = dst_dir / "mermaid.min.js"

    # Theme copy runs on env-check-consistency (skipped on no-op incremental
    # builds). Ensure the dist exists before overriding with the vendored build.
    if not dst.is_file():
        theme_mermaid = Path(sphinx_immaterial.__file__).parent / "bundles" / "mermaid"
        if theme_mermaid.is_dir():
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(theme_mermaid, dst_dir, dirs_exist_ok=True)

    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(vendor, dst)


def _upgrade_mermaid_dist_on_finish(app, exception):
    if exception is not None:
        return
    _upgrade_mermaid_dist(app)


def setup(app):
    app.set_translator("markdown", CustomMarkdownTranslator)

    def _init_domain_synopses(app):
        for domain_name in ("py", "std"):
            domain = app.env.get_domain(domain_name)
            if "synopses" not in domain.data:
                domain.data["synopses"] = {}

    app.connect("builder-inited", _init_domain_synopses)
    app.connect("doctree-read", _flatten_mermaid_diagrams)
    app.connect("doctree-read", _mark_content_tables)
    app.connect("env-check-consistency", _upgrade_mermaid_dist, priority=1000)
    app.connect("build-finished", _upgrade_mermaid_dist_on_finish, priority=1000)
    app.connect("html-page-context", _patch_landing_nav, priority=999)
    #app.add_builder(MarkdownBuilder)
