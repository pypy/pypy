import collections
import sys
from pypy.tool.error import source_lines
from pypy.interpreter import pyframe
from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.pycode import CO_OPTIMIZED, CO_NEWLOCALS
from pypy.interpreter.argument import ArgumentsForTranslation
from pypy.interpreter.pyopcode import (Return, Yield, SuspendedUnroller,
        SReturnValue, SApplicationException, BytecodeCorruption)
from pypy.objspace.flow.model import *
from pypy.objspace.flow.framestate import (FrameState, recursively_unflatten,
        recursively_flatten)
from pypy.objspace.flow.bytecode import HostCode

class FlowingError(Exception):
    """ Signals invalid RPython in the function being analysed"""
    def __init__(self, frame, msg):
        super(FlowingError, self).__init__(msg)
        self.frame = frame

    def __str__(self):
        msg = ['-+' * 30]
        msg += map(str, self.args)
        msg += source_lines(self.frame.graph, None, offset=self.frame.last_instr)
        return "\n".join(msg)


class StopFlowing(Exception):
    pass

class FSException(Exception):
    def __init__(self, w_type, w_value):
        assert w_type is not None
        self.w_type = w_type
        self.w_value = w_value

    def get_w_value(self, _):
        return self.w_value

    def __str__(self):
        return '[%s: %s]' % (self.w_type, self.w_value)

class ImplicitOperationError(FSException):
    pass

class SpamBlock(Block):
    # make slots optional, for debugging
    if hasattr(Block, '__slots__'):
        __slots__ = "dead framestate".split()

    def __init__(self, framestate):
        Block.__init__(self, framestate.getvariables())
        self.framestate = framestate
        self.dead = False

class EggBlock(Block):
    # make slots optional, for debugging
    if hasattr(Block, '__slots__'):
        __slots__ = "prevblock booloutcome last_exception".split()

    def __init__(self, inputargs, prevblock, booloutcome):
        Block.__init__(self, inputargs)
        self.prevblock = prevblock
        self.booloutcome = booloutcome

    def extravars(self, last_exception=None, last_exc_value=None):
        self.last_exception = last_exception

def fixeggblocks(graph):
    # EggBlocks reuse the variables of their previous block,
    # which is deemed not acceptable for simplicity of the operations
    # that will be performed later on the flow graph.
    for link in list(graph.iterlinks()):
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
    for block in graph.iterblocks():
        if isinstance(link, SpamBlock):
            del link.framestate     # memory saver

# ____________________________________________________________

class Recorder:

    def append(self, operation):
        raise NotImplementedError

    def bytecode_trace(self, frame):
        pass

    def guessbool(self, frame, w_condition, **kwds):
        raise AssertionError, "cannot guessbool(%s)" % (w_condition,)


class BlockRecorder(Recorder):
    # Records all generated operations into a block.

    def __init__(self, block):
        self.crnt_block = block
        # saved state at the join point most recently seen
        self.last_join_point = None
        self.enterspamblock = isinstance(block, SpamBlock)

    def append(self, operation):
        self.crnt_block.operations.append(operation)

    def bytecode_trace(self, frame):
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
            self.last_join_point = frame.getstate()

    def guessbool(self, frame, w_condition):
        block = self.crnt_block
        vars = block.getvariables()
        links = []
        for case in [False, True]:
            egg = EggBlock(vars, block, case)
            frame.pendingblocks.append(egg)
            link = Link(vars, egg, case)
            links.append(link)

        block.exitswitch = w_condition
        block.closeblock(*links)
        # forked the graph. Note that False comes before True by default
        # in the exits tuple so that (just in case we need it) we
        # actually have block.exits[False] = elseLink and
        # block.exits[True] = ifLink.
        raise StopFlowing

    def guessexception(self, frame, *cases):
        block = self.crnt_block
        bvars = vars = vars2 = block.getvariables()
        links = []
        for case in [None] + list(cases):
            if case is not None:
                assert block.operations[-1].result is bvars[-1]
                vars = bvars[:-1]
                vars2 = bvars[:-1]
                if case is Exception:
                    last_exc = Variable('last_exception')
                else:
                    last_exc = Constant(case)
                last_exc_value = Variable('last_exc_value')
                vars.extend([last_exc, last_exc_value])
                vars2.extend([Variable(), Variable()])
            egg = EggBlock(vars2, block, case)
            frame.pendingblocks.append(egg)
            link = Link(vars, egg, case)
            if case is not None:
                link.extravars(last_exception=last_exc, last_exc_value=last_exc_value)
                egg.extravars(last_exception=last_exc)
            links.append(link)

        block.exitswitch = c_last_exception
        block.closeblock(*links)
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

    def guessbool(self, frame, w_condition, **kwds):
        assert self.index == len(self.listtoreplay)
        frame.recorder = self.nextreplayer
        return self.booloutcome

    def guessexception(self, frame, *classes):
        assert self.index == len(self.listtoreplay)
        frame.recorder = self.nextreplayer
        outcome = self.booloutcome
        if outcome is not None:
            egg = self.nextreplayer.crnt_block
            w_exc_cls, w_exc_value = egg.inputargs[-2:]
            if isinstance(egg.last_exception, Constant):
                w_exc_cls = egg.last_exception
            raise ImplicitOperationError(w_exc_cls, w_exc_value)

# ____________________________________________________________

class FlowSpaceFrame(pyframe.CPythonFrame):

    def __init__(self, space, func, constargs=None):
        code = HostCode._from_code(space, func.func_code)
        self.pycode = code
        self.space = space
        self.w_globals = Constant(func.func_globals)
        self.locals_stack_w = [None] * (code.co_nlocals + code.co_stacksize)
        self.valuestackdepth = code.co_nlocals
        self.lastblock = None

        if func.func_closure is not None:
            cl = [c.cell_contents for c in func.func_closure]
            closure = [Cell(Constant(value)) for value in cl]
        else:
            closure = []
        self.initialize_frame_scopes(closure, code)
        self.f_lineno = code.co_firstlineno
        self.last_instr = 0

        if constargs is None:
            constargs = {}
        formalargcount = code.getformalargcount()
        arg_list = [Variable() for i in range(formalargcount)]
        for position, value in constargs.items():
            arg_list[position] = Constant(value)
        self.setfastscope(arg_list)

        self.w_locals = None # XXX: only for compatibility with PyFrame

        self.joinpoints = {}
        self._init_graph(func)
        self.pendingblocks = collections.deque([self.graph.startblock])

    def initialize_frame_scopes(self, closure, code):
        if not (code.co_flags & CO_NEWLOCALS):
            raise ValueError("The code object for a function should have "
                    "the flag CO_NEWLOCALS set.")
        if len(closure) != len(code.co_freevars):
            raise ValueError("code object received a closure with "
                                 "an unexpected number of free variables")
        self.cells = [Cell() for _ in code.co_cellvars] + closure

    def _init_graph(self, func):
        # CallableFactory.pycall may add class_ to functions that are methods
        name = func.func_name
        class_ = getattr(func, 'class_', None)
        if class_ is not None:
            name = '%s.%s' % (class_.__name__, name)
        for c in "<>&!":
            name = name.replace(c, '_')

        initialblock = SpamBlock(self.getstate())
        if self.pycode.is_generator:
            initialblock.operations.append(
                SpaceOperation('generator_mark', [], Variable()))
        graph = FunctionGraph(name, initialblock)
        graph.func = func
        # attach a signature and defaults to the graph
        # so that it becomes even more interchangeable with the function
        # itself
        graph.signature = self.pycode.signature()
        graph.defaults = func.func_defaults or ()
        graph.is_generator = self.pycode.is_generator
        self.graph = graph

    def getstate(self):
        # getfastscope() can return real None, for undefined locals
        data = self.save_locals_stack()
        if self.last_exception is None:
            data.append(Constant(None))
            data.append(Constant(None))
        else:
            data.append(self.last_exception.w_type)
            data.append(self.last_exception.w_value)
        recursively_flatten(self.space, data)
        nonmergeable = (self.get_blocklist(),
            self.last_instr)   # == next_instr when between bytecodes
        return FrameState(data, nonmergeable)

    def setstate(self, state):
        """ Reset the frame to the given state. """
        data = state.mergeable[:]
        recursively_unflatten(self.space, data)
        self.restore_locals_stack(data[:-2])  # Nones == undefined locals
        if data[-2] == Constant(None):
            assert data[-1] == Constant(None)
            self.last_exception = None
        else:
            self.last_exception = FSException(data[-2], data[-1])
        blocklist, self.last_instr = state.nonmergeable
        self.set_blocklist(blocklist)

    def recording(self, block):
        """ Setup recording of the block and return the recorder. """
        parentblocks = []
        parent = block
        while isinstance(parent, EggBlock):
            parent = parent.prevblock
            parentblocks.append(parent)
        # parentblocks = [Egg, Egg, ..., Egg, Spam] not including block
        if parent.dead:
            raise StopFlowing
        self.setstate(parent.framestate)
        recorder = BlockRecorder(block)
        prevblock = block
        for parent in parentblocks:
            recorder = Replayer(parent, prevblock.booloutcome, recorder)
            prevblock = parent
        return recorder

    def record(self, spaceop):
        """Record an operation into the active block"""
        recorder = self.recorder
        if getattr(recorder, 'last_join_point', None) is not None:
            self.mergeblock(recorder.crnt_block, recorder.last_join_point)
            raise StopFlowing
        recorder.append(spaceop)

    def guessbool(self, w_condition, **kwds):
        return self.recorder.guessbool(self, w_condition, **kwds)

    def handle_implicit_exceptions(self, exceptions):
        """
        Catch possible exceptions implicitly.

        If the FSException is not caught in the same function, it will
        produce an exception-raising return block in the flow graph. Note that
        even if the interpreter re-raises the exception, it will not be the
        same ImplicitOperationError instance internally.
        """
        if not exceptions:
            return
        return self.recorder.guessexception(self, *exceptions)

    def build_flow(self):
        while self.pendingblocks:
            block = self.pendingblocks.popleft()
            try:
                self.recorder = self.recording(block)
                self.frame_finished_execution = False
                next_instr = self.last_instr
                while True:
                    next_instr = self.handle_bytecode(next_instr)

            except ImplicitOperationError, e:
                if isinstance(e.w_type, Constant):
                    exc_cls = e.w_type.value
                else:
                    exc_cls = Exception
                msg = "implicit %s shouldn't occur" % exc_cls.__name__
                w_type = Constant(AssertionError)
                w_value = Constant(AssertionError(msg))
                link = Link([w_type, w_value], self.graph.exceptblock)
                self.recorder.crnt_block.closeblock(link)

            except FSException, e:
                if e.w_type is self.space.w_ImportError:
                    msg = 'import statement always raises %s' % e
                    raise ImportError(msg)
                link = Link([e.w_type, e.w_value], self.graph.exceptblock)
                self.recorder.crnt_block.closeblock(link)

            except StopFlowing:
                pass

            except Return:
                w_result = self.popvalue()
                assert w_result is not None
                link = Link([w_result], self.graph.returnblock)
                self.recorder.crnt_block.closeblock(link)

        del self.recorder

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
        link = Link(outputargs, newblock)
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
                block.recloseblock(Link(outputargs, newblock))
                candidates.remove(block)
            candidates.insert(0, newblock)
            self.pendingblocks.append(newblock)

    # hack for unrolling iterables, don't use this
    def replace_in_stack(self, oldvalue, newvalue):
        w_new = Constant(newvalue)
        stack_items_w = self.locals_stack_w
        for i in range(self.valuestackdepth-1, self.pycode.co_nlocals-1, -1):
            w_v = stack_items_w[i]
            if isinstance(w_v, Constant):
                if w_v.value is oldvalue:
                    # replace the topmost item of the stack that is equal
                    # to 'oldvalue' with 'newvalue'.
                    stack_items_w[i] = w_new
                    break

    def handle_bytecode(self, next_instr):
        try:
            while True:
                self.last_instr = next_instr
                self.recorder.bytecode_trace(self)
                next_instr, methodname, oparg = self.pycode.read(next_instr)
                res = getattr(self, methodname)(oparg, next_instr)
                if res is not None:
                    next_instr = res
        except FSException, operr:
            next_instr = self.handle_operation_error(operr)
        return next_instr

    def handle_operation_error(self, operr):
        block = self.unrollstack(SFlowException.kind)
        if block is None:
            raise operr
        else:
            unroller = SFlowException(operr)
            next_instr = block.handle(self, unroller)
            return next_instr

    def RAISE_VARARGS(self, nbargs, next_instr):
        space = self.space
        if nbargs == 0:
            if self.last_exception is not None:
                operr = self.last_exception
                if isinstance(operr, ImplicitOperationError):
                    # re-raising an implicit operation makes it an explicit one
                    operr = FSException(operr.w_type, operr.w_value)
                self.last_exception = operr
                raise operr
            else:
                raise FSException(space.w_TypeError,
                    space.wrap("raise: no active exception to re-raise"))

        w_value = w_traceback = space.w_None
        if nbargs >= 3:
            w_traceback = self.popvalue()
        if nbargs >= 2:
            w_value = self.popvalue()
        if 1:
            w_type = self.popvalue()
        operror = space.exc_from_raise(w_type, w_value)
        raise operror

    def IMPORT_NAME(self, nameindex, next_instr):
        space = self.space
        modulename = self.getname_u(nameindex)
        glob = space.unwrap(self.w_globals)
        fromlist = space.unwrap(self.popvalue())
        level = self.popvalue().value
        w_obj = space.import_name(modulename, glob, None, fromlist, level)
        self.pushvalue(w_obj)

    def IMPORT_FROM(self, nameindex, next_instr):
        w_name = self.getname_w(nameindex)
        w_module = self.peekvalue()
        self.pushvalue(self.space.import_from(w_module, w_name))

    def RETURN_VALUE(self, oparg, next_instr):
        w_returnvalue = self.popvalue()
        block = self.unrollstack(SReturnValue.kind)
        if block is None:
            self.pushvalue(w_returnvalue)   # XXX ping pong
            raise Return
        else:
            unroller = SReturnValue(w_returnvalue)
            next_instr = block.handle(self, unroller)
            return next_instr    # now inside a 'finally' block

    def END_FINALLY(self, oparg, next_instr):
        unroller = self.end_finally()
        if isinstance(unroller, SuspendedUnroller):
            # go on unrolling the stack
            block = self.unrollstack(unroller.kind)
            if block is None:
                w_result = unroller.nomoreblocks()
                self.pushvalue(w_result)
                raise Return
            else:
                next_instr = block.handle(self, unroller)
        return next_instr

    def JUMP_ABSOLUTE(self, jumpto, next_instr):
        return jumpto

    def YIELD_VALUE(self, _, next_instr):
        assert self.pycode.is_generator
        w_result = self.popvalue()
        self.space.do_operation('yield', w_result)
        # XXX yield expressions not supported. This will blow up if the value
        # isn't popped straightaway.
        self.pushvalue(None)

    def FOR_ITER(self, jumpby, next_instr):
        w_iterator = self.peekvalue()
        try:
            w_nextitem = self.space.next(w_iterator)
        except FSException, e:
            if not self.space.exception_match(e.w_type, self.space.w_StopIteration):
                raise
            # iterator exhausted
            self.popvalue()
            next_instr += jumpby
        else:
            self.pushvalue(w_nextitem)
        return next_instr

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

    def WITH_CLEANUP(self, oparg, next_instr):
        # Note: RPython context managers receive None in lieu of tracebacks
        # and cannot suppress the exception.
        # This opcode changed a lot between CPython versions
        if (self.pycode.magic >= 0xa0df2ef
            # Implementation since 2.7a0: 62191 (introduce SETUP_WITH)
            or self.pycode.magic >= 0xa0df2d1):
            # implementation since 2.6a1: 62161 (WITH_CLEANUP optimization)
            w_unroller = self.popvalue()
            w_exitfunc = self.popvalue()
            self.pushvalue(w_unroller)
        elif self.pycode.magic >= 0xa0df28c:
            # Implementation since 2.5a0: 62092 (changed WITH_CLEANUP opcode)
            w_exitfunc = self.popvalue()
            w_unroller = self.peekvalue(0)
        else:
            raise NotImplementedError("WITH_CLEANUP for CPython <= 2.4")

        unroller = self.space.interpclass_w(w_unroller)
        w_None = self.space.w_None
        is_app_exc = (unroller is not None and
                      isinstance(unroller, SApplicationException))
        if is_app_exc:
            operr = unroller.operr
            # The annotator won't allow to merge exception types with None.
            # Replace it with the exception value...
            self.space.call_function(w_exitfunc,
                    operr.w_value, operr.w_value, w_None)
        else:
            self.space.call_function(w_exitfunc, w_None, w_None, w_None)

    def LOAD_GLOBAL(self, nameindex, next_instr):
        w_result = self.space.find_global(self.w_globals, self.getname_u(nameindex))
        self.pushvalue(w_result)

    def BUILD_LIST_FROM_ARG(self, _, next_instr):
        # This opcode was added with pypy-1.8.  Here is a simpler
        # version, enough for annotation.
        last_val = self.popvalue()
        self.pushvalue(self.space.newlist([]))
        self.pushvalue(last_val)

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

### Frame blocks ###

class SFlowException(SApplicationException):
    """Flowspace override for SApplicationException"""
    def nomoreblocks(self):
        raise self.operr

    def state_unpack_variables(self, space):
        return [self.operr.w_type, self.operr.w_value]

    @staticmethod
    def state_pack_variables(space, w_type, w_value):
        return SFlowException(FSException(w_type, w_value))
