import py
from rpython.rlib import jit
from rpython.annotator import model as annmodel
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.lltypesystem import lltype, rffi


class SandboxExternalFunc(object):
    def __init__(self, cptrname):
        self.cptrname = cptrname


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
        # map from 'fnname' to the C name of the function pointer
        cptrname = fnname
        if '.' in fnname:
            cptrname = fnname.split('.', 1)[1]   # drop the part before the '.'
        cptrname = 'sandbox_' + cptrname
        assert cptrname not in seen, "duplicate name %r" % (cptrname,)
        seen.add(cptrname)
        sandboxfunc = SandboxExternalFunc(cptrname)
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

        args_r = [hop.rtyper.getrepr(s) for s in args_s]
        r_result = hop.rtyper.getrepr(s_result)
        FUNCPTR = lltype.Ptr(lltype.FuncType([r.lowleveltype for r in args_r],
                                             r_result.lowleveltype))
        externalfuncptr = rffi.CConstant(sandbox.cptrname, FUNCPTR)
        import pdb;pdb.set_trace()
        
        for i in range(nb_args):
            v_arg = hop.inputarg(args_r[i], 2 + i)
            xxx


def add_sandbox_files(translator, eci):
    srcdir = py.path.local(__file__).join('..', 'src')
    files = [
        srcdir / 'foo.c',
    ]
    fnnames = sorted(translator._sandboxlib_fnnames[0])
    import pdb;pdb.set_trace()
    
    return eci.merge(ExternalCompilationInfo(separate_module_files=files))
