import py
import sys
from rpython.tool.udir import udir
from rpython.tool.version import rpythonroot
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.tool import rffi_platform as platform

from rpython.jit.backend import detect_cpu

class VMProfPlatformUnsupported(Exception):
    pass

ROOT = py.path.local(rpythonroot).join('rpython', 'rlib', 'rvmprof')
SRC = ROOT.join('src')

if sys.platform.startswith('linux'):
    _libs = ['dl']
else:
    _libs = []
eci_kwds = dict(
    include_dirs = [SRC],
    includes = ['rvmprof.h'],
    libraries = _libs,
    separate_module_files = [SRC.join('rvmprof.c')],
    post_include_bits=['#define RPYTHON_VMPROF\n'],
    )
global_eci = ExternalCompilationInfo(**eci_kwds)


def setup():
    if not detect_cpu.autodetect().startswith(detect_cpu.MODEL_X86_64):
        raise VMProfPlatformUnsupported("rvmprof only supports"
                                        " x86-64 CPUs for now")

    platform.verify_eci(ExternalCompilationInfo(
        compile_extra=['-DRPYTHON_LL2CTYPES'],
        **eci_kwds))


    eci = global_eci
    vmprof_init = rffi.llexternal("vmprof_init",
                                  [rffi.INT, rffi.DOUBLE, rffi.CCHARP],
                                  rffi.CCHARP, compilation_info=eci)
    vmprof_enable = rffi.llexternal("vmprof_enable", [], rffi.INT,
                                    compilation_info=eci,
                                    save_err=rffi.RFFI_SAVE_ERRNO)
    vmprof_disable = rffi.llexternal("vmprof_disable", [], rffi.INT,
                                     compilation_info=eci,
                                     save_err=rffi.RFFI_SAVE_ERRNO)
    vmprof_register_virtual_function = rffi.llexternal(
                                           "vmprof_register_virtual_function",
                                           [rffi.CCHARP, rffi.LONG, rffi.INT],
                                           rffi.INT, compilation_info=eci)
    vmprof_ignore_signals = rffi.llexternal("vmprof_ignore_signals",
                                            [rffi.INT], lltype.Void,
                                            compilation_info=eci,
                                            _nowrapper=True)
    return CInterface(locals())


class CInterface(object):
    def __init__(self, namespace):
        for k, v in namespace.iteritems():
            setattr(self, k, v)

    def _freeze_(self):
        return True

def token2lltype(tok):
    if tok == 'i':
        return lltype.Signed
    if tok == 'r':
        return llmemory.GCREF
    raise NotImplementedError(repr(tok))

def token2ctype(tok):
    if tok == 'i':
        return 'long'
    elif tok == 'r':
        return 'void*'
    elif tok == 'f':
        return 'double'
    else:
        raise NotImplementedError(repr(tok))

def make_c_trampoline_function(name, func, token, restok):
    cont_name = 'rpyvmprof_f_%s_%s' % (name, token)
    tramp_name = 'rpyvmprof_t_%s_%s' % (name, token)

    func.c_name = cont_name
    func._dont_inline_ = True

    assert detect_cpu.autodetect().startswith(detect_cpu.MODEL_X86_64), (
        "rvmprof only supports x86-64 CPUs for now")

    llargs = ", ".join(["%s arg%d" % (token2ctype(x), i) for i, x in
        enumerate(token)])
    type = token2ctype(restok)
    target = udir.join('module_cache')
    target.ensure(dir=1)
    argnames = ", ".join(["arg%d" % i for i in range(len(token))])
    vmprof_stack_h = SRC.join("vmprof_stack.h").read()
    target = target.join('trampoline_%s_%s.vmprof.c' % (name, token))
    target.write("""
#include "src/precommondefs.h"
#include "vmprof_stack.h"

%(type)s %(cont_name)s(%(llargs)s);

%(type)s %(tramp_name)s(%(llargs)s, long unique_id)
{
    %(type)s result;
    struct vmprof_stack node;

    node.value = unique_id;
    node.kind = VMPROF_CODE_TAG;
    node.next = vmprof_global_stack;
    vmprof_global_stack = &node;
    result = %(cont_name)s(%(argnames)s);
    vmprof_global_stack = node.next;
    return result;
}
""" % locals())
    header = 'RPY_EXTERN %s %s(%s);\n' % (
        token2ctype(restok), tramp_name,
        ', '.join([token2ctype(tok) for tok in token] + ['long']))

    eci = ExternalCompilationInfo(
        post_include_bits = [header],
        separate_module_files = [str(target)],
    )
    eci = eci.merge(global_eci)
    ARGS = [token2lltype(tok) for tok in token] + [lltype.Signed]
    return rffi.llexternal(
        tramp_name, ARGS,
        token2lltype(restok),
        compilation_info=eci,
        _nowrapper=True, sandboxsafe=True,
        random_effects_on_gcobjs=True)
