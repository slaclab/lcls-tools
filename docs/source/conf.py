# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "../../../")))
from lcls_tools.common.data_analysis.fitting_tool import *
from lcls_tools.common.devices.magnet import *
from lcls_tools.common.devices.beampath import *
from lcls_tools.common.devices.device import *
from lcls_tools.common.devices.screen import *
from lcls_tools.common.matlab2py.mat_image import *
from lcls_tools.common.matlab2py.mat_emit_scan import *
from lcls_tools.common.matlab2py.mat_corr_plot import *


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "lcls-tools"
copyright = "2023, Nicole Neveu, Lisa Zacarias, Chris Garnier, Matt King"
author = "Nicole Neveu, Lisa Zacarias, Chris Garnier, Matt King"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx_rtd_theme",
]
autoclass_content = "both"
autodoc_inherit_docstrings = False
templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
    "logo_only": False,
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "vcs_pageview_mode": "",
    "style_nav_header_background": "white",
    # Toc options
    "collapse_navigation": True,
    "sticky_navigation": True,
    "navigation_depth": 4,
    "includehidden": True,
    "titles_only": False,
}
