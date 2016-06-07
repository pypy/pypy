import py
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.c.support import cdecl


def extra_files():
    srcdir = py.path.local(__file__).join('..', 'rdb-src')
    return [
        srcdir / 'revdb.c',
    ]

def emit_void(normal_code):
    return 'RPY_REVDB_EMIT_VOID(%s);' % (normal_code,)

def emit(normal_code, tp, value):
    if tp == 'void @':
        return emit_void(normal_code)
    return 'RPY_REVDB_EMIT(%s, %s, %s);' % (normal_code, cdecl(tp, '_e'), value)
