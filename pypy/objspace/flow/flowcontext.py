from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.miscutils import Stack
from pypy.interpreter.pyframe \
     import ControlFlowException, ExitFrame, PyFrame
from pypy.objspace.flow.wrapper import W_Variable, W_Constant, UnwrapException
from pypy.translator.flowmodel import *


def constantsof(lst):
    result = {}
    for i in range(len(lst)):
        if isinstance(lst[i], W_Constant):
            result[i] = lst[i]
    return result

class SpamBlock(BasicBlock):
    dead = False
    
    def __init__(self, framestate):
        mergeablestate, unmergeablestate = framestate
        newstate = []
        inputargs = []
        for w in mergeablestate:
            if isinstance(w, W_Variable):
                w = W_Variable()  # make fresh variables
                inputargs.append(w)   # collects all variables
            newstate.append(w)
        self.framestate = newstate, unmergeablestate
        #import sys; print >> sys.stderr, "** creating SpamBlock", self.framestate
        BasicBlock.__init__(self, inputargs, inputargs, [], None)

    def patchframe(self, frame, executioncontext):
        if self.dead:
            raise ExitFrame(None)
        frame.setflowstate(self.framestate)
        executioncontext.crnt_block = self
        executioncontext.crnt_ops = self.operations

    def union(self, other):
        mergeablestate1, unmergeablestate1 = self.framestate
        mergeablestate2, unmergeablestate2 = other.framestate
##        XXX reintroduce me
##        assert unmergeablestate1 == unmergeablestate2, (
##            "non mergeable states reached:\n%r\n%r" % (
##            unmergeablestate1, unmergeablestate2))
        assert len(mergeablestate1) == len(mergeablestate2), (
            "non mergeable states (different value stack depth)")

        newstate = []
        for w1, w2 in zip(mergeablestate1, mergeablestate2):
            if w1 == w2 or isinstance(w1, W_Variable):
                w = w1
            else:
                w = W_Variable()
            newstate.append(w)
        if constantsof(newstate) == constantsof(mergeablestate1):
            return self
        elif constantsof(newstate) == constantsof(mergeablestate2):
            return other
        else:
            return SpamBlock((newstate, unmergeablestate1))

class EggBlock(BasicBlock):

    def __init__(self, prevblock, booloutcome):
        BasicBlock.__init__(self, [], prevblock.locals, [], None)
        self.prevblock = prevblock
        self.booloutcome = booloutcome

    def patchframe(self, frame, executioncontext):
        parentblocks = []
        block = self
        while isinstance(block, EggBlock):
            block = block.prevblock
            parentblocks.append(block)
        # parentblocks = [Egg, Egg, ..., Egg, Spam] not including self
        block.patchframe(frame, executioncontext)
        replaylist = self.operations
        prevblock = self
        for block in parentblocks:
            replaylist = ReplayList(block.operations,
                                    prevblock, prevblock.booloutcome,
                                    replaylist)
            prevblock = block
        executioncontext.crnt_ops = replaylist

class ReplayList:
    
    def __init__(self, listtoreplay, nextblock, booloutcome, nextreplaylist):
        self.listtoreplay = listtoreplay
        self.nextblock = nextblock
        self.booloutcome = booloutcome
        self.nextreplaylist = nextreplaylist
        self.index = 0
        
    def append(self, operation):
        operation.result = self.listtoreplay[self.index].result
        assert operation == self.listtoreplay[self.index]
        self.index += 1

    def finished(self):
        return self.index == len(self.listtoreplay)

class FlowExecutionContext(ExecutionContext):

    def __init__(self, space, code, globals):
        ExecutionContext.__init__(self, space)
        self.code = code
        self.w_globals = w_globals = space.wrap(globals)
        frame = code.create_frame(space, w_globals)
        formalargcount = code.getformalargcount()
        arg_list = ([W_Variable() for i in range(formalargcount)] +
                    [W_Constant(None)] * (len(frame.fastlocals_w) -
                                          formalargcount))
        frame.setfastscope(arg_list)
        self.joinpoints = {}
        for joinpoint in code.getjoinpoints():
            self.joinpoints[joinpoint] = None
        initialblock = SpamBlock(frame.getflowstate())
        # only keep arguments of the function in initialblock.input_args
        del initialblock.input_args[formalargcount:]
        self.pendingblocks = [initialblock]
        self.graph = FunctionGraph(initialblock, code.co_name)

    def bytecode_trace(self, frame):
        if isinstance(self.crnt_ops, ReplayList):
            return
        next_instr = frame.next_instr
        if next_instr in self.joinpoints:
            block = self.joinpoints[next_instr]
            currentframestate = frame.getflowstate()
            newblock = SpamBlock(currentframestate)
            if block is not None:
                newblock = block.union(newblock)
            finished = newblock is block
            outputargs = []
            for w_output, w_target in zip(currentframestate[0],
                                          newblock.framestate[0]):
                if isinstance(w_target, W_Variable):
                    outputargs.append(w_output)
            self.crnt_block.closeblock(Branch(outputargs, newblock))
            # phew
            if finished:
                raise ExitFrame(None)
            if block is not None and isinstance(block.operations, tuple):
                # patch the old block to point directly at the new block
                block.dead = True
                block.operations = ()
                outputargs = []
                for w_output, w_target in zip(block.framestate[0],
                                              newblock.framestate[0]):
                    if isinstance(w_target, W_Variable):
                        outputargs.append(w_output)
                block.branch = Branch(outputargs, newblock)
            newblock.patchframe(frame, self)
            self.joinpoints[next_instr] = newblock

    def guessbool(self, w_condition):
        if not isinstance(self.crnt_ops, ReplayList):
            block = self.crnt_block
            ifegg = EggBlock(block, True)
            elseegg = EggBlock(block, False)
            ifbranch = Branch([], ifegg)
            elsebranch = Branch([], elseegg)
            branch = ConditionalBranch(w_condition, ifbranch, elsebranch)
            block.closeblock(branch)
            self.pendingblocks.append(ifegg)
            self.pendingblocks.append(elseegg)
            raise ExitFrame(None)
        replaylist = self.crnt_ops
        assert replaylist.finished()
        self.crnt_block = replaylist.nextblock
        self.crnt_ops = replaylist.nextreplaylist
        return replaylist.booloutcome

    def build_flow(self):
        while self.pendingblocks:
            block = self.pendingblocks.pop(0)
            frame = self.code.create_frame(self.space, self.w_globals)
            try:
                block.patchframe(frame, self)
            except ExitFrame:
                continue   # restarting a dead SpamBlock
            w_result = frame.eval(self)
            if w_result is not None:
                self.crnt_block.closeblock(EndBranch(w_result))
