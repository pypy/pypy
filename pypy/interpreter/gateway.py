"""

Gateway between app-level and interpreter-level:
* BuiltinCode (call interp-level code from app-level)
* app2interp  (embed an app-level function into an interp-level callable)
* interp2app  (publish an interp-level object to be visible from app-level)
* interpindirect2app (publish an interp-level object to be visible from
                      app-level as an indirect call to implementation)

"""

import sys
import os
import types
import inspect

import py

from pypy.interpreter.eval import Code
from pypy.interpreter.argument import Arguments
from pypy.interpreter.signature import Signature
from pypy.interpreter.baseobjspace import (W_Root, ObjSpace, SpaceCache,
    DescrMismatch)
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.function import ClassMethod, FunctionWithFixedCode
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.rarithmetic import r_longlong, r_int, r_ulonglong, r_uint
from rpython.tool.sourcetools import func_with_new_name, compile2

NO_DEFAULT = object()


# internal non-translatable parts:
class SignatureBuilder(object):
    "NOT_RPYTHON"
    def __init__(self, func=None, argnames=None, varargname=None,
                 kwargname=None, name=None):
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
        self.kwonlyargnames = None

    def append(self, argname):
        if self.kwonlyargnames is None:
            self.argnames.append(argname)
        else:
            self.kwonlyargnames.append(argname)

    def marker_kwonly(self):
        assert self.kwonlyargnames is None
        self.kwonlyargnames = []

    def signature(self):
        return Signature(self.argnames, self.varargname, self.kwargname,
                         self.kwonlyargnames)

#________________________________________________________________


class Unwrapper(object):
    """A base class for custom unwrap_spec items.

    Subclasses must override unwrap().
    """
    def _freeze_(self):
        return True

    def unwrap(self, space, w_value):
        """NOT_RPYTHON"""
        raise NotImplementedError


class UnwrapSpecRecipe(object):
    "NOT_RPYTHON"

    bases_order = [W_Root, ObjSpace, Arguments, Unwrapper, object]

    def dispatch(self, el, *args):
        if isinstance(el, str):
            getattr(self, "visit_%s" % (el,))(el, *args)
        elif isinstance(el, tuple):
            if el[0] == 'INTERNAL:self':
                self.visit_self(el[1], *args)
            else:
                assert False, "not supported any more, use WrappedDefault"
        elif isinstance(el, WrappedDefault):
            self.visit__W_Root(W_Root, *args)
        elif isinstance(el, type):
            for typ in self.bases_order:
                if issubclass(el, typ):
                    visit = getattr(self, "visit__%s" % (typ.__name__,))
                    visit(el, *args)
                    break
            else:
                raise Exception("%s: no match for unwrap_spec element %s" % (
                    self.__class__.__name__, el))
        else:
            raise Exception("unable to dispatch, %s, perhaps your parameter should have started with w_?" % el)

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

    def visit_self(self, cls, app_sig):
        self.visit__W_Root(cls, app_sig)

    def checked_space_method(self, typname, app_sig):
        argname = self.orig_arg()
        assert not argname.startswith('w_'), (
            "unwrapped %s argument %s of built-in function %r in %r should "
            "not start with 'w_'" % (typname, argname, self.func.func_name, self.func.func_globals['__name__']))
        app_sig.append(argname)

    def visit_index(self, index, app_sig):
        self.checked_space_method(index, app_sig)

    def visit_bufferstr(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_str_or_None(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_str0(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_bytes(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_fsencode(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_nonnegint(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_c_int(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_c_uint(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_c_nonnegint(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_c_short(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_c_ushort(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_c_uid_t(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit_truncatedint_w(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit__Unwrapper(self, el, app_sig):
        self.checked_space_method(el, app_sig)

    def visit__ObjSpace(self, el, app_sig):
        self.orig_arg()

    def visit__W_Root(self, el, app_sig):
        argname = self.orig_arg()
        if argname == 'self':
            assert el is not W_Root
            app_sig.append(argname)
            return
        assert argname.startswith('w_'), (
            "argument %s of built-in function %r in %r should "
            "start with 'w_'" % (argname, self.func.func_name, self.func.func_globals['__name__']))
        app_sig.append(argname[2:])

    def visit__Arguments(self, el, app_sig):
        self.orig_arg()
        assert app_sig.varargname is None, (
            "built-in function %r has conflicting rest args specs" % self.func)
        app_sig.varargname = 'args'
        app_sig.kwargname = 'keywords'

    def visit_args_w(self, el, app_sig):
        argname = self.orig_arg()
        assert argname.endswith('_w'), (
            "rest arguments arg %s of built-in function %r should end in '_w'" %
            (argname, self.func))
        assert app_sig.varargname is None, (
            "built-in function %r has conflicting rest args specs" % self.func)
        app_sig.varargname = argname[:-2]

    def visit_w_args(self, el, app_sig):
        argname = self.orig_arg()
        assert argname.startswith('w_'), (
            "rest arguments arg %s of built-in function %r should start 'w_'" %
            (argname, self.func))
        assert app_sig.varargname is None, (
            "built-in function %r has conflicting rest args specs" % self.func)
        app_sig.varargname = argname[2:]

    def visit__object(self, typ, app_sig):
        name = int_unwrapping_space_method(typ)
        self.checked_space_method(name, app_sig)

    def visit_kwonly(self, _, app_sig):
        argname = self.orig_arg()
        assert argname == '__kwonly__'
        app_sig.marker_kwonly()


class UnwrapSpec_EmitRun(UnwrapSpecEmit):

    # collect code to emit for interp2app builtin frames based on unwrap_spec

    def __init__(self):
        UnwrapSpecEmit.__init__(self)
        self.run_args = []

    def scopenext(self):
        return "scope_w[%d]" % self.succ()

    def visit_self(self, typ):
        self.run_args.append("space.descr_self_interp_w(%s, %s)" %
                             (self.use(typ), self.scopenext()))

    def visit__Unwrapper(self, typ):
        self.run_args.append("%s().unwrap(space, %s)" %
                             (self.use(typ), self.scopenext()))

    def visit__ObjSpace(self, el):
        self.run_args.append('space')

    def visit__W_Root(self, el):
        if el is not W_Root:
            self.run_args.append("space.interp_w(%s, %s)" % (self.use(el),
                                                         self.scopenext()))
        else:
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

    def visit_str0(self, typ):
        self.run_args.append("space.str0_w(%s)" % (self.scopenext(),))

    def visit_bytes(self, typ):
        self.run_args.append("space.bytes_w(%s)" % (self.scopenext(),))

    def visit_fsencode(self, typ):
        self.run_args.append("space.fsencode_w(%s)" % (self.scopenext(),))

    def visit_nonnegint(self, typ):
        self.run_args.append("space.gateway_nonnegint_w(%s)" % (
            self.scopenext(),))

    def visit_c_int(self, typ):
        self.run_args.append("space.c_int_w(%s)" % (self.scopenext(),))

    def visit_c_uint(self, typ):
        self.run_args.append("space.c_uint_w(%s)" % (self.scopenext(),))

    def visit_c_nonnegint(self, typ):
        self.run_args.append("space.c_nonnegint_w(%s)" % (self.scopenext(),))

    def visit_c_short(self, typ):
        self.run_args.append("space.c_short_w(%s)" % (self.scopenext(),))

    def visit_c_ushort(self, typ):
        self.run_args.append("space.c_ushort_w(%s)" % (self.scopenext(),))

    def visit_c_uid_t(self, typ):
        self.run_args.append("space.c_uid_t_w(%s)" % (self.scopenext(),))

    def visit_truncatedint_w(self, typ):
        self.run_args.append("space.truncatedint_w(%s)" % (self.scopenext(),))

    def visit_kwonly(self, typ):
        self.run_args.append("None")

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
                elif isinstance(el, WrappedDefault):
                    parts.append('W_Root')
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
        raise TypeError("abstract")

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

    def visit_self(self, typ):
        self.unwrap.append("space.descr_self_interp_w(%s, %s)" %
                           (self.use(typ), self.nextarg()))

    def visit__Unwrapper(self, typ):
        self.unwrap.append("%s().unwrap(space, %s)" %
                           (self.use(typ), self.nextarg()))

    def visit__ObjSpace(self, el):
        if self.finger > 1:
            raise FastFuncNotSupported
        self.unwrap.append("space")

    def visit__W_Root(self, el):
        if el is not W_Root:
            self.unwrap.append("space.interp_w(%s, %s)" % (self.use(el),
                                                           self.nextarg()))
        else:
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

    def visit_str0(self, typ):
        self.unwrap.append("space.str0_w(%s)" % (self.nextarg(),))

    def visit_bytes(self, typ):
        self.unwrap.append("space.bytes_w(%s)" % (self.nextarg(),))

    def visit_fsencode(self, typ):
        self.unwrap.append("space.fsencode_w(%s)" % (self.nextarg(),))

    def visit_nonnegint(self, typ):
        self.unwrap.append("space.gateway_nonnegint_w(%s)" % (self.nextarg(),))

    def visit_c_int(self, typ):
        self.unwrap.append("space.c_int_w(%s)" % (self.nextarg(),))

    def visit_c_uint(self, typ):
        self.unwrap.append("space.c_uint_w(%s)" % (self.nextarg(),))

    def visit_c_nonnegint(self, typ):
        self.unwrap.append("space.c_nonnegint_w(%s)" % (self.nextarg(),))

    def visit_c_short(self, typ):
        self.unwrap.append("space.c_short_w(%s)" % (self.nextarg(),))

    def visit_c_ushort(self, typ):
        self.unwrap.append("space.c_ushort_w(%s)" % (self.nextarg(),))

    def visit_c_uid_t(self, typ):
        self.unwrap.append("space.c_uid_t_w(%s)" % (self.nextarg(),))

    def visit_truncatedint_w(self, typ):
        self.unwrap.append("space.truncatedint_w(%s)" % (self.nextarg(),))

    def visit_kwonly(self, typ):
        raise FastFuncNotSupported

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
            #if (not mod.startswith('pypy.module.__builtin__') and
            #    not mod.startswith('pypy.module.sys') and
            #    not mod.startswith('pypy.module.math')):
            #    if not func.__name__.startswith('descr'):
            #        raise FastFuncNotSupported
            d = {}
            unwrap_info.miniglobals['func'] = func
            source = """if 1:
                def fastfunc_%s_%d(%s):
                    return func(%s)
                \n""" % (func.__name__.replace('-', '_'), narg,
                         ', '.join(args),
                         ', '.join(unwrap_info.unwrap))
            exec compile2(source) in unwrap_info.miniglobals, d
            fastfunc = d['fastfunc_%s_%d' % (func.__name__.replace('-', '_'), narg)]
        return narg, fastfunc
    make_fastfunc = staticmethod(make_fastfunc)


def int_unwrapping_space_method(typ):
    assert typ in (int, str, float, unicode, r_longlong, r_uint, r_ulonglong, bool)
    if typ is r_int is r_longlong:
        return 'gateway_r_longlong_w'
    elif typ in (str, unicode):
        return typ.__name__ + '_w'
    elif typ is bool:
        # For argument clinic's "bool" specifier: accept any object, and
        # convert it to a boolean value.  If you don't want this
        # behavior, you need to say "int" in the unwrap_spec().  Please
        # use only to emulate "bool" in argument clinic or the 'p'
        # letter in PyArg_ParseTuple().  Accepting *anything* when a
        # boolean flag is expected feels like it comes straight from
        # JavaScript: it is a sure way to hide bugs imho <arigo>.
        return 'is_true'
    else:
        return 'gateway_' + typ.__name__ + '_w'


def unwrap_spec(*spec, **kwargs):
    """A decorator which attaches the unwrap_spec attribute.
    Use either positional or keyword arguments.
    - positional arguments must be as many as the function parameters
    - keywords arguments allow to change only some parameter specs
    """
    assert spec or kwargs
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

class WrappedDefault(object):
    """ Can be used inside unwrap_spec as WrappedDefault(3) which means
    it'll be treated as W_Root, but fed with default which will be a wrapped
    argument to constructor.
    """
    def __init__(self, default_value):
        self.default_value = default_value


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
            elif argname == '__kwonly__':
                unwrap_spec.append('kwonly')
            else:
                unwrap_spec.append(None)

    # apply kw_spec
    for name, spec in kw_spec.items():
        try:
            unwrap_spec[argnames.index(name)] = spec
        except ValueError:
            raise ValueError("unwrap_spec() got a keyword %r but it is not "
                             "the name of an argument of the following "
                             "function" % (name,))

    return unwrap_spec


class BuiltinCode(Code):
    "The code object implementing a built-in (interpreter-level) hook."
    _immutable_ = True
    hidden_applevel = True
    descrmismatch_op = None
    descr_reqcls = None

    # When a BuiltinCode is stored in a Function object,
    # you get the functionality of CPython's built-in function type.

    def __init__(self, func, unwrap_spec=None, self_type=None,
                 descrmismatch=None, doc=None):
        "NOT_RPYTHON"
        # 'implfunc' is the interpreter-level function.
        # Note that this uses a lot of (construction-time) introspection.
        Code.__init__(self, func.__name__)
        self.docstring = doc or func.__doc__

        self.identifier = "%s-%s-%s" % (func.__module__, func.__name__,
                                        getattr(self_type, '__name__', '*'))

        # unwrap_spec can be passed to interp2app or
        # attached as an attribute to the function.
        # It is a list of types or singleton objects:
        #  baseobjspace.ObjSpace is used to specify the space argument
        #  baseobjspace.W_Root is for wrapped arguments to keep wrapped
        #  argument.Arguments is for a final rest arguments Arguments object
        # 'args_w' for fixedview applied to rest arguments
        # 'w_args' for rest arguments passed as wrapped tuple
        # str,int,float: unwrap argument as such type
        # (function, cls) use function to check/unwrap argument of type cls

        # First extract the signature from the (CPython-level) code object
        from pypy.interpreter import pycode
        sig = pycode.cpython_code_signature(func.func_code)
        argnames = sig.argnames
        varargname = sig.varargname
        kwargname = sig.kwargname
        if sig.kwonlyargnames:
            import pdb; pdb.set_trace()
        self._argnames = argnames

        if unwrap_spec is None:
            unwrap_spec = build_unwrap_spec(func, argnames, self_type)

        if self_type:
            assert unwrap_spec[0] == 'self', "self_type without 'self' spec element"
            unwrap_spec = list(unwrap_spec)
            if descrmismatch is not None:
                assert issubclass(self_type, W_Root)
                unwrap_spec[0] = ('INTERNAL:self', self_type)
                self.descrmismatch_op = descrmismatch
                self.descr_reqcls = self_type
            else:
                unwrap_spec[0] = self_type
        else:
            assert descrmismatch is None, (
                "descrmismatch without a self-type specified")

        orig_sig = SignatureBuilder(func, argnames, varargname, kwargname)
        app_sig = SignatureBuilder(func)

        UnwrapSpec_Check(orig_sig).apply_over(unwrap_spec, app_sig)
        self.sig = app_sig.signature()
        argnames = self.sig.argnames
        varargname = self.sig.varargname

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
                elif unwrap_spec == [self_type, ObjSpace, Arguments]:
                    self.__class__ = BuiltinCodePassThroughArguments1
                    miniglobals = {'func': func, 'self_type': self_type}
                    d = {}
                    source = """if 1:
                        def _call(space, w_obj, args):
                            self = space.descr_self_interp_w(self_type, w_obj)
                            return func(self, space, args)
                        \n"""
                    exec compile2(source) in miniglobals, d
                    self.func__args__ = d['_call']
            else:
                self.__class__ = globals()['BuiltinCode%d' % arity]
                setattr(self, 'fastfunc_%d' % arity, fastfunc)

    def descr__reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod = space.getbuiltinmodule('_pickle_support')
        mod = space.interp_w(MixedModule, w_mod)
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
                                 func.defs_w, func.w_kw_defs, self.minargs)
        try:
            w_result = activation._run(space, scope_w)
        except DescrMismatch:
            if w_obj is not None:
                args = args.prepend(w_obj)
            return scope_w[0].descr_call_mismatch(space,
                                                  self.descrmismatch_op,
                                                  self.descr_reqcls,
                                                  args)
        except Exception as e:
            self.handle_exception(space, e)
            w_result = None
        if w_result is None:
            w_result = space.w_None
        return w_result

    def handle_exception(self, space, e):
        try:
            if not we_are_translated():
                raise
            raise e
        except OperationError:
            raise
        except Exception as e:      # general fall-back
            from pypy.interpreter import error
            raise error.get_converted_unexpected_exception(space, e)

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
        except Exception as e:
            self.handle_exception(space, e)
            w_result = None
        if w_result is None:
            w_result = space.w_None
        return w_result


class BuiltinCodePassThroughArguments1(BuiltinCode):
    _immutable_ = True
    fast_natural_arity = Code.PASSTHROUGHARGS1

    def funcrun_obj(self, func, w_obj, args):
        space = func.space
        try:
            w_result = self.func__args__(space, w_obj, args)
        except DescrMismatch:
            return args.firstarg().descr_call_mismatch(space,
                                                  self.descrmismatch_op,
                                                  self.descr_reqcls,
                                                  args.prepend(w_obj))
        except Exception as e:
            self.handle_exception(space, e)
            w_result = None
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
            raise oefmt(space.w_SystemError, "unexpected DescrMismatch error")
        except Exception as e:
            self.handle_exception(space, e)
            w_result = None
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
            return w1.descr_call_mismatch(space,
                                          self.descrmismatch_op,
                                          self.descr_reqcls,
                                          Arguments(space, [w1]))
        except Exception as e:
            self.handle_exception(space, e)
            w_result = None
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
            return w1.descr_call_mismatch(space,
                                          self.descrmismatch_op,
                                          self.descr_reqcls,
                                          Arguments(space, [w1, w2]))
        except Exception as e:
            self.handle_exception(space, e)
            w_result = None
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
            return w1.descr_call_mismatch(space,
                                          self.descrmismatch_op,
                                          self.descr_reqcls,
                                          Arguments(space, [w1, w2, w3]))
        except Exception as e:
            self.handle_exception(space, e)
            w_result = None
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
            return w1.descr_call_mismatch(space,
                                          self.descrmismatch_op,
                                          self.descr_reqcls,
                                          Arguments(space,
                                                    [w1, w2, w3, w4]))
        except Exception as e:
            self.handle_exception(space, e)
            w_result = None
        if w_result is None:
            w_result = space.w_None
        return w_result

def interpindirect2app(unbound_meth, unwrap_spec=None):
    base_cls = unbound_meth.im_class
    func = unbound_meth.im_func
    args = inspect.getargs(func.func_code)
    if args.varargs or args.keywords:
        raise TypeError("Varargs and keywords not supported in unwrap_spec")
    argspec = ', '.join([arg for arg in args.args[1:]])
    func_code = py.code.Source("""
    def f(self, %(args)s):
        return self.%(func_name)s(%(args)s)
    """ % {'args': argspec, 'func_name': func.func_name})
    d = {}
    exec func_code.compile() in d
    f = d['f']
    f.func_defaults = unbound_meth.func_defaults
    f.func_doc = unbound_meth.func_doc
    f.__module__ = func.__module__
    # necessary for unique identifiers for pickling
    f.func_name = func.func_name
    if unwrap_spec is None:
        unwrap_spec = getattr(unbound_meth, 'unwrap_spec', {})
    else:
        assert isinstance(unwrap_spec, dict)
        unwrap_spec = unwrap_spec.copy()
    unwrap_spec['self'] = base_cls
    return interp2app(globals()['unwrap_spec'](**unwrap_spec)(f))

class interp2app(W_Root):
    """Build a gateway that calls 'f' at interp-level."""

    # Takes optionally an unwrap_spec, see BuiltinCode

    instancecache = {}

    def __new__(cls, f, app_name=None, unwrap_spec=None, descrmismatch=None,
                as_classmethod=False, doc=None):

        "NOT_RPYTHON"
        # f must be a function whose name does NOT start with 'app_'
        self_type = None
        if hasattr(f, 'im_func'):
            self_type = f.im_class
            f = f.im_func
        if not isinstance(f, types.FunctionType):
            raise TypeError("function expected, got %r instead" % f)
        if app_name is None:
            if f.func_name.startswith('app_'):
                raise ValueError("function name %r suspiciously starts "
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
        self = W_Root.__new__(cls)
        cls.instancecache[key] = self
        self._code = BuiltinCode(f, unwrap_spec=unwrap_spec,
                                 self_type=self_type,
                                 descrmismatch=descrmismatch,
                                 doc=doc)
        self.__name__ = f.func_name
        self.name = app_name
        self.as_classmethod = as_classmethod

        argnames = self._code._argnames
        defaults = f.func_defaults or ()
        self._staticdefs = dict(zip(
            argnames[len(argnames) - len(defaults):], defaults))

        return self

    def _getdefaults(self, space):
        "NOT_RPYTHON"
        alldefs_w = {}
        assert len(self._code._argnames) == len(self._code._unwrap_spec)
        for name, spec in zip(self._code._argnames, self._code._unwrap_spec):
            if name == '__kwonly__':
                continue

            defaultval = self._staticdefs.get(name, NO_DEFAULT)
            w_def = Ellipsis
            if name.startswith('w_'):
                assert defaultval in (NO_DEFAULT, None), (
                    "%s: default value for '%s' can only be None, got %r; "
                    "use unwrap_spec(...=WrappedDefault(default))" % (
                    self._code.identifier, name, defaultval))
                if defaultval is None:
                    w_def = None

            if isinstance(spec, tuple) and spec[0] is W_Root:
                assert False, "use WrappedDefault"
            elif isinstance(spec, WrappedDefault):
                assert name.startswith('w_')
                defaultval = spec.default_value
                w_def = Ellipsis

            if defaultval is not NO_DEFAULT:
                if name != '__args__' and name != 'args_w':
                    if w_def is Ellipsis:
                        if isinstance(defaultval, str) and spec not in [str]:
                            w_def = space.newbytes(defaultval)
                        else:
                            w_def = space.wrap(defaultval)
                    if name.startswith('w_'):
                        name = name[2:]
                    alldefs_w[name] = w_def
        #
        # Here, 'alldefs_w' maps some argnames to their wrapped default
        # value.  We return two lists:
        #  - a list of defaults for positional arguments, which covers
        #    some suffix of the sig.argnames list
        #  - a list of pairs (w_name, w_def) for kwonly arguments
        #
        sig = self._code.sig
        first_defined = 0
        while (first_defined < len(sig.argnames) and
               sig.argnames[first_defined] not in alldefs_w):
            first_defined += 1
        defs_w = [alldefs_w.pop(name) for name in sig.argnames[first_defined:]]

        kw_defs_w = None
        if alldefs_w:
            kw_defs_w = []
            for name, w_def in sorted(alldefs_w.items()):
                assert name in sig.kwonlyargnames
                w_name = space.newunicode(name.decode('utf-8'))
                kw_defs_w.append((w_name, w_def))

        return defs_w, kw_defs_w

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
        defs_w, kw_defs_w = gateway._getdefaults(space)
        code = gateway._code
        fn = FunctionWithFixedCode(space, code, None, defs_w, kw_defs_w,
                                   forcename=gateway.name)
        if not space.config.translating:
            fn.add_to_table()
        if gateway.as_classmethod:
            fn = ClassMethod(space.wrap(fn))
        #
        from pypy.module.sys.vm import exc_info
        if code._bltin is exc_info:
            assert space._code_of_sys_exc_info is None
            space._code_of_sys_exc_info = code
        #
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
        self.filename = filename
        self.source = str(py.code.Source(source).deindent())
        self.modname = modname
        if filename is None:
            f = sys._getframe(1)
            filename = '<%s:%d>' % (f.f_code.co_filename, f.f_lineno)
        if not os.path.exists(filename):
            # make source code available for tracebacks
            lines = [x + "\n" for x in source.split("\n")]
            py.std.linecache.cache[filename] = (1, None, lines, filename)
        self.filename = filename

    def __repr__(self):
        return "<ApplevelClass filename=%r>" % (self.filename,)

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

# ____________________________________________________________


def appdef(source, applevel=ApplevelClass, filename=None):
    """ NOT_RPYTHON: build an app-level helper function, like for example:
    myfunc = appdef('''myfunc(x, y):
                           return x+y
                    ''')
    """
    prefix = ""
    if not isinstance(source, str):
        flags = source.__code__.co_flags
        source = py.std.inspect.getsource(source).lstrip()
        while source.startswith(('@py.test.mark.', '@pytest.mark.')):
            # these decorators are known to return the same function
            # object, we may ignore them
            assert '\n' in source
            source = source[source.find('\n') + 1:].lstrip()
        assert source.startswith("def "), "can only transform functions"
        source = source[4:]
        # The following flags have no effect any more in app-level code
        # (i.e. they are always on anyway), and have been removed:
        #    CO_FUTURE_DIVISION
        #    CO_FUTURE_ABSOLUTE_IMPORT
        #    CO_FUTURE_PRINT_FUNCTION
        #    CO_FUTURE_UNICODE_LITERALS
        # Original code was, for each of these flags:
        #    if flags & __future__.CO_xxx:
        #        prefix += "from __future__ import yyy\n"
    p = source.find('(')
    assert p >= 0
    funcname = source[:p].strip()
    source = source[p:]
    assert source.strip()
    funcsource = prefix + "def %s%s\n" % (funcname, source)
    #for debugging of wrong source code: py.std.parser.suite(funcsource)
    a = applevel(funcsource, filename=filename)
    return a.interphook(funcname)

applevel = ApplevelClass   # backward compatibility
app2interp = appdef   # backward compatibility


class applevel_temp(ApplevelClass):
    hidden_applevel = False
    def getwdict(self, space):    # no cache
        return build_applevel_dict(self, space)


# app2interp_temp is used for testing mainly
def app2interp_temp(func, applevel_temp=applevel_temp, filename=None):
    """ NOT_RPYTHON """
    return appdef(func, applevel_temp, filename=filename)
