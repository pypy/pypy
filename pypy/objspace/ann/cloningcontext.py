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

class FunctionInfo(object):

    def __init__(self):
        self.result = None
        self.clones = [] # List of frames
        self.knownframes = {} # Mapping from next_instr to list of frames

    def addresult(self, result):
        self.result = union(self.result, result)

    def addclone(self, frame):
        self.clones.append(frame)

    def addknown(self, frame):
        frames = self.knownframes.setdefault(frame.next_instr, [])
        frames.append(frame)
        assert len(frames) <= 1 # We think this is true

    def iterknown(self, frame):
        return iter(self.knownframes.get(frame.next_instr, []))

    def todo(self):
        return len(self.clones)

    def getframe(self):
        return self.clones.pop()

    def getresult(self):
        return self.result

class CloningExecutionContext(ExecutionContext):

    def __init__(self, space):
        ExecutionContext.__init__(self, space)
        self.functioninfos = {}
        # {(bytecode, w_globals): FunctionInfo(), ...}

    def bytecode_trace(self, frame):
        assert isinstance(frame.w_globals, W_Constant)
        key = (frame.bytecode, id(frame.w_globals.value))
        info = self.functioninfos[key]

        if frame.restarting is not None:
            w_obj, flag = frame.restarting
            frame.restarting = None
            w_obj.force = flag
            if flag:
                f2 = frame.clone()
                f2.restarting = (w_obj, False)
                info.addclone(f2)
            return

        for f in info.iterknown(frame):
            if compatible_frames(frame, f):
                c1, c2 = unite_frames(frame, f)
                if not c2:
                    # A fixpoint
                    raise ExitFrame(None)
                return
        info.addknown(frame.clone())

    def eval_frame(self, frame):
        assert self.space is frame.space
        frame.restarting = None
        key = (frame.bytecode, id(frame.w_globals.value))
        info = self.functioninfos.get(key)
        if info is None:
            self.functioninfos[key] = info = FunctionInfo()
        info.addclone(frame)
        while info.todo():
            f = info.getframe()
            r = ExecutionContext.eval_frame(self, f)
            info.addresult(r)
        return info.getresult()
