from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.lltypesystem.lltype import typeOf, FuncType, functionptr, _ptr
from rpython.annotator.model import unionof
from rpython.annotator.signature import annotation, SignatureError

class ExtFuncEntry(ExtRegistryEntry):
    safe_not_sandboxed = False

    def check_args(self, *args_s):
        params_s = self.signature_args
        assert len(args_s) == len(params_s),\
               "Argument number mismatch"

        for i, s_param in enumerate(params_s):
            arg = unionof(args_s[i], s_param)
            if not s_param.contains(arg):
                raise SignatureError("In call to external function %r:\n"
                                "arg %d must be %s,\n"
                                "          got %s" % (
                    self.name, i+1, s_param, args_s[i]))
        return params_s

    def compute_result_annotation(self, *args_s):
        self.check_args(*args_s)
        return self.signature_result

    def compute_annotation(self):
        s_result = super(ExtFuncEntry, self).compute_annotation()
        if (self.bookkeeper.annotator.translator.config.translation.sandbox
                and not self.safe_not_sandboxed):
            s_result.needs_sandboxing = True
            s_result.entry = self
        return s_result

    def specialize_call(self, hop):
        rtyper = hop.rtyper
        args_r = [rtyper.getrepr(s_arg) for s_arg in self.signature_args]
        r_result = rtyper.getrepr(self.signature_result)
        obj = self.get_funcptr(rtyper, args_r, r_result)
        vlist = [hop.inputconst(typeOf(obj), obj)] + hop.inputargs(*args_r)
        hop.exception_is_here()
        return hop.genop('direct_call', vlist, r_result)

    def get_funcptr(self, rtyper, args_r, r_result):
        from rpython.rtyper.rtyper import llinterp_backend
        args_ll = [r_arg.lowleveltype for r_arg in args_r]
        ll_result = r_result.lowleveltype
        impl = getattr(self, 'lltypeimpl', None)
        fakeimpl = getattr(self, 'lltypefakeimpl', self.instance)
        if impl:
            if hasattr(self, 'lltypefakeimpl') and rtyper.backend is llinterp_backend:
                FT = FuncType(args_ll, ll_result)
                return functionptr(
                    FT, self.name, _external_name=self.name,
                    _callable=fakeimpl)
            elif isinstance(impl, _ptr):
                return impl
            else:
                # store some attributes to the 'impl' function, where
                # the eventual call to rtyper.getcallable() will find them
                # and transfer them to the final lltype.functionptr().
                impl._llfnobjattrs_ = {'_name': self.name}
                return rtyper.getannmixlevel().delayedfunction(
                    impl, self.signature_args, self.signature_result)
        else:
            FT = FuncType(args_ll, ll_result)
            return functionptr(
                FT, self.name, _external_name=self.name, _callable=fakeimpl,
                _safe_not_sandboxed=self.safe_not_sandboxed)


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
    params_s = [annotation(arg) for arg in args]
    s_result = annotation(result)

    class FunEntry(ExtFuncEntry):
        _about_ = function
        safe_not_sandboxed = sandboxsafe
        signature_args = params_s
        signature_result = s_result
        name = export_name
        if llimpl:
            lltypeimpl = staticmethod(llimpl)
        if llfakeimpl:
            lltypefakeimpl = staticmethod(llfakeimpl)

def is_external(func):
    if hasattr(func, 'value'):
        func = func.value
    if hasattr(func, '_external_name'):
        return True
    return False
