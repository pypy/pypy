from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator import cdir
from rpython.translator.tool.cbuild import ExternalCompilationInfo


cwd = py.path.local(__file__).dirpath()
eci = ExternalCompilationInfo(
    includes=[cwd.join('faulthandler.h')],
    include_dirs=[str(cwd), cdir],
    separate_module_files=[cwd.join('faulthandler.c')])

def llexternal(*args, **kwargs):
    kwargs.setdefault('releasegil', False)
    kwargs.setdefault('compilation_info', eci)
    return rffi.llexternal(*args, **kwargs)

pypy_faulthandler_setup = llexternal(
    'pypy_faulthandler_setup', [], lltype.Void)
pypy_faulthandler_teardown = llexternal(
    'pypy_faulthandler_teardown', [], lltype.Void)
pypy_faulthandler_enable = llexternal(
    'pypy_faulthandler_enable', [], lltype.Void,
    save_err=rffi.RFFI_SAVE_ERRNO)
pypy_faulthandler_disable = llexternal(
    'pypy_faulthandler_disable', [], lltype.Void)
