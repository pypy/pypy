from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.miscutils import Stack
from pypy.interpreter.pyframe \
     import ControlFlowException, ExitFrame, PyFrame
from pypy.objspace.flow.model import *
from pypy.objspace.flow.framestate import FrameState


class SpamBlock(Block):
    dead = False
      
    def __init__(self, framestate):
        Block.__init__(self, framestate.getvariables())
        self.framestate = framestate

    def patchframe(self, frame, executioncontext):
        if self.dead:
            raise ExitFrame(None)
        self.framestate.restoreframe(frame)
        executioncontext.crnt_block = self
        executioncontext.crnt_ops = self.operations


class EggBlock(Block):

    def __init__(self, inputargs, prevblock, booloutcome):
        Block.__init__(self, inputargs)
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
        dummy = UndefinedConstant()
        arg_list = ([Variable() for i in range(formalargcount)] +
                    [dummy] * (len(frame.fastlocals_w) - formalargcount))
        frame.setfastscope(arg_list)
        self.joinpoints = {}
        for joinpoint in code.getjoinpoints():
            self.joinpoints[joinpoint] = None
        initialblock = SpamBlock(FrameState(frame).copy())
        self.pendingblocks = [initialblock]
        self.graph = FunctionGraph(code.co_name, initialblock)

    def bytecode_trace(self, frame):
        if isinstance(self.crnt_ops, ReplayList):
            return
        next_instr = frame.next_instr
        if next_instr in self.joinpoints:
            block = self.joinpoints[next_instr]
            currentstate = FrameState(frame)
            if block is None:
                newstate = currentstate.copy()
                finished = False
            else:
                # there is already a block for this bytecode position,
                # we merge its state with the new (current) state.
                newstate = block.framestate.union(currentstate)
                finished = newstate == block.framestate
            if finished:
                newblock = block
            else:
                newblock = SpamBlock(newstate)
            # unconditionally link the current block to the newblock
            outputargs = currentstate.getoutputargs(newstate)
            self.crnt_block.closeblock(Link(outputargs, newblock))
            # phew
            if finished:
                raise ExitFrame(None)
            if block is not None and block.exits:
                # to simplify the graph, we patch the old block to point
                # directly at the new block which is its generalization
                block.dead = True
                block.operations = ()
                outputargs = block.framestate.getoutputargs(newstate)
                block.recloseblock(Link(outputargs, newblock))
            newblock.patchframe(frame, self)
            self.joinpoints[next_instr] = newblock

    def guessbool(self, w_condition):
        if not isinstance(self.crnt_ops, ReplayList):
            block = self.crnt_block
            vars = block.getvariables()
            ifEgg = EggBlock(vars, block, True)
            elseEgg = EggBlock(vars, block, False)
            ifLink = Link(vars, ifEgg, True)
            elseLink = Link(vars, elseEgg, False)
            block.exitswitch = w_condition
            block.closeblock(elseLink, ifLink)
            # forked the graph. Note that elseLink comes before ifLink
            # in the exits tuple so that (just in case we need it) we
            # actually have block.exits[False] = elseLink and
            # block.exits[True] = ifLink.
            self.pendingblocks.append(ifEgg)
            self.pendingblocks.append(elseEgg)
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
                link = Link([w_result], self.graph.returnblock)
                self.crnt_block.closeblock(link)
        self.fixeggblocks()

    def fixeggblocks(self):
        # EggBlocks reuse the variables of their previous block,
        # which is deemed not acceptable for simplicity of the operations
        # that will be performed later on the flow graph.
        def fixegg(node):
            if isinstance(node, EggBlock):
                mapping = {}
                for a in node.inputargs:
                    mapping[a] = Variable()
                node.renamevariables(mapping)
        traverse(fixegg, self.graph)
