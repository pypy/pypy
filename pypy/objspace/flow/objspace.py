# ______________________________________________________________________
import operator
import pypy
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.pycode import PyCode
from pypy.objspace.flow.wrapper import *
from pypy.translator.controlflow import *
from pypy.objspace.flow.cloningcontext import IndeterminateCondition

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

    def getattr(self, w_obj, w_key):
        # XXX Issue a delayed command
        return W_Variable()

    def wrap(self, obj):
        if isinstance(obj, W_Object):
            raise TypeError("already wrapped: " + repr(obj))
        return W_Constant(obj)

    def unwrap(self, w_obj):
        if isinstance(w_obj, W_Object):
            return w_obj.unwrap()
        else:
            raise TypeError("not wrapped: " + repr(w_obj))

    def build_flow(self, func, w_args, w_kwds):
        """
        """
        code = func.func_code
        bytecode = PyCode()
        bytecode._from_code(code)
        w_globals = self.wrap(func.func_globals)
        frame = bytecode.create_frame(self, w_globals)
        arg_list = [W_Variable() for w in frame.fastlocals_w]
        frame.setfastscope(arg_list)
        self._crnt_ops = []
        self._crnt_block = BasicBlock(arg_list, [], self._crnt_ops, None)
        self._graph = FunctionGraph(self._crnt_block, code.co_name)
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
    def is_true(self, w_obj):
        try:
            obj = self.unwrap(w_obj)
        except UnwrapException:
            pass
        else:
            return bool(obj)
        context = self.getexecutioncontext()
        return context.guessbool()

# ______________________________________________________________________

def make_op(name, symbol, arity, specialnames):
    if hasattr(FlowObjSpace, name):
        return # Shouldn't do it

    op = getattr(operator, name, None)
    if not op:
        return # Can't do it

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
            # All arguments are constants: call the operator now
            try:
                result = op(*args)
            except:
                self.reraise()
            else:
                return self.wrap(result)

        w_result = W_Variable()
        self._crnt_ops.append(SpaceOperation(name, args_w, w_result))
        return w_result

    setattr(FlowObjSpace, name, generic_operator)

for line in ObjSpace.MethodTable:
    make_op(*line)

# ______________________________________________________________________
# End of objspace.py
