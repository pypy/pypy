from rpython.tool.udir import udir
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo


def vmprof_init(): pass
def vmprof_enable(fileno, interval_usec): return 0
def vmprof_ignore_signals(ignore): pass


def token2lltype(tok):
    if tok == 'i':
        return lltype.Signed
    if tok == 'r':
        return llmemory.GCREF
    raise NotImplementedError(repr(tok))

def make_trampoline_function(name, func, token, restok):
    from rpython.jit.backend import detect_cpu

    cont_name = 'vmprof_f_%s_%s' % (name, token)
    tramp_name = 'vmprof_t_%s_%s' % (name, token)

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
    reg = reg[len(token)]

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

    header = '%s %s(%s);\n' % (
        tok2cname(restok),
        tramp_name,
        ', '.join([tok2cname(tok) for tok in token] + ['long']))

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
