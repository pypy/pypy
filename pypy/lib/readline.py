"""readline - Importing this module enables command line editing using
the pyrepl library.  The API is a subset of the GNU readline library.
It also contains extensions for multiline input.

Note that some of the functions present in the CPython module 'readline'
are only stubs at the moment.
"""

# Note that PyPy contains also a built-in module 'readline' which will hide
# this one if compiled in.  However the built-in module is incomplete;
# don't use it.

from pyrepl.readline import *
