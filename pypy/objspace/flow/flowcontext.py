import collections
import sys
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.error import OperationError
from pypy.interpreter import pyframe, nestedscope
from pypy.interpreter.argument import ArgumentsForTranslation
from pypy.objspace.flow import operation
from pypy.objspace.flow.model import *
from pypy.objspace.flow.framestate import FrameState
from pypy.rlib import jit
from pypy.tool.stdlib_opcode import host_bytecode_spec

class StopFlowing(Exception):
    pass

class MergeBlock(Exception):
    def __init__(self, block, currentstate):
        self.block = block
        self.currentstate = currentstate

class SpamBlock(Block):
    # make slots optional, for debugging
    if hasattr(Block, '__slots__'):
        __slots__ = "dead framestate".split()

    def __init__(self, framestate):
        Block.__init__(self, framestate.getvariables())
        self.framestate = framestate
        self.dead = False

    def patchframe(self, frame):
        if self.dead:
            raise StopFlowing
        self.framestate.restoreframe(frame)
        return BlockRecorder(self)


class EggBlock(Block):
    # make slots optional, for debugging
    if hasattr(Block, '__slots__'):
        __slots__ = "prevblock booloutcome last_exception".split()

    def __init__(self, inputargs, prevblock, booloutcome):
        Block.__init__(self, inputargs)
        self.prevblock = prevblock
        self.booloutcome = booloutcome

    def patchframe(self, frame):
        parentblocks = []
        block = self
        while isinstance(block, EggBlock):
            block = block.prevblock
            parentblocks.append(block)
        # parentblocks = [Egg, Egg, ..., Egg, Spam] not including self
        block.patchframe(frame)
        recorder = BlockRecorder(self)
        prevblock = self
        for block in parentblocks:
            recorder = Replayer(block, prevblock.booloutcome, recorder)
            prevblock = block
        return recorder

    def extravars(self, last_exception=None, last_exc_value=None):
        self.last_exception = last_exception

# ____________________________________________________________

class Recorder:

    def append(self, operation):
        raise NotImplementedError

    def bytecode_trace(self, ec, frame):
        pass

    def guessbool(self, ec, w_condition, **kwds):
        raise AssertionError, "cannot guessbool(%s)" % (w_condition,)


class BlockRecorder(Recorder):
    # Records all generated operations into a block.

    def __init__(self, block):
        self.crnt_block = block
        # saved state at the join point most recently seen
        self.last_join_point = None
        self.enterspamblock = isinstance(block, SpamBlock)

    def append(self, operation):
        if self.last_join_point is not None:
            # only add operations corresponding to the first bytecode
            raise MergeBlock(self.crnt_block, self.last_join_point)
        self.crnt_block.operations.append(operation)

    def bytecode_trace(self, ec, frame):
        assert frame is ec.crnt_frame, "seeing an unexpected frame!"
        ec.crnt_offset = frame.last_instr      # save offset for opcode
        if self.enterspamblock:
            # If we have a SpamBlock, the first call to bytecode_trace()
            # occurs as soon as frame.resume() starts, before interpretation
            # really begins.
            varnames = frame.pycode.getvarnames()
            for name, w_value in zip(varnames, frame.getfastscope()):
                if isinstance(w_value, Variable):
                    w_value.rename(name)
            self.enterspamblock = False
        else:
            # At this point, we progress to the next bytecode.  When this
            # occurs, we no longer allow any more operations to be recorded in
            # the same block.  We will continue, to figure out where the next
            # such operation *would* appear, and we make a join point just
            # before.
            self.last_join_point = FrameState(frame)

    def guessbool(self, ec, w_condition, cases=[False,True],
                  replace_last_variable_except_in_first_case = None):
        block = self.crnt_block
        bvars = vars = vars2 = block.getvariables()
        links = []
        first = True
        attach = {}
        for case in cases:
            if first:
                first = False
            elif replace_last_variable_except_in_first_case is not None:
                assert block.operations[-1].result is bvars[-1]
                vars = bvars[:-1]
                vars2 = bvars[:-1]
                for name, newvar in replace_last_variable_except_in_first_case(case):
                    attach[name] = newvar
                    vars.append(newvar)
                    vars2.append(Variable())
            egg = EggBlock(vars2, block, case)
            ec.pendingblocks.append(egg)
            link = ec.make_link(vars, egg, case)
            if attach:
                link.extravars(**attach)
                egg.extravars(**attach) # xxx
            links.append(link)

        block.exitswitch = w_condition
        block.closeblock(*links)
        # forked the graph. Note that False comes before True by default
        # in the exits tuple so that (just in case we need it) we
        # actually have block.exits[False] = elseLink and
        # block.exits[True] = ifLink.
        raise StopFlowing


class Replayer(Recorder):

    def __init__(self, block, booloutcome, nextreplayer):
        self.crnt_block = block
        self.listtoreplay = block.operations
        self.booloutcome = booloutcome
        self.nextreplayer = nextreplayer
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

    def guessbool(self, ec, w_condition, **kwds):
        assert self.index == len(self.listtoreplay)
        ec.recorder = self.nextreplayer
        return self.booloutcome


class ConcreteNoOp(Recorder):
    # In "concrete mode", no SpaceOperations between Variables are allowed.
    # Concrete mode is used to precompute lazily-initialized caches,
    # when we don't want this precomputation to show up on the flow graph.
    def append(self, operation):
        raise AssertionError, "concrete mode: cannot perform %s" % operation

# ____________________________________________________________


class FlowExecutionContext(ExecutionContext):

    def __init__(self, space, code, globals, constargs={}, closure=None,
                 name=None):
        ExecutionContext.__init__(self, space)
        self.code = code

        self.w_globals = w_globals = space.wrap(globals)

        self.crnt_offset = -1
        self.crnt_frame = None
        if closure is None:
            self.closure = None
        else:
            self.closure = [nestedscope.Cell(Constant(value))
                            for value in closure]
        frame = self.create_frame()
        formalargcount = code.getformalargcount()
        arg_list = [Variable() for i in range(formalargcount)]
        for position, value in constargs.items():
            arg_list[position] = Constant(value)
        frame.setfastscope(arg_list)
        self.joinpoints = {}
        initialblock = SpamBlock(FrameState(frame).copy())
        self.pendingblocks = collections.deque([initialblock])
        self.graph = FunctionGraph(name or code.co_name, initialblock)

    make_link = Link # overridable for transition tracking

    def create_frame(self):
        # create an empty frame suitable for the code object
        # while ignoring any operation like the creation of the locals dict
        self.recorder = []
        frame = FlowSpaceFrame(self.space, self.code,
                               self.w_globals, self.closure)
        frame.last_instr = 0
        return frame

    def bytecode_trace(self, frame):
        self.recorder.bytecode_trace(self, frame)

    def guessbool(self, w_condition, **kwds):
        return self.recorder.guessbool(self, w_condition, **kwds)

    def guessexception(self, *classes):
        def replace_exc_values(case):
            if case is not Exception:
                yield 'last_exception', Constant(case)
                yield 'last_exc_value', Variable('last_exc_value')
            else:
                yield 'last_exception', Variable('last_exception')
                yield 'last_exc_value', Variable('last_exc_value')
        outcome = self.guessbool(c_last_exception,
                                 cases = [None] + list(classes),
                                 replace_last_variable_except_in_first_case = replace_exc_values)
        if outcome is None:
            w_exc_cls, w_exc_value = None, None
        else:
            egg = self.recorder.crnt_block
            w_exc_cls, w_exc_value = egg.inputargs[-2:]
            if isinstance(egg.last_exception, Constant):
                w_exc_cls = egg.last_exception
        return outcome, w_exc_cls, w_exc_value

    def build_flow(self):
        while self.pendingblocks:
            block = self.pendingblocks.popleft()
            frame = self.create_frame()
            try:
                self.recorder = block.patchframe(frame)
            except StopFlowing:
                continue   # restarting a dead SpamBlock
            try:
                old_frameref = self.topframeref
                self.topframeref = jit.non_virtual_ref(frame)
                self.crnt_frame = frame
                try:
                    w_result = frame.dispatch(frame.pycode,
                                              frame.last_instr,
                                              self)
                finally:
                    self.crnt_frame = None
                    self.topframeref = old_frameref

            except operation.OperationThatShouldNotBePropagatedError, e:
                raise Exception(
                    'found an operation that always raises %s: %s' % (
                        self.space.unwrap(e.w_type).__name__,
                        self.space.unwrap(e.get_w_value(self.space))))

            except operation.ImplicitOperationError, e:
                if isinstance(e.w_type, Constant):
                    exc_cls = e.w_type.value
                else:
                    exc_cls = Exception
                msg = "implicit %s shouldn't occur" % exc_cls.__name__
                w_type = Constant(AssertionError)
                w_value = Constant(AssertionError(msg))
                link = self.make_link([w_type, w_value], self.graph.exceptblock)
                self.recorder.crnt_block.closeblock(link)

            except OperationError, e:
                #print "OE", e.w_type, e.get_w_value(self.space)
                if (self.space.do_imports_immediately and
                    e.w_type is self.space.w_ImportError):
                    raise ImportError('import statement always raises %s' % (
                        e,))
                w_value = e.get_w_value(self.space)
                link = self.make_link([e.w_type, w_value], self.graph.exceptblock)
                self.recorder.crnt_block.closeblock(link)

            except StopFlowing:
                pass

            except MergeBlock, e:
                self.mergeblock(e.block, e.currentstate)

            else:
                assert w_result is not None
                link = self.make_link([w_result], self.graph.returnblock)
                self.recorder.crnt_block.closeblock(link)

            del self.recorder
        self.fixeggblocks()

    def fixeggblocks(self):
        # EggBlocks reuse the variables of their previous block,
        # which is deemed not acceptable for simplicity of the operations
        # that will be performed later on the flow graph.
        for link in list(self.graph.iterlinks()):
                block = link.target
                if isinstance(block, EggBlock):
                    if (not block.operations and len(block.exits) == 1 and
                        link.args == block.inputargs):   # not renamed
                        # if the variables are not renamed across this link
                        # (common case for EggBlocks) then it's easy enough to
                        # get rid of the empty EggBlock.
                        link2 = block.exits[0]
                        link.args = list(link2.args)
                        link.target = link2.target
                        assert link2.exitcase is None
                    else:
                        mapping = {}
                        for a in block.inputargs:
                            mapping[a] = Variable(a)
                        block.renamevariables(mapping)
        for block in self.graph.iterblocks():
            if isinstance(link, SpamBlock):
                del link.framestate     # memory saver

    def mergeblock(self, currentblock, currentstate):
        next_instr = currentstate.next_instr
        # can 'currentstate' be merged with one of the blocks that
        # already exist for this bytecode position?
        candidates = self.joinpoints.setdefault(next_instr, [])
        for block in candidates:
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
        link = self.make_link(outputargs, newblock)
        currentblock.closeblock(link)
        # phew
        if not finished:
            if block is not None:
                # to simplify the graph, we patch the old block to point
                # directly at the new block which is its generalization
                block.dead = True
                block.operations = ()
                block.exitswitch = None
                outputargs = block.framestate.getoutputargs(newstate)
                block.recloseblock(self.make_link(outputargs, newblock))
                candidates.remove(block)
            candidates.insert(0, newblock)
            self.pendingblocks.append(newblock)

    def _convert_exc(self, operr):
        if isinstance(operr, operation.ImplicitOperationError):
            # re-raising an implicit operation makes it an explicit one
            w_value = operr.get_w_value(self.space)
            operr = OperationError(operr.w_type, w_value)
        return operr

    def exception_trace(self, frame, operationerr):
        pass    # overridden for performance only

    # hack for unrolling iterables, don't use this
    def replace_in_stack(self, oldvalue, newvalue):
        w_new = Constant(newvalue)
        f = self.crnt_frame
        stack_items_w = f.locals_stack_w
        for i in range(f.valuestackdepth-1, f.nlocals-1, -1):
            w_v = stack_items_w[i]
            if isinstance(w_v, Constant):
                if w_v.value is oldvalue:
                    # replace the topmost item of the stack that is equal
                    # to 'oldvalue' with 'newvalue'.
                    stack_items_w[i] = w_new
                    break

class FlowSpaceFrame(pyframe.CPythonFrame):

    def SETUP_WITH(self, offsettoend, next_instr):
        # A simpler version than the 'real' 2.7 one:
        # directly call manager.__enter__(), don't use special lookup functions
        # which don't make sense on the RPython type system.
        from pypy.interpreter.pyopcode import WithBlock
        w_manager = self.peekvalue()
        w_exit = self.space.getattr(w_manager, self.space.wrap("__exit__"))
        self.settopvalue(w_exit)
        w_result = self.space.call_method(w_manager, "__enter__")
        block = WithBlock(self, next_instr + offsettoend, self.lastblock)
        self.lastblock = block
        self.pushvalue(w_result)

    # XXX Unimplemented 2.7 opcodes ----------------

    # Set literals, set comprehensions

    def BUILD_SET(self, oparg, next_instr):
        raise NotImplementedError("BUILD_SET")

    def SET_ADD(self, oparg, next_instr):
        raise NotImplementedError("SET_ADD")

    # Dict comprehensions

    def MAP_ADD(self, oparg, next_instr):
        raise NotImplementedError("MAP_ADD")

    def make_arguments(self, nargs):
        return ArgumentsForTranslation(self.space, self.peekvalues(nargs))
    def argument_factory(self, *args):
        return ArgumentsForTranslation(self.space, *args)

    def handle_operation_error(self, ec, operr, *args, **kwds):
        # see test_propagate_attribute_error for why this is here
        if isinstance(operr, operation.OperationThatShouldNotBePropagatedError):
            raise operr
        return pyframe.PyFrame.handle_operation_error(self, ec, operr,
                                                      *args, **kwds)

    def call_contextmanager_exit_function(self, w_func, w_typ, w_val, w_tb):
        if w_typ is not self.space.w_None:
            # The annotator won't allow to merge exception types with None.
            # Replace it with the exception value...
            w_typ = w_val
        self.space.call_function(w_func, w_typ, w_val, w_tb)
        # Return None so that the flow space statically knows that we didn't
        # swallow the exception
        return self.space.w_None

