"""
This will create the _testmultiphase c-extension module. Unlike _testcapi, the
extension cannot be wrapped with a _testmultiphase.py module since test.importlib
explicitly does a c-extension import
"""


import imp
import os
import shutil

try:
    import cpyext
except ImportError:
    raise RuntimeError("must have cpyext")
import _pypy_testcapi
cfile = '_testmultiphase.c'
thisdir = os.path.dirname(__file__)
output_dir = _pypy_testcapi.get_hashed_dir(os.path.join(thisdir, cfile))
try:
    fp, filename, description = imp.find_module('_testmultiphase', path=[thisdir])
    with fp:
        imp.load_module('_testmultiphase', fp, filename, description)
except ImportError:
    _pypy_testcapi.compile_shared('_testmultiphase.c', '_testmultiphase', thisdir)
