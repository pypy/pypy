from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem.lltype import typeOf
from pypy.objspace.flow.model import Constant
from pypy.annotation.model import unionof
from pypy.annotation.signature import annotation

import py, sys

def lazy_register(func_or_list, register_func):
    """ Lazily register external function. Will create a function,
    which explodes when llinterpd/translated, but does not explode
    earlier
    """
    if isinstance(func_or_list, list):
        funcs = func_or_list
    else:
        funcs = [func_or_list]
    try:
        return register_func()
    except:
        exc, exc_inst, tb = sys.exc_info()
        for func in funcs:
            class ExtRaisingEntry(ExtRegistryEntry):
                _about_ = func
                def compute_result_annotation(self, *args_s):
                    raise exc, exc_inst, tb

def registering(func):
    def decorator(method):
        method._registering_func = func
        return method
    return decorator

class LazyRegisteringMeta(type):
    def __new__(self, _name, _type, _vars):
        retval = type.__new__(self, _name, _type, _vars)
        allfuncs = []
        for varname in _vars:
            attr = getattr(retval, varname)
            f = getattr(attr, '_registering_func', None)
            if f:
                allfuncs.append(f)
        instance = lazy_register(allfuncs, retval)
        if instance is not None:
            for varname in _vars:
                attr = getattr(instance, varname)
                f = getattr(attr, '_registering_func', None)
                if f:
                    lazy_register(f, attr)
        retval.instance = instance
        # override __init__ to avoid confusion
        def raising(self):
            raise TypeError("Cannot call __init__ directly, use cls.instance to access singleton")
        retval.__init__ = raising
        return retval

class BaseLazyRegistering(object):
    __metaclass__ = LazyRegisteringMeta

class genericcallable(object):
    """ A way to specify the callable annotation, but deferred until
    we have bookkeeper
    """
    def __init__(self, args, result=None):
        self.args = args
        self.result = result

class _ext_callable(ExtRegistryEntry):
    _type_ = genericcallable
    # we defer a bit annotation here

    def compute_result_annotation(self):
        from pypy.annotation import model as annmodel
        return annmodel.SomeGenericCallable([annotation(i, self.bookkeeper)
                                             for i in self.instance.args],
                           annotation(self.instance.result, self.bookkeeper))

class ExtFuncEntry(ExtRegistryEntry):
    safe_not_sandboxed = False

    def compute_result_annotation(self, *args_s):
        if hasattr(self, 'ann_hook'):
            self.ann_hook()
        if self.signature_args is not None:
            assert len(args_s) == len(self.signature_args),\
                   "Argument number mismatch"
            for i, expected in enumerate(self.signature_args):
                arg = unionof(args_s[i], expected)
                if not expected.contains(arg):
                    name = getattr(self, 'name', None)
                    if not name:
                        try:
                            name = self.instance.__name__
                        except AttributeError:
                            name = '?'
                    raise Exception("In call to external function %r:\n"
                                    "arg %d must be %s,\n"
                                    "          got %s" % (
                        name, i+1, expected, args_s[i]))
        return self.signature_result

    def specialize_call(self, hop):
        rtyper = hop.rtyper
        if self.signature_args is None:
            iter_args = hop.args_s
        else:
            iter_args = self.signature_args
        args_r = [rtyper.getrepr(s_arg) for s_arg in iter_args]
        args_ll = [r_arg.lowleveltype for r_arg in args_r]
        r_result = rtyper.getrepr(hop.s_result)
        ll_result = r_result.lowleveltype
        name = getattr(self, 'name', None) or self.instance.__name__
        method_name = rtyper.type_system.name[:2] + 'typeimpl'
        fake_method_name = rtyper.type_system.name[:2] + 'typefakeimpl'
        impl = getattr(self, method_name, None)
        fakeimpl = getattr(self, fake_method_name, self.instance)
        if impl:
            obj = rtyper.getannmixlevel().delayedfunction(
                impl, self.signature_args, hop.s_result)
        else:
            obj = rtyper.type_system.getexternalcallable(args_ll, ll_result,
                                 name, _external_name=self.name, _callable=fakeimpl,
                                 _safe_not_sandboxed=self.safe_not_sandboxed)
        vlist = [hop.inputconst(typeOf(obj), obj)] + hop.inputargs(*args_r)
        hop.exception_is_here()
        return hop.genop('direct_call', vlist, r_result)

def _register_external(function, args, result=None, export_name=None,
                       llimpl=None, ooimpl=None,
                       llfakeimpl=None, oofakeimpl=None,
                       annotation_hook=None,
                       sandboxsafe=False):
    """
    function: the RPython function that will be rendered as an external function (e.g.: math.floor)
    args: a list containing the annotation of the arguments
    result: surprisingly enough, the annotation of the result
    export_name: the name of the function as it will be seen by the backends
    llimpl, ooimpl: optional; if provided, these RPython functions are called instead of the target function
    llfakeimpl, oofakeimpl: optional; if provided, they are called by the llinterpreter
    annotationhook: optional; a callable that is called during annotation, useful for genc hacks
    sandboxsafe: use True if the function performs no I/O (safe for --sandbox)
    """

    class FunEntry(ExtFuncEntry):
        _about_ = function
        safe_not_sandboxed = sandboxsafe
        if args is None:
            signature_args = None
        else:
            signature_args = [annotation(arg, None) for arg in args]
        signature_result = annotation(result, None)
        name=export_name
        if llimpl:
            lltypeimpl = staticmethod(llimpl)
        if ooimpl:
            ootypeimpl = staticmethd(ooimpl)
        if llfakeimpl:
            lltypefakeimpl = staticmethod(llfakeimpl)
        if oofakeimpl:
            ootypefakeimpl = staticmethod(oofakeimpl)
        if annotation_hook:
            ann_hook = staticmethod(annotation_hook)

    if export_name:
        FunEntry.__name__ = export_name
    else:
        FunEntry.__name__ = function.func_name

BaseLazyRegistering.register = staticmethod(_register_external)

def is_external(func):
    if hasattr(func, 'value'):
        func = func.value
    if getattr(func._callable, 'suggested_primitive', False):
        return True
    if hasattr(func, '_external_name'):
        return True
    return False
