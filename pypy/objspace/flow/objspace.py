# ______________________________________________________________________
import sys, operator, types
from pypy.interpreter.baseobjspace import ObjSpace, BaseWrappable
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.module import Module
from pypy.interpreter.error import OperationError
from pypy.objspace.flow.model import *
from pypy.objspace.flow import flowcontext

debug = 0

class UnwrapException(Exception):
    "Attempted to unwrap a Variable."

class WrapException(Exception):
    """Attempted wrapping of a type that cannot sanely appear in flow graph or during its construction"""

# method-wrappers
method_wrapper = type(complex.real.__get__)


# ______________________________________________________________________
class FlowObjSpace(ObjSpace):
    """NOT_RPYTHON.
    The flow objspace space is used to produce a flow graph by recording
    the space operations that the interpreter generates when it interprets
    (the bytecode of) some function.
    """
    
    full_exceptions = False

    builtins_can_raise_exceptions = False

    do_imports_immediately = True  # overridden in geninterplevel

    def initialize(self):
        import __builtin__
        self.concrete_mode = 0
        self.builtin    = Module(self, Constant('__builtin__'), Constant(__builtin__.__dict__))
        def pick_builtin(w_globals):
            return self.builtin
        self.builtin.pick_builtin = pick_builtin
        self.sys        = Module(self, Constant('sys'), Constant(sys.__dict__))
        self.sys.recursionlimit = 100
        self.w_None     = Constant(None)
        self.w_False    = Constant(False)
        self.w_True     = Constant(True)
        for exc in [KeyError, ValueError, IndexError, StopIteration,
                    AssertionError]:
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

    def loadfromcache(self, key, builder, cache):
        # when populating the caches, the flow space switches to
        # "concrete mode".  In this mode, only Constants are allowed
        # and no SpaceOperation is recorded.
        def my_builder(key, stuff):
            previous_recorder = self.executioncontext.recorder
            self.executioncontext.recorder = flowcontext.ConcreteNoOp()
            self.concrete_mode += 1
            try:
                return builder(key, stuff)
            finally:
                self.executioncontext.recorder = previous_recorder
                self.concrete_mode -= 1
        return super(FlowObjSpace, self).loadfromcache(key, my_builder, cache)

    def newdict(self, items_w):
        if self.concrete_mode:
            content = [(self.unwrap(w_key), self.unwrap(w_value))
                       for w_key, w_value in items_w]
            return Constant(dict(content))
        flatlist_w = []
        for w_key, w_value in items_w:
            flatlist_w.append(w_key)
            flatlist_w.append(w_value)
        return self.do_operation('newdict', *flatlist_w)

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

    def newslice(self, w_start=None, w_stop=None, w_step=None):
        if w_start is None: w_start = self.w_None
        if w_stop  is None: w_stop  = self.w_None
        if w_step  is None: w_step  = self.w_None
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
        if type(obj) is method_wrapper:
            raise WrapException
        return Constant(obj)

    def int_w(self, w_obj):
        if isinstance(w_obj, Constant):
            val = w_obj.value
            if type(val) not in (int,long):
                raise TypeError("expected integer: " + repr(w_obj))
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
        if (not isinstance(to_check, (type, types.ClassType)) and # classes/types are assumed immutable
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
        if isinstance(obj, BaseWrappable):
            return obj
        return None

    def getexecutioncontext(self):
        return self.executioncontext

    def setup_executioncontext(self, ec):
        self.executioncontext = ec
        from pypy.objspace.flow import specialcase
        specialcase.setup(self)

    def exception_match(self, w_exc_type, w_check_class):
        self.executioncontext.recorder.crnt_block.exc_handler = True
        if not isinstance(self.unwrap(w_check_class), tuple):
            # the simple case
            return ObjSpace.exception_match(self, w_exc_type, w_check_class)
        # checking a tuple of classes
        for w_klass in self.unpacktuple(w_check_class):
            if ObjSpace.exception_match(self, w_exc_type, w_klass):
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

    def normalize_exception(space, w_arg1, w_arg2, w_tb):
        """Special-case for 'raise' statements.  Case-by-case analysis:

        * raise Class
           - with a constant Class, it is easy to recognize.
             But we don't normalize: the associated value is None.

        * raise Class(...)
           - when the class is instantiated in-place, we can figure that out

        * raise Instance
           - assumes that it's not a class, and raises an exception whose class
             is variable and whose value is Instance.

        * raise Class, Arg
           - assumes that Arg is the value you want for the exception, and
             that Class is exactly the exception class.  No check or normalization.
        """

        # w_arg3 (the traceback) is ignored and replaced with None
        # if it is a Variable, because pyopcode.py tries to unwrap it.
        # It means that we ignore the 'tb' argument of 'raise' in most cases.
        if not isinstance(w_tb, Constant):
            w_tb = space.w_None

        if w_arg2 != space.w_None:
            # raise Class, Arg: no normalization
            return (w_arg1, w_arg2, w_tb)

        etype = space.getconstclass(w_arg1)
        if etype is not None:
            # raise Class
            return (w_arg1, space.w_None, w_tb)

        # raise Class(..)?  We need a hack to figure out of which class it is.
        # Normally, Instance should have been created by the previous operation
        # which should be a simple_call(<Class>, ...).
        # Fetch the <Class> out of there.  (This doesn't work while replaying)
        # XXX this case is likely not triggered anymore, because the instance creation op
        # is walled off in a different block by the surrounding it with exception
        # handling logic that is always put in place for calls.
        # We may want to make this more clever!
        operations = space.executioncontext.recorder.crnt_block.operations
        if operations:
            spaceop = operations[-1]
            if (spaceop.opname == 'simple_call' and
                spaceop.result is w_arg1):
                w_type = spaceop.args[0]
                return (w_type, w_arg1, w_tb)

        # raise Instance.  Fall-back.
        w_type = space.do_operation('type', w_arg1)
        return (w_type, w_arg1, w_tb)
        # this function returns a real tuple that can be handled
        # by FlowObjSpace.unpacktuple()


    def build_flow(self, func, constargs={}):
        """
        """
        if func.func_doc and func.func_doc.lstrip().startswith('NOT_RPYTHON'):
            raise Exception, "%r is tagged as NOT_RPYTHON" % (func,)
        code = func.func_code
        code = PyCode(self)._from_code(code)
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
        self.setup_executioncontext(ec)
        ec.build_flow()
        checkgraph(ec.graph)
        return ec.graph

    def unpacktuple(self, w_tuple, expected_length=None):
        # special case to accept either Constant tuples
        # or real tuples of Variables/Constants
        if isinstance(w_tuple, tuple):
            result = w_tuple
        else:
            unwrapped = self.unwrap(w_tuple)
            result = tuple([Constant(x) for x in unwrapped])
        if expected_length is not None and len(result) != expected_length:
            raise ValueError, "got a tuple of length %d instead of %d" % (
                len(result), expected_length)
        return result

    def unpackiterable(self, w_iterable, expected_length=None):
        if isinstance(w_iterable, Variable) and expected_length is None:
            raise UnwrapException, ("cannot unpack a Variable iterable"
                                    "without knowing its length")
##            # XXX TEMPORARY HACK XXX TEMPORARY HACK XXX TEMPORARY HACK
##            print ("*** cannot unpack a Variable iterable "
##                   "without knowing its length,")
##            print "    assuming a list or tuple with up to 7 items"
##            items = []
##            w_len = self.len(w_iterable)
##            i = 0
##            while True:
##                w_i = self.wrap(i)
##                w_cond = self.eq(w_len, w_i)
##                if self.is_true(w_cond):
##                    break  # done
##                if i == 7:
##                    # too many values
##                    raise OperationError(self.w_AssertionError, self.w_None)
##                w_item = self.do_operation('getitem', w_iterable, w_i)
##                items.append(w_item)
##                i += 1
##            return items
##            # XXX TEMPORARY HACK XXX TEMPORARY HACK XXX TEMPORARY HACK
        elif expected_length is not None:
            w_len = self.len(w_iterable)
            w_correct = self.eq(w_len, self.wrap(expected_length))
            if not self.is_true(w_correct):
                raise OperationError(self.w_ValueError, self.w_None)
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

    def next(self, w_iter):
        w_item = self.do_operation("next", w_iter)
        context = self.getexecutioncontext()
        outcome, w_exc_cls, w_exc_value = context.guessexception(StopIteration)
        if outcome is StopIteration:
            raise OperationError(self.w_StopIteration, self.w_None)
        else:
            return w_item

    def call_args(self, w_callable, args):
        try:
            fn = self.unwrap(w_callable)
            sc = self.specialcases[fn]   # TypeError if 'fn' not hashable
        except (UnwrapException, KeyError, TypeError):
            pass
        else:
            return sc(self, fn, args)

        try:
            args_w, kwds_w = args.unpack()
        except UnwrapException:
            args_w, kwds_w = '?', '?'
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
            if isinstance(c, (types.BuiltinFunctionType,
                              types.BuiltinMethodType)):
                if not self.builtins_can_raise_exceptions:
                    exceptions = None
            elif (isinstance(c, (type, types.ClassType)) and
                  c.__module__ in ['__builtin__', 'exceptions']):
                exceptions = None
        self.handle_implicit_exceptions(exceptions)
        return w_res

    def handle_implicit_exceptions(self, exceptions):
        if exceptions:
            # catch possible exceptions implicitly.  If the OperationError
            # below is not caught in the same function, it will produce an
            # exception-raising return block in the flow graph.  The special
            # value 'wrap(last_exception)' is used as a marker for this kind
            # of implicit exceptions, and simplify.py will remove it as per
            # the RPython definition: implicit exceptions not explicitly
            # caught in the same function are assumed not to occur.
            context = self.getexecutioncontext()
            outcome, w_exc_cls, w_exc_value = context.guessexception(*exceptions)
            if outcome is not None:
                # we assume that the caught exc_cls will be exactly the
                # one specified by 'outcome', and not a subclass of it,
                # unless 'outcome' is Exception.
                if outcome is not Exception:
                    w_exc_cls = Constant(outcome, last_exception=True)
                raise OperationError(w_exc_cls, w_exc_value)

# ______________________________________________________________________

implicit_exceptions = {
    'getitem': [IndexError, KeyError],
    'delitem': [IndexError, KeyError],
    'getattr': [AttributeError],
    'delattr': [AttributeError],
    'iter'   : [TypeError],
    'coerce' : [TypeError],
    }
# continuing like above, but in a more programmatic style.
def _add_exceptions(names, exc):
    for name in names.split():
        lis = implicit_exceptions.setdefault(name, [])
        if exc in lis:
            raise ValueError, "your list is causing duplication!"
        lis.append(exc)

_add_exceptions("""div mod divmod truediv floordiv pow
                   inplace_div inplace_mod inplace_divmod inplace_truediv
                   inplace_floordiv inplace_pow""", ZeroDivisionError)
_add_exceptions("""pos neg abs invert add sub mul truediv
                   floordiv div mod divmod pow lshift
                   inplace_add inplace_sub inplace_mul inplace_truediv
                   inplace_floordiv inplace_div inplace_mod inplace_pow
                   inplace_lshift""", OverflowError)
_add_exceptions("""pow inplace_pow""", ValueError)
_add_exceptions("""add sub mul truediv floordiv div mod divmod pow
                   inplace_add inplace_sub inplace_mul inplace_truediv
                   inplace_floordiv inplace_div inplace_mod inplace_divmod
                   inplace_pow""", FloatingPointError)
del _add_exceptions

def extract_cell_content(c):
    """Get the value contained in a CPython 'cell', as read through
    the func_closure of a function object."""
    # yuk! this is all I could come up with that works in Python 2.2 too
    class X(object):
        def __eq__(self, other):
            self.other = other
    x = X()
    x_cell, = (lambda: x).func_closure
    x_cell == c
    return x.other

def make_op(name, symbol, arity, specialnames):
    if hasattr(FlowObjSpace, name):
        return # Shouldn't do it

    if name == 'pow':
        op = pow
    else:
        op = getattr(operator, name, None)
    if not op:
        #if name == 'call':
        #    op = apply
        if name == 'issubtype':
            op = issubclass
        elif name == 'is_':
            op = lambda x, y: x is y
        elif name == 'getattr':
            op = getattr
        else:
            if debug: print >> sys.stderr, "XXX missing operator:", name

    exceptions = implicit_exceptions.get(name)

    def generic_operator(self, *args_w):
        assert len(args_w) == arity, name+" got the wrong number of arguments"
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
                #print >> sys.stderr, 'Constant operation', op
                try:
                    result = op(*args)
                except:
                    etype, evalue, etb = sys.exc_info()
                    msg = "generated by a constant operation:  %s%r" % (
                        name, tuple(args))
                    raise flowcontext.OperationThatShouldNotBePropagatedError(
                        self.wrap(etype), self.wrap(msg))
                else:
                    try:
                        return self.wrap(result)
                    except WrapException:
                        # type cannot sanely appear in flow graph,
                        # store operation with variable result instead
                        pass

        #print >> sys.stderr, 'Variable operation', name, args_w
        w_result = self.do_operation(name, *args_w)
        self.handle_implicit_exceptions(exceptions)
        return w_result

    setattr(FlowObjSpace, name, generic_operator)

for line in ObjSpace.MethodTable:
    make_op(*line)

# ______________________________________________________________________
# End of objspace.py
