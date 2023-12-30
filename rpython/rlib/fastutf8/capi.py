import py
import sys
from rpython.tool.version import rpythonroot
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.tool import rffi_platform as platform
from rpython.translator.platform import platform as trans_platform
from rpython.translator.platform import is_host_build

ROOT = py.path.local(rpythonroot).join('rpython', 'rlib', 'fastutf8')
SRC = ROOT.join('src')

if sys.platform.startswith('linux'):
    _libs = ['dl']
else:
    _libs = []


IDXTAB = lltype.ForwardReference()
IDXTAB.become(rffi.CStruct("fu8_idxtab",
                           ('character_step', rffi.INT),
                           ('byte_positions', rffi.SIZE_TP),
                           ('bytepos_table_length', rffi.SIZE_T)))
IDXTABP = lltype.Ptr(IDXTAB)

def setup():
    import platform as pyplatform
    compile_extra = ['-fPIC']
    eci_kwds = dict(
        include_dirs = [SRC],
        includes = ['utf8.h'],
        libraries = _libs,
        compile_extra = compile_extra)
    if is_host_build() and pyplatform.processor() == 'x86_64':
        # compile the SSE4.1 and AVX version
        compile_extra.append('-msse4.1')
        ofile_eci = ExternalCompilationInfo(**eci_kwds)
        sse4_o, = trans_platform._compile_o_files([SRC.join('utf8-sse4.c')], ofile_eci)
        compile_extra.pop()
        compile_extra.append('-mavx2')
        ofile_eci = ExternalCompilationInfo(**eci_kwds)
        avx_o, = trans_platform._compile_o_files([SRC.join('utf8-avx.c')], ofile_eci)
        compile_extra.pop()
        del ofile_eci
        eci_kwds['link_files'] = [sse4_o.strpath, avx_o.strpath]

    eci_kwds['separate_module_files'] = [SRC.join('utf8.c')]
    eci = ExternalCompilationInfo(**eci_kwds)
    platform.verify_eci(eci)
    count_utf8_codepoints = rffi.llexternal("fu8_count_utf8_codepoints",
                                  [rffi.CCHARP, rffi.SSIZE_T],
                                  rffi.SSIZE_T, compilation_info=eci,
                                  _nowrapper=True)
    return CInterface(locals())


class CInterface(object):
    def __init__(self, namespace):
        for k, v in namespace.iteritems():
            setattr(self, k, v)

    def _freeze_(self):
        return True


