# ______________________________________________________________________
import sys, operator
import pypy
from pypy.interpreter.baseobjspace import ObjSpace, NoValue
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError
from pypy.objspace.flow.wrapper import *
from pypy.translator.controlflow import *
from pypy.objspace.flow import flowcontext

# ______________________________________________________________________
class FlowObjSpace(ObjSpace):
    def initialize(self):
        self.w_builtins = W_Variable()
        #self.make_builtins()
        #self.make_sys()

    def newdict(self, items_w):
        # XXX Issue a delayed command to create a dictionary
        return W_Variable()

    def newtuple(self, args_w):
        # XXX Issue a delayed command to create a tuple and assign to a new W_Variable
        return W_Variable()

    #def getattr(self, w_obj, w_key):
    #    # XXX Issue a delayed command
    #    return W_Variable()

    def wrap(self, obj):
        if isinstance(obj, W_Object):
            raise TypeError("already wrapped: " + repr(obj))
        return W_Constant(obj)

    def unwrap(self, w_obj):
        if isinstance(w_obj, W_Object):
            return w_obj.unwrap()
        else:
            raise TypeError("not wrapped: " + repr(w_obj))

    def getexecutioncontext(self):
        return self.executioncontext

    def reraise(self):
        #import traceback
        #traceback.print_exc()
        #ec = self.getexecutioncontext() # .framestack.items[-1]
        #ec.print_detailed_traceback(self)

        etype, evalue, etb = sys.exc_info()
        if etype is OperationError:
            raise etype, evalue, etb   # just re-raise it
        name = etype.__name__
        if hasattr(self, 'w_' + name):
            nt = getattr(self, 'w_' + name)
            nv = object.__new__(nt)
            if isinstance(evalue, etype):
                nv.args = evalue.args
            else:
                print [etype, evalue, nt, nv], 
                print '!!!!!!!!'
                nv.args = (evalue,)
        else:
            nt = etype
            nv = evalue
        raise OperationError, OperationError(nt, nv), etb

    def build_flow(self, func):
        """
        """
        code = func.func_code
        code = PyCode()._from_code(code)
        ec = flowcontext.FlowExecutionContext(self, code, func.func_globals)
        self.executioncontext = ec
        ec.build_flow()
        return ec.graph
        
        frames = [frame]
        while len(frames) > 0:
            crnt_frame = frames.pop()
            ret_val = crnt_frame.run()
            self._crnt_block.branch = EndBranch(ret_val)
        g = self._graph
        del self._graph
        del self._crnt_block
        del self._crnt_ops
        return g

    # ____________________________________________________________
    def do_operation(self, name, *args_w):
        spaceop = SpaceOperation(name, args_w, W_Variable())
        self.executioncontext.crnt_ops.append(spaceop)
        return spaceop.result
    
    def is_true(self, w_obj):
        try:
            obj = self.unwrap(w_obj)
        except UnwrapException:
            pass
        else:
            return bool(obj)
        context = self.getexecutioncontext()
        return context.guessbool(w_obj)

    def next(self, w_iter):
        w_tuple = self.do_operation("next_and_flag", w_iter)
        w_flag = self.do_operation("getitem", w_tuple, W_Constant(1))
        context = self.getexecutioncontext()
        if context.guessbool(w_flag):
            return self.do_operation("getitem", w_tuple, W_Constant(0))
        else:
            raise NoValue

# ______________________________________________________________________

def make_op(name, symbol, arity, specialnames):
    if hasattr(FlowObjSpace, name):
        return # Shouldn't do it

    op = getattr(operator, name, None)
    if not op:
        if name == 'call':
            op = apply

    def generic_operator(self, *args_w):
        assert len(args_w) == arity, name+" got the wrong number of arguments"
        args = []
        for w_arg in args_w:
            try:
                arg = self.unwrap(w_arg)
            except UnwrapException:
                break
            else:
                args.append(arg)
        else:
            if op:
                # All arguments are constants: call the operator now
                #print >> sys.stderr, 'Constant operation:', op, args
                try:
                    result = op(*args)
                except:
                    self.reraise()
                else:
                    return self.wrap(result)

        return self.do_operation(name, *args_w)

    setattr(FlowObjSpace, name, generic_operator)

for line in ObjSpace.MethodTable:
    make_op(*line)

# ______________________________________________________________________
# End of objspace.py
