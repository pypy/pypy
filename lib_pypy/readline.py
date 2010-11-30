"""readline - Importing this module enables command line editing using
the pyrepl library.  The API is a subset of the GNU readline library.
It also contains extensions for multiline input.

Note that some of the functions present in the CPython module 'readline'
are only stubs at the moment.
"""

import __pypy__

import pyrepl.readline
__all__ = pyrepl.readline.__all__

for _name in __all__:
    globals()[_name] = __pypy__.builtinify(getattr(pyrepl.readline, _name))
