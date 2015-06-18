from pypy.objspace.fake.checkmodule import checkmodule
from pypy.module._cffi_backend import ctypeptr
from rpython.rtyper.lltypesystem import lltype, rffi

# side-effect: FORMAT_LONGDOUBLE must be built before test_checkmodule()
from pypy.module._cffi_backend import misc
from pypy.module._cffi_backend import cffi1_module


def test_checkmodule():
    # prepare_file_argument() is not working without translating the _file
    # module too
    def dummy_prepare_file_argument(space, fileobj):
        # call load_cffi1_module() too, from a random place like here
        cffi1_module.load_cffi1_module(space, "foo", "foo", 42)
        return lltype.nullptr(rffi.CCHARP.TO)
    old = ctypeptr.prepare_file_argument
    try:
        ctypeptr.prepare_file_argument = dummy_prepare_file_argument
        #
        checkmodule('_cffi_backend')
        #
    finally:
        ctypeptr.prepare_file_argument = old
