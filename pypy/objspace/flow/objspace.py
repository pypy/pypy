# ______________________________________________________________________
import sys, operator
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError
from pypy.objspace.flow.model import *
from pypy.objspace.flow import flowcontext

debug = 0

class UnwrapException(Exception):
    "Attempted to unwrap a Variable."

# ______________________________________________________________________
class FlowObjSpace(ObjSpace):
    full_exceptions = False
    
    def initialize(self):
        import __builtin__
        self.concrete_mode = 0
        self.w_builtins = Constant(__builtin__.__dict__)
        self.w_None     = Constant(None)
        self.w_False    = Constant(False)
        self.w_True     = Constant(True)
        for exc in [KeyError, ValueError, IndexError, StopIteration,
                    AssertionError]:
            clsname = exc.__name__
            setattr(self, 'w_'+clsname, Constant(exc))
        self.specialcases = {}
        #self.make_builtins()
        #self.make_sys()

    def loadfromcache(self, key, builder, cache):
        # when populating the caches, the flow space switches to
        # "concrete mode".  In this mode, only Constants are allowed
        # and no SpaceOperation is recorded.
        def my_builder(key, stuff):
            previous_ops = self.executioncontext.crnt_ops
            self.executioncontext.crnt_ops = flowcontext.ConcreteNoOp()
            self.concrete_mode += 1
            try:
                return builder(key, stuff)
            finally:
                self.executioncontext.crnt_ops = previous_ops
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
        if isinstance(obj, (Variable, Constant)) and obj is not UNDEFINED:
            raise TypeError("already wrapped: " + repr(obj))
        return Constant(obj)

    def unwrap(self, w_obj):
        if isinstance(w_obj, Variable):
            raise UnwrapException
        elif isinstance(w_obj, Constant):
            return w_obj.value
        else:
            raise TypeError("not wrapped: " + repr(w_obj))

    def getexecutioncontext(self):
        return self.executioncontext

    def reraise(self):
        etype, evalue, etb = sys.exc_info()
        #print >> sys.stderr, '*** reraise', etype, evalue
        raise OperationError, OperationError(self.wrap(etype), self.wrap(evalue)), etb

    def setup_executioncontext(self, ec):
        self.executioncontext = ec
        from pypy.objspace.flow import specialcase
        specialcase.setup(self)

    def build_flow(self, func, constargs={}):
        """
        """
        if func.func_doc and func.func_doc.startswith('NOT_RPYTHON'):
            raise Exception, "%r is tagged as NOT_RPYTHON" % (func,)
        code = func.func_code
        code = PyCode()._from_code(code)
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
            # XXX TEMPORARY HACK XXX TEMPORARY HACK XXX TEMPORARY HACK
            print ("*** cannot unpack a Variable iterable "
                   "without knowing its length,")
            print "    assuming a list or tuple with up to 7 items"
            items = []
            w_len = self.len(w_iterable)
            i = 0
            while True:
                w_i = self.wrap(i)
                w_cond = self.eq(w_len, w_i)
                if self.is_true(w_cond):
                    break  # done
                if i == 7:
                    # too many values
                    raise OperationError(self.w_AssertionError, self.w_None)
                w_item = self.do_operation('getitem', w_iterable, w_i)
                items.append(w_item)
                i += 1
            return items
            # XXX TEMPORARY HACK XXX TEMPORARY HACK XXX TEMPORARY HACK
        return ObjSpace.unpackiterable(self, w_iterable, expected_length)

    # ____________________________________________________________
    def do_operation(self, name, *args_w):
        spaceop = SpaceOperation(name, args_w, Variable())
        if hasattr(self, 'executioncontext'):  # not here during bootstrapping
            self.executioncontext.crnt_ops.append(spaceop)
        return spaceop.result
    
    def is_true(self, w_obj):
        try:
            obj = self.unwrap(w_obj)
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
        outcome = context.guessexception(StopIteration)
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

        if args.kwds_w:
            w_args, w_kwds = args.pack()
            return self.do_operation('call', w_callable, w_args, w_kwds)
        else:
            return self.do_operation('simple_call', w_callable, *args.args_w)

# ______________________________________________________________________

implicit_exceptions = {
    'getitem': [IndexError, KeyError],
    }

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
                    arg = self.unwrap(w_arg)
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
                    self.reraise()
                else:
                    return self.wrap(result)

        #print >> sys.stderr, 'Variable operation', name, args_w
        w_result = self.do_operation(name, *args_w)
        if exceptions:
            # catch possible exceptions implicitly.  If the OperationError
            # below is not caught in the same function, it will produce an
            # exception-raising return block in the flow graph.  The special
            # value 'wrap(last_exception)' is used as a marker for this kind
            # of implicit exceptions, and simplify.py will remove it as per
            # the RPython definition: implicit exceptions not explicitly
            # caught in the same function are assumed not to occur.
            context = self.getexecutioncontext()
            outcome = context.guessexception(*exceptions)
            if outcome is not None:
                raise OperationError(self.wrap(outcome),
                                     self.wrap(last_exception))
        return w_result

    setattr(FlowObjSpace, name, generic_operator)

for line in ObjSpace.MethodTable:
    make_op(*line)

# ______________________________________________________________________
# End of objspace.py
