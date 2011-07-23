"""

Gateway between app-level and interpreter-level:
* BuiltinCode (call interp-level code from app-level)
* app2interp  (embed an app-level function into an interp-level callable)
* interp2app  (publish an interp-level object to be visible from app-level)

"""

import types, sys, os
from pypy.tool.compat import md5

NoneNotWrapped = object()

from pypy.tool.sourcetools import func_with_new_name
from pypy.interpreter.error import OperationError
from pypy.interpreter import eval
from pypy.interpreter.function import Function, Method, ClassMethod
from pypy.interpreter.function import FunctionWithFixedCode
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable
from pypy.interpreter.baseobjspace import Wrappable, SpaceCache, DescrMismatch
from pypy.interpreter.argument import Arguments, Signature
from pypy.tool.sourcetools import NiceCompile, compile2
from pypy.rlib.rarithmetic import r_longlong, r_int, r_ulonglong, r_uint
from pypy.rlib import rstackovf
from pypy.rlib.objectmodel import we_are_translated

# internal non-translatable parts:
import py

class SignatureBuilder(object):
    "NOT_RPYTHON"
    def __init__(self, func=None, argnames=None, varargname=None,
                 kwargname=None, name = None):
        self.func = func
        if func is not None:
            self.name = func.__name__
        else:
            self.name = name
        if argnames is None:
            argnames = []
        self.argnames = argnames
        self.varargname = varargname
        self.kwargname = kwargname

    def append(self, argname):
        self.argnames.append(argname)

    def signature(self):
        return Signature(self.argnames, self.varargname, self.kwargname)

#________________________________________________________________

class UnwrapSpecRecipe(object):
    "NOT_RPYTHON"

    bases_order = [Wrappable, W_Root, ObjSpace, Arguments, object]

    def dispatch(self, el, *args):
        if isinstance(el, str):
            getattr(self, "visit_%s" % (el,))(el, *args)
        elif isinstance(el, tuple):
            if el[0] == 'self':
                self.visit_self(el[1], *args)
            else:
                self.visit_function(el, *args)
        else:
            for typ in self.bases_order:
                if issubclass(el, typ):
                    visit = getattr(self, "visit__%s" % (typ.__name__,))
                    visit(el, *args)
                    break
            else:
                raise Exception("%s: no match for unwrap_spec element %s" % (
                    self.__class__.__name__, el))

    def apply_over(self, unwrap_spec, *extra):
        dispatch = self.dispatch
        for el in unwrap_spec:
            dispatch(el, *extra)

class UnwrapSpecEmit(UnwrapSpecRecipe):

    def __init__(self):
        self.n = 0
        self.miniglobals = {}

    def succ(self):
        n = self.n
        self.n += 1
        return n

    def use(self, obj):
        name = obj.__name__
        self.miniglobals[name] = obj
        return name

#________________________________________________________________

class UnwrapSpec_Check(UnwrapSpecRecipe):

    # checks for checking interp2app func argument names wrt unwrap_spec
    # and synthetizing an app-level signature

    def __init__(self, original_sig):
        self.func = original_sig.func
        self.orig_arg = iter(original_sig.argnames).next

    def visit_function(self, (func, cls), app_sig):
        self.dispatch(cls, app_sig)

    def visit_self(self, cls, app_sig):
        self.visit__Wrappable(cls, app_sig)

    def checked_space_method(self, typname, app_sig):
        argname = self.orig_arg()
        assert not argname.startswith('w_'), (
            "unwrapped %s argument %s of built-in function %r should "
            "not start with 'w_'" % (typname, argname, self.func))
        app_sig.append(argname)

    def visit_index(self, index, app_sig):
        self.checked_space_method(index, app_sig)

    def visit_bufferstr(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_str_or_None(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_nonnegint(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_c_int(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_c_uint(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_c_nonnegint(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_truncatedint(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit__Wrappable(self, el, app_sig):
        name = el.__name__
        argname = self.orig_arg()
        assert not argname.startswith('w_'), (
            "unwrapped %s argument %s of built-in function %r should "
            "not start with 'w_'" % (name, argname, self.func))
        app_sig.append(argname)

    def visit__ObjSpace(self, el, app_sig):
        self.orig_arg()

    def visit__W_Root(self, el, app_sig):
        assert el is W_Root, "%s is not W_Root (forgotten to put .im_func in interp2app argument?)" % (el,)
        argname = self.orig_arg()
        assert argname.startswith('w_'), (
            "argument %s of built-in function %r should "
            "start with 'w_'" % (argname, self.func))
        app_sig.append(argname[2:])

    def visit__Arguments(self, el, app_sig):
        argname = self.orig_arg()
        assert app_sig.varargname is None,(
            "built-in function %r has conflicting rest args specs" % self.func)
        app_sig.varargname = 'args'
        app_sig.kwargname = 'keywords'

    def visit_args_w(self, el, app_sig):
        argname = self.orig_arg()
        assert argname.endswith('_w'), (
            "rest arguments arg %s of built-in function %r should end in '_w'" %
            (argname, self.func))
        assert app_sig.varargname is None,(
            "built-in function %r has conflicting rest args specs" % self.func)
        app_sig.varargname = argname[:-2]

    def visit_w_args(self, el, app_sig):
        argname = self.orig_arg()
        assert argname.startswith('w_'), (
            "rest arguments arg %s of built-in function %r should start 'w_'" %
            (argname, self.func))
        assert app_sig.varargname is None,(
            "built-in function %r has conflicting rest args specs" % self.func)
        app_sig.varargname = argname[2:]

    def visit__object(self, typ, app_sig):
        name = int_unwrapping_space_method(typ)
        self.checked_space_method(name, app_sig)


class UnwrapSpec_EmitRun(UnwrapSpecEmit):

    # collect code to emit for interp2app builtin frames based on unwrap_spec

    def __init__(self):
        UnwrapSpecEmit.__init__(self)
        self.run_args = []

    def scopenext(self):
        return "scope_w[%d]" % self.succ()

    def visit_function(self, (func, cls)):
        self.run_args.append("%s(%s)" % (self.use(func),
                                         self.scopenext()))

    def visit_self(self, typ):
        self.run_args.append("space.descr_self_interp_w(%s, %s)" %
                             (self.use(typ), self.scopenext()))

    def visit__Wrappable(self, typ):
        self.run_args.append("space.interp_w(%s, %s)" % (self.use(typ),
                                                         self.scopenext()))

    def visit__ObjSpace(self, el):
        self.run_args.append('space')

    def visit__W_Root(self, el):
        self.run_args.append(self.scopenext())

    def visit__Arguments(self, el):
        self.miniglobals['Arguments'] = Arguments
        self.run_args.append("Arguments.frompacked(space, %s, %s)"
                             % (self.scopenext(), self.scopenext()))

    def visit_args_w(self, el):
        self.run_args.append("space.fixedview(%s)" % self.scopenext())

    def visit_w_args(self, el):
        self.run_args.append(self.scopenext())

    def visit__object(self, typ):
        name = int_unwrapping_space_method(typ)
        self.run_args.append("space.%s(%s)" %
                             (name, self.scopenext()))

    def visit_index(self, typ):
        self.run_args.append("space.getindex_w(%s, space.w_OverflowError)"
                             % (self.scopenext(), ))

    def visit_bufferstr(self, typ):
        self.run_args.append("space.bufferstr_w(%s)" % (self.scopenext(),))

    def visit_str_or_None(self, typ):
        self.run_args.append("space.str_or_None_w(%s)" % (self.scopenext(),))

    def visit_nonnegint(self, typ):
        self.run_args.append("space.gateway_nonnegint_w(%s)" % (
            self.scopenext(),))

    def visit_c_int(self, typ):
        self.run_args.append("space.c_int_w(%s)" % (self.scopenext(),))

    def visit_c_uint(self, typ):
        self.run_args.append("space.c_uint_w(%s)" % (self.scopenext(),))

    def visit_c_nonnegint(self, typ):
        self.run_args.append("space.c_nonnegint_w(%s)" % (self.scopenext(),))

    def visit_truncatedint(self, typ):
        self.run_args.append("space.truncatedint(%s)" % (self.scopenext(),))

    def _make_unwrap_activation_class(self, unwrap_spec, cache={}):
        try:
            key = tuple(unwrap_spec)
            activation_factory_cls, run_args = cache[key]
            assert run_args == self.run_args, (
                "unexpected: same spec, different run_args")
            return activation_factory_cls
        except KeyError:
            parts = []
            for el in unwrap_spec:
                if isinstance(el, tuple):
                    parts.append(''.join([getattr(subel, '__name__', subel)
                                          for subel in el]))
                else:
                    parts.append(getattr(el, '__name__', el))
            label = '_'.join(parts)
            #print label

            d = {}
            source = """if 1:
                def _run(self, space, scope_w):
                    return self.behavior(%s)
                \n""" % (', '.join(self.run_args),)
            exec compile2(source) in self.miniglobals, d

            activation_cls = type("BuiltinActivation_UwS_%s" % label,
                             (BuiltinActivation,), d)
            activation_cls._immutable_ = True

            cache[key] = activation_cls, self.run_args
            return activation_cls

    def make_activation(unwrap_spec, func):
        emit = UnwrapSpec_EmitRun()
        emit.apply_over(unwrap_spec)
        activation_uw_cls = emit._make_unwrap_activation_class(unwrap_spec)
        return activation_uw_cls(func)
    make_activation = staticmethod(make_activation)


class BuiltinActivation(object):
    _immutable_ = True

    def __init__(self, behavior):
        """NOT_RPYTHON"""
        self.behavior = behavior

    def _run(self, space, scope_w):
        """Subclasses with behavior specific for an unwrap spec are generated"""
        raise TypeError, "abstract"

#________________________________________________________________

class FastFuncNotSupported(Exception):
    pass

class UnwrapSpec_FastFunc_Unwrap(UnwrapSpecEmit):

    def __init__(self):
        UnwrapSpecEmit.__init__(self)
        self.args = []
        self.unwrap = []
        self.finger = 0

    def dispatch(self, el, *args):
        UnwrapSpecEmit.dispatch(self, el, *args)
        self.finger += 1
        if self.n > 4:
            raise FastFuncNotSupported

    def nextarg(self):
        arg = "w%d" % self.succ()
        self.args.append(arg)
        return arg

    def visit_function(self, (func, cls)):
        raise FastFuncNotSupported

    def visit_self(self, typ):
        self.unwrap.append("space.descr_self_interp_w(%s, %s)" %
                           (self.use(typ), self.nextarg()))

    def visit__Wrappable(self, typ):
        self.unwrap.append("space.interp_w(%s, %s)" % (self.use(typ),
                                                       self.nextarg()))

    def visit__ObjSpace(self, el):
        if self.finger != 0:
            raise FastFuncNotSupported
        self.unwrap.append("space")

    def visit__W_Root(self, el):
        self.unwrap.append(self.nextarg())

    def visit__Arguments(self, el):
        raise FastFuncNotSupported

    def visit_args_w(self, el):
        raise FastFuncNotSupported

    def visit_w_args(self, el):
        raise FastFuncNotSupported

    def visit__object(self, typ):
        name = int_unwrapping_space_method(typ)
        self.unwrap.append("space.%s(%s)" % (name,
                                               self.nextarg()))

    def visit_index(self, typ):
        self.unwrap.append("space.getindex_w(%s, space.w_OverflowError)"
                           % (self.nextarg()), )

    def visit_bufferstr(self, typ):
        self.unwrap.append("space.bufferstr_w(%s)" % (self.nextarg(),))

    def visit_str_or_None(self, typ):
        self.unwrap.append("space.str_or_None_w(%s)" % (self.nextarg(),))

    def visit_nonnegint(self, typ):
        self.unwrap.append("space.gateway_nonnegint_w(%s)" % (self.nextarg(),))

    def visit_c_int(self, typ):
        self.unwrap.append("space.c_int_w(%s)" % (self.nextarg(),))

    def visit_c_uint(self, typ):
        self.unwrap.append("space.c_uint_w(%s)" % (self.nextarg(),))

    def visit_c_nonnegint(self, typ):
        self.unwrap.append("space.c_nonnegint_w(%s)" % (self.nextarg(),))

    def visit_truncatedint(self, typ):
        self.unwrap.append("space.truncatedint(%s)" % (self.nextarg(),))

    def make_fastfunc(unwrap_spec, func):
        unwrap_info = UnwrapSpec_FastFunc_Unwrap()
        unwrap_info.apply_over(unwrap_spec)
        narg = unwrap_info.n
        args = ['space'] + unwrap_info.args
        if args == unwrap_info.unwrap:
            fastfunc = func
        else:
            # try to avoid excessive bloat
            mod = func.__module__
            if mod is None:
                mod = ""
            if mod == 'pypy.interpreter.astcompiler.ast':
                raise FastFuncNotSupported
            if (not mod.startswith('pypy.module.__builtin__') and
                not mod.startswith('pypy.module.sys') and
                not mod.startswith('pypy.module.math')):
                if not func.__name__.startswith('descr'):
                    raise FastFuncNotSupported
            d = {}
            unwrap_info.miniglobals['func'] = func
            source = """if 1:
                def fastfunc_%s_%d(%s):
                    return func(%s)
                \n""" % (func.__name__, narg,
                         ', '.join(args),
                         ', '.join(unwrap_info.unwrap))
            exec compile2(source) in unwrap_info.miniglobals, d
            fastfunc = d['fastfunc_%s_%d' % (func.__name__, narg)]
        return narg, fastfunc
    make_fastfunc = staticmethod(make_fastfunc)

def int_unwrapping_space_method(typ):
    assert typ in (int, str, float, unicode, r_longlong, r_uint, r_ulonglong, bool)
    if typ is r_int is r_longlong:
        return 'gateway_r_longlong_w'
    elif typ in (str, unicode, bool):
        return typ.__name__ + '_w'
    else:
        return 'gateway_' + typ.__name__ + '_w'


def unwrap_spec(*spec, **kwargs):
    """A decorator which attaches the unwrap_spec attribute.
    Use either positional or keyword arguments.
    - positional arguments must be as many as the function parameters
    - keywords arguments allow to change only some parameter specs
    """
    def decorator(func):
        if kwargs:
            if spec:
                raise ValueError("Please specify either positional or "
                                 "keywords arguments")
            func.unwrap_spec = kwargs
        else:
            func.unwrap_spec = spec
        return func
    return decorator

def build_unwrap_spec(func, argnames, self_type=None):
    """build the list of parameter unwrap spec for the function.
    """
    unwrap_spec = getattr(func, 'unwrap_spec', None)

    if isinstance(unwrap_spec, dict):
        kw_spec = unwrap_spec
        unwrap_spec = None
    else:
        kw_spec = {}

    if unwrap_spec is None:
        # build unwrap_spec after the name of arguments
        unwrap_spec = []
        for argname in argnames:
            if argname == 'self':
                unwrap_spec.append('self')
            elif argname == 'space':
                unwrap_spec.append(ObjSpace)
            elif argname == '__args__':
                unwrap_spec.append(Arguments)
            elif argname == 'args_w':
                unwrap_spec.append('args_w')
            elif argname.startswith('w_'):
                unwrap_spec.append(W_Root)
            else:
                unwrap_spec.append(None)

    # apply kw_spec
    for name, spec in kw_spec.items():
        unwrap_spec[argnames.index(name)] = spec

    return unwrap_spec

class BuiltinCode(eval.Code):
    "The code object implementing a built-in (interpreter-level) hook."
    _immutable_ = True
    hidden_applevel = True
    descrmismatch_op = None
    descr_reqcls = None

    # When a BuiltinCode is stored in a Function object,
    # you get the functionality of CPython's built-in function type.

    NOT_RPYTHON_ATTRIBUTES = ['_bltin', '_unwrap_spec']

    def __init__(self, func, unwrap_spec = None, self_type = None,
                 descrmismatch=None):
        "NOT_RPYTHON"
        # 'implfunc' is the interpreter-level function.
        # Note that this uses a lot of (construction-time) introspection.
        eval.Code.__init__(self, func.__name__)
        self.docstring = func.__doc__

        self.identifier = "%s-%s-%s" % (func.__module__, func.__name__,
                                        getattr(self_type, '__name__', '*'))

        # unwrap_spec can be passed to interp2app or
        # attached as an attribute to the function.
        # It is a list of types or singleton objects:
        #  baseobjspace.ObjSpace is used to specify the space argument
        #  baseobjspace.W_Root is for wrapped arguments to keep wrapped
        #  baseobjspace.Wrappable subclasses imply interp_w and a typecheck
        #  argument.Arguments is for a final rest arguments Arguments object
        # 'args_w' for fixedview applied to rest arguments
        # 'w_args' for rest arguments passed as wrapped tuple
        # str,int,float: unwrap argument as such type
        # (function, cls) use function to check/unwrap argument of type cls

        # First extract the signature from the (CPython-level) code object
        from pypy.interpreter import pycode
        argnames, varargname, kwargname = pycode.cpython_code_signature(func.func_code)

        if unwrap_spec is None:
            unwrap_spec = build_unwrap_spec(func, argnames, self_type)

        if self_type:
            assert unwrap_spec[0] == 'self',"self_type without 'self' spec element"
            unwrap_spec = list(unwrap_spec)
            if descrmismatch is not None:
                assert issubclass(self_type, Wrappable)
                unwrap_spec[0] = ('self', self_type)
                self.descrmismatch_op = descrmismatch
                self.descr_reqcls = self_type
            else:
                unwrap_spec[0] = self_type
        else:
            assert descrmismatch is None, (
                "descrmismatch without a self-type specified")


        orig_sig = SignatureBuilder(func, argnames, varargname, kwargname)
        app_sig = SignatureBuilder(func)

        UnwrapSpec_Check(orig_sig).apply_over(unwrap_spec,
                                              app_sig #to populate
                                              )
        self.sig = argnames, varargname, kwargname = app_sig.signature()

        self.minargs = len(argnames)
        if varargname:
            self.maxargs = sys.maxint
        else:
            self.maxargs = self.minargs

        self.activation = UnwrapSpec_EmitRun.make_activation(unwrap_spec, func)
        self._bltin = func
        self._unwrap_spec = unwrap_spec

        # speed hack
        if 0 <= len(unwrap_spec) <= 5:
            try:
                arity, fastfunc = UnwrapSpec_FastFunc_Unwrap.make_fastfunc(
                                                 unwrap_spec, func)
            except FastFuncNotSupported:
                if unwrap_spec == [ObjSpace, Arguments]:
                    self.__class__ = BuiltinCodePassThroughArguments0
                    self.func__args__ = func
                elif unwrap_spec == [ObjSpace, W_Root, Arguments]:
                    self.__class__ = BuiltinCodePassThroughArguments1
                    self.func__args__ = func
            else:
                self.__class__ = globals()['BuiltinCode%d' % arity]
                setattr(self, 'fastfunc_%d' % arity, fastfunc)

    def descr__reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        builtin_code = mod.get('builtin_code')
        return space.newtuple([builtin_code,
                               space.newtuple([space.wrap(self.identifier)])])

    def find(indentifier):
        from pypy.interpreter.function import Function
        return Function._all[indentifier].code
    find = staticmethod(find)

    def signature(self):
        return self.sig

    def getdocstring(self, space):
        return space.wrap(self.docstring)

    def funcrun(self, func, args):
        return BuiltinCode.funcrun_obj(self, func, None, args)

    def funcrun_obj(self, func, w_obj, args):
        space = func.space
        activation = self.activation
        scope_w = args.parse_obj(w_obj, func.name, self.sig,
                                 func.defs_w, self.minargs)
        try:
            w_result = activation._run(space, scope_w)
        except DescrMismatch:
            if w_obj is not None:
                args = args.prepend(w_obj)
            return scope_w[0].descr_call_mismatch(space,
                                                  self.descrmismatch_op,
                                                  self.descr_reqcls,
                                                  args)
        except Exception, e:
            raise self.handle_exception(space, e)
        if w_result is None:
            w_result = space.w_None
        return w_result

    def handle_exception(self, space, e):
        try:
            if not we_are_translated():
                raise
            raise e
        except KeyboardInterrupt:
            raise OperationError(space.w_KeyboardInterrupt,
                                 space.w_None)
        except MemoryError:
            raise OperationError(space.w_MemoryError, space.w_None)
        except rstackovf.StackOverflow, e:
            rstackovf.check_stack_overflow()
            raise space.prebuilt_recursion_error
        except RuntimeError:   # not on top of py.py
            raise OperationError(space.w_RuntimeError, space.w_None)

# (verbose) performance hack below

class BuiltinCodePassThroughArguments0(BuiltinCode):
    _immutable_ = True

    def funcrun(self, func, args):
        space = func.space
        try:
            w_result = self.func__args__(space, args)
        except DescrMismatch:
            return args.firstarg().descr_call_mismatch(space,
                                                  self.descrmismatch_op,
                                                  self.descr_reqcls,
                                                  args)
        except Exception, e:
            raise self.handle_exception(space, e)
        if w_result is None:
            w_result = space.w_None
        return w_result

class BuiltinCodePassThroughArguments1(BuiltinCode):
    _immutable_ = True
    fast_natural_arity = eval.Code.PASSTHROUGHARGS1

    def funcrun_obj(self, func, w_obj, args):
        space = func.space
        try:
            w_result = self.func__args__(space, w_obj, args)
        except DescrMismatch:
            return args.firstarg().descr_call_mismatch(space,
                                                  self.descrmismatch_op,
                                                  self.descr_reqcls,
                                                  args.prepend(w_obj))
        except Exception, e:
            raise self.handle_exception(space, e)
        if w_result is None:
            w_result = space.w_None
        return w_result

class BuiltinCode0(BuiltinCode):
    _immutable_ = True
    fast_natural_arity = 0

    def fastcall_0(self, space, w_func):
        try:
            w_result = self.fastfunc_0(space)
        except DescrMismatch:
            raise OperationError(space.w_SystemError,
                                 space.wrap("unexpected DescrMismatch error"))
        except Exception, e:
            raise self.handle_exception(space, e)
        if w_result is None:
            w_result = space.w_None
        return w_result

class BuiltinCode1(BuiltinCode):
    _immutable_ = True
    fast_natural_arity = 1

    def fastcall_1(self, space, w_func, w1):
        try:
            w_result = self.fastfunc_1(space, w1)
        except DescrMismatch:
            return  w1.descr_call_mismatch(space,
                                           self.descrmismatch_op,
                                           self.descr_reqcls,
                                           Arguments(space, [w1]))
        except Exception, e:
            raise self.handle_exception(space, e)
        if w_result is None:
            w_result = space.w_None
        return w_result

class BuiltinCode2(BuiltinCode):
    _immutable_ = True
    fast_natural_arity = 2

    def fastcall_2(self, space, w_func, w1, w2):
        try:
            w_result = self.fastfunc_2(space, w1, w2)
        except DescrMismatch:
            return  w1.descr_call_mismatch(space,
                                           self.descrmismatch_op,
                                           self.descr_reqcls,
                                           Arguments(space, [w1, w2]))
        except Exception, e:
            raise self.handle_exception(space, e)
        if w_result is None:
            w_result = space.w_None
        return w_result

class BuiltinCode3(BuiltinCode):
    _immutable_ = True
    fast_natural_arity = 3

    def fastcall_3(self, space, func, w1, w2, w3):
        try:
            w_result = self.fastfunc_3(space, w1, w2, w3)
        except DescrMismatch:
            return  w1.descr_call_mismatch(space,
                                           self.descrmismatch_op,
                                           self.descr_reqcls,
                                           Arguments(space, [w1, w2, w3]))
        except Exception, e:
            raise self.handle_exception(space, e)
        if w_result is None:
            w_result = space.w_None
        return w_result

class BuiltinCode4(BuiltinCode):
    _immutable_ = True
    fast_natural_arity = 4

    def fastcall_4(self, space, func, w1, w2, w3, w4):
        try:
            w_result = self.fastfunc_4(space, w1, w2, w3, w4)
        except DescrMismatch:
            return  w1.descr_call_mismatch(space,
                                           self.descrmismatch_op,
                                           self.descr_reqcls,
                                           Arguments(space,
                                                     [w1, w2, w3, w4]))
        except Exception, e:
            raise self.handle_exception(space, e)
        if w_result is None:
            w_result = space.w_None
        return w_result


class interp2app(Wrappable):
    """Build a gateway that calls 'f' at interp-level."""

    # NOTICE interp2app defaults are stored and passed as
    # wrapped values, this to avoid having scope_w be of mixed
    # wrapped and unwrapped types;
    # an exception is made for the NoneNotWrapped special value
    # which is passed around as default as an unwrapped None,
    # unwrapped None and wrapped types are compatible
    #
    # Takes optionally an unwrap_spec, see BuiltinCode

    NOT_RPYTHON_ATTRIBUTES = ['_staticdefs']

    instancecache = {}

    def __new__(cls, f, app_name=None, unwrap_spec = None,
                descrmismatch=None, as_classmethod=False):

        "NOT_RPYTHON"
        # f must be a function whose name does NOT start with 'app_'
        self_type = None
        if hasattr(f, 'im_func'):
            self_type = f.im_class
            f = f.im_func
        if not isinstance(f, types.FunctionType):
            raise TypeError, "function expected, got %r instead" % f
        if app_name is None:
            if f.func_name.startswith('app_'):
                raise ValueError, ("function name %r suspiciously starts "
                                   "with 'app_'" % f.func_name)
            app_name = f.func_name

        if unwrap_spec is not None:
            unwrap_spec_key = tuple(unwrap_spec)
        else:
            unwrap_spec_key = None
        key = (f, self_type, unwrap_spec_key, descrmismatch, as_classmethod)
        if key in cls.instancecache:
            result = cls.instancecache[key]
            assert result.__class__ is cls
            return result
        self = Wrappable.__new__(cls)
        cls.instancecache[key] = self
        self._code = BuiltinCode(f, unwrap_spec=unwrap_spec,
                                 self_type = self_type,
                                 descrmismatch=descrmismatch)
        self.__name__ = f.func_name
        self.name = app_name
        self.as_classmethod = as_classmethod
        self._staticdefs = list(f.func_defaults or ())
        return self

    def _getdefaults(self, space):
        "NOT_RPYTHON"
        defs_w = []
        for val in self._staticdefs:
            if val is NoneNotWrapped:
                defs_w.append(None)
            else:
                defs_w.append(space.wrap(val))
        return defs_w

    # lazy binding to space

    def __spacebind__(self, space):
        # we first make a real Function object out of it
        # and the result is a wrapped version of this Function.
        return self.get_function(space)

    def get_function(self, space):
        return self.getcache(space).getorbuild(self)

    def getcache(self, space):
        return space.fromcache(GatewayCache)


class GatewayCache(SpaceCache):
    def build(cache, gateway):
        "NOT_RPYTHON"
        space = cache.space
        defs = gateway._getdefaults(space) # needs to be implemented by subclass
        code = gateway._code
        fn = FunctionWithFixedCode(space, code, None, defs, forcename = gateway.name)
        if not space.config.translating:
            fn.add_to_table()
        if gateway.as_classmethod:
            fn = ClassMethod(space.wrap(fn))
        return fn


#
# the next gateways are to be used only for
# temporary/initialization purposes

class interp2app_temp(interp2app):
    "NOT_RPYTHON"
    def getcache(self, space):
        return self.__dict__.setdefault(space, GatewayCache(space))


# and now for something completely different ...
#

class ApplevelClass:
    """NOT_RPYTHON
    A container for app-level source code that should be executed
    as a module in the object space;  interphook() builds a static
    interp-level function that invokes the callable with the given
    name at app-level."""

    hidden_applevel = True

    def __init__(self, source, filename=None, modname='__builtin__'):
        # HAAACK (but a good one)
        if filename is None:
            f = sys._getframe(1)
            filename = '<%s:%d>' % (f.f_code.co_filename, f.f_lineno)
        self.filename = filename
        self.source = str(py.code.Source(source).deindent())
        self.modname = modname
        # look at the first three lines for a NOT_RPYTHON tag
        first = "\n".join(source.split("\n", 3)[:3])
        if "NOT_RPYTHON" in first:
            self.can_use_geninterp = False
        else:
            self.can_use_geninterp = True
        # make source code available for tracebacks
        lines = [x + "\n" for x in source.split("\n")]
        py.std.linecache.cache[filename] = (1, None, lines, filename)

    def __repr__(self):
        return "<ApplevelClass filename=%r can_use_geninterp=%r>" % (self.filename, self.can_use_geninterp)

    def getwdict(self, space):
        return space.fromcache(ApplevelCache).getorbuild(self)

    def buildmodule(self, space, name='applevel'):
        from pypy.interpreter.module import Module
        return Module(space, space.wrap(name), self.getwdict(space))

    def wget(self, space, name):
        w_globals = self.getwdict(space)
        return space.getitem(w_globals, space.wrap(name))

    def interphook(self, name):
        "NOT_RPYTHON"
        def appcaller(space, *args_w):
            if not isinstance(space, ObjSpace):
                raise TypeError("first argument must be a space instance.")
            # redirect if the space handles this specially
            # XXX can this be factored a bit less flow space dependently?
            if hasattr(space, 'specialcases'):
                sc = space.specialcases
                if ApplevelClass in sc:
                    ret_w = sc[ApplevelClass](space, self, name, args_w)
                    if ret_w is not None: # it was RPython
                        return ret_w
            # the last argument can be an Arguments
            w_func = self.wget(space, name)
            if not args_w:
                return space.call_function(w_func)
            else:
                args = args_w[-1]
                assert args is not None
                if not isinstance(args, Arguments):
                    return space.call_function(w_func, *args_w)
                else:
                    if len(args_w) == 2:
                        return space.call_obj_args(w_func, args_w[0], args)
                    elif len(args_w) > 2:
                        # xxx is this used at all?
                        # ...which is merged with the previous arguments, if any
                        args = args.replace_arguments(list(args_w[:-1]) +
                                                      args.arguments_w)
            return space.call_args(w_func, args)
        def get_function(space):
            w_func = self.wget(space, name)
            return space.unwrap(w_func)
        appcaller = func_with_new_name(appcaller, name)
        appcaller.get_function = get_function
        return appcaller

    def _freeze_(self):
        return True  # hint for the annotator: applevel instances are constants


class ApplevelCache(SpaceCache):
    """NOT_RPYTHON
    The cache mapping each applevel instance to its lazily built w_dict"""

    def build(self, app):
        "NOT_RPYTHON.  Called indirectly by Applevel.getwdict()."
        if self.space.config.objspace.geninterp and app.can_use_geninterp:
            return PyPyCacheDir.build_applevelinterp_dict(app, self.space)
        else:
            return build_applevel_dict(app, self.space)


# __________ pure applevel version __________

def build_applevel_dict(self, space):
    "NOT_RPYTHON"
    w_glob = space.newdict(module=True)
    space.setitem(w_glob, space.wrap('__name__'), space.wrap(self.modname))
    space.exec_(self.source, w_glob, w_glob,
                hidden_applevel=self.hidden_applevel,
                filename=self.filename)
    return w_glob

# __________ geninterplevel version __________

class PyPyCacheDir:
    "NOT_RPYTHON"
    # similar to applevel, but using translation to interp-level.
    # This version maintains a cache folder with single files.

    def build_applevelinterp_dict(cls, self, space):
        "NOT_RPYTHON"
        # N.B. 'self' is the ApplevelInterp; this is a class method,
        # just so that we have a convenient place to store the global state.
        if not cls._setup_done:
            cls._setup()

        from pypy.translator.geninterplevel import translate_as_module
        import marshal
        scramble = md5(cls.seed)
        scramble.update(marshal.dumps(self.source))
        key = scramble.hexdigest()
        initfunc = cls.known_code.get(key)
        if not initfunc:
            # try to get it from file
            name = key
            if self.filename:
                prename = os.path.splitext(os.path.basename(self.filename))[0]
            else:
                prename = 'zznoname'
            name = "%s_%s" % (prename, name)
            try:
                __import__("pypy._cache."+name)
            except ImportError, x:
                # print x
                pass
            else:
                initfunc = cls.known_code[key]
        if not initfunc:
            # build it and put it into a file
            initfunc, newsrc = translate_as_module(
                self.source, self.filename, self.modname)
            fname = cls.cache_path.join(name+".py").strpath
            f = file(get_tmp_file_name(fname), "w")
            print >> f, """\
# self-destruct on double-click:
if __name__ == "__main__":
    from pypy import _cache
    import os
    namestart = os.path.join(os.path.split(_cache.__file__)[0], '%s')
    for ending in ('.py', '.pyc', '.pyo'):
        try:
            os.unlink(namestart+ending)
        except os.error:
            pass""" % name
            print >> f
            print >> f, newsrc
            print >> f, "from pypy._cache import known_code"
            print >> f, "known_code[%r] = %s" % (key, initfunc.__name__)
            f.close()
            rename_tmp_to_eventual_file_name(fname)
        w_glob = initfunc(space)
        return w_glob
    build_applevelinterp_dict = classmethod(build_applevelinterp_dict)

    _setup_done = False

    def _setup(cls):
        """NOT_RPYTHON"""
        lp = py.path.local
        import pypy, os
        p = lp(pypy.__file__).new(basename='_cache').ensure(dir=1)
        cls.cache_path = p
        ini = p.join('__init__.py')
        try:
            if not ini.check():
                raise ImportError  # don't import if only a .pyc file left!!!
            from pypy._cache import known_code, \
                 GI_VERSION_RENDERED
        except ImportError:
            GI_VERSION_RENDERED = 0
        from pypy.translator.geninterplevel import GI_VERSION
        cls.seed = md5(str(GI_VERSION)).digest()
        if GI_VERSION != GI_VERSION_RENDERED or GI_VERSION is None:
            for pth in p.listdir():
                if pth.check(file=1):
                    try:
                        pth.remove()
                    except: pass
            f = file(get_tmp_file_name(str(ini)), "w")
            f.write("""\
# This folder acts as a cache for code snippets which have been
# compiled by compile_as_module().
# It will get a new entry for every piece of code that has
# not been seen, yet.
#
# Caution! Only the code snippet is checked. If something
# is imported, changes are not detected. Also, changes
# to geninterplevel or gateway are also not checked.
# Exception: There is a checked version number in geninterplevel.py
#
# If in doubt, remove this file from time to time.

GI_VERSION_RENDERED = %r

known_code = {}

# self-destruct on double-click:
def harakiri():
    import pypy._cache as _c
    import py
    lp = py.path.local
    for pth in lp(_c.__file__).dirpath().listdir():
        try:
            pth.remove()
        except: pass

if __name__ == "__main__":
    harakiri()

del harakiri
""" % GI_VERSION)
            f.close()
            rename_tmp_to_eventual_file_name(str(ini))
        import pypy._cache
        cls.known_code = pypy._cache.known_code
        cls._setup_done = True
    _setup = classmethod(_setup)


def gethostname(_cache=[]):
    if not _cache:
        try:
            import socket
            hostname = socket.gethostname()
        except:
            hostname = ''
        _cache.append(hostname)
    return _cache[0]

def get_tmp_file_name(fname):
    return '%s~%s~%d' % (fname, gethostname(), os.getpid())

def rename_tmp_to_eventual_file_name(fname):
    # generated files are first written to the host- and process-specific
    # file 'tmpname', and then atomically moved to their final 'fname'
    # to avoid problems if py.py is started several times in parallel
    tmpname = get_tmp_file_name(fname)
    try:
        os.rename(tmpname, fname)
    except (OSError, IOError):
        os.unlink(fname)    # necessary on Windows
        os.rename(tmpname, fname)

# ____________________________________________________________

def appdef(source, applevel=ApplevelClass, filename=None):
    """ NOT_RPYTHON: build an app-level helper function, like for example:
    myfunc = appdef('''myfunc(x, y):
                           return x+y
                    ''')
    """
    if not isinstance(source, str):
        source = py.std.inspect.getsource(source).lstrip()
        while source.startswith(('@py.test.mark.', '@pytest.mark.')):
            # these decorators are known to return the same function
            # object, we may ignore them
            assert '\n' in source
            source = source[source.find('\n') + 1:].lstrip()
        assert source.startswith("def "), "can only transform functions"
        source = source[4:]
    p = source.find('(')
    assert p >= 0
    funcname = source[:p].strip()
    source = source[p:]
    assert source.strip()
    funcsource = "def %s%s\n"  % (funcname, source)
    #for debugging of wrong source code: py.std.parser.suite(funcsource)
    a = applevel(funcsource, filename=filename)
    return a.interphook(funcname)

applevel = ApplevelClass   # backward compatibility
app2interp = appdef   # backward compatibility


class applevel_temp(ApplevelClass):
    hidden_applevel = False
    def getwdict(self, space):    # no cache
        return build_applevel_dict(self, space)


class applevelinterp_temp(ApplevelClass):
    hidden_applevel = False
    def getwdict(self, space):   # no cache
        return PyPyCacheDir.build_applevelinterp_dict(self, space)

# app2interp_temp is used for testing mainly
def app2interp_temp(func, applevel_temp=applevel_temp, filename=None):
    """ NOT_RPYTHON """
    return appdef(func, applevel_temp, filename=filename)
