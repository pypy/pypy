from pypy.objspace.fake.checkmodule import checkmodule
from pypy.module._cffi_backend import ctypeptr
from rpython.rtyper.lltypesystem import lltype, rffi

# side-effect: FORMAT_LONGDOUBLE must be built before test_checkmodule()
from pypy.module._cffi_backend import misc

def test_checkmodule():
    # W_CTypePointer.prepare_file() is not working without translating
    # the _io module too
    def dummy_prepare_file(self, w_ob):
        return lltype.nullptr(rffi.CCHARP.TO)
    old = ctypeptr.W_CTypePointer.prepare_file
    try:
        ctypeptr.W_CTypePointer.prepare_file = dummy_prepare_file
        #
        checkmodule('_cffi_backend')
        #
    finally:
        ctypeptr.W_CTypePointer.prepare_file = old
