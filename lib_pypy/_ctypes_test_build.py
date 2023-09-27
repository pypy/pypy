"""
This will create the _ctypes_test c-extension module. Unlike _testcapi, the
extension cannot be wrapped with a _ctypes_test.py module since test.importlib
explicitly does a c-extension import
"""
import imp
import os

try:
    import cpyext
except ImportError:
    raise RuntimeError("must have cpyext")
import _pypy_testcapi
cfile = '_ctypes_test.c'
thisdir = os.path.dirname(__file__)
output_dir = _pypy_testcapi.get_hashed_dir(os.path.join(thisdir, cfile))
try:
    import _ctypes
except ImportError:
    pass    # obscure condition of _ctypes_test.py being imported by py.test
else:
    _ctypes.PyObj_FromPtr = None
    del _ctypes
    try:
        fp, filename, description = imp.find_module('_ctypes_test', path=[thisdir])
        with fp:
            imp.load_module('_ctypes_test', fp, filename, description)
    except ImportError:
        _pypy_testcapi.compile_shared('_ctypes_test.c', '_ctypes_test', thisdir)
