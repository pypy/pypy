# ______________________________________________________________________
import __builtin__
import sys
import operator
import types
from pypy.interpreter.baseobjspace import ObjSpace, Wrappable
from pypy.interpreter import pyframe, argument
from pypy.objspace.flow.model import *
from pypy.objspace.flow import operation
from pypy.objspace.flow.flowcontext import (FlowSpaceFrame, fixeggblocks,
    FSException, FlowingError)
from pypy.objspace.flow.specialcase import SPECIAL_CASES
from pypy.rlib.unroll import unrolling_iterable, _unroller
from pypy.rlib import rstackovf, rarithmetic
from pypy.rlib.rarithmetic import is_valid_int


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

# ______________________________________________________________________
class FlowObjSpace(ObjSpace):
    """NOT_RPYTHON.
    The flow objspace space is used to produce a flow graph by recording
    the space operations that the interpreter generates when it interprets
    (the bytecode of) some function.
    """

    full_exceptions = False
    FrameClass = FlowSpaceFrame

    def initialize(self):
        self.w_None     = Constant(None)
        self.builtin = Constant(__builtin__)
        self.sys = Constant(sys)
        self.w_False    = Constant(False)
        self.w_True     = Constant(True)
        self.w_type     = Constant(type)
        self.w_tuple    = Constant(tuple)
        for exc in [KeyError, ValueError, IndexError, StopIteration,
                    AssertionError, TypeError, AttributeError, ImportError]:
            clsname = exc.__name__
            setattr(self, 'w_'+clsname, Constant(exc))
        # the following exceptions are the ones that should not show up
        # during flow graph construction; they are triggered by
        # non-R-Pythonic constructs or real bugs like typos.
        for exc in [NameError, UnboundLocalError]:
            clsname = exc.__name__
            setattr(self, 'w_'+clsname, None)
        self.specialcases = SPECIAL_CASES.copy()
        #self.make_builtins()
        #self.make_sys()
        # w_str is needed because cmp_exc_match of frames checks against it,
        # as string exceptions are deprecated
        self.w_str = Constant(str)
        # objects which should keep their SomeObjectness
        self.not_really_const = NOT_REALLY_CONST

    # disable superclass methods
    enter_cache_building_mode = None
    leave_cache_building_mode = None
    createcompiler = None
    interpclass_w = None

    def is_w(self, w_one, w_two):
        return self.is_true(self.is_(w_one, w_two))

    is_ = None     # real version added by add_operations()
    id  = None     # real version added by add_operations()

    def newdict(self, module="ignored"):
        return self.do_operation('newdict')

    def newtuple(self, args_w):
        try:
            content = [self.unwrap(w_arg) for w_arg in args_w]
        except UnwrapException:
            return self.do_operation('newtuple', *args_w)
        else:
            return Constant(tuple(content))

    def newlist(self, args_w, sizehint=None):
        return self.do_operation('newlist', *args_w)

    def newslice(self, w_start, w_stop, w_step):
        return self.do_operation('newslice', w_start, w_stop, w_step)

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

    def unwrap_for_computation(self, w_obj):
        obj = self.unwrap(w_obj)
        to_check = obj
        if hasattr(to_check, 'im_self'):
            to_check = to_check.im_self
        if (not isinstance(to_check, (type, types.ClassType, types.ModuleType)) and
            # classes/types/modules are assumed immutable
            hasattr(to_check, '__class__') and to_check.__class__.__module__ != '__builtin__'):
            frozen = hasattr(to_check, '_freeze_') and to_check._freeze_()
            if not frozen:
                # cannot count on it not mutating at runtime!
                raise UnwrapException
        return obj

    def getexecutioncontext(self):
        return self.frame

    def exception_match(self, w_exc_type, w_check_class):
        try:
            check_class = self.unwrap(w_check_class)
        except UnwrapException:
            raise FlowingError(self.frame, "Non-constant except guard.")
        if check_class in (NotImplementedError, AssertionError):
            raise FlowingError(self.frame,
                "Catching %s is not valid in RPython" % check_class.__name__)
        if not isinstance(check_class, tuple):
            # the simple case
            return ObjSpace.exception_match(self, w_exc_type, w_check_class)
        # special case for StackOverflow (see rlib/rstackovf.py)
        if check_class == rstackovf.StackOverflow:
            w_real_class = self.wrap(rstackovf._StackOverflow)
            return ObjSpace.exception_match(self, w_exc_type, w_real_class)
        # checking a tuple of classes
        for w_klass in self.fixedview(w_check_class):
            if self.exception_match(w_exc_type, w_klass):
                return True
        return False

    def exc_from_raise(self, w_type, w_value):
        """
        Create a wrapped exception from the arguments of a raise statement.

        Returns an FSException object whose w_value is an instance of w_type.
        """
        if self.exception_is_valid_obj_as_class_w(w_type):
            # this is for all cases of the form (Class, something)
            if self.is_w(w_value, self.w_None):
                # raise Type: we assume we have to instantiate Type
                w_value = self.call_function(w_type)
                w_type = self.type(w_value)
            else:
                w_valuetype = self.type(w_value)
                if self.exception_issubclass_w(w_valuetype, w_type):
                    # raise Type, Instance: let etype be the exact type of value
                    w_type = w_valuetype
                else:
                    # raise Type, X: assume X is the constructor argument
                    w_value = self.call_function(w_type, w_value)
                    w_type = self.type(w_value)
        else:
            # the only case left here is (inst, None), from a 'raise inst'.
            w_inst = w_type
            w_instclass = self.type(w_inst)
            if not self.is_w(w_value, self.w_None):
                raise FSException(self.w_TypeError, self.wrap(
                    "instance exception may not have a separate value"))
            w_value = w_inst
            w_type = w_instclass
        return FSException(w_type, w_value)

    def getconstclass(space, w_cls):
        try:
            ecls = space.unwrap(w_cls)
        except UnwrapException:
            pass
        else:
            if isinstance(ecls, (type, types.ClassType)):
                return ecls
        return None

    def build_flow(self, func, constargs={}, tweak_for_generator=True):
        """
        """
        if func.func_doc and func.func_doc.lstrip().startswith('NOT_RPYTHON'):
            raise Exception, "%r is tagged as NOT_RPYTHON" % (func,)
        frame = self.frame = FlowSpaceFrame(self, func, constargs)
        frame.build_flow()
        graph = frame.graph
        fixeggblocks(graph)
        checkgraph(graph)
        if graph.is_generator and tweak_for_generator:
            from pypy.translator.generator import tweak_generator_graph
            tweak_generator_graph(graph)
        return graph

    def fixedview(self, w_tuple, expected_length=None):
        return self.unpackiterable(w_tuple, expected_length)
    listview = fixedview

    def unpackiterable(self, w_iterable, expected_length=None):
        if not isinstance(w_iterable, Variable):
            l = list(self.unwrap(w_iterable))
            if expected_length is not None and len(l) != expected_length:
                raise ValueError
            return [self.wrap(x) for x in l]
        if isinstance(w_iterable, Variable) and expected_length is None:
            raise UnwrapException, ("cannot unpack a Variable iterable"
                                    "without knowing its length")
        elif expected_length is not None:
            w_len = self.len(w_iterable)
            w_correct = self.eq(w_len, self.wrap(expected_length))
            if not self.is_true(w_correct):
                e = self.exc_from_raise(self.w_ValueError, self.w_None)
                raise e
            return [self.do_operation('getitem', w_iterable, self.wrap(i))
                        for i in range(expected_length)]
        return ObjSpace.unpackiterable(self, w_iterable, expected_length)

    # ____________________________________________________________
    def do_operation(self, name, *args_w):
        spaceop = SpaceOperation(name, args_w, Variable())
        spaceop.offset = self.frame.last_instr
        self.frame.record(spaceop)
        return spaceop.result

    def do_operation_with_implicit_exceptions(self, name, *args_w):
        w_result = self.do_operation(name, *args_w)
        self.frame.handle_implicit_exceptions(
                operation.implicit_exceptions.get(name))
        return w_result

    def is_true(self, w_obj):
        try:
            obj = self.unwrap_for_computation(w_obj)
        except UnwrapException:
            pass
        else:
            return bool(obj)
        w_truthvalue = self.do_operation('is_true', w_obj)
        return self.frame.guessbool(w_truthvalue)

    def iter(self, w_iterable):
        try:
            iterable = self.unwrap(w_iterable)
        except UnwrapException:
            pass
        else:
            if isinstance(iterable, unrolling_iterable):
                return self.wrap(iterable.get_unroller())
        w_iter = self.do_operation("iter", w_iterable)
        return w_iter

    def next(self, w_iter):
        frame = self.frame
        try:
            it = self.unwrap(w_iter)
        except UnwrapException:
            pass
        else:
            if isinstance(it, _unroller):
                try:
                    v, next_unroller = it.step()
                except IndexError:
                    raise FSException(self.w_StopIteration, self.w_None)
                else:
                    frame.replace_in_stack(it, next_unroller)
                    return self.wrap(v)
        w_item = self.do_operation("next", w_iter)
        frame.handle_implicit_exceptions([StopIteration, RuntimeError])
        return w_item

    def setitem(self, w_obj, w_key, w_val):
        # protect us from globals write access
        if w_obj is self.frame.w_globals:
            raise FlowingError(self.frame,
                    "Attempting to modify global variable  %r." % (w_key))
        return self.do_operation_with_implicit_exceptions('setitem', w_obj,
                                                          w_key, w_val)

    def getattr(self, w_obj, w_name):
        # handling special things like sys
        # unfortunately this will never vanish with a unique import logic :-(
        if w_obj in self.not_really_const:
            const_w = self.not_really_const[w_obj]
            if w_name not in const_w:
                return self.do_operation_with_implicit_exceptions('getattr',
                                                                w_obj, w_name)
        try:
            obj = self.unwrap_for_computation(w_obj)
            name = self.unwrap_for_computation(w_name)
        except UnwrapException:
            pass
        else:
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
        return self.do_operation_with_implicit_exceptions('getattr',
                w_obj, w_name)

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
                return self.do_operation_with_implicit_exceptions('getattr',
                                                                w_obj, w_name)
        try:
            return self.wrap(getattr(w_module.value, w_name.value))
        except AttributeError:
            raise FSException(self.w_ImportError,
                self.wrap("cannot import name '%s'" % w_name.value))

    def call_function(self, w_func, *args_w):
        nargs = len(args_w)
        args = argument.ArgumentsForTranslation(self, list(args_w))
        return self.call_args(w_func, args)

    def call_args(self, w_callable, args):
        try:
            fn = self.unwrap(w_callable)
            if hasattr(fn, "_flowspace_rewrite_directly_as_"):
                fn = fn._flowspace_rewrite_directly_as_
                w_callable = self.wrap(fn)
            sc = self.specialcases[fn]   # TypeError if 'fn' not hashable
        except (UnwrapException, KeyError, TypeError):
            pass
        else:
            return sc(self, fn, args)

        try:
            args_w, kwds_w = args.copy().unpack()
        except UnwrapException:
            args_w, kwds_w = '?', '?'
        # NOTE: annrpython needs to know about the following two operations!
        if not kwds_w:
            # simple case
            w_res = self.do_operation('simple_call', w_callable, *args_w)
        else:
            # general case
            shape, args_w = args.flatten()
            w_res = self.do_operation('call_args', w_callable, Constant(shape),
                                      *args_w)

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

    def w_KeyboardInterrupt(self):
        # the reason to do this is: if you interrupt the flowing of a function
        # with <Ctrl-C> the bytecode interpreter will raise an applevel
        # KeyboardInterrupt and you will get an AttributeError: space does not
        # have w_KeyboardInterrupt, which is not very helpful
        raise KeyboardInterrupt
    w_KeyboardInterrupt = property(w_KeyboardInterrupt)

    def w_RuntimeError(self):
        # XXX same as w_KeyboardInterrupt()
        raise RuntimeError("the interpreter raises RuntimeError during "
                           "flow graph construction")
    w_RuntimeError = prebuilt_recursion_error = property(w_RuntimeError)

def make_op(name, arity):
    """Add function operation to the flow space."""
    if getattr(FlowObjSpace, name, None) is not None:
        return

    op = None
    skip = False
    arithmetic = False

    if (name.startswith('del') or
        name.startswith('set') or
        name.startswith('inplace_')):
        # skip potential mutators
        skip = True
    elif name in ('id', 'hash', 'iter', 'userdel'):
        # skip potential runtime context dependecies
        skip = True
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

    if not op and not skip:
        raise ValueError("XXX missing operator: %s" % (name,))

    def generic_operator(self, *args_w):
        assert len(args_w) == arity, name + " got the wrong number of arguments"
        if op:
            args = []
            for w_arg in args_w:
                try:
                    arg = self.unwrap_for_computation(w_arg)
                except UnwrapException:
                    break
                else:
                    args.append(arg)
            else:
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
        w_result = self.do_operation_with_implicit_exceptions(name, *args_w)
        return w_result

    setattr(FlowObjSpace, name, generic_operator)


for (name, symbol, arity, specialnames) in ObjSpace.MethodTable:
    make_op(name, arity)
