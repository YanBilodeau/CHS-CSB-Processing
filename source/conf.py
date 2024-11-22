from pathlib import Path
import sys

sys.path.insert(0, str(Path("../..").resolve()))

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'CHS-CSB-Processing'
copyright = '2024, Yan Bilodeau'
author = 'Yan Bilodeau'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',  # Automatically generate documentation from docstrings
    'sphinx.ext.viewcode',  # Add links to highlighted source code
    'sphinx.ext.todo',  # Support for todo items
    'sphinx.ext.coverage',  # Collect doc coverage stats
    'sphinx.ext.githubpages',  # Publish HTML docs on GitHub Pages
]

templates_path = ['_templates']
exclude_patterns = []

language = 'fr'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

html_theme_options = {
    # "sidebarwidth": 450,
    # "relbarbgcolor": "black",
    "body_min_width": "84%",
    #"stickysidebar": True,
    # "externalrefs": True,
}
