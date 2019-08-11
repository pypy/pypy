"""Generation of sandboxing stand-alone executable from RPython code.
In place of real calls to any external function, this code builds
trampolines that marshal their input arguments, dump them to STDOUT,
and wait for an answer on STDIN.  Enable with 'translate.py --sandbox'.
"""
import py
import sys

from rpython.rlib import types
from rpython.rlib.objectmodel import specialize
from rpython.rlib.signature import signature
from rpython.rlib.unroll import unrolling_iterable

# ____________________________________________________________
#
# Sandboxing code generator for external functions
#

from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.llannotation import lltype_to_annotation
from rpython.rtyper.annlowlevel import MixLevelHelperAnnotator
from rpython.tool.ansi_print import AnsiLogger

log = AnsiLogger("sandbox")


def getkind(TYPE, parent_function):
    if TYPE is lltype.Void:
        return 'v'
    elif isinstance(TYPE, lltype.Primitive):
        if TYPE is lltype.Float or TYPE is lltype.SingleFloat:
            return 'f'
        if TYPE is lltype.LongFloat:
            log.WARNING("%r uses a 'long double' argument or return value; "
                        "sandboxing will export it only as 'double'" %
                        (parent_function,))
            return 'f'
        if TYPE == llmemory.Address:
            return 'p'
        return 'i'
    elif isinstance(TYPE, lltype.Ptr):
        return 'p'
    else:
        log.WARNING("%r: sandboxing does not support argument "
                    "or return type %r" % (parent_function, TYPE))
        return 'v'


def extra_eci(rtyper):
    from rpython.translator.c.support import c_string_constant

    sandboxed_functions = getattr(rtyper, '_sandboxed_functions', [])
    dump = (
        "Version: 20001\n" +
        "Platform: %s\n" % sys.platform +
        "Funcs: %s" % ' '.join(sorted(sandboxed_functions))
    )
    dump = c_string_constant(dump).replace('\n', '\\\n')

    return rffi.ExternalCompilationInfo(separate_module_sources=[
            '#define RPY_SANDBOX_DUMP %s\n' % (dump,) +
            py.path.local(__file__).join('..', 'src', 'rsandbox.c').read(),
        ],
        post_include_bits=[
            py.path.local(__file__).join('..', 'src', 'rsandbox.h').read(),
        ])

def external(funcname, ARGS, RESULT):
    return rffi.llexternal(funcname, ARGS, RESULT,
                           sandboxsafe=True, _nowrapper=True)

rpy_sandbox_arg = {
    'i': external('rpy_sandbox_arg_i', [lltype.UnsignedLongLong], lltype.Void),
    'f': external('rpy_sandbox_arg_f', [lltype.Float],            lltype.Void),
    'p': external('rpy_sandbox_arg_p', [llmemory.Address],        lltype.Void),
}
rpy_sandbox_res = {
    'v': external('rpy_sandbox_res_v', [rffi.CCHARP], lltype.Void),
    'i': external('rpy_sandbox_res_i', [rffi.CCHARP], lltype.UnsignedLongLong),
    'f': external('rpy_sandbox_res_f', [rffi.CCHARP], lltype.Float),
    'p': external('rpy_sandbox_res_p', [rffi.CCHARP], llmemory.Address),
}


def sig_ll(fnobj):
    FUNCTYPE = lltype.typeOf(fnobj)
    args_s = [lltype_to_annotation(ARG) for ARG in FUNCTYPE.ARGS]
    s_result = lltype_to_annotation(FUNCTYPE.RESULT)
    return args_s, s_result

def get_sandbox_stub(fnobj, rtyper):
    fnname = fnobj._name
    FUNCTYPE = lltype.typeOf(fnobj)
    arg_kinds = [getkind(ARG, fnname) for ARG in FUNCTYPE.ARGS]
    result_kind = getkind(FUNCTYPE.RESULT, fnname)

    unroll_args = unrolling_iterable([
        (arg_kind, rpy_sandbox_arg[arg_kind],
         lltype.typeOf(rpy_sandbox_arg[arg_kind]).TO.ARGS[0])
        for arg_kind in arg_kinds])

    result_func = rpy_sandbox_res[result_kind]
    RESTYPE = FUNCTYPE.RESULT

    try:
        lst = rtyper._sandboxed_functions
    except AttributeError:
        lst = rtyper._sandboxed_functions = []
    name_and_sig = '%s(%s)%s' % (fnname, ''.join(arg_kinds), result_kind)
    lst.append(name_and_sig)
    log(name_and_sig)
    name_and_sig = rffi.str2charp(name_and_sig, track_allocation=False)

    def execute(*args):
        #
        # serialize the arguments
        i = 0
        for arg_kind, func, ARGTYPE in unroll_args:
            if arg_kind == 'v':
                continue
            func(rffi.cast(ARGTYPE, args[i]))
            i = i + 1
        #
        # send the function name and the arguments and wait for an answer
        result = result_func(name_and_sig)
        #
        # result the answer, if any
        if RESTYPE is not lltype.Void:
            return rffi.cast(RESTYPE, result)
    execute.__name__ = 'sandboxed_%s' % (fnname,)
    #
    args_s, s_result = sig_ll(fnobj)
    return _annotate(rtyper, execute, args_s, s_result)

def _annotate(rtyper, f, args_s, s_result):
    ann = MixLevelHelperAnnotator(rtyper)
    llfunc = ann.delayedfunction(f, args_s, s_result, needtype=True)
    ann.finish()
    ann.backend_optimize()
    return llfunc
