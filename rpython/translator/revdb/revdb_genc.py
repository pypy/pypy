import py
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.c.support import cdecl


def extra_files():
    srcdir = py.path.local(__file__).join('..', 'rdb-src')
    return [
        srcdir / 'revdb.c',
    ]

def emit(tp, value):
    if tp == 'void @':
        return '/* void */'
    return 'rpy_reverse_db_EMIT(%s=%s);' % (cdecl(tp, '_e'), value)
