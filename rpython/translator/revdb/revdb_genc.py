import py
from rpython.rtyper.lltypesystem import lltype, rffi, rstr
from rpython.translator.c.support import cdecl
from rpython.rlib import exports, revdb


def extra_files():
    srcdir = py.path.local(__file__).join('..', 'src-revdb')
    return [
        srcdir / 'revdb.c',
    ]

def emit_void(normal_code):
    return 'RPY_REVDB_EMIT_VOID(%s);' % (normal_code,)

def emit(normal_code, tp, value):
    if tp == 'void @':
        return emit_void(normal_code)
    return 'RPY_REVDB_EMIT(%s, %s, %s);' % (normal_code, cdecl(tp, '_e'), value)

def record_malloc_uid(expr):
    return ' RPY_REVDB_REC_UID(%s);' % (expr,)


def prepare_database(db):
    FUNCPTR = lltype.Ptr(lltype.FuncType([revdb._CMDPTR,
                                          rffi.CCHARP], lltype.Void))

    bk = db.translator.annotator.bookkeeper
    cmds = getattr(db.translator, 'revdb_commands', [])

    array_names = lltype.malloc(rffi.CArray(rffi.INT), len(cmds) + 1,
                                flavor='raw', immortal=True, zero=True)
    array_funcs = lltype.malloc(rffi.CArray(FUNCPTR), len(cmds),
                                flavor='raw', immortal=True, zero=True)

    for i, (name, func) in enumerate(cmds):
        fnptr = lltype.getfunctionptr(bk.getdesc(func).getuniquegraph())
        assert lltype.typeOf(fnptr) == FUNCPTR
        assert isinstance(name, int) and name != 0
        array_names[i] = rffi.cast(rffi.INT, name)
        array_funcs[i] = fnptr

    exports.EXPORTS_obj2name[array_names._as_obj()] = 'rpy_revdb_command_names'
    exports.EXPORTS_obj2name[array_funcs._as_obj()] = 'rpy_revdb_command_funcs'
    db.get(array_names)
    db.get(array_funcs)
