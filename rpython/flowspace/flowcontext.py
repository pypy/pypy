"""Implements the core parts of flow graph creation, in tandem
with rpython.flowspace.objspace.
"""

import sys
import collections
import types
import __builtin__

from rpython.tool.error import source_lines
from rpython.tool.stdlib_opcode import host_bytecode_spec
from rpython.rlib import rstackovf
from rpython.flowspace.argument import CallSpec
from rpython.flowspace.model import (Constant, Variable, Block, Link,
    c_last_exception, const, FSException)
from rpython.flowspace.framestate import (FrameState, recursively_unflatten,
    recursively_flatten)
from rpython.flowspace.specialcase import (rpython_print_item,
    rpython_print_newline)
from rpython.flowspace.operation import op

w_None = const(None)

class FlowingError(Exception):
    """ Signals invalid RPython in the function being analysed"""
    frame = None

    def __str__(self):
        msg = ["\n"]
        msg += map(str, self.args)
        msg += [""]
        msg += source_lines(self.frame.graph, None, offset=self.frame.last_instr)
        return "\n".join(msg)

class StopFlowing(Exception):
    pass

class BytecodeCorruption(Exception):
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
    varnames = graph.func.func_code.co_varnames
    for block in graph.iterblocks():
        if isinstance(block, SpamBlock):
            for name, w_value in zip(varnames, block.framestate.mergeable):
                if isinstance(w_value, Variable):
                    w_value.rename(name)
            del block.framestate     # memory saver

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

# ____________________________________________________________

class Recorder(object):
    def append(self, operation):
        raise NotImplementedError

    def guessbool(self, frame, w_condition):
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

    def guessbool(self, frame, w_condition):
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
                assert not isinstance(w_exc_cls.value, list)
            raise RaiseImplicit(FSException(w_exc_cls, w_exc_value))

# ____________________________________________________________

_unary_ops = [
    ('UNARY_POSITIVE', op.pos),
    ('UNARY_NEGATIVE', op.neg),
    ('UNARY_CONVERT', op.repr),
    ('UNARY_INVERT', op.invert),
]

def unaryoperation(OPCODE, operation):
    def UNARY_OP(self, *ignored):
        w_1 = self.popvalue()
        w_result = operation(w_1).eval(self)
        self.pushvalue(w_result)
    UNARY_OP.func_name = OPCODE
    return UNARY_OP

_binary_ops = [
    ('BINARY_MULTIPLY', op.mul),
    ('BINARY_TRUE_DIVIDE', op.truediv),
    ('BINARY_FLOOR_DIVIDE', op.floordiv),
    ('BINARY_DIVIDE', op.div),
    ('BINARY_MODULO', op.mod),
    ('BINARY_ADD', op.add),
    ('BINARY_SUBTRACT', op.sub),
    ('BINARY_SUBSCR', op.getitem),
    ('BINARY_LSHIFT', op.lshift),
    ('BINARY_RSHIFT', op.rshift),
    ('BINARY_AND', op.and_),
    ('BINARY_XOR', op.xor),
    ('BINARY_OR', op.or_),
    ('INPLACE_MULTIPLY', op.inplace_mul),
    ('INPLACE_TRUE_DIVIDE', op.inplace_truediv),
    ('INPLACE_FLOOR_DIVIDE', op.inplace_floordiv),
    ('INPLACE_DIVIDE', op.inplace_div),
    ('INPLACE_MODULO', op.inplace_mod),
    ('INPLACE_ADD', op.inplace_add),
    ('INPLACE_SUBTRACT', op.inplace_sub),
    ('INPLACE_LSHIFT', op.inplace_lshift),
    ('INPLACE_RSHIFT', op.inplace_rshift),
    ('INPLACE_AND', op.inplace_and),
    ('INPLACE_XOR', op.inplace_xor),
    ('INPLACE_OR', op.inplace_or),
]

def binaryoperation(OPCODE, operation):
    """NOT_RPYTHON"""
    def BINARY_OP(self, _):
        w_2 = self.popvalue()
        w_1 = self.popvalue()
        w_result = operation(w_1, w_2).eval(self)
        self.pushvalue(w_result)
    BINARY_OP.func_name = OPCODE
    return BINARY_OP

_unsupported_ops = [
    ('BINARY_POWER', "a ** b"),
    ('BUILD_CLASS', 'defining classes inside functions'),
    ('EXEC_STMT', 'exec statement'),
    ('STOP_CODE', '???'),
    ('STORE_NAME', 'modifying globals'),
    ('INPLACE_POWER', 'a **= b'),
    ('LOAD_LOCALS', 'locals()'),
    ('IMPORT_STAR', 'import *'),
    ('MISSING_OPCODE', '???'),
    ('DELETE_GLOBAL', 'modifying globals'),
    ('DELETE_NAME', 'modifying globals'),
    ('DELETE_ATTR', 'deleting attributes'),
]

def unsupportedoperation(OPCODE, msg):
    def UNSUPPORTED(self, *ignored):
        raise FlowingError("%s is not RPython" % (msg,))
    UNSUPPORTED.func_name = OPCODE
    return UNSUPPORTED

compare_method = [
    "cmp_lt",   # "<"
    "cmp_le",   # "<="
    "cmp_eq",   # "=="
    "cmp_ne",   # "!="
    "cmp_gt",   # ">"
    "cmp_ge",   # ">="
    "cmp_in",
    "cmp_not_in",
    "cmp_is",
    "cmp_is_not",
    "cmp_exc_match",
    ]

class FlowSpaceFrame(object):
    opcode_method_names = host_bytecode_spec.method_names

    def __init__(self, space, graph, code):
        self.graph = graph
        func = graph.func
        self.pycode = code
        self.space = space
        self.w_globals = Constant(func.func_globals)
        self.blockstack = []

        self.init_closure(func.func_closure)
        self.f_lineno = code.co_firstlineno
        self.last_instr = 0

        self.init_locals_stack(code)
        self.w_locals = None # XXX: only for compatibility with PyFrame

        self.joinpoints = {}

    def init_closure(self, closure):
        if closure is None:
            self.closure = []
        else:
            self.closure = list(closure)
        assert len(self.closure) == len(self.pycode.co_freevars)

    def init_locals_stack(self, code):
        """
        Initialize the locals and the stack.

        The locals are ordered according to self.pycode.signature.
        """
        self.valuestackdepth = code.co_nlocals
        self.locals_stack_w = [None] * (code.co_stacksize + code.co_nlocals)

    def pushvalue(self, w_object):
        depth = self.valuestackdepth
        self.locals_stack_w[depth] = w_object
        self.valuestackdepth = depth + 1

    def popvalue(self):
        depth = self.valuestackdepth - 1
        assert depth >= self.pycode.co_nlocals, "pop from empty value stack"
        w_object = self.locals_stack_w[depth]
        self.locals_stack_w[depth] = None
        self.valuestackdepth = depth
        return w_object

    def peekvalue(self, index_from_top=0):
        # NOTE: top of the stack is peekvalue(0).
        index = self.valuestackdepth + ~index_from_top
        assert index >= self.pycode.co_nlocals, (
            "peek past the bottom of the stack")
        return self.locals_stack_w[index]

    def settopvalue(self, w_object, index_from_top=0):
        index = self.valuestackdepth + ~index_from_top
        assert index >= self.pycode.co_nlocals, (
            "settop past the bottom of the stack")
        self.locals_stack_w[index] = w_object

    def popvalues(self, n):
        values_w = [self.popvalue() for i in range(n)]
        values_w.reverse()
        return values_w

    def dropvalues(self, n):
        finaldepth = self.valuestackdepth - n
        for n in range(finaldepth, self.valuestackdepth):
            self.locals_stack_w[n] = None
        self.valuestackdepth = finaldepth

    def dropvaluesuntil(self, finaldepth):
        for n in range(finaldepth, self.valuestackdepth):
            self.locals_stack_w[n] = None
        self.valuestackdepth = finaldepth

    def save_locals_stack(self):
        return self.locals_stack_w[:self.valuestackdepth]

    def restore_locals_stack(self, items_w):
        self.locals_stack_w[:len(items_w)] = items_w
        self.dropvaluesuntil(len(items_w))

    def getstate(self, next_pos):
        # getfastscope() can return real None, for undefined locals
        data = self.save_locals_stack()
        if self.last_exception is None:
            data.append(Constant(None))
            data.append(Constant(None))
        else:
            data.append(self.last_exception.w_type)
            data.append(self.last_exception.w_value)
        recursively_flatten(data)
        return FrameState(data, self.blockstack[:], next_pos)

    def setstate(self, state):
        """ Reset the frame to the given state. """
        data = state.mergeable[:]
        recursively_unflatten(data)
        self.restore_locals_stack(data[:-2])  # Nones == undefined locals
        if data[-2] == Constant(None):
            assert data[-1] == Constant(None)
            self.last_exception = None
        else:
            self.last_exception = FSException(data[-2], data[-1])
        self.blockstack = state.blocklist[:]

    def guessbool(self, w_condition):
        if isinstance(w_condition, Constant):
            return w_condition.value
        return self.recorder.guessbool(self, w_condition)

    def record(self, spaceop):
        recorder = self.recorder
        if getattr(recorder, 'final_state', None) is not None:
            self.mergeblock(recorder.crnt_block, recorder.final_state)
            raise StopFlowing
        spaceop.offset = self.last_instr
        recorder.append(spaceop)

    def do_op(self, op):
        self.record(op)
        self.guessexception(op.canraise)
        return op.result

    def guessexception(self, exceptions, force=False):
        """
        Catch possible exceptions implicitly.
        """
        if not exceptions:
            return
        if not force and not any(isinstance(block, (ExceptBlock, FinallyBlock))
                for block in self.blockstack):
            # The implicit exception wouldn't be caught and would later get
            # removed, so don't bother creating it.
            return
        self.recorder.guessexception(self, *exceptions)

    def build_flow(self):
        graph = self.graph
        self.pendingblocks = collections.deque([graph.startblock])
        while self.pendingblocks:
            block = self.pendingblocks.popleft()
            if not block.dead:
                self.record_block(block)

    def record_block(self, block):
        self.setstate(block.framestate)
        next_pos = block.framestate.next_instr
        self.recorder = block.make_recorder()
        try:
            while True:
                next_pos = self.handle_bytecode(next_pos)
                self.recorder.final_state = self.getstate(next_pos)

        except RaiseImplicit as e:
            w_exc = e.w_exc
            if isinstance(w_exc.w_type, Constant):
                exc_cls = w_exc.w_type.value
            else:
                exc_cls = Exception
            msg = "implicit %s shouldn't occur" % exc_cls.__name__
            w_type = Constant(AssertionError)
            w_value = Constant(AssertionError(msg))
            link = Link([w_type, w_value], self.graph.exceptblock)
            self.recorder.crnt_block.closeblock(link)

        except Raise as e:
            w_exc = e.w_exc
            if w_exc.w_type == const(ImportError):
                msg = 'import statement always raises %s' % e
                raise ImportError(msg)
            link = Link([w_exc.w_type, w_exc.w_value], self.graph.exceptblock)
            self.recorder.crnt_block.closeblock(link)

        except StopFlowing:
            pass

        except Return as exc:
            w_result = exc.w_value
            link = Link([w_result], self.graph.returnblock)
            self.recorder.crnt_block.closeblock(link)

        except FlowingError as exc:
            if exc.frame is None:
                exc.frame = self
            raise

        self.recorder = None

    def mergeblock(self, currentblock, currentstate):
        next_instr = currentstate.next_instr
        # can 'currentstate' be merged with one of the blocks that
        # already exist for this bytecode position?
        candidates = self.joinpoints.setdefault(next_instr, [])
        for block in candidates:
            newstate = block.framestate.union(currentstate)
            if newstate is None:
                continue
            elif newstate == block.framestate:
                outputargs = currentstate.getoutputargs(newstate)
                currentblock.closeblock(Link(outputargs, block))
                return
            else:
                break
        else:
            newstate = currentstate.copy()
            block = None

        newblock = SpamBlock(newstate)
        # unconditionally link the current block to the newblock
        outputargs = currentstate.getoutputargs(newstate)
        link = Link(outputargs, newblock)
        currentblock.closeblock(link)

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
        for i in range(self.valuestackdepth - 1, self.pycode.co_nlocals - 1, -1):
            w_v = stack_items_w[i]
            if isinstance(w_v, Constant):
                if w_v.value is oldvalue:
                    # replace the topmost item of the stack that is equal
                    # to 'oldvalue' with 'newvalue'.
                    stack_items_w[i] = w_new
                    break

    def handle_bytecode(self, next_instr):
        self.last_instr = next_instr
        next_instr, methodname, oparg = self.pycode.read(next_instr)
        try:
            res = getattr(self, methodname)(oparg)
            return res if res is not None else next_instr
        except FlowSignal as signal:
            return self.unroll(signal)

    def unroll(self, signal):
        while self.blockstack:
            block = self.blockstack.pop()
            if isinstance(signal, block.handles):
                return block.handle(self, signal)
            block.cleanupstack(self)
        return signal.nomoreblocks()

    def getlocalvarname(self, index):
        return self.pycode.co_varnames[index]

    def getconstant_w(self, index):
        return const(self.pycode.consts[index])

    def getname_u(self, index):
        return self.pycode.names[index]

    def getname_w(self, index):
        return Constant(self.pycode.names[index])

    def BAD_OPCODE(self, _):
        raise FlowingError("This operation is not RPython")

    def BREAK_LOOP(self, oparg):
        raise Break

    def CONTINUE_LOOP(self, startofloop):
        raise Continue(startofloop)

    def not_(self, w_obj):
        w_bool = op.bool(w_obj).eval(self)
        return const(not self.guessbool(w_bool))

    def UNARY_NOT(self, _):
        w_obj = self.popvalue()
        self.pushvalue(self.not_(w_obj))

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
        if check_class in (NotImplementedError, AssertionError):
            raise FlowingError(
                "Catching %s is not valid in RPython" % check_class.__name__)
        if not isinstance(check_class, tuple):
            # the simple case
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

    def COMPARE_OP(self, testnum):
        w_2 = self.popvalue()
        w_1 = self.popvalue()
        w_result = getattr(self, compare_method[testnum])(w_1, w_2)
        self.pushvalue(w_result)

    def exc_from_raise(self, w_arg1, w_arg2):
        """
        Create a wrapped exception from the arguments of a raise statement.

        Returns an FSException object whose w_value is an instance of w_type.
        """
        if self.guessbool(self.space.call_function(const(isinstance), w_arg1,
                const(type))):
            # this is for all cases of the form (Class, something)
            if self.guessbool(op.is_(w_arg2, w_None).eval(self)):
                # raise Type: we assume we have to instantiate Type
                w_value = self.space.call_function(w_arg1)
            else:
                w_valuetype = op.type(w_arg2).eval(self)
                if self.guessbool(op.issubtype(w_valuetype, w_arg1).eval(self)):
                    # raise Type, Instance: let etype be the exact type of value
                    w_value = w_arg2
                else:
                    # raise Type, X: assume X is the constructor argument
                    w_value = self.space.call_function(w_arg1, w_arg2)
        else:
            # the only case left here is (inst, None), from a 'raise inst'.
            if not self.guessbool(op.is_(w_arg2, const(None)).eval(self)):
                exc = TypeError("instance exception may not have a "
                                "separate value")
                raise Raise(const(exc))
            w_value = w_arg1
        w_type = op.type(w_value).eval(self)
        return FSException(w_type, w_value)

    def RAISE_VARARGS(self, nbargs):
        if nbargs == 0:
            if self.last_exception is not None:
                w_exc = self.last_exception
            else:
                w_exc = const(TypeError(
                    "raise: no active exception to re-raise"))
            raise Raise(w_exc)

        if nbargs >= 3:
            self.popvalue()
        if nbargs >= 2:
            w_value = self.popvalue()
            w_type = self.popvalue()
            operror = self.exc_from_raise(w_type, w_value)
        else:
            w_type = self.popvalue()
            operror = self.exc_from_raise(w_type, w_None)
        raise Raise(operror)

    def import_name(self, name, glob=None, loc=None, frm=None, level=-1):
        try:
            mod = __import__(name, glob, loc, frm, level)
        except ImportError as e:
            raise Raise(const(e))
        return const(mod)

    def IMPORT_NAME(self, nameindex):
        modulename = self.getname_u(nameindex)
        glob = self.w_globals.value
        fromlist = self.popvalue().value
        level = self.popvalue().value
        w_obj = self.import_name(modulename, glob, None, fromlist, level)
        self.pushvalue(w_obj)

    def import_from(self, w_module, w_name):
        assert isinstance(w_module, Constant)
        assert isinstance(w_name, Constant)
        try:
            return op.getattr(w_module, w_name).eval(self)
        except FlowingError:
            exc = ImportError("cannot import name '%s'" % w_name.value)
            raise Raise(const(exc))

    def IMPORT_FROM(self, nameindex):
        w_name = self.getname_w(nameindex)
        w_module = self.peekvalue()
        self.pushvalue(self.import_from(w_module, w_name))

    def RETURN_VALUE(self, oparg):
        w_returnvalue = self.popvalue()
        raise Return(w_returnvalue)

    def END_FINALLY(self, oparg):
        # unlike CPython, there are two statically distinct cases: the
        # END_FINALLY might be closing an 'except' block or a 'finally'
        # block.  In the first case, the stack contains three items:
        #   [exception type we are now handling]
        #   [exception value we are now handling]
        #   [Raise]
        # In the case of a finally: block, the stack contains only one
        # item (unlike CPython which can have 1, 2 or 3 items):
        #   [subclass of FlowSignal]
        w_top = self.popvalue()
        if w_top == w_None:
            # finally: block with no unroller active
            return
        elif isinstance(w_top, FlowSignal):
            # case of a finally: block
            raise w_top
        else:
            # case of an except: block.  We popped the exception type
            self.popvalue()        #     Now we pop the exception value
            signal = self.popvalue()
            raise signal

    def POP_BLOCK(self, oparg):
        block = self.blockstack.pop()
        block.cleanupstack(self)  # the block knows how to clean up the value stack

    def JUMP_ABSOLUTE(self, jumpto):
        return jumpto

    def YIELD_VALUE(self, _):
        assert self.pycode.is_generator
        w_result = self.popvalue()
        op.yield_(w_result).eval(self)
        # XXX yield expressions not supported. This will blow up if the value
        # isn't popped straightaway.
        self.pushvalue(None)

    PRINT_EXPR = BAD_OPCODE
    PRINT_ITEM_TO = BAD_OPCODE
    PRINT_NEWLINE_TO = BAD_OPCODE

    def PRINT_ITEM(self, oparg):
        w_item = self.popvalue()
        w_s = op.str(w_item).eval(self)
        self.space.appcall(rpython_print_item, w_s)

    def PRINT_NEWLINE(self, oparg):
        self.space.appcall(rpython_print_newline)

    def JUMP_FORWARD(self, target):
        return target

    def JUMP_IF_FALSE(self, target):
        # Python <= 2.6 only
        w_cond = self.peekvalue()
        if not self.guessbool(op.bool(w_cond).eval(self)):
            return target

    def JUMP_IF_TRUE(self, target):
        # Python <= 2.6 only
        w_cond = self.peekvalue()
        if self.guessbool(op.bool(w_cond).eval(self)):
            return target

    def POP_JUMP_IF_FALSE(self, target):
        w_value = self.popvalue()
        if not self.guessbool(op.bool(w_value).eval(self)):
            return target

    def POP_JUMP_IF_TRUE(self, target):
        w_value = self.popvalue()
        if self.guessbool(op.bool(w_value).eval(self)):
            return target

    def JUMP_IF_FALSE_OR_POP(self, target):
        w_value = self.peekvalue()
        if not self.guessbool(op.bool(w_value).eval(self)):
            return target
        self.popvalue()

    def JUMP_IF_TRUE_OR_POP(self, target):
        w_value = self.peekvalue()
        if self.guessbool(op.bool(w_value).eval(self)):
            return target
            return target
        self.popvalue()

    def JUMP_IF_NOT_DEBUG(self, target):
        pass

    def GET_ITER(self, oparg):
        w_iterable = self.popvalue()
        w_iterator = op.iter(w_iterable).eval(self)
        self.pushvalue(w_iterator)

    def FOR_ITER(self, target):
        w_iterator = self.peekvalue()
        try:
            w_nextitem = op.next(w_iterator).eval(self)
            self.pushvalue(w_nextitem)
        except Raise as e:
            if self.exception_match(e.w_exc.w_type, const(StopIteration)):
                self.popvalue()
                return target
            else:
                raise

    def SETUP_LOOP(self, target):
        block = LoopBlock(self, target)
        self.blockstack.append(block)

    def SETUP_EXCEPT(self, target):
        block = ExceptBlock(self, target)
        self.blockstack.append(block)

    def SETUP_FINALLY(self, target):
        block = FinallyBlock(self, target)
        self.blockstack.append(block)

    def SETUP_WITH(self, target):
        # A simpler version than the 'real' 2.7 one:
        # directly call manager.__enter__(), don't use special lookup functions
        # which don't make sense on the RPython type system.
        w_manager = self.peekvalue()
        w_exit = op.getattr(w_manager, const("__exit__")).eval(self)
        self.settopvalue(w_exit)
        w_result = self.space.call_method(w_manager, "__enter__")
        block = WithBlock(self, target)
        self.blockstack.append(block)
        self.pushvalue(w_result)

    def WITH_CLEANUP(self, oparg):
        # Note: RPython context managers receive None in lieu of tracebacks
        # and cannot suppress the exception.
        # This opcode changed a lot between CPython versions
        if sys.version_info >= (2, 6):
            unroller = self.popvalue()
            w_exitfunc = self.popvalue()
            self.pushvalue(unroller)
        else:
            w_exitfunc = self.popvalue()
            unroller = self.peekvalue(0)

        if isinstance(unroller, Raise):
            w_exc = unroller.w_exc
            # The annotator won't allow to merge exception types with None.
            # Replace it with the exception value...
            self.space.call_function(w_exitfunc,
                    w_exc.w_value, w_exc.w_value, w_None)
        else:
            self.space.call_function(w_exitfunc, w_None, w_None, w_None)

    def LOAD_FAST(self, varindex):
        w_value = self.locals_stack_w[varindex]
        if w_value is None:
            raise FlowingError("Local variable referenced before assignment")
        self.pushvalue(w_value)

    def LOAD_CONST(self, constindex):
        w_const = self.getconstant_w(constindex)
        self.pushvalue(w_const)

    def find_global(self, w_globals, varname):
        try:
            value = w_globals.value[varname]
        except KeyError:
            # not in the globals, now look in the built-ins
            try:
                value = getattr(__builtin__, varname)
            except AttributeError:
                raise FlowingError("global name '%s' is not defined" % varname)
        return const(value)

    def LOAD_GLOBAL(self, nameindex):
        w_result = self.find_global(self.w_globals, self.getname_u(nameindex))
        self.pushvalue(w_result)
    LOAD_NAME = LOAD_GLOBAL

    def LOAD_ATTR(self, nameindex):
        "obj.attributename"
        w_obj = self.popvalue()
        w_attributename = self.getname_w(nameindex)
        w_value = op.getattr(w_obj, w_attributename).eval(self)
        self.pushvalue(w_value)
    LOOKUP_METHOD = LOAD_ATTR

    def LOAD_DEREF(self, varindex):
        cell = self.closure[varindex]
        try:
            content = cell.cell_contents
        except ValueError:
            name = self.pycode.co_freevars[varindex]
            raise FlowingError("Undefined closure variable '%s'" % name)
        self.pushvalue(const(content))

    def STORE_FAST(self, varindex):
        w_newvalue = self.popvalue()
        assert w_newvalue is not None
        self.locals_stack_w[varindex] = w_newvalue

    def STORE_GLOBAL(self, nameindex):
        varname = self.getname_u(nameindex)
        raise FlowingError(
            "Attempting to modify global variable  %r." % (varname))

    def POP_TOP(self, oparg):
        self.popvalue()

    def ROT_TWO(self, oparg):
        w_1 = self.popvalue()
        w_2 = self.popvalue()
        self.pushvalue(w_1)
        self.pushvalue(w_2)

    def ROT_THREE(self, oparg):
        w_1 = self.popvalue()
        w_2 = self.popvalue()
        w_3 = self.popvalue()
        self.pushvalue(w_1)
        self.pushvalue(w_3)
        self.pushvalue(w_2)

    def ROT_FOUR(self, oparg):
        w_1 = self.popvalue()
        w_2 = self.popvalue()
        w_3 = self.popvalue()
        w_4 = self.popvalue()
        self.pushvalue(w_1)
        self.pushvalue(w_4)
        self.pushvalue(w_3)
        self.pushvalue(w_2)

    def DUP_TOP(self, oparg):
        w_1 = self.peekvalue()
        self.pushvalue(w_1)

    def DUP_TOPX(self, itemcount):
        delta = itemcount - 1
        while True:
            itemcount -= 1
            if itemcount < 0:
                break
            w_value = self.peekvalue(delta)
            self.pushvalue(w_value)

    for OPCODE, op in _unary_ops:
        locals()[OPCODE] = unaryoperation(OPCODE, op)

    for OPCODE, op in _binary_ops:
        locals()[OPCODE] = binaryoperation(OPCODE, op)

    for OPCODE, op in _unsupported_ops:
        locals()[OPCODE] = unsupportedoperation(OPCODE, op)

    def BUILD_LIST_FROM_ARG(self, _):
        # This opcode was added with pypy-1.8.  Here is a simpler
        # version, enough for annotation.
        last_val = self.popvalue()
        self.pushvalue(op.newlist().eval(self))
        self.pushvalue(last_val)

    def call_function(self, oparg, w_star=None, w_starstar=None):
        if w_starstar is not None:
            raise FlowingError("Dict-unpacking is not RPython")
        n_arguments = oparg & 0xff
        n_keywords = (oparg >> 8) & 0xff
        keywords = {}
        for _ in range(n_keywords):
            w_value = self.popvalue()
            w_key = self.popvalue()
            key = w_key.value
            keywords[key] = w_value
        arguments = self.popvalues(n_arguments)
        args = CallSpec(arguments, keywords, w_star)
        w_function = self.popvalue()
        w_result = self.space.call(w_function, args)
        self.pushvalue(w_result)

    def CALL_FUNCTION(self, oparg):
        self.call_function(oparg)
    CALL_METHOD = CALL_FUNCTION

    def CALL_FUNCTION_VAR(self, oparg):
        w_varargs = self.popvalue()
        self.call_function(oparg, w_varargs)

    def CALL_FUNCTION_KW(self, oparg):
        w_varkw = self.popvalue()
        self.call_function(oparg, None, w_varkw)

    def CALL_FUNCTION_VAR_KW(self, oparg):
        w_varkw = self.popvalue()
        w_varargs = self.popvalue()
        self.call_function(oparg, w_varargs, w_varkw)

    def newfunction(self, w_code, defaults_w):
        if not all(isinstance(value, Constant) for value in defaults_w):
            raise FlowingError("Dynamically created function must"
                    " have constant default values.")
        code = w_code.value
        globals = self.w_globals.value
        defaults = tuple([default.value for default in defaults_w])
        fn = types.FunctionType(code, globals, code.co_name, defaults)
        return Constant(fn)

    def MAKE_FUNCTION(self, numdefaults):
        w_codeobj = self.popvalue()
        defaults = self.popvalues(numdefaults)
        fn = self.newfunction(w_codeobj, defaults)
        self.pushvalue(fn)

    def STORE_ATTR(self, nameindex):
        "obj.attributename = newvalue"
        w_attributename = self.getname_w(nameindex)
        w_obj = self.popvalue()
        w_newvalue = self.popvalue()
        op.setattr(w_obj, w_attributename, w_newvalue).eval(self)

    def unpack_sequence(self, w_iterable, expected_length):
        w_len = op.len(w_iterable).eval(self)
        w_correct = op.eq(w_len, const(expected_length)).eval(self)
        if not self.guessbool(op.bool(w_correct).eval(self)):
            w_exc = self.exc_from_raise(const(ValueError), const(None))
            raise Raise(w_exc)
        return [op.getitem(w_iterable, const(i)).eval(self)
                    for i in range(expected_length)]

    def UNPACK_SEQUENCE(self, itemcount):
        w_iterable = self.popvalue()
        items = self.unpack_sequence(w_iterable, itemcount)
        for w_item in reversed(items):
            self.pushvalue(w_item)

    def slice(self, w_start, w_end):
        w_obj = self.popvalue()
        w_result = op.getslice(w_obj, w_start, w_end).eval(self)
        self.pushvalue(w_result)

    def SLICE_0(self, oparg):
        self.slice(w_None, w_None)

    def SLICE_1(self, oparg):
        w_start = self.popvalue()
        self.slice(w_start, w_None)

    def SLICE_2(self, oparg):
        w_end = self.popvalue()
        self.slice(w_None, w_end)

    def SLICE_3(self, oparg):
        w_end = self.popvalue()
        w_start = self.popvalue()
        self.slice(w_start, w_end)

    def storeslice(self, w_start, w_end):
        w_obj = self.popvalue()
        w_newvalue = self.popvalue()
        op.setslice(w_obj, w_start, w_end, w_newvalue).eval(self)

    def STORE_SLICE_0(self, oparg):
        self.storeslice(w_None, w_None)

    def STORE_SLICE_1(self, oparg):
        w_start = self.popvalue()
        self.storeslice(w_start, w_None)

    def STORE_SLICE_2(self, oparg):
        w_end = self.popvalue()
        self.storeslice(w_None, w_end)

    def STORE_SLICE_3(self, oparg):
        w_end = self.popvalue()
        w_start = self.popvalue()
        self.storeslice(w_start, w_end)

    def deleteslice(self, w_start, w_end):
        w_obj = self.popvalue()
        op.delslice(w_obj, w_start, w_end).eval(self)

    def DELETE_SLICE_0(self, oparg):
        self.deleteslice(w_None, w_None)

    def DELETE_SLICE_1(self, oparg):
        w_start = self.popvalue()
        self.deleteslice(w_start, w_None)

    def DELETE_SLICE_2(self, oparg):
        w_end = self.popvalue()
        self.deleteslice(w_None, w_end)

    def DELETE_SLICE_3(self, oparg):
        w_end = self.popvalue()
        w_start = self.popvalue()
        self.deleteslice(w_start, w_end)

    def LIST_APPEND(self, oparg):
        w = self.popvalue()
        if sys.version_info < (2, 7):
            v = self.popvalue()
        else:
            v = self.peekvalue(oparg - 1)
        self.space.call_method(v, 'append', w)

    def DELETE_FAST(self, varindex):
        if self.locals_stack_w[varindex] is None:
            varname = self.getlocalvarname(varindex)
            message = "local variable '%s' referenced before assignment"
            raise UnboundLocalError(message, varname)
        self.locals_stack_w[varindex] = None

    def STORE_MAP(self, oparg):
        w_key = self.popvalue()
        w_value = self.popvalue()
        w_dict = self.peekvalue()
        op.setitem(w_dict, w_key, w_value).eval(self)

    def STORE_SUBSCR(self, oparg):
        "obj[subscr] = newvalue"
        w_subscr = self.popvalue()
        w_obj = self.popvalue()
        w_newvalue = self.popvalue()
        op.setitem(w_obj, w_subscr, w_newvalue).eval(self)

    def BUILD_SLICE(self, numargs):
        if numargs == 3:
            w_step = self.popvalue()
        elif numargs == 2:
            w_step = w_None
        else:
            raise BytecodeCorruption
        w_end = self.popvalue()
        w_start = self.popvalue()
        w_slice = op.newslice(w_start, w_end, w_step).eval(self)
        self.pushvalue(w_slice)

    def DELETE_SUBSCR(self, oparg):
        "del obj[subscr]"
        w_subscr = self.popvalue()
        w_obj = self.popvalue()
        op.delitem(w_obj, w_subscr).eval(self)

    def BUILD_TUPLE(self, itemcount):
        items = self.popvalues(itemcount)
        w_tuple = op.newtuple(*items).eval(self)
        self.pushvalue(w_tuple)

    def BUILD_LIST(self, itemcount):
        items = self.popvalues(itemcount)
        w_list = op.newlist(*items).eval(self)
        self.pushvalue(w_list)

    def BUILD_MAP(self, itemcount):
        w_dict = op.newdict().eval(self)
        self.pushvalue(w_dict)

    def NOP(self, *args):
        pass

    # XXX Unimplemented 2.7 opcodes ----------------

    # Set literals, set comprehensions

    def BUILD_SET(self, oparg):
        raise NotImplementedError("BUILD_SET")

    def SET_ADD(self, oparg):
        raise NotImplementedError("SET_ADD")

    # Dict comprehensions

    def MAP_ADD(self, oparg):
        raise NotImplementedError("MAP_ADD")

    # Closures

    STORE_DEREF = BAD_OPCODE
    LOAD_CLOSURE = BAD_OPCODE
    MAKE_CLOSURE = BAD_OPCODE

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
    def nomoreblocks(self):
        raise BytecodeCorruption("misplaced bytecode - should not return")


class Return(FlowSignal):
    """Signals a 'return' statement.
    Argument is the wrapped object to return."""

    def __init__(self, w_value):
        self.w_value = w_value

    def nomoreblocks(self):
        raise Return(self.w_value)

    def state_unpack_variables(self):
        return [self.w_value]

    @staticmethod
    def state_pack_variables(w_value):
        return Return(w_value)

class Raise(FlowSignal):
    """Signals an application-level exception
    (i.e. an OperationException)."""

    def __init__(self, w_exc):
        self.w_exc = w_exc

    def nomoreblocks(self):
        raise self

    def state_unpack_variables(self):
        return [self.w_exc.w_type, self.w_exc.w_value]

    @staticmethod
    def state_pack_variables(w_type, w_value):
        return Raise(FSException(w_type, w_value))

class RaiseImplicit(Raise):
    """Signals an exception raised implicitly"""


class Break(FlowSignal):
    """Signals a 'break' statement."""

    def state_unpack_variables(self):
        return []

    @staticmethod
    def state_pack_variables():
        return Break.singleton

Break.singleton = Break()

class Continue(FlowSignal):
    """Signals a 'continue' statement.
    Argument is the bytecode position of the beginning of the loop."""

    def __init__(self, jump_to):
        self.jump_to = jump_to

    def state_unpack_variables(self):
        return [const(self.jump_to)]

    @staticmethod
    def state_pack_variables(w_jump_to):
        return Continue(w_jump_to.value)


class FrameBlock(object):
    """Abstract base class for frame blocks from the blockstack,
    used by the SETUP_XXX and POP_BLOCK opcodes."""

    def __init__(self, frame, handlerposition):
        self.handlerposition = handlerposition
        self.valuestackdepth = frame.valuestackdepth

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.handlerposition == other.handlerposition and
                self.valuestackdepth == other.valuestackdepth)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.handlerposition, self.valuestackdepth))

    def cleanupstack(self, frame):
        frame.dropvaluesuntil(self.valuestackdepth)

    def handle(self, frame, unroller):
        raise NotImplementedError

class LoopBlock(FrameBlock):
    """A loop block.  Stores the end-of-loop pointer in case of 'break'."""

    handles = (Break, Continue)

    def handle(self, frame, unroller):
        if isinstance(unroller, Continue):
            # re-push the loop block without cleaning up the value stack,
            # and jump to the beginning of the loop, stored in the
            # exception's argument
            frame.blockstack.append(self)
            return unroller.jump_to
        else:
            # jump to the end of the loop
            self.cleanupstack(frame)
            return self.handlerposition

class ExceptBlock(FrameBlock):
    """An try:except: block.  Stores the position of the exception handler."""

    handles = Raise

    def handle(self, frame, unroller):
        # push the exception to the value stack for inspection by the
        # exception handler (the code after the except:)
        self.cleanupstack(frame)
        assert isinstance(unroller, Raise)
        w_exc = unroller.w_exc
        # the stack setup is slightly different than in CPython:
        # instead of the traceback, we store the unroller object,
        # wrapped.
        frame.pushvalue(unroller)
        frame.pushvalue(w_exc.w_value)
        frame.pushvalue(w_exc.w_type)
        frame.last_exception = w_exc
        return self.handlerposition   # jump to the handler

class FinallyBlock(FrameBlock):
    """A try:finally: block.  Stores the position of the exception handler."""

    handles = FlowSignal

    def handle(self, frame, unroller):
        # any abnormal reason for unrolling a finally: triggers the end of
        # the block unrolling and the entering the finally: handler.
        self.cleanupstack(frame)
        frame.pushvalue(unroller)
        return self.handlerposition   # jump to the handler


class WithBlock(FinallyBlock):

    def handle(self, frame, unroller):
        return FinallyBlock.handle(self, frame, unroller)
