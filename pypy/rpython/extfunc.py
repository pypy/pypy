
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem.lltype import typeOf

class ExtFuncEntry(ExtRegistryEntry):
    def compute_result_annotation(self, *args_s):
        assert len(args_s) == len(self.signature_args),\
               "Argument number mismatch"
        for arg, expected in zip(args_s, self.signature_args):
            assert expected.contains(arg)
        return self.signature_result

    def specialize_call(self, hop):
        rtyper = hop.rtyper
        args_r = [rtyper.getrepr(s_arg) for s_arg in self.signature_args]
        args_ll = [r_arg.lowleveltype for r_arg in args_r]
        r_result = rtyper.getrepr(self.signature_result)
        ll_result = r_result.lowleveltype
        name = getattr(self, 'name', None) or self.instance.__name__
        obj = rtyper.type_system.getexternalcallable(args_ll, ll_result, name,
                                      _entry=self, _callable=self.instance)
        vlist = [hop.inputconst(typeOf(obj), obj)] + hop.inputargs(*args_r)
        hop.exception_is_here()
        return hop.genop('direct_call', vlist, r_result)

#def register_
