"""Python control flow graph generation and bytecode assembly."""

import math
import os
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.rlib import rstring

from pypy.interpreter.astcompiler import ast, consts, misc, symtable
from pypy.interpreter.error import OperationError
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.miscutils import string_sort
from pypy.tool import stdlib_opcode as ops

is_absolute_jump = misc.dict_to_switch(
    {opcode.index: True
        for opcode in ops.unrolling_opcode_descs
        if opcode.index in ops.hasjabs},
    default=False)


class StackDepthComputationError(Exception):
    pass


class Instruction(object):
    """Represents a single opcode."""

    _stack_depth_after = -99 # used before translation only

    def __init__(self, opcode, arg=0):
        self.opcode = opcode
        self.arg = arg
        if opcode < ops.HAVE_ARGUMENT:
            assert arg == 0
        self.lineno = 0
        self.jump = None

    def size(self):
        """Return the size of bytes of this instruction when it is
        encoded.
        """
        if self.arg <= 0xff:
            return 2
        if self.arg <= 0xffff:
            return 4
        if self.arg <= 0xffffff:
            return 6
        return 8

    def encode(self, code):
        opcode = self.opcode

        arg = self.arg
        size = self.size()
        if size == 8:
            code.append(chr(ops.EXTENDED_ARG))
            code.append(chr((arg >> 24) & 0xff))
            assert ((arg >> 24) & 0xff) == (arg >> 24)
        if size >= 6:
            code.append(chr(ops.EXTENDED_ARG))
            code.append(chr((arg >> 16) & 0xff))
        if size >= 4:
            code.append(chr(ops.EXTENDED_ARG))
            code.append(chr((arg >> 8) & 0xff))
        if size >= 2:
            code.append(chr(opcode))
            code.append(chr(arg & 0xff))


    def jump_to(self, target):
        """Indicate the target this jump instruction.

        The opcode must be a JUMP opcode.
        """
        self.jump = target

    def __repr__(self):
        data = [ops.opname[self.opcode]]
        template = "<%s"
        if self.opcode >= ops.HAVE_ARGUMENT:
            data.append(self.arg)
            template += " %i"
            if self.jump is not None:
                data.append(self.jump)
                template += " %s"
        template += ">"
        return template % tuple(data)


class Block(object):
    """A basic control flow block.

    It has one entry point and several possible exit points.  Its
    instructions may be jumps to other blocks, or if control flow
    reaches the end of the block, it continues to next_block.
    """

    _source = None

    def __init__(self):
        self.instructions = []
        self.next_block = None
        self.marked = 0
        # is True if instructions[-1] is one that unconditionally leaves the
        # execution of the instructions in the block (return, raise,
        # unconditional jumps)
        self.cant_add_instructions = False
        self.auto_inserted_return = False

    def _post_order_see(self, stack):
        if self.marked == 0:
            self.marked = 1
            stack.append(self)

    def post_order(self):
        """Return this block and its children in post order.  This means
        that the graph of blocks is first cleaned up to ignore
        back-edges, thus turning it into a DAG.  Then the DAG is
        linearized.  For example:

                   A --> B -\           =>     [A, D, B, C]
                     \-> D ---> C
        """
        resultblocks = []
        stack = [self]
        self.marked = 1
        while stack:
            current = stack[-1]
            if current.marked == 1:
                current.marked = 2
                if current.next_block is not None:
                    current.next_block._post_order_see(stack)
            else:
                i = current.marked - 2
                assert i >= 0
                while i < len(current.instructions):
                    instr = current.instructions[i]
                    i += 1
                    if instr.jump is not None:
                        current.marked = i + 2
                        instr.jump._post_order_see(stack)
                        break
                else:
                    resultblocks.append(current)
                    stack.pop()
        resultblocks.reverse()
        return resultblocks

    def code_size(self):
        """Return the encoded size of all the instructions in this
        block.
        """
        i = 0
        for instr in self.instructions:
            i += instr.size()
        return i

    def get_code(self, code):
        """Encode the instructions in this block into bytecode."""
        startsize = code.getlength()
        for instr in self.instructions:
            instr.encode(code)
        assert code.getlength() == startsize + self.code_size()
        assert code.getlength() & 1 == 0


def _make_index_dict_filter(syms, flag1, flag2):
    names = syms.keys()
    string_sort(names)   # return cell vars in alphabetical order
    i = 0
    result = {}
    for name in names:
        scope = syms[name]
        if scope in (flag1, flag2):
            result[name] = i
            i += 1
    return result


@specialize.argtype(0)
def _iter_to_dict(iterable, offset=0):
    result = {}
    index = offset
    for item in iterable:
        result[item] = index
        index += 1
    return result


class PythonCodeMaker(ast.ASTVisitor):
    """Knows how to assemble a PyCode object."""

    def __init__(self, space, name, first_lineno, scope, compile_info):
        self.space = space
        self.name = name
        self.first_lineno = first_lineno
        self.compile_info = compile_info
        self.first_block = self.new_block()
        self.current_block = self.first_block
        self._is_dead_code = False
        self.names = {}
        self.var_names = _iter_to_dict(scope.varnames)
        self.cell_vars = _make_index_dict_filter(scope.symbols,
                                                 symtable.SCOPE_CELL,
                                                 symtable.SCOPE_CELL_CLASS)
        string_sort(scope.free_vars)    # return free vars in alphabetical order
        self.free_vars = _iter_to_dict(scope.free_vars, len(self.cell_vars))
        self.w_consts = space.newdict()
        self.consts_w = []
        self.argcount = 0
        self.posonlyargcount = 0
        self.kwonlyargcount = 0
        self.lineno = 0
        self.add_none_to_final_return = True
        self.match_context = None

    def _check_consistency(self, blocks):
        current_off = 0
        for block in blocks:
            assert block.offset == current_off
            for instr in block.instructions:
                current_off += instr.size()

    def new_block(self):
        return Block()

    def use_block(self, block):
        """Start emitting bytecode into block."""
        self.current_block = block

    def use_next_block(self, block=None):
        """Set this block as the next_block for the last and use it."""
        if block is None:
            block = self.new_block()
        self.current_block.next_block = block
        self.use_block(block)
        return block

    def is_dead_code(self):
        """Return False if any code can be meaningfully added to the
        current block, or True if it would be dead code."""
        return self._is_dead_code or self.current_block.cant_add_instructions

    def all_dead_code(self):
        return DeadCode(self)

    def emit_instr(self, instr):
        self.current_block.instructions.append(instr)
        op = instr.opcode
        if (
                op == ops.RETURN_VALUE or
                op == ops.RAISE_VARARGS or
                op == ops.JUMP_FORWARD or
                op == ops.JUMP_ABSOLUTE
        ):
            self.current_block.cant_add_instructions = True

    def emit_op(self, op):
        """Emit an opcode without an argument."""
        instr = Instruction(op)
        instr.lineno = self.lineno
        if not self.is_dead_code():
            self.emit_instr(instr)
        return instr

    def emit_op_arg(self, op, arg):
        """Emit an opcode with an integer argument."""
        instr = Instruction(op, arg)
        instr.lineno = self.lineno
        if not self.is_dead_code():
            self.emit_instr(instr)

    def emit_rot_n(self, arg):
        if arg == 2:
            self.emit_op(ops.ROT_TWO)
        elif arg == 3:
            self.emit_op(ops.ROT_THREE)
        elif arg == 4:
            self.emit_op(ops.ROT_FOUR)
        else:
            self.emit_op_arg(ops.ROT_N, arg)

    def emit_op_name(self, op, container, name):
        """Emit an opcode referencing a name."""
        self.emit_op_arg(op, self.add_name(container, name))

    def emit_jump(self, op, block_to):
        """Emit a jump opcode to another block."""
        self.emit_op(op).jump_to(block_to)

    def emit_compare(self, ast_op_kind):
        from pypy.interpreter.astcompiler.codegen import compare_operations
        opcode, op_kind = compare_operations(ast_op_kind)
        self.emit_op_arg(opcode, op_kind)

    def add_name(self, container, name):
        """Get the index of a name in container."""
        name = self.scope.mangle(name)
        try:
            index = container[name]
        except KeyError:
            index = len(container)
            container[name] = index
        return index

    def add_const(self, w_obj):
        """Add a W_Root to the constant array and return its location."""
        space = self.space
        if isinstance(w_obj, PyCode):
            # unlike CPython, never share code objects, it's pointless
            w_key = space.id(w_obj)
        else:
            w_key = PyCode.const_comparison_key(self.space, w_obj)

        w_len = space.finditem(self.w_consts, w_key)
        if w_len is not None:
            length = space.int_w(w_len)
        else:
            length = len(self.consts_w)
            w_obj = misc.intern_if_common_string(space, w_obj)
            self.consts_w.append(w_obj)
            space.setitem(self.w_consts, w_key, space.newint(length))
        if length == 0:
            self.scope.doc_removable = False
        return length


    def load_const(self, obj):
        if self.is_dead_code():
            return
        index = self.add_const(obj)
        self.emit_op_arg(ops.LOAD_CONST, index)

    def update_position(self, lineno):
        """Change the lineno for the next instructions."""
        self.lineno = lineno

    def new_match_context(self):
        return MatchContext(self)

    def sub_pattern_context(self):
        return SubMatchContext(self)

    def _resolve_block_targets(self, blocks):
        """Compute the arguments of jump instructions."""
        # The reason for this loop is extended jumps.  EXTENDED_ARG
        # extends the bytecode size, so it might invalidate the offsets we've
        # already given.  Thus we have to loop until the size of all jump
        # instructions is stable. Any extended jump at all is extremely rare,
        # so performance should not be too concerning.
        while True:
            offset = 0
            force_redo = False
            # Calculate the code offset of each block.
            for block in blocks:
                block.offset = offset
                offset += block.code_size()
            totalsize = offset
            for block in blocks:
                offset = block.offset
                for instr in block.instructions:
                    size = instr.size()
                    offset += size
                    if instr.jump is not None:
                        target = instr.jump
                        op = instr.opcode
                        # Optimize an unconditional jump going to another
                        # unconditional jump.
                        if op == ops.JUMP_ABSOLUTE or op == ops.JUMP_FORWARD:
                            if target.instructions:
                                target_op = target.instructions[0].opcode
                                if target_op == ops.JUMP_ABSOLUTE:
                                    target = target.instructions[0].jump
                                    instr.opcode = ops.JUMP_ABSOLUTE
                                elif target_op == ops.RETURN_VALUE:
                                    # Replace JUMP_* to a RETURN into
                                    # just a RETURN
                                    instr.opcode = ops.RETURN_VALUE
                                    instr.arg = 0
                                    instr.jump = None
                                    # The size of the code maybe have changed,
                                    # we have to trigger another pass
                                    if instr.size() != size:
                                        force_redo = True
                                    continue
                        elif target.instructions and (
                                op == ops.POP_JUMP_IF_FALSE or
                                op == ops.POP_JUMP_IF_TRUE or
                                op == ops.JUMP_IF_FALSE_OR_POP or
                                op == ops.JUMP_IF_TRUE_OR_POP):
                            target_op = target.instructions[0]
                            if (target_op.opcode == ops.JUMP_ABSOLUTE or
                                    target_op.opcode == ops.JUMP_FORWARD):
                                target = target_op.jump
                                instr.jump = target
                        if is_absolute_jump(instr.opcode):
                            jump_arg = target.offset
                        else:
                            jump_arg = target.offset - offset
                            assert jump_arg >= 0
                        instr.arg = jump_arg
                        if instr.size() != size:
                            force_redo = True
            if not force_redo:
                self._check_consistency(blocks)
                return totalsize

    def _get_code_flags(self):
        """Get an extra flags that should be attached to the code object."""
        raise NotImplementedError

    def _stacksize_error_pos(self, depth, blocks, block, instr):
        # This case occurs if this code object uses some
        # construction for which the stack depth computation
        # is wrong (too high).  If you get here while working
        # on the astcompiler, then you should at first ignore
        # the error, and comment out the 'raise' below.  Such
        # an error is not really bad: it is just a bit
        # wasteful.  For release-ready versions, though, we'd
        # like not to be wasteful. :-)
        if not we_are_translated():
            self._stack_depth_debug_print(blocks, block, instr)
        os.write(2, "StackDepthComputationError(POS) in %s at %s:%s depth %s\n"
          % (self.compile_info.filename, self.name, self.first_lineno, depth))
        raise StackDepthComputationError   # would-be-nice-not-to-have

    def _stack_depth_debug_print(self, blocks, errorblock, errorinstr):
        print "\n" * 5
        print self.name
        for block in blocks:
            print "======="
            print block
            if block is errorblock:
                print "ERROR IS IN THIS BLOCK"
            print "stack depth at start", block.initial_depth
            if block._source is not None:
                print "stack depth at start set via", block._source
            for instr in block.instructions:
                print "--->" if instr is errorinstr else "    ", instr,
                if instr._stack_depth_after != -99:
                    print "stacksize afterwards: %s" % instr._stack_depth_after
                else:
                    print


    def _stacksize(self, blocks):
        """Compute co_stacksize."""
        for block in blocks:
            block.initial_depth = -99
        blocks[0].initial_depth = 0
        # Assumes that it is sufficient to walk the blocks in 'post-order'.
        # This means we ignore all back-edges, but apart from that, we only
        # look into a block when all the previous blocks have been done.
        self._max_depth = 0
        for block in blocks:
            depth = self._do_stack_depth_walk(block, blocks)
            if block.auto_inserted_return and depth != 0:
                self._stacksize_error_pos(depth, blocks, block, None)
        return self._max_depth

    def _next_stack_depth_walk(self, nextblock, depth, source):
        if depth > nextblock.initial_depth:
            nextblock.initial_depth = depth
            if not we_are_translated():
                nextblock._source = source

    def _do_stack_depth_walk(self, block, blocks):
        depth = block.initial_depth
        if depth == -99:     # this block is never reached, skip
             return 0

        for instr in block.instructions:
            orig_depth = depth
            depth += _opcode_stack_effect(instr.opcode, instr.arg)
            if depth < 0:
                # This is really a fatal error, don't comment out this
                # 'raise'.  It means that the stack depth computation
                # thinks there is a path that yields a negative stack
                # depth, which means that it underestimates the space
                # needed and it would crash when interpreting this
                # code.
                if not we_are_translated():
                    instr._stack_depth_after = depth
                    self._stack_depth_debug_print(blocks, block, instr)
                os.write(2, "StackDepthComputationError(NEG) in %s at %s:%s\n"
                  % (self.compile_info.filename, self.name, self.first_lineno))
                raise StackDepthComputationError   # really fatal error
            if depth >= self._max_depth:
                self._max_depth = depth
            jump_op = instr.opcode
            if instr.jump is not None:
                target_depth = orig_depth + _opcode_stack_effect_jump(jump_op)
                if target_depth > self._max_depth:
                    self._max_depth = target_depth
                self._next_stack_depth_walk(instr.jump, target_depth, (block, instr))
                if jump_op == ops.JUMP_ABSOLUTE or jump_op == ops.JUMP_FORWARD:
                    # Nothing more can occur.
                    break
            elif jump_op == ops.RETURN_VALUE:
                if depth:
                    self._stacksize_error_pos(depth, blocks, block, instr)
                break
            elif jump_op == ops.RAISE_VARARGS:
                break
            elif jump_op == ops.RERAISE:
                break
            if not we_are_translated():
                instr._stack_depth_after = depth
        else:
            if block.next_block:
                self._next_stack_depth_walk(block.next_block, depth, (block, None))
        return depth

    def _build_lnotab(self, blocks):
        """Build the line number table for tracebacks and tracing."""
        current_line = self.first_lineno
        current_off = 0
        table = rstring.StringBuilder()
        for block in blocks:
            offset = block.offset
            for instr in block.instructions:
                if instr.lineno:
                    # compute deltas
                    line = instr.lineno - current_line
                    addr = offset - current_off
                    if line:
                        _encode_lnotab_pair(addr, line, table)
                        current_line = instr.lineno
                        current_off = offset
                offset += instr.size()
        return table.build()

    def _build_code(self, blocks, size):
        bytecode = rstring.StringBuilder(size)
        for block in blocks:
            block.get_code(bytecode)
        return bytecode.build()

    def assemble(self):
        """Build a PyCode object."""
        # Unless it's interactive, every code object must end in a return.
        if not self.current_block.cant_add_instructions:
            if self.add_none_to_final_return:
                self.load_const(self.space.w_None)
            self.emit_op(ops.RETURN_VALUE)
            self.current_block.auto_inserted_return = True
        # Set the first lineno if it is not already explicitly set.
        if self.first_lineno == -1:
            if self.first_block.instructions:
                self.first_lineno = self.first_block.instructions[0].lineno
            else:
                self.first_lineno = 1
        blocks = self.first_block.post_order()
        size = self._resolve_block_targets(blocks)
        lnotab = self._build_lnotab(blocks)
        stack_depth = self._stacksize(blocks)
        consts_w = self.consts_w[:]
        names = _list_from_dict(self.names)
        var_names = _list_from_dict(self.var_names)
        cell_names = _list_from_dict(self.cell_vars)
        free_names = _list_from_dict(self.free_vars, len(cell_names))
        flags = self._get_code_flags()
        bytecode = self._build_code(blocks, size)
        # (Only) inherit compilerflags in PyCF_MASK
        flags |= (self.compile_info.flags & consts.PyCF_MASK)
        return PyCode(self.space,
                      self.argcount,
                      self.posonlyargcount,
                      self.kwonlyargcount,
                      len(self.var_names),
                      stack_depth,
                      flags,
                      bytecode,
                      list(consts_w),
                      names,
                      var_names,
                      self.compile_info.filename,
                      self.name,
                      self.first_lineno,
                      lnotab,
                      free_names,
                      cell_names,
                      self.compile_info.hidden_applevel)


class DeadCode(object):
    def __init__(self, codegen):
        self.codegen = codegen

    def __enter__(self, *args):
        self.old_value = self.codegen._is_dead_code
        self.codegen._is_dead_code = True

    def __exit__(self, *args):
        self.codegen._is_dead_code = self.old_value


class MatchContext(object):
    def __init__(self, codegen):
        self.codegen = codegen
        self._init_names()
        self.allow_always_passing = False
        # the extra objects currently on the stack that need cleaning up
        self.on_top = 0
        self._reset_cleanup_blocks()

    def _init_names(self):
        self.names_stored = {} # name -> int
        self.names_list = [] # list of names in order
        self.names_origins = [] # ast nodes to blame if a name repeats

    def add_name(self, name, node, codegen):
        index = self.names_stored.get(name, -1)
        if index >= 0:
            # already exists
            previous_node = self.names_origins[index]
            codegen.error(
                "multiple assignments to name '%s' in pattern, previous one was on line %s" % (
                    name, previous_node.lineno), node)
        else:
            self.names_stored[name] = len(self.names_stored)
            self.names_list.append(name)
            self.names_origins.append(node)

    def _reset_cleanup_blocks(self):
        self.next = self.codegen.new_block()
        # the cleanup blocks will all be chained in reverse order, each one
        # contains a POP_TOP and a jump to the next one
        self.cleanup_blocks = [self.next]

    def next_case(self):
        # add the POP_TOP instructions to the cleanup blocks
        for index in range(len(self.cleanup_blocks) - 1, 0, -1):
            block = self.cleanup_blocks[index]
            self.codegen.use_next_block(block)
            self.codegen.emit_op(ops.POP_TOP)
        self.codegen.use_next_block(self.next)
        self._reset_cleanup_blocks()
        self._init_names()

    def emit_fail_jump(self, op, absolute, cleanup=0):
        # emits a (conditional or unconditional) jump to the cleanup block (ie,
        # failure) with the right number of POP_TOPs
        cleanup += self.on_top + len(self.names_stored)
        while cleanup >= len(self.cleanup_blocks):
            self.cleanup_blocks.append(self.codegen.new_block())
        target = self.cleanup_blocks[cleanup]
        self.codegen.emit_jump(op, target, absolute)

    def __enter__(self, *args):
        self.old_context = self.codegen.match_context
        self.codegen.match_context = self
        return self

    def __exit__(self, *args):
        self.codegen.match_context = self.old_context

class SubMatchContext(object):
    """ context manager for setting allow_always_passing to True and then
    restoring the old value on leaving. """
    def __init__(self, codegen):
        self.codegen = codegen

    def __enter__(self, *args):
        match_context = self.codegen.match_context
        self.old_value = match_context.allow_always_passing
        match_context.allow_always_passing = True
        return match_context

    def __exit__(self, *args):
        self.codegen.match_context.allow_always_passing = self.old_value


def _list_from_dict(d, offset=0):
    result = [None] * len(d)
    for obj, index in d.iteritems():
        result[index - offset] = obj
    return result


def _encode_lnotab_pair(addr, line, table):
    while addr > 255:
        table.append(chr(255))
        table.append(chr(0))
        addr -= 255
    while line < -128:
        table.append(chr(addr))
        table.append(chr(-128 + 256))
        line += 128
        addr = 0
    while line > 127:
        table.append(chr(addr))
        table.append(chr(127))
        line -= 127
        addr = 0
    table.append(chr(addr))

    # store as signed char
    assert -128 <= line <= 127
    if line < 0:
        line += 256
    table.append(chr(line))

_static_opcode_stack_effects = {
    ops.NOP: 0,

    ops.POP_TOP: -1,
    ops.ROT_TWO: 0,
    ops.ROT_THREE: 0,
    ops.ROT_FOUR: 0,
    ops.DUP_TOP: 1,
    ops.DUP_TOP_TWO: 2,

    ops.UNARY_POSITIVE: 0,
    ops.UNARY_NEGATIVE: 0,
    ops.UNARY_NOT: 0,
    ops.UNARY_INVERT: 0,

    ops.LIST_APPEND: -1,
    ops.LIST_EXTEND: -1,
    ops.LIST_TO_TUPLE: 0,
    ops.SET_ADD: -1,
    ops.SET_UPDATE: -1,
    ops.MAP_ADD: -2,

    ops.BINARY_POWER: -1,
    ops.BINARY_MULTIPLY: -1,
    ops.BINARY_MODULO: -1,
    ops.BINARY_ADD: -1,
    ops.BINARY_SUBTRACT: -1,
    ops.BINARY_SUBSCR: -1,
    ops.BINARY_FLOOR_DIVIDE: -1,
    ops.BINARY_TRUE_DIVIDE: -1,
    ops.BINARY_MATRIX_MULTIPLY: -1,
    ops.BINARY_LSHIFT: -1,
    ops.BINARY_RSHIFT: -1,
    ops.BINARY_AND: -1,
    ops.BINARY_OR: -1,
    ops.BINARY_XOR: -1,

    ops.INPLACE_FLOOR_DIVIDE: -1,
    ops.INPLACE_TRUE_DIVIDE: -1,
    ops.INPLACE_ADD: -1,
    ops.INPLACE_SUBTRACT: -1,
    ops.INPLACE_MULTIPLY: -1,
    ops.INPLACE_MODULO: -1,
    ops.INPLACE_POWER: -1,
    ops.INPLACE_MATRIX_MULTIPLY: -1,
    ops.INPLACE_LSHIFT: -1,
    ops.INPLACE_RSHIFT: -1,
    ops.INPLACE_AND: -1,
    ops.INPLACE_OR: -1,
    ops.INPLACE_XOR: -1,

    ops.STORE_SUBSCR: -3,
    ops.DELETE_SUBSCR: -2,

    ops.GET_ITER: 0,
    ops.FOR_ITER: 1,

    ops.PRINT_EXPR: -1,

    ops.LOAD_BUILD_CLASS: 1,
    ops.POP_BLOCK: 0,
    ops.POP_EXCEPT: -1,
    ops.SETUP_WITH: 1,
    ops.SETUP_FINALLY: 0,
    ops.SETUP_EXCEPT: 0,

    ops.RETURN_VALUE: -1,
    ops.YIELD_VALUE: 0,
    ops.YIELD_FROM: -1,
    ops.COMPARE_OP: -1,
    ops.IS_OP: -1,
    ops.CONTAINS_OP: -1,

    ops.LOAD_METHOD: 1,

    ops.LOAD_NAME: 1,
    ops.STORE_NAME: -1,
    ops.DELETE_NAME: 0,

    ops.LOAD_FAST: 1,
    ops.STORE_FAST: -1,
    ops.DELETE_FAST: 0,

    ops.LOAD_ATTR: 0,
    ops.STORE_ATTR: -2,
    ops.DELETE_ATTR: -1,

    ops.LOAD_GLOBAL: 1,
    ops.STORE_GLOBAL: -1,
    ops.DELETE_GLOBAL: 0,
    ops.DELETE_DEREF: 0,

    ops.LOAD_CLOSURE: 1,
    ops.LOAD_DEREF: 1,
    ops.STORE_DEREF: -1,
    ops.DELETE_DEREF: 0,

    ops.GET_AWAITABLE: 0,
    ops.SETUP_ASYNC_WITH: 0,
    ops.BEFORE_ASYNC_WITH: 1,
    ops.GET_AITER: 0,
    ops.GET_ANEXT: 1,
    ops.GET_YIELD_FROM_ITER: 0,
    ops.END_ASYNC_FOR: -5, # this is really only -4, but it needs to be -5 to
    # balance the SETUP_EXCEPT, which pretends to push +4

    ops.LOAD_CONST: 1,

    ops.IMPORT_STAR: -1,
    ops.IMPORT_NAME: -1,
    ops.IMPORT_FROM: 1,

    ops.JUMP_FORWARD: 0,
    ops.JUMP_ABSOLUTE: 0,
    ops.JUMP_IF_TRUE_OR_POP: -1,
    ops.JUMP_IF_FALSE_OR_POP: -1,
    ops.POP_JUMP_IF_TRUE: -1,
    ops.POP_JUMP_IF_FALSE: -1,
    ops.JUMP_IF_NOT_EXC_MATCH: -2,

    ops.SETUP_ANNOTATIONS: 0,

    ops.DICT_MERGE: -1,
    ops.DICT_UPDATE: -1,

    # TODO
    ops.BUILD_LIST_FROM_ARG: 1,
    ops.LOAD_REVDB_VAR: 1,

    ops.LOAD_CLASSDEREF: 1,
    ops.LOAD_ASSERTION_ERROR: 1,

    ops.RERAISE: -1,

    ops.WITH_EXCEPT_START: 0,

    ops.GET_LEN: 1,
    ops.MATCH_MAPPING: 1,
    ops.MATCH_SEQUENCE: 1,
    ops.MATCH_KEYS: 2,
    ops.COPY_DICT_WITHOUT_KEYS: 0,
    ops.ROT_N: 0,
    ops.MATCH_CLASS: -1,
}


def _compute_UNPACK_SEQUENCE(arg):
    return arg - 1

def _compute_UNPACK_EX(arg):
    return (arg & 0xFF) + (arg >> 8)

def _compute_BUILD_TUPLE(arg):
    return 1 - arg

def _compute_BUILD_LIST(arg):
    return 1 - arg

def _compute_BUILD_SET(arg):
    return 1 - arg

def _compute_BUILD_MAP(arg):
    return 1 - 2 * arg

def _compute_MAKE_FUNCTION(arg):
    return -1 - bool(arg & 0x01) - bool(arg & 0x02) - bool(arg & 0x04) - bool(arg & 0x08)

def _compute_BUILD_SLICE(arg):
    if arg == 3:
        return -2
    else:
        return -1

def _compute_RAISE_VARARGS(arg):
    return -arg

def _compute_CALL_FUNCTION(arg):
    return -arg

def _compute_CALL_FUNCTION_KW(arg):
    return -arg - 1

def _compute_CALL_FUNCTION_EX(arg):
    assert arg == 0 or arg == 1
    # either -1 or -2
    return -arg - 1

def _compute_CALL_METHOD(arg):
    return -arg - 1

def _compute_CALL_METHOD_KW(arg):
    return -arg - 2

def _compute_FORMAT_VALUE(arg):
    if (arg & consts.FVS_MASK) == consts.FVS_HAVE_SPEC:
        return -1
    return 0

def _compute_BUILD_STRING(arg):
    return 1 - arg

def _compute_BUILD_CONST_KEY_MAP(arg):
    return  -arg


_stack_effect_computers = {}
for name, func in globals().items():
    if name.startswith("_compute_"):
        func._always_inline_ = True
        _stack_effect_computers[getattr(ops, name[9:])] = func
for op, value in _static_opcode_stack_effects.iteritems():
    def func(arg, _value=value):
        return _value
    func._always_inline_ = True
    _stack_effect_computers[op] = func
del name, func, op, value


def _opcode_stack_effect(op, arg):
    """Return the stack effect of a opcode an its argument."""
    if we_are_translated():
        for possible_op in ops.unrolling_opcode_descs:
            # EXTENDED_ARG should never get in here.
            if possible_op.index == ops.EXTENDED_ARG:
                continue
            if op == possible_op.index:
                return _stack_effect_computers[possible_op.index](arg)
        else:
            raise KeyError("unknown opcode: %s" % (op,))
    else:
        try:
            return _static_opcode_stack_effects[op]
        except KeyError:
            try:
                return _stack_effect_computers[op](arg)
            except KeyError:
                raise KeyError("Unknown stack effect for %s (%s)" %
                               (ops.opname[op], op))

def _opcode_stack_effect_jump(op):
    if op == ops.FOR_ITER:
        return -1
    elif op == ops.SETUP_FINALLY:
        return 2
    elif op == ops.SETUP_EXCEPT:
        return 4 # XXX why is this not 3?
    elif op == ops.SETUP_WITH:
        return 2
    elif op == ops.SETUP_ASYNC_WITH:
        return 1
    elif op == ops.JUMP_IF_TRUE_OR_POP:
        return 0
    elif op == ops.JUMP_IF_FALSE_OR_POP:
        return 0
    elif op == ops.JUMP_IF_NOT_EXC_MATCH:
        return -2
    elif op == ops.POP_JUMP_IF_TRUE:
        return -1
    elif op == ops.POP_JUMP_IF_FALSE:
        return -1
    elif op == ops.JUMP_FORWARD:
        return 0
    elif op == ops.JUMP_ABSOLUTE:
        return 0
    raise KeyError

