from pypy.rpython import extregistry
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem.lltype import typeOf
from pypy.objspace.flow.model import Constant
from pypy.annotation.model import unionof
from pypy.annotation.signature import annotation

import py, sys

class extdef(object):

    def __init__(self, *args, **kwds):
        self.def_args = args
        self.def_kwds = kwds

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
        val = register_func()
        if isinstance(val, extdef):
            assert len(funcs) == 1
            register_external(funcs[0], *val.def_args, **val.def_kwds)
            return
        return val
    except (SystemExit, MemoryError, KeyboardInterrupt), e:
        raise
    except:
        if 0:
            import traceback
            print >> sys.stderr, 'WARNING: cannot register', func_or_list, ':'
            traceback.print_exc()
            import pdb; pdb.set_trace()
        exc, exc_inst, tb = sys.exc_info()
        for func in funcs:
            # if the function has already been registered and we got
            # an exception afterwards, the ExtRaisingEntry would create
            # a double-registration and crash in an AssertionError that
            # masks the original problem.  In this case, just re-raise now.
            if extregistry.is_registered(func):
                raise exc, exc_inst, tb
            class ExtRaisingEntry(ExtRegistryEntry):
                _about_ = func
                def __getattr__(self, attr):
                    if attr == '_about_' or attr == '__dict__':
                        return super(ExtRegistryEntry, self).__getattr__(attr)
                    raise exc, exc_inst, tb

def registering(func):
    def decorator(method):
        method._registering_func = func
        return method
    return decorator

def registering_if(ns, name):
    try:
        func = getattr(ns, name)
    except AttributeError:
        return lambda method: None
    else:
        return registering(func)

class LazyRegisteringMeta(type):
    def __new__(self, _name, _type, _vars):
        RegisteringClass = type.__new__(self, _name, _type, _vars)
        allfuncs = []
        for varname in _vars:
            attr = getattr(RegisteringClass, varname)
            f = getattr(attr, '_registering_func', None)
            if f:
                allfuncs.append(f)
        registering_inst = lazy_register(allfuncs, RegisteringClass)
        if registering_inst is not None:
            for varname in _vars:
                attr = getattr(registering_inst, varname)
                f = getattr(attr, '_registering_func', None)
                if f:
                    lazy_register(f, attr)
        RegisteringClass.instance = registering_inst
        # override __init__ to avoid confusion
        def raising(self):
            raise TypeError("Cannot call __init__ directly, use cls.instance to access singleton")
        RegisteringClass.__init__ = raising
        return RegisteringClass

class BaseLazyRegistering(object):
    __metaclass__ = LazyRegisteringMeta

    def configure(self, CConfig):
        classes_seen = self.__dict__.setdefault('__classes_seen', {})
        if CConfig in classes_seen:
            return
        from pypy.rpython.tool import rffi_platform as platform
        # copy some stuff
        self.compilation_info = CConfig._compilation_info_
        self.__dict__.update(platform.configure(CConfig))
        classes_seen[CConfig] = True

    def llexternal(self, *args, **kwds):
        kwds = kwds.copy()
        from pypy.rpython.lltypesystem import rffi

        if 'compilation_info' in kwds:
            kwds['compilation_info'] = self.compilation_info.merge(
                kwds['compilation_info'])
        else:
            kwds['compilation_info'] = self.compilation_info
        return rffi.llexternal(*args, **kwds)

    def _freeze_(self):
        return True

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

    # common case: args is a list of annotation or types
    def normalize_args(self, *args_s):
        args = self.signature_args
        signature_args = [annotation(arg, None) for arg in args]
        assert len(args_s) == len(signature_args),\
               "Argument number mismatch"
        for i, expected in enumerate(signature_args):
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
        return signature_args

    def compute_result_annotation(self, *args_s):
        if hasattr(self, 'ann_hook'):
            self.ann_hook()
        self.normalize_args(*args_s)   # check arguments
        return self.signature_result

    def specialize_call(self, hop):
        rtyper = hop.rtyper
        signature_args = self.normalize_args(*hop.args_s)
        args_r = [rtyper.getrepr(s_arg) for s_arg in signature_args]
        args_ll = [r_arg.lowleveltype for r_arg in args_r]
        s_result = hop.s_result
        r_result = rtyper.getrepr(s_result)
        ll_result = r_result.lowleveltype
        name = getattr(self, 'name', None) or self.instance.__name__
        method_name = rtyper.type_system.name[:2] + 'typeimpl'
        fake_method_name = rtyper.type_system.name[:2] + 'typefakeimpl'
        impl = getattr(self, method_name, None)
        fakeimpl = getattr(self, fake_method_name, self.instance)
        if impl:
            if hasattr(self, fake_method_name):
                # If we have both an {ll,oo}impl and a {ll,oo}fakeimpl,
                # we need a wrapper that selects the proper one and calls it
                from pypy.tool.sourcetools import func_with_new_name
                # Using '*args' is delicate because this wrapper is also
                # created for init-time functions like llarena.arena_malloc
                # which are called before the GC is fully initialized
                args = ', '.join(['arg%d' % i for i in range(len(args_ll))])
                d = {'original_impl': impl,
                     's_result': s_result,
                     'fakeimpl': fakeimpl,
                     '__name__': __name__,
                     }
                exec py.code.compile("""
                    from pypy.rlib.objectmodel import running_on_llinterp
                    from pypy.rlib.debug import llinterpcall
                    def ll_wrapper(%s):
                        if running_on_llinterp:
                            return llinterpcall(s_result, fakeimpl, %s)
                        else:
                            return original_impl(%s)
                """ % (args, args, args)) in d
                impl = func_with_new_name(d['ll_wrapper'], name + '_wrapper')
            if rtyper.annotator.translator.config.translation.sandbox:
                impl._dont_inline_ = True
            # store some attributes to the 'impl' function, where
            # the eventual call to rtyper.getcallable() will find them
            # and transfer them to the final lltype.functionptr().
            impl._llfnobjattrs_ = {
                '_name': self.name,
                '_safe_not_sandboxed': self.safe_not_sandboxed,
                }
            obj = rtyper.getannmixlevel().delayedfunction(
                impl, signature_args, hop.s_result)
        else:
            #if not self.safe_not_sandboxed:
            #    print '>>>>>>>>>>>>>-----------------------------------'
            #    print name, self.name
            #    print '<<<<<<<<<<<<<-----------------------------------'
            obj = rtyper.type_system.getexternalcallable(args_ll, ll_result,
                                 name, _external_name=self.name, _callable=fakeimpl,
                                 _safe_not_sandboxed=self.safe_not_sandboxed)
        vlist = [hop.inputconst(typeOf(obj), obj)] + hop.inputargs(*args_r)
        hop.exception_is_here()
        return hop.genop('direct_call', vlist, r_result)

def register_external(function, args, result=None, export_name=None,
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
            def normalize_args(self, *args_s):
                return args_s    # accept any argument unmodified
        elif callable(args):
            # custom annotation normalizer (see e.g. os.utime())
            normalize_args = staticmethod(args)
        else: # use common case behavior
            signature_args = args

        signature_result = annotation(result, None)
        name=export_name
        if llimpl:
            lltypeimpl = staticmethod(llimpl)
        if ooimpl:
            ootypeimpl = staticmethod(ooimpl)
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

BaseLazyRegistering.register = staticmethod(register_external)

def is_external(func):
    if hasattr(func, 'value'):
        func = func.value
    if hasattr(func, '_external_name'):
        return True
    return False
