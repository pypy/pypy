from pypy.objspace.fake.checkmodule import checkmodule

# side-effect: FORMAT_LONGDOUBLE must be built before test_checkmodule()
from pypy.module._cffi_backend import misc

import py
def test_checkmodule():
    py.test.py3k_skip('not yet supported')
    checkmodule('_cffi_backend')
