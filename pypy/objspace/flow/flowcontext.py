from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.pyframe import ExitFrame
from pypy.interpreter.error import OperationError
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
        assert operation == self.listtoreplay[self.index], (
            '\n'.join(["Not generating the same operation sequence:"] +
                      [str(s) for s in self.listtoreplay[:self.index]] +
                      ["  ---> | while repeating we see here"] +
                      ["       | %s" % operation] +
                      [str(s) for s in self.listtoreplay[self.index:]]))
        self.index += 1

    def finished(self):
        return self.index == len(self.listtoreplay)

class ConcreteNoOp:
    # In "concrete mode", no SpaceOperations between Variables are allowed.
    # Concrete mode is used to precompute lazily-initialized caches,
    # when we don't want this precomputation to show up on the flow graph.
    def append(self, operation):
        raise AssertionError, "concrete mode: cannot perform %s" % operation

class FlowExecutionContext(ExecutionContext):

    def __init__(self, space, code, globals, constargs={}, closure=None):
        ExecutionContext.__init__(self, space)
        self.code = code
        self.w_globals = w_globals = space.wrap(globals)
        if closure is None:
            self.closure = None
        else:
            from pypy.interpreter.nestedscope import Cell
            self.closure = [Cell(Constant(value)) for value in closure]
        frame = self.create_frame()
        formalargcount = code.getformalargcount()
        arg_list = [Variable() for i in range(formalargcount)]
        for position, value in constargs.items():
            arg_list[position] = Constant(value)
        frame.setfastscope(arg_list)
        self.joinpoints = {}
        for joinpoint in code.getjoinpoints():
            self.joinpoints[joinpoint] = []  # list of blocks
        initialblock = SpamBlock(FrameState(frame).copy())
        self.pendingblocks = [initialblock]
        self.graph = FunctionGraph(code.co_name, initialblock)

    def create_frame(self):
        # create an empty frame suitable for the code object
        # while ignoring any operation like the creation of the locals dict
        self.crnt_ops = []
        return self.code.create_frame(self.space, self.w_globals,
                                      self.closure)

    def bytecode_trace(self, frame):
        if not isinstance(self.crnt_ops, list):
            return
        next_instr = frame.next_instr
        if next_instr in self.joinpoints:
            currentstate = FrameState(frame)
            # can 'currentstate' be merged with one of the blocks that
            # already exist for this bytecode position?
            for block in self.joinpoints[next_instr]:
                newstate = block.framestate.union(currentstate)
                if newstate is not None:
                    # yes
                    finished = newstate == block.framestate
                    break
            else:
                # no
                newstate = currentstate.copy()
                finished = False
                block = None
            
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
            self.joinpoints[next_instr].insert(0, newblock)

    def guessbool(self, w_condition, cases=[False,True]):
        if isinstance(self.crnt_ops, list):
            block = self.crnt_block
            vars = block.getvariables()
            links = []
            for case in cases:
                egg = EggBlock(vars, block, case)
                self.pendingblocks.append(egg)
                link = Link(vars, egg, case)
                links.append(link)
            block.exitswitch = w_condition
            block.closeblock(*links)
            # forked the graph. Note that False comes before True by default
            # in the exits tuple so that (just in case we need it) we
            # actually have block.exits[False] = elseLink and
            # block.exits[True] = ifLink.
            raise ExitFrame(None)
        if isinstance(self.crnt_ops, ReplayList):
            replaylist = self.crnt_ops
            assert replaylist.finished()
            self.crnt_block = replaylist.nextblock
            self.crnt_ops = replaylist.nextreplaylist
            return replaylist.booloutcome
        raise AssertionError, "concrete mode: cannot guessbool(%s)" % (
            w_condition,)

    def build_flow(self):
        while self.pendingblocks:
            block = self.pendingblocks.pop(0)
            frame = self.create_frame()
            try:
                block.patchframe(frame, self)
            except ExitFrame:
                continue   # restarting a dead SpamBlock
            try:
                w_result = frame.eval(self)
            except OperationError, e:
                exc_type = self.space.unwrap(e.w_type)
                link = Link([e.w_value], self.graph.getexceptblock(exc_type))
                self.crnt_block.closeblock(link)
            else:
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
