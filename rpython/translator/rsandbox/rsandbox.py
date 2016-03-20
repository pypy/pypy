import py
from rpython.rlib import jit
from rpython.annotator import model as annmodel
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.lltypesystem import lltype, rffi


class SandboxExternalFunc(object):
    def __init__(self, cfuncname):
        self.cfuncname = cfuncname


def make_sandbox_trampoline(translator, fnname, args_s, s_result):
    """Create a trampoline function with the specified signature.

    The trampoline is meant to be used in place of real calls to the external
    function named 'fnname'.  Instead, it calls a function pointer that is
    under control of the main C program using the sandboxed library.
    """
    try:
        extfuncs, seen = translator._sandboxlib_fnnames
    except AttributeError:
        extfuncs, seen = translator._sandboxlib_fnnames = {}, set()

    if fnname not in extfuncs:
        # map from 'fnname' to the C function doing the call
        cfuncname = fnname
        if '.' in fnname:
            cfuncname = fnname.split('.', 1)[1]   # drop the part before the '.'
        cfuncname = 'sandbox_' + cfuncname
        assert cfuncname not in seen, "duplicate name %r" % (cfuncname,)
        seen.add(cfuncname)
        sandboxfunc = SandboxExternalFunc(cfuncname)
        extfuncs[fnname] = sandboxfunc
    else:
        sandboxfunc = extfuncs[fnname]
        pargs_s, s_presult = sandboxfunc.args_s, sandboxfunc.s_result
        assert len(args_s) == len(pargs_s), (
            "non-constant argument length for %r" % (fnname,))
        args_s = [annmodel.unionof(s1, s2) for (s1, s2) in zip(args_s, pargs_s)]
        s_result = annmodel.unionof(s_result, s_presult)
    sandboxfunc.args_s = args_s
    sandboxfunc.s_result = s_result
    #
    @jit.dont_look_inside
    def execute(*args):
        return _call_sandbox(fnname, *args)
    execute.__name__ = 'sandboxed_%s' % (fnname,)
    return execute

def _call_sandbox(fnname, *args):
    "NOT_RPYTHON"
    raise NotImplementedError

class ExtEntry(ExtRegistryEntry):
    _about_ = _call_sandbox

    def compute_result_annotation(self, s_fnname, *args_s):
        fnname = s_fnname.const
        translator = self.bookkeeper.annotator.translator
        sandboxfunc = translator._sandboxlib_fnnames[0][fnname]
        return sandboxfunc.s_result

    def specialize_call(self, hop):
        fnname = hop.spaceop.args[1].value
        translator = hop.rtyper.annotator.translator
        sandboxfunc = translator._sandboxlib_fnnames[0][fnname]
        args_s, s_result = sandboxfunc.args_s, sandboxfunc.s_result
        nb_args = len(args_s)
        assert len(hop.spaceop.args) == 2 + nb_args
        assert len(hop.args_r) == 1 + nb_args
        args_r = [hop.rtyper.getrepr(s) for s in args_s]
        r_result = hop.rtyper.getrepr(s_result)

        if not hasattr(sandboxfunc, 'externalfunc'):
            externalfunc = rffi.llexternal(sandboxfunc.cfuncname,
                                           [r.lowleveltype for r in args_r],
                                           r_result.lowleveltype,
                                           sandboxsafe=True,
                                           _nowrapper=True)
            sandboxfunc.externalfunc = externalfunc
        else:
            externalfunc = sandboxfunc.externalfunc

        c_externalfunc = hop.inputconst(lltype.typeOf(externalfunc),
                                        externalfunc)

        args_v = [hop.inputarg(args_r[i], 1 + i) for i in range(nb_args)]
        hop.exception_cannot_occur()
        return hop.genop("direct_call", [c_externalfunc] + args_v,
                         resulttype = r_result)


def add_sandbox_files(database, eci):
    from rpython.translator.c.support import cdecl

    c_header = ['#include "common_header.h"\n']
    c_source = ['#include "rsandbox.h"\n']
    fnnames = database.translator._sandboxlib_fnnames[0]
    for fnname in sorted(fnnames):
        sandboxfunc = fnnames[fnname]
        if hasattr(sandboxfunc, 'externalfunc'):
            externalfunc = sandboxfunc.externalfunc
            TP = lltype.typeOf(externalfunc)
            vardecl = cdecl(database.gettype(TP), sandboxfunc.cfuncname)
            c_header.append('RPY_SANDBOX_EXPORTED %s;\n' % (vardecl,))
            #
            emptyfuncname = 'empty_' + sandboxfunc.cfuncname
            argnames = ['a%d' % i for i in range(len(TP.TO.ARGS))]
            c_source.append("""
static %s {
    abort();
};
%s = %s;
""" % (cdecl(database.gettype(TP.TO, argnames=argnames), emptyfuncname),
       vardecl, emptyfuncname))

    import pdb;pdb.set_trace()
    
    #srcdir = py.path.local(__file__).join('..', 'src')
    #files = [
    #    srcdir / 'foo.c',
    #]
    #return eci.merge(ExternalCompilationInfo(separate_module_files=files))
