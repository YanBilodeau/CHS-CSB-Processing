import sys
from pathlib import Path

# -- Path setup --------------------------------------------------------------
sys.path.insert(0, str(Path("../../src").resolve()))

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "CHS-CSB-Processing"
copyright = "2024, Yan Bilodeau"
author = "Yan Bilodeau"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",  # Permet de générer la documentation à partir des docstrings
    "sphinx.ext.viewcode",  # Permet de générer des liens vers le code source
    "sphinx.ext.todo",  # Permet de générer des listes de tâches
    "sphinx.ext.githubpages",  # Permet de générer des liens vers les pages GitHub
    "sphinx.ext.intersphinx",  # Permet de générer des liens vers d'autres documentations
    "sphinx.ext.graphviz",  # Permet de générer des graphiques
    "sphinx.ext.autosummary",  # Permet de générer des résumés de documentation
    "sphinx.ext.inheritance_diagram",  # Permet de générer des diagrammes d'héritage
    "sphinx_click",
]

templates_path = ["_templates"]
exclude_patterns = []

language = "fr"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_css_files = [
    "custom.css",
]

html_js_files = [
    "https://code.jquery.com/jquery-3.6.0.min.js",
    # "_static/js/jquery.min.js",
]

# -- Options for autodoc -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "inherited-members": False,
    "member-order": "groupwise",
    # "special-members": "__init__",
    "inheritance-diagram": True,
    "private-members": True,
    "exclude-members": "_abc_impl, model_computed_fields, model_config, model_fields, _generate_next_value_",
}
