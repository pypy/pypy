"""readline - Importing this module enables command line editing using
the pyrepl library.  The API is a subset of the GNU readline library.
It also contains extensions for multiline input.

Note that some of the functions present in the CPython module 'readline'
are only stubs at the moment.
"""

try:
    from pyrepl.readline import *
except ImportError:
    import sys
    if sys.platform == 'win32':
        raise ModuleNotFoundError("the 'readline' module is not available on Windows"
                                  " (on either PyPy or CPython)", name="readline")
    raise
else:
    from pyrepl.readline import _setup
    _setup()

# PyPy uses a pure Python readline implementation (pyrepl) rather than
# linking against the GNU readline C library.  These version attributes
# are set to a value below 0x0600 to reflect that parse_and_bind() is a
# stub and features gated on GNU readline >= 6.0 are not available.
_READLINE_VERSION = 0x0504
_READLINE_RUNTIME_VERSION = 0x0504
_READLINE_LIBRARY_VERSION = "pyrepl"
