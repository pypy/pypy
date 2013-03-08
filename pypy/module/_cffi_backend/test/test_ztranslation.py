from pypy.objspace.fake.checkmodule import checkmodule

# side-effect: FORMAT_LONGDOUBLE must be built before test_checkmodule()
from pypy.module._cffi_backend import misc


def test_checkmodule():
    checkmodule('_cffi_backend')
