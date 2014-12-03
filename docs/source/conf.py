import sys
import os

import sphinx.ext.autodoc
import sphinx

sys.path.insert(0, os.path.abspath('../theme'))  # for Pygments Solarized style
sys.path.insert(0, os.path.abspath('../..'))

import guv

needs_sphinx = '1.2'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode'
]

# configure autodoc member grouping and ordering
sphinx.ext.autodoc.DataDocumenter.member_order = 5
sphinx.ext.autodoc.AttributeDocumenter.member_order = 6
sphinx.ext.autodoc.InstanceAttributeDocumenter.member_order = 7
autodoc_member_order = 'groupwise'
autodoc_default_flags = ['members', 'show-inheritance']

intersphinx_mapping = {'http://docs.python.org/3.4': None}

templates_path = ['_templates']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'guv'
copyright = '2014, V G'

# The short X.Y version.
version = guv.__version__
# The full version, including alpha/beta/rc tags.
release = guv.__version__

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# default_role = None

pygments_style = 'pygments_solarized_light.LightStyle'

# A list of ignored prefixes for module index sorting.
# modindex_common_prefix = []

# -- Options for HTML output ----------------------------------------------

html_context = {'sphinx_versioninfo': sphinx.version_info}

html_theme_path = ['../theme']
html_theme = 'bootstrap'
html_theme_options = {
    # Tab name for entire site. (Default: "Site")
    'navbar_site_name': 'guv Docs',

    # Render the next and previous page links in navbar. (Default: true)
    'navbar_sidebarrel': False,

    # Render the current pages TOC in the navbar. (Default: true)
    # 'navbar_pagenav': True,

    # Tab name for the current pages TOC. (Default: "Page")
    'navbar_pagenav_name': 'Page',

    # Global TOC depth for "site" navbar tab. (Default: 1)
    # Switching to -1 shows all levels.
    'globaltoc_depth': 2,

    # Include hidden TOCs in Site navbar?
    #
    # Note: If this is "false", you cannot have mixed ``:hidden:`` and
    # non-hidden ``toctree`` directives in the same page, or else the build
    # will break.
    #
    # Values: "true" (default) or "false"
    # 'globaltoc_includehidden': "true",

    # HTML navbar class (Default: "navbar") to attach to <div> element.
    # For black navbar, do "navbar navbar-inverse"
    # 'navbar_class': "navbar",

    # Fix navigation bar to top of page?
    # Values: "true" (default) or "false"
    'navbar_fixed_top': 'true',

    # Location of link to source.
    # Options are "nav" (default), "footer" or anything else to exclude.
    'source_link_position': 'nav',

    # Bootswatch (http://bootswatch.com/) theme.
    #
    # Options are nothing with "" (default) or the name of a valid theme
    # such as "amelia" or "cosmo".
    'bootswatch_theme': 'flatly',
}

# html_static_path = ['_static']

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {}

# Output file base name for HTML help builder.
htmlhelp_basename = 'guvdoc'

