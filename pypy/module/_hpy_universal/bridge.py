from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.module._hpy_universal import llapi
from pypy.module._hpy_universal.apiset import APISet

# =============== HPy-RPython BRIDGE ===============
#
# Semi-complicate (but hopefully not too magic!) machinery to make it possible
# to call RPython functions from C in a way which works both before and after
# translation:
#
#   - during tests, the code runs on top of CPython, so we need ll2ctypes
#     callbacks: in bridge.h, a set of macros turn e.g. a call to foo() into
#     hpy_get_bridge()->foo()
#
#   - after translations, we want a direct call to the generated C functions


llapi.cts.parse_source("""
typedef struct {
    void * hpy_err_Occurred_rpy;
    void * hpy_err_SetString;
} _HPyBridge;
""")

_HPyBridge = llapi.cts.gettype('_HPyBridge')
hpy_get_bridge = rffi.llexternal('hpy_get_bridge', [], lltype.Ptr(_HPyBridge),
                                 compilation_info=llapi.eci, _nowrapper=True)


BRIDGE = APISet(llapi.cts, prefix='^hpy_')
