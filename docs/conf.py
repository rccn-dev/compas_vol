# flake8: noqa
# -*- coding: utf-8 -*-

import importlib
import inspect
import os
import sys

import sphinx_compas_theme

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

# -- Project information -----------------------------------------------------

project = "compas_vol"
copyright = (
    "2017-2021 Digital Building Technologies - ETH Zurich; "
    "2025-2026 compas_vol contributors"
)
author = "Mathias Bernhard (original), ChiaChing-Yen (COMPAS 2 fork)"
release = "0.2.0"
version = ".".join(release.split(".")[0:2])

# -- General configuration ---------------------------------------------------

root_doc = "index"
source_suffix = [".rst"]
templates_path = sphinx_compas_theme.get_autosummary_templates_path()
exclude_patterns = ["_build"]

pygments_style = "sphinx"
show_authors = True
add_module_names = True
language = "en"

# -- Extensions --------------------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "sphinx.ext.coverage",
    "sphinx.ext.linkcode",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.githubpages",
]

# compas_viewer is an optional dependency and pulls in PySide6, which cannot
# initialize on a headless docs builder. The scene module is documented from
# its docstrings instead of by import.
autodoc_mock_imports = [
    "compas_viewer",
    "matplotlib",
]

autodoc_default_options = {
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_member_order = "alphabetical"
autoclass_content = "class"


def skip(app, what, name, obj, would_skip, options):
    if name.startswith("_"):
        return True
    return would_skip


def add_theme_defaults(app, pagename, templatename, context, doctree):
    # sphinx_compas_theme's layout.html reads `theme_maxdepth`, but its
    # theme.conf never declares that option. Sphinx <7 rendered the undefined
    # value as empty; Sphinx 8 and 9 raise. Supplying it here keeps the COMPAS
    # theme usable without vendoring a patched copy of it.
    context.setdefault("theme_maxdepth", 2)


def setup(app):
    app.connect("autodoc-skip-member", skip)
    app.connect("html-page-context", add_theme_defaults)


autosummary_generate = True

# -- napoleon ----------------------------------------------------------------

napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = False
napoleon_use_rtype = False

# -- intersphinx -------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "compas": ("https://compas.dev/compas/latest/", None),
}

# -- linkcode ----------------------------------------------------------------

REPO = "https://github.com/rccn-dev/compas_vol"


def linkcode_resolve(domain, info):
    if domain != "py":
        return None
    if not info["module"] or not info["fullname"]:
        return None
    if not info["module"].split(".")[0].startswith("compas_vol"):
        return None

    try:
        module = importlib.import_module(info["module"])
    except ImportError:
        return None

    parts = info["fullname"].split(".")
    try:
        if len(parts) == 1:
            obj = getattr(module, info["fullname"])
            filename = inspect.getmodule(obj).__name__.replace(".", "/")
            lineno = inspect.getsourcelines(obj)[1]
        elif len(parts) == 2:
            obj_name, attr_name = parts
            obj = getattr(module, obj_name)
            attr = getattr(obj, attr_name)
            if not inspect.isfunction(attr):
                return None
            filename = inspect.getmodule(obj).__name__.replace(".", "/")
            lineno = inspect.getsourcelines(attr)[1]
        else:
            return None
    except (AttributeError, TypeError, OSError):
        return None

    return "{}/blob/main/src/{}.py#L{}".format(REPO, filename, lineno)


extlinks = {}

# -- HTML output -------------------------------------------------------------

html_theme = "compaspkg"
html_theme_path = sphinx_compas_theme.get_html_theme_path()

html_theme_options = {
    "package_name": "compas_vol",
    "package_title": project,
    "package_version": release,
    "package_author": "Mathias Bernhard, ChiaChing-Yen",
    "package_docs": "https://rccn-dev.github.io/compas_vol/",
    "package_repo": REPO,
    "package_old_versions_txt": "https://rccn-dev.github.io/compas_vol/doc_versions.txt",
}

html_context = {}
html_static_path = []
html_extra_path = []
html_last_updated_fmt = ""
html_copy_source = False
html_show_sourcelink = False
html_permalinks = False
html_compact_lists = True
