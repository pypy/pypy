from pypy.interpreter.executioncontext import ExecutionContext, Stack
from pypy.interpreter.pyframe \
     import ControlFlowException, ExitFrame, PyFrame, Cell
from pypy.objspace.ann.wrapper \
     import union, compatible_frames, unify_frames, W_Anything, W_Constant, \
            W_KnownKeysContainer

class FunctionInfo(object):

    def __init__(self, ec):
        self.ec = ec
        self.result = None
        self.clones = [] # List of (next_instr, w_obj, force) tuples
        self.knownframes = {} # Mapping from next_instr to list of frames

    def addresult(self, result):
        self.result = union(self.result, result)

    def addclone(self, next_instr, stack_level, block_level, w_obj, force):
        self.clones.append((next_instr, stack_level, block_level, w_obj, force))

    def getclone(self):
        if not self.clones:
            return None
        next_instr, stack_level, block_level, w_obj, force = self.clones.pop()
        frames = self.knownframes[next_instr]
        for f in frames:
            assert f.next_instr == next_instr
            if (f.valuestack.depth() == stack_level and
                f.blockstack.depth() == block_level):
                f = self.ec.clone_frame(f)
                f.restarting = (w_obj, force)
                return f
        assert False, "no suitable clone found -- impossible"

    def addknown(self, frame):
        frames = self.knownframes.setdefault(frame.next_instr, [])
        frames.append(frame)

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
        info.addclone(last_instr,
                      frame.valuestack.depth(),
                      frame.blockstack.depth(),
                      self.w_obj,
                      True)
        info.addclone(last_instr,
                      frame.valuestack.depth(),
                      frame.blockstack.depth(),
                      self.w_obj,
                      False)
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
            self.functioninfos[key] = info = FunctionInfo(self)
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
        info.addknown(self.clone_frame(frame))

    def eval_frame(self, frame):
        assert self.space is frame.space
        frame.restarting = None
        info = self.getfunctioninfo(frame, True)
        while frame is not None:
            result = ExecutionContext.eval_frame(self, frame)
            info.addresult(result)
            frame = info.getclone()
        w_result = info.getresult()
        if w_result is None:
            raise TypeError("no result at all?!?!")
        return w_result

    def clone_frame(self, frame):
        f = PyFrame(self.space, frame.bytecode, frame.w_globals, frame.w_locals)
        f.valuestack = clonevaluestack(frame.valuestack)
        f.blockstack = cloneblockstack(frame.blockstack)
        f.last_exception = frame.last_exception
        f.next_instr = frame.next_instr
        f.localcells = clonecells(frame.localcells)
        f.nestedcells = clonecells(frame.nestedcells)
        return f

class HelperExecutionContext(CloningExecutionContext):

    def eval_frame(self, frame):
        frame.key = object()
        result = CloningExecutionContext.eval_frame(self, frame)
        return result

    def makekey(self, frame):
        return frame.key

    def clone_frame(self, frame):
        f = CloningExecutionContext.clone_frame(self, frame)
        f.key = frame.key
        return f

def cloneblockstack(stk):
    newstk = Stack()
    newstk.items = stk.items[:]
    return newstk

def clonevaluestack(stk):
    newstk = Stack()
    for item in stk.items:
        try:
           newitem = item.clone()
        except AttributeError:
           newitem = item
        newstk.push(newitem)
    return newstk
          
def clonecells(cells):
    """Clone a list of cells."""
    newcells = []
    for cell in cells:
        try:
            value = cell.get()
        except ValueError:
            newcell = Cell()
        else:
            newcell = Cell(value)
        newcells.append(newcell)
    return newcells
