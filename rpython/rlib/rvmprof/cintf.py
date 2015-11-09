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
%(vmprof_stack_h)s

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
    return finish_ll_trampoline(tramp_name, tramp_name, target, token,
                                restok)

def make_trampoline_function(name, func, token, restok):
    from rpython.jit.backend import detect_cpu

    cont_name = 'rpyvmprof_f_%s_%s' % (name, token)
    tramp_name = 'rpyvmprof_t_%s_%s' % (name, token)
    orig_tramp_name = tramp_name

    func.c_name = cont_name
    func._dont_inline_ = True

    if sys.platform == 'darwin':
        # according to internet "At the time UNIX was written in 1974...."
        # "... all C functions are prefixed with _"
        cont_name = '_' + cont_name
        tramp_name = '_' + tramp_name
        PLT = ""
        size_decl = ""
        type_decl = ""
        extra_align = ""
    else:
        PLT = "@PLT"
        type_decl = "\t.type\t%s, @function" % (tramp_name,)
        size_decl = "\t.size\t%s, .-%s" % (
            tramp_name, tramp_name)
        extra_align = "\t.cfi_def_cfa_offset 8"

    assert detect_cpu.autodetect().startswith(detect_cpu.MODEL_X86_64), (
        "rvmprof only supports x86-64 CPUs for now")

    # mapping of argument count (not counting the final uid argument) to
    # the register that holds this uid argument
    reg = {0: '%rdi',
           1: '%rsi',
           2: '%rdx',
           3: '%rcx',
           4: '%r8',
           5: '%r9',
           }
    try:
        reg = reg[len(token)]
    except KeyError:
        raise NotImplementedError(
            "not supported: %r takes more than 5 arguments" % (func,))

    target = udir.join('module_cache')
    target.ensure(dir=1)
    target = target.join('trampoline_%s_%s.vmprof.s' % (name, token))
    # NOTE! the tabs in this file are absolutely essential, things
    #       that don't start with \t are silently ignored (<arigato>: WAT!?)
    target.write("""\
\t.text
\t.globl\t%(tramp_name)s
%(type_decl)s
%(tramp_name)s:
\t.cfi_startproc
\tpushq\t%(reg)s
\t.cfi_def_cfa_offset 16
\tcall %(cont_name)s%(PLT)s
\taddq\t$8, %%rsp
%(extra_align)s
\tret
\t.cfi_endproc
%(size_decl)s
""" % locals())
    return finish_ll_trampoline(orig_tramp_name, tramp_name, target, token,
                                restok)

def finish_ll_trampoline(orig_tramp_name, tramp_name, target, token, restok):

    extra_args = ['long']
    header = 'RPY_EXTERN %s %s(%s);\n' % (
        token2ctype(restok),
        orig_tramp_name,
        ', '.join([token2ctype(tok) for tok in token] + extra_args))

    header += """\
static int cmp_%s(void *addr) {
    if (addr == %s) return 1;
#ifdef VMPROF_ADDR_OF_TRAMPOLINE
    return VMPROF_ADDR_OF_TRAMPOLINE(addr);
#undef VMPROF_ADDR_OF_TRAMPOLINE
#else
    return 0;
#endif
#define VMPROF_ADDR_OF_TRAMPOLINE cmp_%s
}
""" % (tramp_name, orig_tramp_name, tramp_name)

    eci = ExternalCompilationInfo(
        post_include_bits = [header],
        separate_module_files = [str(target)],
    )
    eci = eci.merge(global_eci)

    ARGS = [token2lltype(tok) for tok in token] + [lltype.Signed]
    return rffi.llexternal(
        orig_tramp_name, ARGS,
        token2lltype(restok),
        compilation_info=eci,
        _nowrapper=True, sandboxsafe=True,
        random_effects_on_gcobjs=True)
