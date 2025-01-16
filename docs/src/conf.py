# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
from grana.version import __version__

# version_switch_json_url = "https://grana.readthedocs.io/en/latest/_static/version-switch.json"
version_switch_json_url = "_static/version-switch.json"
# Effective check of the RTD env
version_match = os.environ.get("READTHEDOCS_VERSION")
if version_match == "latest":
    version_match = f"v{__version__}"

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "grana"
copyright = "2025, Artem Novikov"
author = "Artem Novikov"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx_copybutton",
]

templates_path = ["_templates"]
exclude_patterns = ["Thumbs.db", ".DS_Store"]

# -- Sitemap -----------------------------------------------------------------

# ReadTheDocs has its own way of generating sitemaps, etc.
if not os.environ.get("READTHEDOCS"):
    extensions += ["sphinx_sitemap"]
    html_baseurl = os.environ.get("SITEMAP_URL_BASE", "http://127.0.0.1:8000/")
    sitemap_locales = [None]
    sitemap_url_scheme = "{link}"

myst_enable_extensions = ["colon_fence", "linkify", "substitution"]
myst_heading_anchors = 4
myst_substitutions = {"rtd": "[Read the Docs](https://readthedocs.org/)"}

language = "en"

# -- Sphinx-copybutton options ---------------------------------------------
# Exclude copy button from appearing over notebook cell numbers by using :not()
# The default copybutton selector is `div.highlight pre`
# https://github.com/executablebooks/sphinx-copybutton/blob/master/sphinx_copybutton/__init__.py#L82
copybutton_selector = ":not(.prompt) > div.highlight pre"
copybutton_prompt_text = "$ "

html_theme = "pydata_sphinx_theme"
# html_logo = "_static/logo.svg"
# html_favicon = "_static/logo.svg"
html_sourcelink_suffix = ""
html_last_updated_fmt = ""

# Define the version we use for matching in the version switcher.
html_static_path = ["_static"]
# html_css_files = ["custom.css"]
html_js_files = ["pypi-fontawesome-icon.js"]
todo_include_todos = True

html_theme_options = {
    "header_links_before_dropdown": 4,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/reartnew/grana",
            "icon": "fa-brands fa-github",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/grana",
            "icon": "fa-extra fa-pypi",
        },
    ],
    "logo": {
        "text": "Grana",
        # "image_dark": "_static/logo-dark.svg",
    },
    "use_edit_page_button": True,
    "show_toc_level": 1,
    # [left, content, right] For testing that the navbar items align properly
    "navbar_align": "left",
    # "show_nav_level": 2,
    "show_version_warning_banner": True,
    "navbar_center": [
        # "version-switcher",
        "navbar-nav",
    ],
    "footer_start": ["copyright"],
    "footer_center": ["sphinx-version"],
    "secondary_sidebar_items": [
        # "page-toc",
        # "edit-this-page",
        # "sourcelink",
    ],
    # "switcher": {
    #     "json_url": version_switch_json_url,
    #     "version_match": version_match,
    # },
    "back_to_top_button": True,
}

html_context = {
    "github_user": "reartnew",
    "github_repo": "grana",
    "github_version": "main",
    "doc_path": "docs",
}
