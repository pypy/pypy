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
        self.w_builtins = Constant(__builtin__.__dict__)
        self.w_None     = Constant(None)
        self.w_False    = Constant(False)
        self.w_True     = Constant(True)
        for exc in [KeyError, ValueError, StopIteration]:
            clsname = exc.__name__
            setattr(self, 'w_'+clsname, Constant(exc))
        #self.make_builtins()
        #self.make_sys()

    def newdict(self, items_w):
        flatlist_w = []
        for w_key, w_value in items_w:
            flatlist_w.append(w_key)
            flatlist_w.append(w_value)
        return self.do_operation('newdict', *flatlist_w)

    def newtuple(self, args_w):
        return self.do_operation('newtuple', *args_w)

    def newlist(self, args_w):
        return self.do_operation('newlist', *args_w)

    def newslice(self, w_start=None, w_stop=None, w_step=None):
        if w_start is None: w_start = self.w_None
        if w_stop  is None: w_stop  = self.w_None
        if w_step  is None: w_step  = self.w_None
        return self.do_operation('newslice', w_start, w_stop, w_step)

    def wrap(self, obj):
        if isinstance(obj, (Variable, Constant)):
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

    def build_flow(self, func, constargs={}):
        """
        """
        code = func.func_code
        code = PyCode()._from_code(code)
        if func.func_closure is None:
            closure = None
        else:
            closure = [extract_cell_content(c) for c in func.func_closure]
        ec = flowcontext.FlowExecutionContext(self, code, func.func_globals,
                                              constargs, closure)
        self.executioncontext = ec
        ec.build_flow()
        name = ec.graph.name
        for c in "<>&!":
            name = name.replace(c, '_')
        ec.graph.name = name
        return ec.graph

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
        w_curexc = self.do_operation('exception', w_item)
        context = self.getexecutioncontext()
        outcome = context.guessbool(w_curexc, [None, StopIteration])
        if outcome is StopIteration:
            raise OperationError(self.w_StopIteration, self.w_None)
        else:
            return w_item

# ______________________________________________________________________

implicit_exceptions = {
    'getitem': [IndexError],
    }
class ImplicitExcValue:
    def __repr__(self):
        return 'implicitexc'
implicitexc = ImplicitExcValue()

def extract_cell_content(c):
    """Get the value contained in a CPython 'cell', as read through
    the func_closure of a function object."""
    import new
    def hackout():
        return hackout   # this access becomes a cell reference
    # now change the cell to become 'c'
    hackout = new.function(hackout.func_code, {}, '', None, (c,))
    return hackout()

def make_op(name, symbol, arity, specialnames):
    if hasattr(FlowObjSpace, name):
        return # Shouldn't do it

    op = getattr(operator, name, None)
    if not op:
        #if name == 'call':
        #    op = apply
        if name == 'issubtype':
            op = issubclass
        elif name == 'id':
            op = id
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
            # the 'exception(w_result)' operation is a bit strange, it is
            # meant to check if w_result is a correct result or if its
            # computation actually resulted in an exception.  For now this
            # is an approximation of checking if w_result is NULL, and
            # using PyErr_Occurred() to get the current exception if so.
            w_curexc = self.do_operation('exception', w_result)
            context = self.getexecutioncontext()
            outcome = context.guessbool(w_curexc, [None] + exceptions)
            if outcome is not None:
                raise OperationError(self.wrap(outcome),
                                     self.wrap(implicitexc))
        return w_result

    setattr(FlowObjSpace, name, generic_operator)

for line in ObjSpace.MethodTable:
    make_op(*line)

# ______________________________________________________________________
# End of objspace.py
