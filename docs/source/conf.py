import sys
import os
import re
import inspect

from docutils import nodes

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
    'navbar_site_name': 'guv docs',

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


def get_field(doc: str, name: str):
    """Parse ReST field from document

    :param str doc: string of whole document
    :param name: name of field excluding the surrounding `:`
    :return: value of field
    :rtype: str
    """
    match = re.search(':{}: (.*)$'.format(name), doc, re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1).strip()


def autodoc_process_signature(app, what, name, obj, options, signature, return_annotation):
    doc = str(obj.__doc__)
    otype = str(type(obj))
    msg_meth = '{what:11} {otype:23} {name:50} -> {rt}'
    msg_class = '{what:11} {otype:23} {name:50} {sig}'

    rt = None
    if what == 'method' and not name.endswith('__init__'):
        # annotate return type for methods (excluding __init__)
        if 'rtype' in doc:
            rt = get_field(doc, 'rtype')
            print(msg_meth.format(**locals()))
        elif obj.__doc__ is not None:
            # assume methods with a docstring but undocumented rtype return `None`
            rt = 'None'
            print(msg_meth.format(**locals()))
        else:
            # no docstring defined
            rt = '?'
            print(msg_meth.format(**locals()))
    elif type(obj) is property:
        # annotate return type for properties
        if 'rtype' in doc:
            rt = get_field(doc, 'rtype')
            print(msg_meth.format(**locals()))
        else:
            # no docstring defined
            rt = '?'
            print(msg_meth.format(**locals()))
    elif what == 'class':
        # modify the signature of classes to look like Python code
        # check base classes
        sig_items = []
        for cls in obj.__bases__:
            if cls.__module__ == 'builtins':
                name = cls.__name__
            else:
                name = '{}.{}'.format(cls.__module__, cls.__name__)

            if name in ['object']:
                # exclude 'object'
                continue

            sig_items.append(name)

        # check metaclass
        try:
            definition = inspect.getsourcelines(obj)[0][0].strip()
            if 'metaclass' in definition:
                cls = type(obj)
                name = '{}.{}'.format(cls.__module__, cls.__name__)
                sig_items.append('metaclass={}'.format(name))

        except OSError:
            pass

        sig_str = ', '.join(sig_items)
        sig = '({})'.format(sig_str) if sig_str else ''

        print(msg_class.format(**locals()))

        return sig, None
    else:
        rt = 'skip'
        print(msg_meth.format(**locals()))

    if rt and rt not in ['?', 'skip']:
        return signature, rt


def autodoc_process_docstring(app, what, name, obj, options, lines):
    s_before = None
    s_after = None
    if type(obj) == property:
        s_before = ':annotation:`@property`\n'
        # this as a @property
    elif what == 'method' and hasattr(obj, '__isabstractmethod__') and obj.__isabstractmethod__:
        # this is an @abstractmethod
        s_before = ':annotation:`@abstractmethod`\n'
    elif what == 'class' and tuple in obj.__bases__ and hasattr(obj, '_fields'):
        # this is a namedtuple
        lines[0] = '**namedtuple** :namedtuple:`{}`'.format(lines[0])

    if s_before:
        for line in reversed(s_before.split('\n')):
            lines.insert(0, line)
    if s_after:
        for line in s_after.split('\n'):
            lines.append(line)


def autodoc_skip_member(app, what, name, obj, sphinx_skip, options):
    skip = False
    doc = obj.__doc__
    if type(obj) is property:
        if doc and re.match('Alias for field number \d+$', doc):
            # this is a namedtuple property
            skip = True

    return sphinx_skip or skip


def generic_span_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    :param name: role name used in the document
    :param rawtext: entire markup snippet, with role
    :param text: text marked with the role
    :param lineno: line number where rawtext appears in the input
    :param inliner: inliner instance that called us
    :param options: directive options for customization
    :param content: directive content for customization
    :return: list, list
    :rtype: list, list
    """
    node = nodes.inline(rawtext, text)
    node['classes'] = [name]
    return [node], []


def setup(app):
    # register custom ReST roles
    app.add_role('annotation', generic_span_role)
    app.add_role('namedtuple', generic_span_role)

    # connect methods to events
    app.connect('autodoc-process-signature', autodoc_process_signature)
    app.connect('autodoc-process-docstring', autodoc_process_docstring)
    app.connect('autodoc-skip-member', autodoc_skip_member)
