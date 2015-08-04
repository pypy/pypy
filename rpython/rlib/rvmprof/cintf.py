import py
import sys
from rpython.tool.udir import udir
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.tool import rffi_platform as platform


ROOT = py.path.local(__file__).join('..')
SRC = ROOT.join('src')


if sys.platform.startswith('linux'):
    libs = ['dl']
else:
    libs = []

eci_kwds = dict(
    include_dirs = [SRC],
    includes = ['rvmprof.h'],
    libraries = libs,
    separate_module_files = [SRC.join('rvmprof.c')],
    )
eci = ExternalCompilationInfo(**eci_kwds)

platform.verify_eci(eci)


vmprof_init = rffi.llexternal("rpython_vmprof_init", [], rffi.CCHARP,
                              compilation_info=eci)
vmprof_enable = rffi.llexternal("rpython_vmprof_enable",
                                [rffi.INT, rffi.LONG],
                                rffi.INT, compilation_info=eci,
                                save_err=rffi.RFFI_SAVE_ERRNO)
vmprof_disable = rffi.llexternal("rpython_vmprof_disable", [], rffi.INT,
                                 compilation_info=eci,
                                 save_err=rffi.RFFI_SAVE_ERRNO)
vmprof_write_buf = rffi.llexternal("rpython_vmprof_write_buf",
                                   [rffi.CCHARP, rffi.LONG],
                                   lltype.Void, compilation_info=eci)

## vmprof_register_virtual_function = rffi.llexternal(
##     "vmprof_register_virtual_function",
##     [rffi.CCHARP, rffi.VOIDP, rffi.VOIDP], lltype.Void,
##     compilation_info=eci, _nowrapper=True)

vmprof_ignore_signals = rffi.llexternal("rpython_vmprof_ignore_signals",
                                        [rffi.INT], lltype.Void,
                                        compilation_info=eci)


def token2lltype(tok):
    if tok == 'i':
        return lltype.Signed
    if tok == 'r':
        return llmemory.GCREF
    raise NotImplementedError(repr(tok))

def make_trampoline_function(name, func, token, restok):
    from rpython.jit.backend import detect_cpu

    cont_name = 'rpyvmprof_f_%s_%s' % (name, token)
    tramp_name = 'rpyvmprof_t_%s_%s' % (name, token)

    func.c_name = cont_name
    func._dont_inline_ = True

    assert detect_cpu.autodetect() == detect_cpu.MODEL_X86_64, (
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
    target.write("""\
\t.text
\t.globl\t%(tramp_name)s
\t.type\t%(tramp_name)s, @function
%(tramp_name)s:
\t.cfi_startproc
\tpushq\t%(reg)s
\t.cfi_def_cfa_offset 16
\tcall %(cont_name)s@PLT
\taddq\t$8, %%rsp
\t.cfi_def_cfa_offset 8
\tret
\t.cfi_endproc
\t.size\t%(tramp_name)s, .-%(tramp_name)s
""" % locals())

    def tok2cname(tok):
        if tok == 'i':
            return 'long'
        if tok == 'r':
            return 'void *'
        raise NotImplementedError(repr(tok))

    header = 'RPY_EXTERN %s %s(%s);\n' % (
        tok2cname(restok),
        tramp_name,
        ', '.join([tok2cname(tok) for tok in token] + ['long']))

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
""" % (tramp_name, tramp_name, tramp_name)

    eci = ExternalCompilationInfo(
        post_include_bits = [header],
        separate_module_files = [str(target)],
    )

    return rffi.llexternal(
        tramp_name,
        [token2lltype(tok) for tok in token] + [lltype.Signed],
        token2lltype(restok),
        compilation_info=eci,
        _nowrapper=True, sandboxsafe=True,
        random_effects_on_gcobjs=True)
