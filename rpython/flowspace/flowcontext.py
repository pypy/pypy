"""Implements the core parts of flow graph creation.
"""
from __future__ import print_function
import collections
import types

from rpython.tool.error import source_lines
from rpython.tool.twothree import builtins
from rpython.rlib import rstackovf
from rpython.flowspace.argument import CallSpec
from rpython.flowspace.model import (Constant, Variable, Block, Link,
    c_last_exception, const, FSException, SpaceOperation)
from rpython.flowspace.framestate import FrameState
from rpython.flowspace.specialcase import (rpython_print_item,
    rpython_print_newline, rpython_print_end)
from rpython.flowspace.operation import op
from rpython.flowspace.bytecode import BytecodeCorruption

w_None = const(None)
ModuleNotFoundError = getattr(builtins, 'ModuleNotFoundError', ImportError)

class FlowingError(Exception):
    """ Signals invalid RPython in the function being analysed"""
    ctx = None

    def __str__(self):
        msg = ["\n"]
        msg += map(str, self.args)
        msg += [""]
        msg += source_lines(self.ctx.graph, None, offset=self.ctx.last_offset)
        return "\n".join(msg)


class StopFlowing(Exception):
    pass


class SpamBlock(Block):
    def __init__(self, framestate):
        Block.__init__(self, framestate.getvariables())
        self.framestate = framestate
        self.dead = False

    def make_recorder(self):
        return BlockRecorder(self)

class EggBlock(Block):
    def __init__(self, inputargs, prevblock, booloutcome):
        Block.__init__(self, inputargs)
        self.prevblock = prevblock
        self.booloutcome = booloutcome

    @property
    def ancestor(self):
        parent = self.prevblock
        while isinstance(parent, EggBlock):
            parent = parent.prevblock
        return parent

    @property
    def dead(self):
        return self.ancestor.dead

    @property
    def framestate(self):
        return self.ancestor.framestate

    def make_recorder(self):
        recorder = BlockRecorder(self)
        curr = self
        while isinstance(curr, EggBlock):
            prev = curr.prevblock
            recorder = Replayer(prev, curr.booloutcome, recorder)
            curr = prev
        return recorder

    def extravars(self, last_exception=None, last_exc_value=None):
        self.last_exception = last_exception

def fixeggblocks(graph):
    for block in graph.iterblocks():
        if isinstance(block, SpamBlock):
            del block.framestate     # memory saver

# ____________________________________________________________

class Recorder(object):
    def append(self, operation):
        raise NotImplementedError

    def guessbool(self, ctx, w_condition):
        raise AssertionError("cannot guessbool(%s)" % (w_condition,))


class BlockRecorder(Recorder):
    # Records all generated operations into a block.

    def __init__(self, block):
        self.crnt_block = block
        # Final frame state after the operations in the block
        # If this is set, no new space op may be recorded.
        self.final_state = None

    def append(self, operation):
        self.crnt_block.operations.append(operation)

    def guessbool(self, ctx, w_condition):
        block = self.crnt_block
        links = []
        for case in [False, True]:
            egg = EggBlock([], block, case)
            ctx.pendingblocks.append(egg)
            link = Link([], egg, case)
            links.append(link)

        block.exitswitch = w_condition
        block.closeblock(*links)
        # forked the graph. Note that False comes before True by default
        # in the exits tuple so that (just in case we need it) we
        # actually have block.exits[False] = elseLink and
        # block.exits[True] = ifLink.
        raise StopFlowing

    def guessexception(self, ctx, *cases):
        block = self.crnt_block
        links = []
        for case in [None] + list(cases):
            if case is not None:
                if case is Exception:
                    last_exc = Variable('last_exception')
                else:
                    last_exc = Constant(case)
                last_exc_value = Variable('last_exc_value')
                vars = [last_exc, last_exc_value]
                vars2 = [Variable(), Variable()]
            else:
                vars = []
                vars2 = []
            egg = EggBlock(vars2, block, case)
            ctx.pendingblocks.append(egg)
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

    def guessbool(self, ctx, w_condition):
        assert self.index == len(self.listtoreplay)
        ctx.recorder = self.nextreplayer
        return self.booloutcome

    def guessexception(self, ctx, *classes):
        assert self.index == len(self.listtoreplay)
        ctx.recorder = self.nextreplayer
        outcome = self.booloutcome
        if outcome is not None:
            egg = self.nextreplayer.crnt_block
            w_exc_cls, w_exc_value = egg.inputargs[-2:]
            if isinstance(egg.last_exception, Constant):
                w_exc_cls = egg.last_exception
                assert not isinstance(w_exc_cls.value, list)
            raise RaiseImplicit(FSException(w_exc_cls, w_exc_value))

# ____________________________________________________________

class FlowContext(object):
    def __init__(self, graph, code):
        self.graph = graph
        func = graph.func
        self.code = code
        self.w_globals = Constant(func.__globals__)
        self.blockstack = []

        self.init_closure(func.__closure__)
        self.last_offset = 0
        self.last_pos = 0

        self.init_locals_stack(code)

        self.joinpoints = {}

    def init_closure(self, closure):
        if closure is None:
            self.closure = []
        else:
            self.closure = list(closure)
        assert len(self.closure) == len(self.code.freevars)

    def init_locals_stack(self, code):
        """
        Initialize the locals and the stack.

        The locals are ordered according to self.code.signature.
        """
        self.nlocals = code.nlocals
        # locals_w is immutable in the sense that every write should make a new
        # list first. this means FlowContext.getstate does not have to make a
        # copy of locals_w. This is a good trade-off, because changes to
        # locals_w (in STORE_FAST and DELETE_FAST) are much less common that
        # calls to getstate, which happens after every bytecode
        self.locals_w = [None] * code.nlocals
        self.stack = []

    @property
    def stackdepth(self):
        return len(self.stack)

    def pushvalue(self, w_object):
        self.stack.append(w_object)

    def popvalue(self):
        return self.stack.pop()

    def peekvalue(self, index_from_top=0):
        # NOTE: top of the stack is peekvalue(0).
        index = ~index_from_top
        return self.stack[index]

    def settopvalue(self, w_object, index_from_top=0):
        index = ~index_from_top
        self.stack[index] = w_object

    def popvalues(self, n):
        if n == 0:
            return []
        values_w = self.stack[-n:]
        del self.stack[-n:]
        return values_w

    def dropvaluesuntil(self, finaldepth):
        del self.stack[finaldepth:]

    def getstate(self, next_pos):
        return FrameState(self.locals_w, self.stack[:],
                self.last_exception, self.blockstack[:], next_pos)

    def setstate(self, state):
        """ Reset the context to the given frame state. """
        self.locals_w = state.locals_w[:]
        self.stack = state.stack[:]
        self.last_exception = state.last_exception
        self.blockstack = state.blocklist[:]
        self._normalize_raise_signals()

    def _normalize_raise_signals(self):
        st = self.stack
        for i in range(len(st)):
            if isinstance(st[i], RaiseImplicit):
                st[i] = Raise(st[i].w_exc)

    def guessbool(self, w_condition):
        if isinstance(w_condition, Constant):
            return w_condition.value
        return self.recorder.guessbool(self, w_condition)

    def maybe_merge(self):
        recorder = self.recorder
        if getattr(recorder, 'final_state', None) is not None:
            self.mergeblock(recorder.crnt_block, recorder.final_state)
            raise StopFlowing

    def record(self, spaceop):
        spaceop.offset = self.last_offset
        self.recorder.append(spaceop)

    def do_op(self, op):
        self.maybe_merge()
        self.record(op)
        self.guessexception(op.canraise)
        return op.result

    def guessexception(self, exceptions):
        """
        Catch possible exceptions implicitly.
        """
        if not exceptions:
            return
        # Implicit exceptions are ignored unless they are caught explicitly
        if self.has_exc_handler():
            self.recorder.guessexception(self, *exceptions)

    def has_exc_handler(self):
        if any(isinstance(block, (ExceptBlock, FinallyBlock))
               for block in self.blockstack):
            return True
        handler = self.code.find_handler(self.last_pos)
        return handler is not None and handler.catches

    def build_flow(self):
        graph = self.graph
        self.pendingblocks = collections.deque([graph.startblock])
        while self.pendingblocks:
            block = self.pendingblocks.popleft()
            if not block.dead:
                self.record_block(block)

    def record_block(self, block):
        self.setstate(block.framestate)
        next_pos = block.framestate.next_pos
        self.recorder = block.make_recorder()
        try:
            while True:
                next_pos = self.handle_instr(next_pos)
                self.recorder.final_state = self.getstate(next_pos)
        except StopFlowing:
            pass
        except FlowingError as exc:
            if exc.ctx is None:
                exc.ctx = self
            raise

        self.recorder = None

    def mergeblock(self, currentblock, currentstate):
        next_pos = currentstate.next_pos
        # can 'currentstate' be merged with one of the blocks that
        # already exist for this position?
        candidates = self.joinpoints.setdefault(next_pos, [])
        for block in candidates:
            newstate = block.framestate.union(currentstate)
            if newstate is not None:
                break
        else:
            newblock = self.make_next_block(currentblock, currentstate)
            candidates.insert(0, newblock)
            return

        if newstate.matches(block.framestate):
            outputargs = currentstate.getoutputargs(newstate)
            currentblock.closeblock(Link(outputargs, block))
            return

        newblock = SpamBlock(newstate)
        varnames = self.code.varnames
        for name, w_value in zip(varnames, newstate.locals_w):
            if isinstance(w_value, Variable):
                w_value.rename(name)
        # unconditionally link the current block to the newblock
        outputargs = currentstate.getoutputargs(newstate)
        link = Link(outputargs, newblock)
        currentblock.closeblock(link)

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

    def make_next_block(self, block, state):
        newstate = state.copy()
        newblock = SpamBlock(newstate)
        # unconditionally link the current block to the newblock
        outputargs = state.getoutputargs(newstate)
        link = Link(outputargs, newblock)
        block.closeblock(link)
        self.pendingblocks.append(newblock)
        return newblock

    # hack for unrolling iterables, don't use this
    def replace_in_stack(self, oldvalue, newvalue):
        w_new = Constant(newvalue)
        stack_items_w = self.stack
        for i in range(self.stackdepth - 1, - 1, -1):
            w_v = stack_items_w[i]
            if isinstance(w_v, Constant):
                if w_v.value is oldvalue:
                    # replace the topmost item of the stack that is equal
                    # to 'oldvalue' with 'newvalue'.
                    stack_items_w[i] = w_new
                    break

    def handle_instr(self, pos):
        instr = self.code.instrs[pos]
        self.last_offset = instr.offset
        self.last_pos = pos
        try:
            next_pos = instr.eval(self)
        except FlowSignal as signal:
            return self.unroll(signal)
        return next_pos if next_pos is not None else pos + 1

    def unroll(self, signal):
        while self.blockstack:
            block = self.blockstack.pop()
            if isinstance(signal, block.handles):
                return block.handle(self, signal)
            block.cleanupstack(self)
        if isinstance(signal, Raise):
            handler = self.code.find_handler(self.last_pos)
            if handler is not None:
                self.dropvaluesuntil(handler.depth)
                if handler.lasti:
                    self.pushvalue(w_None)
                self.pushvalue(signal)
                return handler.target
        return signal.nomoreblocks(self)

    def appcall(self, func, *args_w):
        """Call an app-level RPython function directly"""
        w_func = const(func)
        return self.do_op(op.simple_call(w_func, *args_w))

    def not_(self, w_obj):
        w_bool = op.bool(w_obj).eval(self)
        return const(not self.guessbool(w_bool))

    def compare(self, kind, w_1, w_2):
        return getattr(self, 'cmp_' + kind)(w_1, w_2)

    def cmp_lt(self, w_1, w_2):
        return op.lt(w_1, w_2).eval(self)

    def cmp_le(self, w_1, w_2):
        return op.le(w_1, w_2).eval(self)

    def cmp_eq(self, w_1, w_2):
        return op.eq(w_1, w_2).eval(self)

    def cmp_ne(self, w_1, w_2):
        return op.ne(w_1, w_2).eval(self)

    def cmp_gt(self, w_1, w_2):
        return op.gt(w_1, w_2).eval(self)

    def cmp_ge(self, w_1, w_2):
        return op.ge(w_1, w_2).eval(self)

    def cmp_in(self, w_1, w_2):
        return op.contains(w_2, w_1).eval(self)

    def cmp_not_in(self, w_1, w_2):
        return self.not_(self.cmp_in(w_1, w_2))

    def cmp_is(self, w_1, w_2):
        return op.is_(w_1, w_2).eval(self)

    def cmp_is_not(self, w_1, w_2):
        return self.not_(op.is_(w_1, w_2).eval(self))

    def exception_match(self, w_exc_type, w_check_class):
        """Checks if the given exception type matches 'w_check_class'."""
        if not isinstance(w_check_class, Constant):
            raise FlowingError("Non-constant except guard.")
        check_class = w_check_class.value
        if not isinstance(check_class, tuple):
            # the simple case
            if issubclass(check_class, (NotImplementedError, AssertionError)):
                raise FlowingError(
                    "Catching NotImplementedError, AssertionError, or a "
                    "subclass is not valid in RPython (%r)" % (check_class,))
            return self.guessbool(op.issubtype(w_exc_type, w_check_class).eval(self))
        # special case for StackOverflow (see rlib/rstackovf.py)
        if check_class == rstackovf.StackOverflow:
            w_real_class = const(rstackovf._StackOverflow)
            return self.guessbool(op.issubtype(w_exc_type, w_real_class).eval(self))
        # checking a tuple of classes
        for klass in w_check_class.value:
            if self.exception_match(w_exc_type, const(klass)):
                return True
        return False

    def cmp_exc_match(self, w_1, w_2):
        return const(self.exception_match(w_1, w_2))

    def exc_from_raise(self, w_arg1, w_arg2):
        """
        Create a wrapped exception from the arguments of a raise statement.

        Returns an FSException object whose w_value is an instance of w_type.
        """
        from rpython.rlib.debug import ll_assert_not_none

        check_not_none = False
        w_is_type = op.isinstance(w_arg1, const(type)).eval(self)
        if self.guessbool(w_is_type):
            # this is for all cases of the form (Class, something)
            if self.guessbool(op.is_(w_arg2, w_None).eval(self)):
                # raise Type: we assume we have to instantiate Type
                w_value = op.simple_call(w_arg1).eval(self)
            else:
                w_valuetype = op.type(w_arg2).eval(self)
                if self.guessbool(op.issubtype(w_valuetype, w_arg1).eval(self)):
                    # raise Type, Instance: let etype be the exact type of value
                    w_value = w_arg2
                    check_not_none = True
                else:
                    # raise Type, X: assume X is the constructor argument
                    w_value = op.simple_call(w_arg1, w_arg2).eval(self)
        else:
            # the only case left here is (inst, None), from a 'raise inst'.
            if not self.guessbool(op.is_(w_arg2, const(None)).eval(self)):
                exc = TypeError("instance exception may not have a "
                                "separate value")
                raise Raise(const(exc))
            w_value = w_arg1
            check_not_none = True
        if check_not_none:
            w_value = op.simple_call(const(ll_assert_not_none),
                                     w_value).eval(self)
        w_type = op.type(w_value).eval(self)
        return FSException(w_type, w_value)

    def import_name(self, name, glob=None, loc=None, frm=None, level=-1):
        try:
            mod = __import__(name, glob, loc, frm, level)
        except ImportError as e:
            raise Raise(const(e))
        return const(mod)

    def import_from(self, w_module, w_name):
        assert isinstance(w_module, Constant)
        assert isinstance(w_name, Constant)
        try:
            return op.getattr(w_module, w_name).eval(self)
        except FlowingError:
            exc = ImportError("cannot import name '%s'" % w_name.value)
            raise Raise(const(exc))

    def find_global(self, w_globals, varname):
        try:
            value = w_globals.value[varname]
        except KeyError:
            # not in the globals, now look in the built-ins
            try:
                value = getattr(builtins, varname)
            except AttributeError:
                raise FlowingError("global name '%s' is not defined" % varname)
        return const(value)

    def call_function(self, w_function, arguments, keywords, w_star=None):
        try:
            # py3-style print function
            if w_function.value == print:
                return self.handle_print_function(arguments, keywords, w_star)
        except (AttributeError, TypeError):
            pass

        args = CallSpec(arguments, keywords, w_star)
        if args.keywords or isinstance(args.w_stararg, Variable):
            shape, args_w = args.flatten()
            hlop = op.call_args(w_function, Constant(shape), *args_w)
        else:
            hlop = op.simple_call(w_function, *args.as_list())
        return hlop.eval(self)

    def handle_print_function(self, arguments, keywords, w_star):
        if w_star:
            raise FlowingError(
                "print function with *args is not RPython"
            )

        bad_kwargs = [k for k in keywords if k != "end"]
        if bad_kwargs:
            raise FlowingError(
                "print function with {}= is not RPython"
                .format(bad_kwargs[0])
            )

        for w_arg in arguments:
            w_s = op.str(w_arg).eval(self)
            self.appcall(rpython_print_item, w_s)

        if "end" in keywords:
            self.appcall(rpython_print_end, keywords["end"])
        else:
            self.appcall(rpython_print_newline)
        return Constant(None)

    def newfunction(self, w_code, defaults_w):
        if not all(isinstance(value, Constant) for value in defaults_w):
            raise FlowingError("Dynamically created function must"
                               " have constant default values.")
        code = w_code.value
        globals = self.w_globals.value
        defaults = tuple([default.value for default in defaults_w])
        fn = types.FunctionType(code, globals, code.co_name, defaults)
        return Constant(fn)

    def unpack_sequence(self, w_iterable, expected_length):
        w_len = op.len(w_iterable).eval(self)
        w_correct = op.eq(w_len, const(expected_length)).eval(self)
        if not self.guessbool(op.bool(w_correct).eval(self)):
            w_exc = self.exc_from_raise(const(ValueError), const(None))
            raise Raise(w_exc)
        return [op.getitem(w_iterable, const(i)).eval(self)
                for i in range(expected_length)]

### Frame blocks ###

class FlowSignal(Exception):
    """Abstract base class for translator-level objects that instruct the
    interpreter to change the control flow and the block stack.

    The concrete subclasses correspond to the various values WHY_XXX
    values of the why_code enumeration in ceval.c:

                WHY_NOT,        OK, not this one :-)
                WHY_EXCEPTION,  Raise
                WHY_RERAISE,    implemented differently, see Reraise
                WHY_RETURN,     Return
                WHY_BREAK,      Break
                WHY_CONTINUE,   Continue
                WHY_YIELD       not needed
    """
    def nomoreblocks(self, ctx):
        raise BytecodeCorruption("misplaced bytecode - should not return")

    def __eq__(self, other):
        return type(other) is type(self) and other.args == self.args


class Return(FlowSignal):
    """Signals a 'return' statement.
    Argument is the wrapped object to return.
    """
    def __init__(self, w_value):
        self.w_value = w_value

    def nomoreblocks(self, ctx):
        w_result = self.w_value
        link = Link([w_result], ctx.graph.returnblock)
        ctx.recorder.crnt_block.closeblock(link)
        raise StopFlowing

    @property
    def args(self):
        return [self.w_value]

    @staticmethod
    def rebuild(w_value):
        return Return(w_value)

class Raise(FlowSignal):
    """Signals an application-level exception
    (i.e. an OperationException)."""

    def __init__(self, w_exc):
        self.w_exc = w_exc

    def nomoreblocks(self, ctx):
        w_exc = self.w_exc
        if w_exc.w_type in (const(ImportError), const(ModuleNotFoundError)):
            msg = 'ImportError is raised in RPython: %s' % (
                getattr(w_exc.w_value, 'value', '<not a constant message>'),)
            raise ImportError(msg)
        link = Link([w_exc.w_type, w_exc.w_value], ctx.graph.exceptblock)
        ctx.recorder.crnt_block.closeblock(link)
        raise StopFlowing

    @property
    def args(self):
        return [self.w_exc.w_type, self.w_exc.w_value]

    @classmethod
    def rebuild(cls, w_type, w_value):
        return cls(FSException(w_type, w_value))

class RaiseImplicit(Raise):
    """Signals an exception raised implicitly"""
    def nomoreblocks(self, ctx):
        w_exc = self.w_exc
        if isinstance(w_exc.w_type, Constant):
            exc_cls = w_exc.w_type.value
        else:
            exc_cls = Exception
        msg = "implicit %s shouldn't occur" % exc_cls.__name__
        w_type = Constant(AssertionError)
        w_value = Constant(AssertionError(msg))
        link = Link([w_type, w_value], ctx.graph.exceptblock)
        ctx.recorder.crnt_block.closeblock(link)
        raise StopFlowing


class Break(FlowSignal):
    """Signals a 'break' statement."""

    @property
    def args(self):
        return []

    @staticmethod
    def rebuild():
        return Break.singleton

Break.singleton = Break()

class Continue(FlowSignal):
    """Signals a 'continue' statement.
    Argument is the position of the beginning of the loop."""

    def __init__(self, jump_to):
        self.jump_to = jump_to

    @property
    def args(self):
        return [const(self.jump_to)]

    @staticmethod
    def rebuild(w_jump_to):
        return Continue(w_jump_to.value)


class FrameBlock(object):
    """Abstract base class for frame blocks from the blockstack,
    used by the SETUP_XXX and POP_BLOCK opcodes."""

    def __init__(self, ctx, handlerposition):
        self.handlerposition = handlerposition
        self.stackdepth = ctx.stackdepth

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.handlerposition == other.handlerposition and
                self.stackdepth == other.stackdepth)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.handlerposition, self.stackdepth))

    def cleanupstack(self, ctx):
        ctx.dropvaluesuntil(self.stackdepth)

    def handle(self, ctx, unroller):
        raise NotImplementedError

class LoopBlock(FrameBlock):
    """A loop block.  Stores the end-of-loop pointer in case of 'break'."""

    handles = (Break, Continue)

    def handle(self, ctx, unroller):
        if isinstance(unroller, Continue):
            # re-push the loop block without cleaning up the value stack,
            # and jump to the beginning of the loop, stored in the
            # exception's argument
            ctx.blockstack.append(self)
            return unroller.jump_to
        else:
            # jump to the end of the loop
            self.cleanupstack(ctx)
            return self.handlerposition

class ExceptBlock(FrameBlock):
    """An try:except: block.  Stores the position of the exception handler."""

    handles = Raise

    def handle(self, ctx, unroller):
        # push the exception to the value stack for inspection by the
        # exception handler (the code after the except:)
        self.cleanupstack(ctx)
        assert isinstance(unroller, Raise)
        w_exc = unroller.w_exc
        # the stack setup is slightly different than in CPython:
        # instead of the traceback, we store the unroller object,
        # wrapped.
        ctx.pushvalue(unroller)
        ctx.pushvalue(w_exc.w_value)
        ctx.pushvalue(w_exc.w_type)
        ctx.last_exception = w_exc
        return self.handlerposition   # jump to the handler

class IterBlock(ExceptBlock):
    """A pseudo-block to catch the StopIteration inside FOR_ITER"""
    def handle(self, ctx, unroller):
        w_exc = unroller.w_exc
        if ctx.exception_match(w_exc.w_type, const(StopIteration)):
            ctx.popvalue()
            return self.handlerposition
        else:
            return ctx.unroll(unroller)

class FinallyBlock(FrameBlock):
    """A try:finally: block.  Stores the position of the exception handler."""

    handles = FlowSignal

    def handle(self, ctx, unroller):
        # any abnormal reason for unrolling a finally: triggers the end of
        # the block unrolling and the entering the finally: handler.
        self.cleanupstack(ctx)
        ctx.pushvalue(unroller)
        return self.handlerposition   # jump to the handler


class WithBlock(FinallyBlock):

    def handle(self, ctx, unroller):
        return FinallyBlock.handle(self, ctx, unroller)
