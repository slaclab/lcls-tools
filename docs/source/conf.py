# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "../../../")))
from lcls_tools.common.devices.magnet import *
from lcls_tools.common.devices.device import *
from lcls_tools.common.devices.screen import *
from lcls_tools.common.image_processing.image import *

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "lcls-tools"
copyright = "2023, Nicole Neveu, Lisa Zacarias, Chris Garnier, Matt King"
author = "Nicole Neveu, Lisa Zacarias, Chris Garnier, Matt King"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autodoc"]
autoclass_content = "both"
autodoc_inherit_docstrings = False
templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]
