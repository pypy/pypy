import py
from rpython.rtyper.lltypesystem import lltype, rffi, rstr
from rpython.translator import cdir
from rpython.translator.tool.cbuild import ExternalCompilationInfo


cwd = py.path.local(__file__).dirpath()
eci = ExternalCompilationInfo(
    includes=[cwd.join('faulthandler.h')],
    include_dirs=[str(cwd), cdir],
    separate_module_files=[cwd.join('faulthandler.c')])

def direct_llexternal(*args, **kwargs):
    kwargs.setdefault('_nowrapper', True)
    kwargs.setdefault('compilation_info', eci)
    return rffi.llexternal(*args, **kwargs)

DUMP_CALLBACK = lltype.Ptr(lltype.FuncType([], lltype.Void))

pypy_faulthandler_setup = direct_llexternal(
    'pypy_faulthandler_setup', [DUMP_CALLBACK], rffi.CCHARP)

pypy_faulthandler_teardown = direct_llexternal(
    'pypy_faulthandler_teardown', [], lltype.Void)

pypy_faulthandler_enable = direct_llexternal(
    'pypy_faulthandler_enable', [rffi.INT, rffi.INT], rffi.CCHARP)

pypy_faulthandler_disable = direct_llexternal(
    'pypy_faulthandler_disable', [], lltype.Void)

pypy_faulthandler_is_enabled = direct_llexternal(
    'pypy_faulthandler_is_enabled', [], rffi.INT)

pypy_faulthandler_write = direct_llexternal(
    'pypy_faulthandler_write', [rffi.CCHARP], lltype.Void)

pypy_faulthandler_write_int = direct_llexternal(
    'pypy_faulthandler_write_int', [lltype.Signed], lltype.Void)

pypy_faulthandler_dump_traceback = direct_llexternal(
    'pypy_faulthandler_dump_traceback', [rffi.INT, rffi.INT], lltype.Void)
