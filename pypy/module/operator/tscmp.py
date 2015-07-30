"""
Provides _compare_digest method, which is a safe comparing to prevent timing
attacks for the hmac module.
"""
import py

from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator import cdir
from rpython.translator.tool.cbuild import ExternalCompilationInfo

from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import BufferInterfaceNotFound

cwd = py.path.local(__file__).dirpath()
eci = ExternalCompilationInfo(
    includes=[cwd.join('tscmp.h')],
    include_dirs=[str(cwd), cdir],
    separate_module_files=[cwd.join('tscmp.c')])


def llexternal(*args, **kwargs):
    kwargs.setdefault('compilation_info', eci)
    kwargs.setdefault('sandboxsafe', True)
    return rffi.llexternal(*args, **kwargs)


pypy_tscmp = llexternal(
    'pypy_tscmp',
    [rffi.CCHARP, rffi.CCHARP, rffi.LONG, rffi.LONG],
    rffi.INT)
pypy_tscmp_wide = llexternal(
    'pypy_tscmp_wide',
    [rffi.CWCHARP, rffi.CWCHARP, rffi.LONG, rffi.LONG],
    rffi.INT)


def compare_digest(space, w_a, w_b):
    """compare_digest(a, b) -> bool

    Return 'a == b'.  This function uses an approach designed to prevent
    timing analysis, making it appropriate for cryptography.  a and b
    must both be of the same type: either str (ASCII only), or any type
    that supports the buffer protocol (e.g. bytes).

    Note: If a and b are of different lengths, or if an error occurs, a
    timing attack could theoretically reveal information about the types
    and lengths of a and b--but not their values.
    """
    if (space.isinstance_w(w_a, space.w_unicode) and
        space.isinstance_w(w_b, space.w_unicode)):
        a = space.unicode_w(w_a)
        b = space.unicode_w(w_b)
        with rffi.scoped_nonmoving_unicodebuffer(a) as a_buf:
            with rffi.scoped_nonmoving_unicodebuffer(b) as b_buf:
                result = pypy_tscmp_wide(a_buf, b_buf, len(a), len(b))
        return space.wrap(rffi.cast(lltype.Bool, result))
    return compare_digest_buffer(space, w_a, w_b)


def compare_digest_buffer(space, w_a, w_b):
    try:
        a_buf = w_a.buffer_w(space, space.BUF_SIMPLE)
        b_buf = w_b.buffer_w(space, space.BUF_SIMPLE)
    except BufferInterfaceNotFound:
        raise oefmt(space.w_TypeError,
                    "unsupported operand types(s) or combination of types: "
                    "'%T' and '%T'", w_a, w_b)

    a = a_buf.as_str()
    b = b_buf.as_str()
    with rffi.scoped_nonmovingbuffer(a) as a_buf:
        with rffi.scoped_nonmovingbuffer(b) as b_buf:
            result = pypy_tscmp(a_buf, b_buf, len(a), len(b))
    return space.wrap(rffi.cast(lltype.Bool, result))
