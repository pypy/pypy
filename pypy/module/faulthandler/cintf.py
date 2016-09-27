import py
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi, rstr
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

DUMP_CALLBACK = lltype.Ptr(lltype.FuncType(
                     [rffi.INT, rffi.SIGNEDP, lltype.Signed], lltype.Void))

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
    'pypy_faulthandler_write', [rffi.INT, rffi.CCHARP], lltype.Void)

pypy_faulthandler_write_int = direct_llexternal(
    'pypy_faulthandler_write_int', [rffi.INT, lltype.Signed], lltype.Void)

pypy_faulthandler_dump_traceback = direct_llexternal(
    'pypy_faulthandler_dump_traceback',
    [rffi.INT, rffi.INT, llmemory.Address], lltype.Void)

# for tests...

pypy_faulthandler_read_null = direct_llexternal(
    'pypy_faulthandler_read_null', [], lltype.Void)

pypy_faulthandler_read_null_releasegil = direct_llexternal(
    'pypy_faulthandler_read_null', [], lltype.Void,
    _nowrapper=False, releasegil=True)

pypy_faulthandler_sigsegv = direct_llexternal(
    'pypy_faulthandler_sigsegv', [], lltype.Void)

pypy_faulthandler_sigsegv_releasegil = direct_llexternal(
    'pypy_faulthandler_sigsegv', [], lltype.Void,
    _nowrapper=False, releasegil=True)

pypy_faulthandler_sigfpe = direct_llexternal(
    'pypy_faulthandler_sigfpe', [], lltype.Void)

pypy_faulthandler_sigabrt = direct_llexternal(
    'pypy_faulthandler_sigabrt', [], lltype.Void)

pypy_faulthandler_stackoverflow = direct_llexternal(
    'pypy_faulthandler_stackoverflow', [lltype.Float], lltype.Float)
