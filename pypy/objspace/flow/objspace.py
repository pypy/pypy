# ______________________________________________________________________
import sys, operator
import pypy
from pypy.interpreter.baseobjspace import ObjSpace, NoValue
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError
from pypy.objspace.flow.wrapper import *
from pypy.translator.flowmodel import *
from pypy.objspace.flow import flowcontext

# ______________________________________________________________________
class FlowObjSpace(ObjSpace):
    def initialize(self):
        import __builtin__
        self.w_builtins = W_Constant(__builtin__.__dict__)
        self.w_KeyError = W_Constant(KeyError)
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
        etype, evalue, etb = sys.exc_info()
        print >> sys.stderr, '*** reraise', etype, evalue
        raise OperationError, OperationError(self.wrap(etype), self.wrap(evalue)), etb

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
        elif name == 'issubtype':
            op = issubclass
        elif name == 'id':
            op = id
        else:
            print >> sys.stderr, "XXX missing operator:", name

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
                #print >> sys.stderr, 'Constant operation', op
                try:
                    result = op(*args)
                except:
                    self.reraise()
                else:
                    return self.wrap(result)

        #print >> sys.stderr, 'Variable operation', name, args_w
        return self.do_operation(name, *args_w)

    setattr(FlowObjSpace, name, generic_operator)

for line in ObjSpace.MethodTable:
    make_op(*line)

# ______________________________________________________________________
# End of objspace.py
