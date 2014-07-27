"""
Provides _compare_digest method, which is a safe comparing to prevent timing
attacks for the hmac module.
"""
import py
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from pypy.interpreter.error import OperationError

cwd = py.path.local(__file__).dirpath()
eci = ExternalCompilationInfo(
    includes=[cwd.join('tscmp.h')],
    separate_module_files=[cwd.join('tscmp.c')],
    export_symbols=['pypy_tscmp'])

def llexternal(*args, **kwargs):
    kwargs.setdefault('compilation_info', eci)
    kwargs.setdefault('sandboxsafe', True)
    return rffi.llexternal(*args, **kwargs)

pypy_tscmp = llexternal('pypy_tscmp', [rffi.CCHARP, rffi.CCHARP, rffi.LONG, rffi.LONG], rffi.INT)

def compare_digest(space, w_a, w_b):
    if space.isinstance_w(w_a, space.w_unicode) and space.isinstance_w(w_b, space.w_unicode):
        try:
            a_value = space.call_method(w_a, "encode", space.wrap("ascii"))
            b_value = space.call_method(w_b, "encode", space.wrap("ascii"))
            return compare_digest_buffer(space, a_value, b_value)
        except OperationError as e:
            if not e.match(space, space.w_UnicodeEncodeError):
                raise
            raise OperationError(space.w_TypeError,
                    space.wrap("comparing strings with non-ASCII characters is not supported"))
    else:
        return compare_digest_buffer(space, w_a, w_b)

def compare_digest_buffer(space, w_a, w_b):
    a = space.bufferstr_w(w_a)
    b = space.bufferstr_w(w_b)
    with rffi.scoped_nonmovingbuffer(a) as a_buffer:
        with rffi.scoped_nonmovingbuffer(b) as b_buffer:
            return space.wrap(pypy_tscmp(a_buffer, b_buffer, len(a), len(b)))
