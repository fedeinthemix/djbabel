# SPDX-FileCopyrightText: NONE
#
# SPDX-License-Identifier: CC0-1.0

import sys
from pathlib import Path

sys.path.insert(0, str(Path('..', 'src').resolve()))

# Work around nixpkgs bug
# https://github.com/sphinx-doc/sphinx/issues/3451
import os
os.environ.pop('SOURCE_DATE_EPOCH', None)

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'djbabel'
copyright = "2025, Federico Beffa"
author = 'Federico Beffa'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    # https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings
    'sphinx.ext.napoleon',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
# html_static_path = ['_static']
html_show_sphinx = False
html_show_sourcelink = False
