# -*- coding: utf-8 -*-
#
# PyPy documentation build configuration file, created by
# sphinx-quickstart on Mon Mar 14 10:44:41 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('../../'))


# -- Read The Docs theme config ------------------------------------------------

# on_rtd is whether we are on readthedocs.org, this line of code grabbed from docs.readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if on_rtd:  # only import and set the theme if we're building docs locally
    html_theme = "sphinx_rtd_theme"
else:
    try:
        import sphinx_rtd_theme
        html_theme = 'sphinx_rtd_theme'
        html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
    except ImportError:
        print('sphinx_rtd_theme is not installed')
        html_theme = 'default'

# Set canonical URL from the Read the Docs Domain
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")
html_context = {}

# Tell Jinja2 templates the build is running on Read the Docs
if os.environ.get("READTHEDOCS", "") == "True":
    html_context["READTHEDOCS"] = True

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.doctest',
              'sphinx.ext.extlinks',
              'sphinx.ext.intersphinx',
              'sphinx.ext.todo',
              'sphinx.ext.ifconfig',
              'sphinx.ext.graphviz',
              'sphinx_issues',
              'pypyconfig',
              # 'sphinx_affiliates',
             ]

# Canonical URL (including the '/') so searching from rpython docs finds these
affiliate_options = {
    'canonical_url': "https://doc.pypy.org/en/latest/"
}

# Other sites to add to the search of this site
sphinx_affiliates = [
    'https://rpython.readthedocs.io/en/latest/affiliate_searchindex.js',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'PyPy'
copyright = u'2024, The PyPy Project'

# For sphinx_issues extension v1.2.0
issues_github_path = "pypy/pypy"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#

# Make sure to keep this in sync with:
#    module/sys/version.py
#    module/cpyext/include/patchlevel.h
#
# The short X.Y version.
version = '7.3'
# The full version, including alpha/beta/rc tags.
release = '7.3.19'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
#html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = 'PyPy documentation'

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
html_use_modindex = False

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'PyPydoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
#latex_documents = [
#  ('temp_index', 'PyPy.tex', u'PyPy Documentation',
#   u'The PyPy Project', 'manual'),
#]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = False


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'python': ('http://docs.python.org/2.7', None),
                       'rpython': ('http://rpython.readthedocs.org/en/latest/', None),
                       'cffi': ('https://cffi.readthedocs.io/en/latest/', None),
                      }

# -- Options for manpage output-------------------------------------------------

man_pages = [
  ('man/pypy3.1', 'pypy3',
   u'fast, compliant alternative implementation of the Python 3 language',
   u'The PyPy Project', 1)
]

extlinks = {'source': ('https://github.com/pypy/pypy/blob/main/%s', '')}
