"""Implements the core parts of flow graph creation, in tandem
with rpython.flowspace.flowcontext.
"""

import __builtin__
import sys
import types
from inspect import CO_NEWLOCALS

from rpython.flowspace.argument import CallSpec
from rpython.flowspace.model import (Constant, Variable, WrapException,
    UnwrapException, checkgraph)
from rpython.flowspace.bytecode import HostCode
from rpython.flowspace import operation
from rpython.flowspace.flowcontext import (FlowSpaceFrame, fixeggblocks,
    FSException, FlowingError)
from rpython.flowspace.generator import (tweak_generator_graph,
        bootstrap_generator)
from rpython.flowspace.pygraph import PyGraph
from rpython.flowspace.specialcase import SPECIAL_CASES
from rpython.rlib.unroll import unrolling_iterable, _unroller
from rpython.rlib import rstackovf, rarithmetic
from rpython.rlib.rarithmetic import is_valid_int


# method-wrappers have not enough introspection in CPython
if hasattr(complex.real.__get__, 'im_self'):
    type_with_bad_introspection = None     # on top of PyPy
else:
    type_with_bad_introspection = type(complex.real.__get__)

# the following gives us easy access to declare more for applications:
NOT_REALLY_CONST = {
    Constant(sys): {
        Constant('maxint'): True,
        Constant('maxunicode'): True,
        Constant('api_version'): True,
        Constant('exit'): True,
        Constant('exc_info'): True,
        Constant('getrefcount'): True,
        Constant('getdefaultencoding'): True,
        # this is an incomplete list of true constants.
        # if we add much more, a dedicated class
        # might be considered for special objects.
        }
    }

def _assert_rpythonic(func):
    """Raise ValueError if ``func`` is obviously not RPython"""
    if func.func_doc and func.func_doc.lstrip().startswith('NOT_RPYTHON'):
        raise ValueError("%r is tagged as NOT_RPYTHON" % (func,))
    if func.func_code.co_cellvars:
        raise ValueError("RPython functions cannot create closures")
    if not (func.func_code.co_flags & CO_NEWLOCALS):
        raise ValueError("The code object for a RPython function should have "
                "the flag CO_NEWLOCALS set.")


# ______________________________________________________________________
class FlowObjSpace(object):
    """NOT_RPYTHON.
    The flow objspace space is used to produce a flow graph by recording
    the space operations that the interpreter generates when it interprets
    (the bytecode of) some function.
    """
    w_None = Constant(None)
    builtin = Constant(__builtin__)
    sys = Constant(sys)
    w_False = Constant(False)
    w_True = Constant(True)
    w_type = Constant(type)
    w_tuple = Constant(tuple)
    for exc in [KeyError, ValueError, IndexError, StopIteration,
                AssertionError, TypeError, AttributeError, ImportError]:
        clsname = exc.__name__
        locals()['w_' + clsname] = Constant(exc)

    # the following exceptions should not show up
    # during flow graph construction
    w_NameError = 'NameError'
    w_UnboundLocalError = 'UnboundLocalError'

    specialcases = SPECIAL_CASES
    # objects which should keep their SomeObjectness
    not_really_const = NOT_REALLY_CONST

    def build_flow(self, func):
        return build_flow(func, self)

    def is_w(self, w_one, w_two):
        return self.is_true(self.is_(w_one, w_two))

    is_ = None     # real version added by add_operations()
    id  = None     # real version added by add_operations()

    def newdict(self, module="ignored"):
        return self.frame.do_operation('newdict')

    def newtuple(self, args_w):
        if all(isinstance(w_arg, Constant) for w_arg in args_w):
            content = [w_arg.value for w_arg in args_w]
            return Constant(tuple(content))
        else:
            return self.frame.do_operation('newtuple', *args_w)

    def newlist(self, args_w, sizehint=None):
        return self.frame.do_operation('newlist', *args_w)

    def newslice(self, w_start, w_stop, w_step):
        return self.frame.do_operation('newslice', w_start, w_stop, w_step)

    def newbool(self, b):
        if b:
            return self.w_True
        else:
            return self.w_False

    def newfunction(self, w_code, w_globals, defaults_w):
        try:
            code = self.unwrap(w_code)
            globals = self.unwrap(w_globals)
            defaults = tuple([self.unwrap(value) for value in defaults_w])
        except UnwrapException:
            raise FlowingError(self.frame, "Dynamically created function must"
                    " have constant default values.")
        fn = types.FunctionType(code, globals, code.co_name, defaults)
        return Constant(fn)

    def wrap(self, obj):
        if isinstance(obj, (Variable, Constant)):
            raise TypeError("already wrapped: " + repr(obj))
        # method-wrapper have ill-defined comparison and introspection
        # to appear in a flow graph
        if type(obj) is type_with_bad_introspection:
            raise WrapException
        return Constant(obj)

    def int_w(self, w_obj):
        if isinstance(w_obj, Constant):
            val = w_obj.value
            if not is_valid_int(val):
                raise TypeError("expected integer: " + repr(w_obj))
            return val
        return self.unwrap(w_obj)

    def uint_w(self, w_obj):
        if isinstance(w_obj, Constant):
            val = w_obj.value
            if type(val) is not rarithmetic.r_uint:
                raise TypeError("expected unsigned: " + repr(w_obj))
            return val
        return self.unwrap(w_obj)


    def str_w(self, w_obj):
        if isinstance(w_obj, Constant):
            val = w_obj.value
            if type(val) is not str:
                raise TypeError("expected string: " + repr(w_obj))
            return val
        return self.unwrap(w_obj)

    def float_w(self, w_obj):
        if isinstance(w_obj, Constant):
            val = w_obj.value
            if type(val) is not float:
                raise TypeError("expected float: " + repr(w_obj))
            return val
        return self.unwrap(w_obj)

    def unwrap(self, w_obj):
        if isinstance(w_obj, Variable):
            raise UnwrapException
        elif isinstance(w_obj, Constant):
            return w_obj.value
        else:
            raise TypeError("not wrapped: " + repr(w_obj))

    def exception_issubclass_w(self, w_cls1, w_cls2):
        return self.is_true(self.issubtype(w_cls1, w_cls2))

    def _exception_match(self, w_exc_type, w_check_class):
        """Helper for exception_match

        Handles the base case where w_check_class is a constant exception
        type.
        """
        if self.is_w(w_exc_type, w_check_class):
            return True   # fast path (also here to handle string exceptions)
        try:
            return self.exception_issubclass_w(w_exc_type, w_check_class)
        except FSException, e:
            if e.match(self, self.w_TypeError):   # string exceptions maybe
                return False
            raise

    def exception_match(self, w_exc_type, w_check_class):
        """Checks if the given exception type matches 'w_check_class'."""
        try:
            check_class = self.unwrap(w_check_class)
        except UnwrapException:
            raise FlowingError(self.frame, "Non-constant except guard.")
        if check_class in (NotImplementedError, AssertionError):
            raise FlowingError(self.frame,
                "Catching %s is not valid in RPython" % check_class.__name__)
        if not isinstance(check_class, tuple):
            # the simple case
            return self._exception_match(w_exc_type, w_check_class)
        # special case for StackOverflow (see rlib/rstackovf.py)
        if check_class == rstackovf.StackOverflow:
            w_real_class = self.wrap(rstackovf._StackOverflow)
            return self._exception_match(w_exc_type, w_real_class)
        # checking a tuple of classes
        for w_klass in self.unpackiterable(w_check_class):
            if self.exception_match(w_exc_type, w_klass):
                return True
        return False

    def exc_from_raise(self, w_arg1, w_arg2):
        """
        Create a wrapped exception from the arguments of a raise statement.

        Returns an FSException object whose w_value is an instance of w_type.
        """
        if self.isinstance_w(w_arg1, self.w_type):
            # this is for all cases of the form (Class, something)
            if self.is_w(w_arg2, self.w_None):
                # raise Type: we assume we have to instantiate Type
                w_value = self.call_function(w_arg1)
            else:
                w_valuetype = self.type(w_arg2)
                if self.exception_issubclass_w(w_valuetype, w_arg1):
                    # raise Type, Instance: let etype be the exact type of value
                    w_value = w_arg2
                else:
                    # raise Type, X: assume X is the constructor argument
                    w_value = self.call_function(w_arg1, w_arg2)
        else:
            # the only case left here is (inst, None), from a 'raise inst'.
            if not self.is_w(w_arg2, self.w_None):
                raise FSException(self.w_TypeError, self.wrap(
                    "instance exception may not have a separate value"))
            w_value = w_arg1
        w_type = self.type(w_value)
        return FSException(w_type, w_value)

    def unpackiterable(self, w_iterable):
        if isinstance(w_iterable, Constant):
            l = w_iterable.value
            return [self.wrap(x) for x in l]
        else:
            raise UnwrapException("cannot unpack a Variable iterable ")

    def unpack_sequence(self, w_iterable, expected_length):
        if isinstance(w_iterable, Constant):
            l = list(self.unwrap(w_iterable))
            if len(l) != expected_length:
                raise ValueError
            return [self.wrap(x) for x in l]
        else:
            w_len = self.len(w_iterable)
            w_correct = self.eq(w_len, self.wrap(expected_length))
            if not self.is_true(w_correct):
                e = self.exc_from_raise(self.w_ValueError, self.w_None)
                raise e
            return [self.frame.do_operation('getitem', w_iterable, self.wrap(i))
                        for i in range(expected_length)]

    # ____________________________________________________________
    def not_(self, w_obj):
        return self.wrap(not self.is_true(w_obj))

    def is_true(self, w_obj):
        if w_obj.foldable():
            return bool(w_obj.value)
        w_truthvalue = self.frame.do_operation('is_true', w_obj)
        return self.frame.guessbool(w_truthvalue)

    def iter(self, w_iterable):
        if isinstance(w_iterable, Constant):
            iterable = w_iterable.value
            if isinstance(iterable, unrolling_iterable):
                return self.wrap(iterable.get_unroller())
        w_iter = self.frame.do_operation("iter", w_iterable)
        return w_iter

    def next(self, w_iter):
        frame = self.frame
        if isinstance(w_iter, Constant):
            it = w_iter.value
            if isinstance(it, _unroller):
                try:
                    v, next_unroller = it.step()
                except IndexError:
                    raise FSException(self.w_StopIteration, self.w_None)
                else:
                    frame.replace_in_stack(it, next_unroller)
                    return self.wrap(v)
        w_item = frame.do_operation("next", w_iter)
        frame.handle_implicit_exceptions([StopIteration, RuntimeError])
        return w_item

    def setitem(self, w_obj, w_key, w_val):
        # protect us from globals write access
        if w_obj is self.frame.w_globals:
            raise FlowingError(self.frame,
                    "Attempting to modify global variable  %r." % (w_key))
        return self.frame.do_operation_with_implicit_exceptions('setitem',
                w_obj, w_key, w_val)

    def setitem_str(self, w_obj, key, w_value):
        return self.setitem(w_obj, self.wrap(key), w_value)

    def getattr(self, w_obj, w_name):
        # handling special things like sys
        # unfortunately this will never vanish with a unique import logic :-(
        if w_obj in self.not_really_const:
            const_w = self.not_really_const[w_obj]
            if w_name not in const_w:
                return self.frame.do_operation_with_implicit_exceptions('getattr',
                                                                w_obj, w_name)
        if w_obj.foldable() and w_name.foldable():
            obj, name = w_obj.value, w_name.value
            try:
                result = getattr(obj, name)
            except Exception, e:
                etype = e.__class__
                msg = "getattr(%s, %s) always raises %s: %s" % (
                    obj, name, etype, e)
                raise FlowingError(self.frame, msg)
            try:
                return self.wrap(result)
            except WrapException:
                pass
        return self.frame.do_operation_with_implicit_exceptions('getattr',
                w_obj, w_name)

    def isinstance_w(self, w_obj, w_type):
        return self.is_true(self.isinstance(w_obj, w_type))

    def import_name(self, name, glob=None, loc=None, frm=None, level=-1):
        try:
            mod = __import__(name, glob, loc, frm, level)
        except ImportError, e:
            raise FSException(self.w_ImportError, self.wrap(str(e)))
        return self.wrap(mod)

    def import_from(self, w_module, w_name):
        assert isinstance(w_module, Constant)
        assert isinstance(w_name, Constant)
        # handle sys
        if w_module in self.not_really_const:
            const_w = self.not_really_const[w_obj]
            if w_name not in const_w:
                return self.frame.do_operation_with_implicit_exceptions('getattr',
                                                                w_obj, w_name)
        try:
            return self.wrap(getattr(w_module.value, w_name.value))
        except AttributeError:
            raise FSException(self.w_ImportError,
                self.wrap("cannot import name '%s'" % w_name.value))

    def call_method(self, w_obj, methname, *arg_w):
        w_meth = self.getattr(w_obj, self.wrap(methname))
        return self.call_function(w_meth, *arg_w)

    def call_function(self, w_func, *args_w):
        args = CallSpec(list(args_w))
        return self.call_args(w_func, args)

    def appcall(self, func, *args_w):
        """Call an app-level RPython function directly"""
        w_func = self.wrap(func)
        return self.frame.do_operation('simple_call', w_func, *args_w)

    def call_args(self, w_callable, args):
        if isinstance(w_callable, Constant):
            fn = w_callable.value
            if hasattr(fn, "_flowspace_rewrite_directly_as_"):
                fn = fn._flowspace_rewrite_directly_as_
                w_callable = self.wrap(fn)
            try:
                sc = self.specialcases[fn]   # TypeError if 'fn' not hashable
            except (KeyError, TypeError):
                pass
            else:
                assert args.keywords == {}, "should not call %r with keyword arguments" % (fn,)
                if args.w_stararg is not None:
                    args_w = args.arguments_w + self.unpackiterable(args.w_stararg)
                else:
                    args_w = args.arguments_w
                return sc(self, fn, args_w)

        if args.keywords or isinstance(args.w_stararg, Variable):
            shape, args_w = args.flatten()
            w_res = self.frame.do_operation('call_args', w_callable,
                    Constant(shape), *args_w)
        else:
            if args.w_stararg is not None:
                args_w = args.arguments_w + self.unpackiterable(args.w_stararg)
            else:
                args_w = args.arguments_w
            w_res = self.frame.do_operation('simple_call', w_callable, *args_w)

        # maybe the call has generated an exception (any one)
        # but, let's say, not if we are calling a built-in class or function
        # because this gets in the way of the special-casing of
        #
        #    raise SomeError(x)
        #
        # as shown by test_objspace.test_raise3.

        exceptions = [Exception]   # *any* exception by default
        if isinstance(w_callable, Constant):
            c = w_callable.value
            if (isinstance(c, (types.BuiltinFunctionType,
                               types.BuiltinMethodType,
                               types.ClassType,
                               types.TypeType)) and
                  c.__module__ in ['__builtin__', 'exceptions']):
                exceptions = operation.implicit_exceptions.get(c)
        self.frame.handle_implicit_exceptions(exceptions)
        return w_res

    def find_global(self, w_globals, varname):
        try:
            value = self.unwrap(w_globals)[varname]
        except KeyError:
            # not in the globals, now look in the built-ins
            try:
                value = getattr(self.unwrap(self.builtin), varname)
            except AttributeError:
                message = "global name '%s' is not defined" % varname
                raise FlowingError(self.frame, self.wrap(message))
        return self.wrap(value)

def make_impure_op(name, arity):
    def generic_operator(self, *args_w):
        assert len(args_w) == arity, name + " got the wrong number of arguments"
        w_result = self.frame.do_operation_with_implicit_exceptions(name, *args_w)
        return w_result
    return generic_operator

def make_op(name, arity):
    """Add function operation to the flow space."""
    op = None
    skip = False
    arithmetic = False

    if (name.startswith('del') or
        name.startswith('set') or
        name.startswith('inplace_')):
        return make_impure_op(name, arity)
    elif name in ('id', 'hash', 'iter', 'userdel'):
        return make_impure_op(name, arity)
    elif name in ('repr', 'str'):
        rep = getattr(__builtin__, name)
        def op(obj):
            s = rep(obj)
            if "at 0x" in s:
                print >>sys.stderr, "Warning: captured address may be awkward"
            return s
    else:
        op = operation.FunctionByName[name]
        arithmetic = (name + '_ovf') in operation.FunctionByName

    def generic_operator(self, *args_w):
        assert len(args_w) == arity, name + " got the wrong number of arguments"
        args = []
        if all(w_arg.foldable() for w_arg in args_w):
            args = [w_arg.value for w_arg in args_w]
            # All arguments are constants: call the operator now
            try:
                result = op(*args)
            except Exception, e:
                etype = e.__class__
                msg = "%s%r always raises %s: %s" % (
                    name, tuple(args), etype, e)
                raise FlowingError(self.frame, msg)
            else:
                # don't try to constant-fold operations giving a 'long'
                # result.  The result is probably meant to be sent to
                # an intmask(), but the 'long' constant confuses the
                # annotator a lot.
                if arithmetic and type(result) is long:
                    pass
                # don't constant-fold getslice on lists, either
                elif name == 'getslice' and type(result) is list:
                    pass
                # otherwise, fine
                else:
                    try:
                        return self.wrap(result)
                    except WrapException:
                        # type cannot sanely appear in flow graph,
                        # store operation with variable result instead
                        pass
        w_result = self.frame.do_operation_with_implicit_exceptions(name, *args_w)
        return w_result
    return generic_operator

for (name, symbol, arity, specialnames) in operation.MethodTable:
    if getattr(FlowObjSpace, name, None) is None:
        setattr(FlowObjSpace, name, make_op(name, arity))


def build_flow(func, space=FlowObjSpace()):
    """
    Create the flow graph for the function.
    """
    _assert_rpythonic(func)
    code = HostCode._from_code(func.func_code)
    if (code.is_generator and
            not hasattr(func, '_generator_next_method_of_')):
        graph = PyGraph(func, code)
        block = graph.startblock
        for name, w_value in zip(code.co_varnames, block.framestate.mergeable):
            if isinstance(w_value, Variable):
                w_value.rename(name)
        return bootstrap_generator(graph)
    graph = PyGraph(func, code)
    frame = space.frame = FlowSpaceFrame(space, graph, code)
    frame.build_flow()
    fixeggblocks(graph)
    checkgraph(graph)
    if code.is_generator:
        tweak_generator_graph(graph)
    return graph
