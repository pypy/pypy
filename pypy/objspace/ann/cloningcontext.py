from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.pyframe import ControlFlowException, ExitFrame
from pypy.objspace.ann.wrapper \
     import union, compatible_frames, unite_frames, W_Anything, W_Constant

class IndeterminateCondition(ControlFlowException):

    def __init__(self, w_obj):
        ControlFlowException.__init__(self)
        self.w_obj = w_obj

    def action(self, frame, last_instr):
        frame.next_instr = last_instr # Restart failed opcode (!)
        frame.restarting = (self.w_obj, True) # For bytecode_trace() below

class CloningExecutionContext(ExecutionContext):

    def __init__(self, space):
        ExecutionContext.__init__(self, space)
        self.knownframes = {}
        # {(bytecode, w_globals): (result, clones, {next_instr: [frame, ...], ...}), ...}

    def bytecode_trace(self, frame):
        assert isinstance(frame.w_globals, W_Constant)
        key = (frame.bytecode, id(frame.w_globals.value))
        result, clones, subdict = self.knownframes[key]

        if frame.restarting is not None:
            w_obj, flag = frame.restarting
            frame.restarting = None
            w_obj.force = flag
            if flag:
                f2 = frame.clone()
                f2.restarting = (w_obj, False)
                clones.append(f2)
            return

        frames = subdict.setdefault(frame.next_instr, [])
        assert len(frames) <= 1 # We think this is true
        for f in frames:
            if compatible_frames(frame, f):
                c1, c2 = unite_frames(frame, f)
                if not c2:
                    # A fixpoint
                    raise ExitFrame(None)
                return
        frames.append(frame.clone())

    def eval_frame(self, frame):
        assert not hasattr(frame, "clones")
        assert self.space == frame.space
        frame.restarting = None
        key = (frame.bytecode, id(frame.w_globals.value))
        result, clones, subdict = self.knownframes.setdefault(key, (None, [], {}))
        clones.append(frame)
        while clones:
            f = clones.pop()
            r = ExecutionContext.eval_frame(self, f)
            result, clones, subdict = self.knownframes[key]
            result = union(result, r)
            self.knownframes[key] = result, clones, subdict
        return result
