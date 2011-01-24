# ______________________________________________________________________
import __builtin__
import sys
import operator
import types
from pypy.tool import error
from pypy.interpreter.baseobjspace import ObjSpace, Wrappable
from pypy.interpreter.pycode import PyCode, cpython_code_signature
from pypy.interpreter.module import Module
from pypy.interpreter.error import OperationError
from pypy.interpreter import pyframe, argument
from pypy.objspace.flow.model import *
from pypy.objspace.flow import flowcontext, operation, specialcase
from pypy.rlib.unroll import unrolling_iterable, _unroller
from pypy.rlib import rstackovf, rarithmetic


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
    do_imports_immediately = True
    FrameClass = flowcontext.FlowSpaceFrame

    def initialize(self):
        self.concrete_mode = 1
        self.w_None     = Constant(None)
        self.builtin    = Module(self, Constant('__builtin__'),
                                 Constant(__builtin__.__dict__))
        def pick_builtin(w_globals):
            return self.builtin
        self.builtin.pick_builtin = pick_builtin
        self.sys        = Module(self, Constant('sys'), Constant(sys.__dict__))
        self.sys.recursionlimit = 100
        self.w_False    = Constant(False)
        self.w_True     = Constant(True)
        self.w_type     = Constant(type)
        self.w_tuple    = Constant(tuple)
        self.concrete_mode = 0
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
        self.specialcases = {}
        #self.make_builtins()
        #self.make_sys()
        # w_str is needed because cmp_exc_match of frames checks against it,
        # as string exceptions are deprecated
        self.w_str = Constant(str)
        # objects which should keep their SomeObjectness
        self.not_really_const = NOT_REALLY_CONST

    def enter_cache_building_mode(self):
        # when populating the caches, the flow space switches to
        # "concrete mode".  In this mode, only Constants are allowed
        # and no SpaceOperation is recorded.
        previous_recorder = self.executioncontext.recorder
        self.executioncontext.recorder = flowcontext.ConcreteNoOp()
        self.concrete_mode += 1
        return previous_recorder

    def leave_cache_building_mode(self, previous_recorder):
        self.executioncontext.recorder = previous_recorder
        self.concrete_mode -= 1

    def newdict(self):
        if self.concrete_mode:
            return Constant({})
        return self.do_operation('newdict')

    def newtuple(self, args_w):
        try:
            content = [self.unwrap(w_arg) for w_arg in args_w]
        except UnwrapException:
            return self.do_operation('newtuple', *args_w)
        else:
            return Constant(tuple(content))

    def newlist(self, args_w):
        if self.concrete_mode:
            content = [self.unwrap(w_arg) for w_arg in args_w]
            return Constant(content)
        return self.do_operation('newlist', *args_w)

    def newslice(self, w_start, w_stop, w_step):
        if self.concrete_mode:
            return Constant(slice(self.unwrap(w_start),
                                  self.unwrap(w_stop),
                                  self.unwrap(w_step)))
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
            if type(val) not in (int,long):
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
                if self.concrete_mode:
                    # xxx do we want some warning? notice that some stuff is harmless
                    # like setitem(dict, 'n', mutable)
                    pass
                else: # cannot count on it not mutating at runtime!
                    raise UnwrapException
        return obj

    def interpclass_w(self, w_obj):
        obj = self.unwrap(w_obj)
        if isinstance(obj, Wrappable):
            return obj
        return None

    def getexecutioncontext(self):
        return getattr(self, 'executioncontext', None)

    def createcompiler(self):
        # no parser/compiler needed - don't build one, it takes too much time
        # because it is done each time a FlowExecutionContext is built
        return None

    def setup_executioncontext(self, ec):
        self.executioncontext = ec
        specialcase.setup(self)

    def exception_match(self, w_exc_type, w_check_class):
        try:
            check_class = self.unwrap(w_check_class)
        except UnwrapException:
            raise Exception, "non-constant except guard"
        if check_class in (NotImplementedError, AssertionError):
            # if we are in geninterp, we cannot catch these exceptions
            if not self.config.translation.builtins_can_raise_exceptions:
                raise error.FlowingError("Catching %s is not valid in RPython" %
                                         check_class.__name__)
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

    def getconstclass(space, w_cls):
        try:
            ecls = space.unwrap(w_cls)
        except UnwrapException:
            pass
        else:
            if isinstance(ecls, (type, types.ClassType)):
                return ecls
        return None

    def build_flow(self, func, constargs={}):
        """
        """
        if func.func_doc and func.func_doc.lstrip().startswith('NOT_RPYTHON'):
            raise Exception, "%r is tagged as NOT_RPYTHON" % (func,)
        code = func.func_code
        if code.co_flags & 32:
            # generator
            raise TypeError("%r is a generator" % (func,))
        code = PyCode._from_code(self, code)
        if func.func_closure is None:
            closure = None
        else:
            closure = [extract_cell_content(c) for c in func.func_closure]
        # CallableFactory.pycall may add class_ to functions that are methods
        name = func.func_name
        class_ = getattr(func, 'class_', None)
        if class_ is not None:
            name = '%s.%s' % (class_.__name__, name)
        for c in "<>&!":
            name = name.replace(c, '_')
        ec = flowcontext.FlowExecutionContext(self, code, func.func_globals,
                                              constargs, closure, name)
        graph = ec.graph
        graph.func = func
        # attach a signature and defaults to the graph
        # so that it becomes even more interchangeable with the function
        # itself
        graph.signature = cpython_code_signature(code)
        graph.defaults = func.func_defaults or ()
        self.setup_executioncontext(ec)

        try:
            ec.build_flow()
        except error.FlowingError, a:
            # attach additional source info to AnnotatorError
            _, _, tb = sys.exc_info()
            formated = error.format_global_error(ec.graph, ec.crnt_offset,
                                                 str(a))
            e = error.FlowingError(formated)
            raise error.FlowingError, e, tb
        checkgraph(graph)
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
                e = OperationError(self.w_ValueError, self.w_None)
                e.normalize_exception(self)
                raise e
            return [self.do_operation('getitem', w_iterable, self.wrap(i)) 
                        for i in range(expected_length)]
        return ObjSpace.unpackiterable(self, w_iterable, expected_length)

    # ____________________________________________________________
    def do_operation(self, name, *args_w):
        spaceop = SpaceOperation(name, args_w, Variable())
        if hasattr(self, 'executioncontext'):  # not here during bootstrapping
            spaceop.offset = self.executioncontext.crnt_offset
            self.executioncontext.recorder.append(spaceop)
        return spaceop.result

    def do_operation_with_implicit_exceptions(self, name, *args_w):
        w_result = self.do_operation(name, *args_w)
        self.handle_implicit_exceptions(operation.implicit_exceptions.get(name))
        return w_result

    def is_true(self, w_obj):
        try:
            obj = self.unwrap_for_computation(w_obj)
        except UnwrapException:
            pass
        else:
            return bool(obj)
        w_truthvalue = self.do_operation('is_true', w_obj)
        context = self.getexecutioncontext()
        return context.guessbool(w_truthvalue)

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
        context = self.getexecutioncontext()
        try:
            it = self.unwrap(w_iter)
        except UnwrapException:
            pass
        else:
            if isinstance(it, _unroller):
                try:
                    v, next_unroller = it.step()
                except IndexError:
                    raise OperationError(self.w_StopIteration, self.w_None)
                else:
                    context.replace_in_stack(it, next_unroller)
                    return self.wrap(v)
        w_item = self.do_operation("next", w_iter)
        outcome, w_exc_cls, w_exc_value = context.guessexception(StopIteration,
                                                                 RuntimeError)
        if outcome is StopIteration:
            raise OperationError(self.w_StopIteration, w_exc_value)
        elif outcome is RuntimeError:
            raise operation.ImplicitOperationError(Constant(RuntimeError),
                                                    w_exc_value)
        else:
            return w_item

    def setitem(self, w_obj, w_key, w_val):
        if self.concrete_mode:
            try:
                obj = self.unwrap_for_computation(w_obj)
                key = self.unwrap_for_computation(w_key)
                val = self.unwrap_for_computation(w_val)
                operator.setitem(obj, key, val)
                return self.w_None
            except UnwrapException:
                pass
        return self.do_operation_with_implicit_exceptions('setitem', w_obj, 
                                                          w_key, w_val)

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
            if not self.config.translation.builtins_can_raise_exceptions:
                if (isinstance(c, (types.BuiltinFunctionType,
                                   types.BuiltinMethodType,
                                   types.ClassType,
                                   types.TypeType)) and
                      c.__module__ in ['__builtin__', 'exceptions']):
                    exceptions = operation.implicit_exceptions.get(c)
        self.handle_implicit_exceptions(exceptions)
        return w_res

    def handle_implicit_exceptions(self, exceptions):
        if not exceptions:
            return
        if not self.config.translation.builtins_can_raise_exceptions:
            # clean up 'exceptions' by removing the non-RPythonic exceptions
            # which might be listed for geninterp.
            exceptions = [exc for exc in exceptions
                              if exc is not TypeError and
                                 exc is not AttributeError]
        if exceptions:
            # catch possible exceptions implicitly.  If the OperationError
            # below is not caught in the same function, it will produce an
            # exception-raising return block in the flow graph.  Note that
            # even if the interpreter re-raises the exception, it will not
            # be the same ImplicitOperationError instance internally.
            context = self.getexecutioncontext()
            outcome, w_exc_cls, w_exc_value = context.guessexception(*exceptions)
            if outcome is not None:
                # we assume that the caught exc_cls will be exactly the
                # one specified by 'outcome', and not a subclass of it,
                # unless 'outcome' is Exception.
                #if outcome is not Exception:
                    #w_exc_cls = Constant(outcome) Now done by guessexception itself
                    #pass
                 raise operation.ImplicitOperationError(w_exc_cls, w_exc_value)

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
operation.add_operations(FlowObjSpace)


def extract_cell_content(c):
    """Get the value contained in a CPython 'cell', as read through
    the func_closure of a function object."""
    try:
        # This is simple on 2.5
        return getattr(c, "cell_contents")
    except AttributeError:
        class X(object):
            def __cmp__(self, other):
                self.other = other
                return 0
            def __eq__(self, other):
                self.other = other
                return True
        x = X()
        x_cell, = (lambda: x).func_closure
        x_cell == c
        try:
            return x.other    # crashes if the cell is actually empty
        except AttributeError:
            raise ValueError("empty cell")
# ______________________________________________________________________
# End of objspace.py
