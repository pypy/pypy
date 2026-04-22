import os
import unittest
from test import support
from test.support import import_helper


# skip tests if _ctypes was not built
ctypes = import_helper.import_module('ctypes')
ctypes_symbols = dir(ctypes)

def need_symbol(name):
    return unittest.skipUnless(name in ctypes_symbols,
                               '{!r} is required'.format(name))

# added for PyPy: skip longdouble FFI tests if not supported
def _longdouble_ffi_supported():
    """Return True if c_longdouble is fully supported as an FFI call type."""
    try:
        from _ctypes.basics import _shape_to_ffi_type
        _shape_to_ffi_type('g')
        return True
    except (ImportError, NotImplementedError, AssertionError, KeyError):
        return False

need_longdouble = unittest.skipUnless(
    'c_longdouble' in ctypes_symbols and _longdouble_ffi_supported(),
    'c_longdouble FFI calls not supported'
)

def load_tests(*args):
    return support.load_package_tests(os.path.dirname(__file__), *args)

def xfail(method):
    """
    Poor's man xfail: remove it when all the failures have been fixed
    """
    def new_method(self, *args, **kwds):
        try:
            method(self, *args, **kwds)
        except:
            pass
        else:
            self.assertTrue(False, "DID NOT RAISE")
    return new_method
