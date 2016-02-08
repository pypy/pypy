from rpython.tool.sourcetools import func_with_new_name
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.lltypesystem.lltype import typeOf, FuncType, functionptr, _ptr
from rpython.annotator.model import unionof
from rpython.annotator.signature import annotation, SignatureError

class ExtFuncEntry(ExtRegistryEntry):
    safe_not_sandboxed = False

    # common case: args is a list of annotation or types
    def normalize_args(self, *args_s):
        args = self.signature_args
        signature_args = [annotation(arg, None) for arg in args]
        assert len(args_s) == len(signature_args),\
               "Argument number mismatch"

        for i, expected in enumerate(signature_args):
            arg = unionof(args_s[i], expected)
            if not expected.contains(arg):
                raise SignatureError("In call to external function %r:\n"
                                "arg %d must be %s,\n"
                                "          got %s" % (
                    self.name, i+1, expected, args_s[i]))
        return signature_args

    def compute_result_annotation(self, *args_s):
        self.normalize_args(*args_s)   # check arguments
        return self.signature_result

    def specialize_call(self, hop):
        from rpython.rtyper.rtyper import llinterp_backend
        rtyper = hop.rtyper
        signature_args = self.normalize_args(*hop.args_s)
        args_r = [rtyper.getrepr(s_arg) for s_arg in signature_args]
        args_ll = [r_arg.lowleveltype for r_arg in args_r]
        s_result = hop.s_result
        r_result = rtyper.getrepr(s_result)
        ll_result = r_result.lowleveltype
        impl = getattr(self, 'lltypeimpl', None)
        fakeimpl = getattr(self, 'lltypefakeimpl', self.instance)
        if impl:
            impl = make_impl(rtyper, impl, self.safe_not_sandboxed, self.name,
                             signature_args, s_result)
            if hasattr(self, 'lltypefakeimpl') and rtyper.backend is llinterp_backend:
                FT = FuncType(args_ll, ll_result)
                obj = functionptr(FT, self.name, _external_name=self.name,
                                _callable=fakeimpl)
            elif isinstance(impl, _ptr):
                obj = impl
            else:
                # store some attributes to the 'impl' function, where
                # the eventual call to rtyper.getcallable() will find them
                # and transfer them to the final lltype.functionptr().
                impl._llfnobjattrs_ = {'_name': self.name}
                obj = rtyper.getannmixlevel().delayedfunction(
                    impl, signature_args, hop.s_result)
        else:
            FT = FuncType(args_ll, ll_result)
            obj = functionptr(FT, self.name, _external_name=self.name,
                              _callable=fakeimpl,
                              _safe_not_sandboxed=self.safe_not_sandboxed)
        vlist = [hop.inputconst(typeOf(obj), obj)] + hop.inputargs(*args_r)
        hop.exception_is_here()
        return hop.genop('direct_call', vlist, r_result)

def make_impl(rtyper, impl, sandboxsafe, name, args_s, s_result):
    if (rtyper.annotator.translator.config.translation.sandbox
            and not sandboxsafe):
        from rpython.translator.sandbox.rsandbox import make_sandbox_trampoline
        impl = make_sandbox_trampoline(name, args_s, s_result)
    return impl

def register_external(function, args, result=None, export_name=None,
                       llimpl=None, llfakeimpl=None, sandboxsafe=False):
    """
    function: the RPython function that will be rendered as an external function (e.g.: math.floor)
    args: a list containing the annotation of the arguments
    result: surprisingly enough, the annotation of the result
    export_name: the name of the function as it will be seen by the backends
    llimpl: optional; if provided, this RPython function is called instead of the target function
    llfakeimpl: optional; if provided, called by the llinterpreter
    sandboxsafe: use True if the function performs no I/O (safe for --sandbox)
    """

    if export_name is None:
        export_name = function.__name__

    class FunEntry(ExtFuncEntry):
        _about_ = function
        safe_not_sandboxed = sandboxsafe

        if args is None:
            def normalize_args(self, *args_s):
                return args_s    # accept any argument unmodified
        elif callable(args):
            # custom annotation normalizer (see e.g. os.utime())
            normalize_args = staticmethod(args)
        else: # use common case behavior
            signature_args = args

        signature_result = annotation(result, None)
        name = export_name
        if llimpl:
            lltypeimpl = staticmethod(llimpl)
        if llfakeimpl:
            lltypefakeimpl = staticmethod(llfakeimpl)

    if export_name:
        FunEntry.__name__ = export_name
    else:
        FunEntry.__name__ = function.func_name

def is_external(func):
    if hasattr(func, 'value'):
        func = func.value
    if hasattr(func, '_external_name'):
        return True
    return False
