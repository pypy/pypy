from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib import rutf8
from pypy.interpreter.error import OperationError, oefmt
from pypy.module.hpy_universal.apiset import API
from pypy.module.hpy_universal import handles

def _maybe_utf8_to_w(space, utf8):
    # should this be a method of space?
    s = rffi.charp2str(utf8)
    try:
        length = rutf8.check_utf8(s, allow_surrogates=False)
    except rutf8.CheckError:
        raise   # XXX do something
    return space.newtext(s, length)

@API.func("HPy HPyUnicode_FromString(HPyContext ctx, const char *utf8)")
def HPyUnicode_FromString(space, ctx, utf8):
    w_obj = _maybe_utf8_to_w(space, utf8)
    return handles.new(space, w_obj)
