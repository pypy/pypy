import py
import sys
from rpython.tool.version import rpythonroot
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.tool import rffi_platform as platform

ROOT = py.path.local(rpythonroot).join('rpython', 'rlib', 'rutf8')
SRC = ROOT.join('src')

if sys.platform.startswith('linux'):
    _libs = ['dl']
else:
    _libs = []
eci_kwds = dict(
    include_dirs = [SRC],
    includes = ['utf8.h'],
    libraries = _libs,
    separate_module_files = [SRC.join('utf8.c')],)
global_eci = ExternalCompilationInfo(**eci_kwds)

IDXTAB = lltype.ForwardReference()
IDXTAB.become(rffi.CStruct("fu8_idxtab",
                           ('character_step', rffi.INT),
                           ('byte_positions', lltype.Ptr(rffi.SIZE_T)),
                           ('bytepos_table_length', rffi.SIZE_T)))
IDXTABPP = lltype.Ptr(lltype.Ptr(IDXTAB))

def setup():
    compile_extra = ['-DRPYTHON_LL2CTYPES']
    platform.verify_eci(ExternalCompilationInfo(
        compile_extra=compile_extra,
        **eci_kwds))

    eci = global_eci
    count_utf8_code_points = rffi.llexternal("fu8_count_utf8_codepoints",
                                  [rffi.CCHARP, rffi.SIZE_T],
                                  rffi.SSIZE_T, compilation_info=eci,
                                  _nowrapper=True)
    index2byteposition = rffi.llexternal("fu8_idx2bytepos",
                                  [rffi.SIZE_T, rffi.CCHARP, rffi.SIZE_T, IDXTABPP],
                                  rffi.SSIZE_T, compilation_info=eci,
                                  _nowrapper=True)

    return CInterface(locals())


class CInterface(object):
    def __init__(self, namespace):
        for k, v in namespace.iteritems():
            setattr(self, k, v)

    def _freeze_(self):
        return True


