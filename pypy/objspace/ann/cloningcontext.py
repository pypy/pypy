from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.pyframe import ControlFlowException

class IndeterminateCondition(ControlFlowException):

    def __init__(self, w_obj):
        ControlFlowException.__init__(self)
        self.w_obj = w_obj

    def action(self, frame, last_instr):
        frame.next_instr = last_instr
        f2 = frame.clone()
        clones = frame.clones
        clones.append(f2)
        f2.clones = clones # Share the joy
        f2.force_w_obj = self.w_obj
        self.w_obj.force = True

class CloningExecutionContext(ExecutionContext):


    def eval_frame(self, frame):
        from pypy.objspace.ann.objspace import W_Anything
        assert not hasattr(frame, "clones")
        space = frame.space
        clones = [frame]
        frame.clones = clones
        frame.force_w_obj = None
        result = None # W_Impossible
        while clones:
            f = clones.pop()
            w_obj = f.force_w_obj
            if w_obj is not None:
                assert w_obj.force == True
                w_obj.force = False
            r = ExecutionContext.eval_frame(self, f)
            result = space.union(result, r)
            if isinstance(result, W_Anything):
                break
        return result
