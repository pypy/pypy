from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.pyframe import ControlFlowException, ExitFrame
from pypy.objspace.ann.wrapper \
     import union, compatible_frames, unify_frames, W_Anything, W_Constant, \
            W_KnownKeysContainer

class FunctionInfo(object):

    def __init__(self):
        self.result = None
        self.clones = [] # List of (next_instr, w_obj, force) tuples
        self.knownframes = {} # Mapping from next_instr to list of frames

    def addresult(self, result):
        self.result = union(self.result, result)

    def addclone(self, next_instr, w_obj, force):
        self.clones.append((next_instr, w_obj, force))

    def getframe(self):
        if not self.clones:
            return None
        next_instr, w_obj, force = self.clones.pop()
        frames = self.knownframes[next_instr]
        assert len(frames) == 1
        f = frames[0].clone()
        f.restarting = (w_obj, force)
        return f

    def addknown(self, frame):
        frames = self.knownframes.setdefault(frame.next_instr, [])
        frames.append(frame)
        assert len(frames) <= 1 # We think this is true

    def iterknown(self, frame):
        return iter(self.knownframes.get(frame.next_instr, []))

    def getresult(self):
        return self.result

class IndeterminateCondition(ControlFlowException):

    def __init__(self, w_obj):
        ControlFlowException.__init__(self)
        self.w_obj = w_obj

    def action(self, frame, last_instr, context):
        info = context.getfunctioninfo(frame)
        info.addclone(last_instr, self.w_obj, True)
        info.addclone(last_instr, self.w_obj, False)
        # Abandon this frame; the two clones will take over
        raise ExitFrame(None)

class CloningExecutionContext(ExecutionContext):

    def __init__(self, space):
        ExecutionContext.__init__(self, space)
        self.functioninfos = {}
        # {(bytecode, w_globals): FunctionInfo(), ...}

    def getfunctioninfo(self, frame, new=False):
        key = self.makekey(frame)
        info = self.functioninfos.get(key)
        if info is None:
            if not new:
                raise KeyError, repr(key)
            self.functioninfos[key] = info = FunctionInfo()
        return info

    def makekey(self, frame):
        if isinstance(frame.w_globals, W_Constant):
            return (frame.bytecode, id(frame.w_globals.value))
        if isinstance(frame.w_globals, W_KnownKeysContainer):
            return (frame.bytecode, id(frame.w_globals.args_w))

    def bytecode_trace(self, frame):
        if frame.restarting is not None:
            w_obj, flag = frame.restarting
            frame.restarting = None
            w_obj.force = flag
            return

        info = self.getfunctioninfo(frame)
        for f in info.iterknown(frame):
            if compatible_frames(frame, f):
                c1, c2 = unify_frames(frame, f)
                if not c2:
                    # A fixpoint; abandon this frame
                    raise ExitFrame(None)
                return
        info.addknown(frame.clone())

    def eval_frame(self, frame):
        assert self.space is frame.space
        frame.restarting = None
        info = self.getfunctioninfo(frame, True)
        while frame is not None:
            result = ExecutionContext.eval_frame(self, frame)
            info.addresult(result)
            frame = info.getframe()
        return info.getresult()
