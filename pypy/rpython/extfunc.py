
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem.lltype import typeOf
from pypy.objspace.flow.model import Constant
from pypy.annotation.model import unionof
from pypy.annotation.signature import annotation
from pypy.annotation import model as annmodel
import py

class _callable(object):
    """ A way to specify the callable annotation, but deferred until
    we have bookkeeper
    """
    def __init__(self, args, result=None):
        self.args = args
        self.result = result

class _ext_callable(ExtRegistryEntry):
    _type_ = _callable
    # we defer a bit annotation here

    def compute_result_annotation(self):
        return annmodel.SomeGenericCallable([annotation(i, self.bookkeeper)
                                             for i in self.instance.args],
                           annotation(self.instance.result, self.bookkeeper))

class ExtFuncEntry(ExtRegistryEntry):
    def compute_result_annotation(self, *args_s):
        if self.signature_args is not None:
            assert len(args_s) == len(self.signature_args),\
                   "Argument number mismatch"
            for arg, expected in zip(args_s, self.signature_args):
                arg = unionof(arg, expected)
                assert expected.contains(arg)
        return self.signature_result

    def specialize_call(self, hop):
        rtyper = hop.rtyper
        if self.signature_args is None:
            iter_args = hop.args_s
        else:
            iter_args = self.signature_args
        args_r = [rtyper.getrepr(s_arg) for s_arg in iter_args]
        args_ll = [r_arg.lowleveltype for r_arg in args_r]
        r_result = rtyper.getrepr(self.signature_result)
        ll_result = r_result.lowleveltype
        name = getattr(self, 'name', None) or self.instance.__name__
        method_name = rtyper.type_system.name[:2] + 'typeimpl'
        impl = getattr(self, method_name, None)
        if impl:
            obj = rtyper.getannmixlevel().delayedfunction(
                impl.im_func, self.signature_args, self.signature_result)
        else:
            obj = rtyper.type_system.getexternalcallable(args_ll, ll_result,
                                 name, _entry=self, _callable=self.instance)
        vlist = [hop.inputconst(typeOf(obj), obj)] + hop.inputargs(*args_r)
        hop.exception_is_here()
        return hop.genop('direct_call', vlist, r_result)

def register_external(function, args, result=None, export_name=None,
                      llimpl=None, ooimpl=None):
    
    class FunEntry(ExtFuncEntry):
        _about_ = function
        if args is None:
            signature_args = None
        else:
            signature_args = [annotation(arg) for arg in args]
        signature_result = annotation(result)
        name=export_name
        if llimpl:
            lltypeimpl = llimpl
        if ooimpl:
            ootypeimpl = ooimpl

    if export_name:
        FunEntry.__name__ = export_name
    else:
        FunEntry.__name__ = function.func_name

def is_external(func):
    if getattr(func.value._callable, 'suggested_primitive', False):
        return True
    if hasattr(func.value, '_entry'):
        if isinstance(func.value._entry, ExtFuncEntry):
            return True
    return False
