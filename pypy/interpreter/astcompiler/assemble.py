"""Python control flow graph generation and bytecode assembly."""

import math
import os
import sys
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

UNKNOWN_POSITION = (-1, -1, -1, -1)

class Instruction(object):
    """Represents a single opcode."""

    _stack_depth_after = -99 # used before translation only

    def __init__(self, opcode, arg=0, position_info=UNKNOWN_POSITION):
        self.opcode = opcode
        self.arg = arg
        if opcode < ops.HAVE_ARGUMENT:
            assert arg == 0
        self.position_info = position_info
        self.jump = None

    def copy(self):
        res = Instruction(self.opcode, self.arg, self.position_info)
        res.jump = self.jump
        return res

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

    def update_position_if_not_set(self, position_info):
        if self.position_info[0] < 0:
            self.position_info = position_info
        else:
            position_info = self.position_info
        # returns the value of self.position_info, whether it was written to or
        # not
        return position_info

    def __repr__(self):
        data = ["<", ops.opname[self.opcode]]
        if self.opcode >= ops.HAVE_ARGUMENT:
            data.append(" ")
            data.append(str(self.arg))
            if self.jump is not None:
                data.append(" ")
                data.append(str(self.jump))
        data.append(" lineno=%s>" % (self.position_info[0], ))
        return "".join(data)


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
        self.exits_function = False
        self.auto_inserted_return = False

    def emit_instr(self, instr):
        self.instructions.append(instr)
        op = instr.opcode
        if (
                op == ops.RETURN_VALUE or
                op == ops.RAISE_VARARGS or
                op == ops.RERAISE
        ):
            self.exits_function = True
            self.cant_add_instructions = True
        elif (
                op == ops.JUMP_FORWARD or
                op == ops.JUMP_ABSOLUTE
        ):
            self.cant_add_instructions = True

    def _post_order_see(self, stack):
        if self.marked == 0:
            self.marked = 1
            stack.append(self)

    def copy(self):
        copy = Block()
        copy.auto_inserted_return = self.auto_inserted_return
        for instr in self.instructions:
            copy.emit_instr(instr.copy())
        return copy


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
        for block in resultblocks:
            block.marked = 0
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

    def jump_thread(self):
        # do jump threading
        # 1) skip empty .next_block
        if not self.cant_add_instructions:
            while self.next_block is not None and not self.next_block.instructions:
                self.next_block = self.next_block.next_block

        # 2) jump-thread instructions
        i = 0
        while i < len(self.instructions):
            instr = self.instructions[i]
            instr_lineno = instr.position_info[0]
            i += 1
            target = instr.jump
            if not target:
                continue
            # replace a jump to an empty block with a jump to its successor
            while not target.instructions:
                target = instr.jump = target.next_block
                assert target is not None
            opcode = instr.opcode
            target_instr = target.instructions[0]
            target_lineno = target_instr.position_info[0]
            target_opcode = target_instr.opcode
            if ((target_opcode == ops.JUMP_ABSOLUTE or target_opcode == ops.JUMP_FORWARD) and
                    target_instr.jump.instructions and
                    target_instr.jump.instructions[0].position_info[0] == target_lineno):
                # we have an unconditional jump where the jump instruction and
                # the target of the jump have the same lineno, so it's safe to
                # skip the jump
                pass
            elif target_lineno != instr_lineno and target_lineno != -1 and instr_lineno != -1:
                continue # don't jump thread to not lose lines
            # Optimize an unconditional jump going to another
            # unconditional jump.
            if opcode == ops.JUMP_ABSOLUTE or opcode == ops.JUMP_FORWARD:
                if target_opcode == ops.JUMP_ABSOLUTE:
                    instr.opcode = ops.JUMP_ABSOLUTE
                    instr.jump = target_instr.jump
                    i -= 1 # look at this instruction again
                elif target_opcode == ops.JUMP_FORWARD:
                    instr.jump = target_instr.jump
                    i -= 1 # look at this instruction again
                elif target_opcode == ops.RETURN_VALUE:
                    # Replace JUMP_* to a RETURN into
                    # just a RETURN
                    instr.opcode = ops.RETURN_VALUE
                    instr.jump = None
                continue
            if opcode == ops.JUMP_IF_FALSE_OR_POP:
                if (target_opcode == ops.JUMP_ABSOLUTE or
                        target_opcode == ops.JUMP_FORWARD or
                        target_opcode == ops.JUMP_IF_FALSE_OR_POP):
                    instr.jump = target_instr.jump
                    i -= 1 # look at this instruction again
            if opcode == ops.JUMP_IF_TRUE_OR_POP:
                if (target_opcode == ops.JUMP_ABSOLUTE or
                        target_opcode == ops.JUMP_FORWARD or
                        target_opcode == ops.JUMP_IF_TRUE_OR_POP):
                    instr.jump = target_instr.jump
                    i -= 1 # look at this instruction again
            if (opcode == ops.POP_JUMP_IF_FALSE or
                  opcode == ops.POP_JUMP_IF_TRUE
            ):
                if (target_opcode == ops.JUMP_ABSOLUTE or
                        target_opcode == ops.JUMP_FORWARD):
                    instr.jump = target_instr.jump
                    i -= 1 # look at this instruction again


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
    _debug_flag = False

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
        self.no_position_info()
        self.add_none_to_final_return = True
        self.match_context = None

    def _check_consistency(self, blocks):
        current_off = 0
        for block in blocks:
            assert block.offset == current_off
            for instr in block.instructions:
                current_off += instr.size()

    def view(self, blocks=None):
        from pypy.interpreter.astcompiler.codegen import view
        return view(blocks or self.first_block)

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

    def emit_op(self, op):
        """Emit an opcode without an argument."""
        instr = Instruction(op, position_info=self.position_info)
        if not self.is_dead_code():
            self.current_block.emit_instr(instr)
        return instr

    def emit_op_arg(self, op, arg):
        """Emit an opcode with an integer argument."""
        instr = Instruction(op, arg, position_info=self.position_info)
        if not self.is_dead_code():
            self.current_block.emit_instr(instr)

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

    def emit_line_tracing_nop(self, node=None):
        old_position_info = UNKNOWN_POSITION
        if node:
            old_position_info = self.position_info
            self.update_position(node)
        self.emit_op(ops.NOP)
        if node:
            self.position_info = old_position_info

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

    @specialize.argtype(1)
    def update_position(self, node):
        """Change the position for the next instructions to that of node."""
        if self.is_dead_code():
            return self.position_info
        if isinstance(node, tuple):
            position_info = node
        else:
            position_info = (node.lineno, node.end_lineno, node.col_offset, node.end_col_offset)
        old_position_info = self.position_info
        self.position_info =  position_info
        return old_position_info

    def no_position_info(self):
        if self.is_dead_code():
            return
        self.position_info = (-1, ) * 4

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
                        if is_absolute_jump(instr.opcode):
                            jump_arg = target.offset
                        else:
                            jump_arg = target.offset - offset
                        assert jump_arg >= 0
                        jump_arg //= 2
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

    def _build_positions(self, blocks):
        """Build the column offset table (with end column offsets)."""
        from pypy.interpreter.location import encode_single_position
        table = rstring.StringBuilder()
        for block in blocks:
            for instr in block.instructions:
                encode_single_position(table, instr.position_info, self.first_lineno)
                for extra in range((instr.size() - 2) // 2):
                    encode_single_position(table, UNKNOWN_POSITION, self.first_lineno)
        return table.build()

    def _build_code(self, blocks, size):
        bytecode = rstring.StringBuilder(size)
        for block in blocks:
            block.get_code(bytecode)
        return bytecode.build()

    def jump_thread(self, blocks):
        for block in blocks:
            block.jump_thread()

    def compute_predecessors_in_marked(self, blocks):
        # compute predecessors, use the 'marked' attribute for it
        def increase_incoming(block, todo):
            block.marked += 1
            if block.marked == 1:
                todo.append(block)
        for block in blocks:
            block.marked = 0
        self.first_block.marked = 1
        todo = [self.first_block]
        while todo:
            block = todo.pop()
            # mark next_block, but only if the edge can actually be taken
            if block.next_block and not block.cant_add_instructions:
                increase_incoming(block.next_block, todo)
            for instr in block.instructions:
                if instr.jump:
                    increase_incoming(instr.jump, todo)

    def propagate_positions(self, blocks):
        # here block.marked stores the number of predecessor blocks.
        # use that info to propagate position information
        for block in blocks:
            if not block.instructions or block.marked == 0:
                continue
            prev_position = UNKNOWN_POSITION
            for instr in block.instructions:
                prev_position = instr.update_position_if_not_set(prev_position)
                if instr.jump is not None and instr.jump.marked == 1 and instr.jump.instructions:
                    if instr.opcode in (ops.SETUP_ASYNC_WITH, ops.SETUP_WITH, ops.SETUP_EXCEPT, ops.SETUP_FINALLY):
                        continue # don't do this for exception handlers
                    instr.jump.instructions[0].update_position_if_not_set(prev_position)
            if block.next_block and block.next_block.marked == 1 and block.instructions:
                block.instructions[0].update_position_if_not_set(prev_position)

    def optimize_unreachable_code(self, blocks):
        # block.marked still stores the predecessor information. use it to
        # remove all instructions from unreachable blocks, and optimize
        # JUMP_FORWARD instructions that go to the next block in the sequence
        # anyway. reset block.marked afterwards
        last_reachable = None
        for i, block in enumerate(blocks):
            # for blocks with 0 predecessors, don't emit any code for them by
            # setting the instructions to the empty list
            if block.marked == 0:
                block.instructions = []
                block.cant_add_instructions = False
                continue
            last_reachable = block
            if block.instructions and i < len(blocks) - 1:
                lastop = block.instructions[-1]
                if lastop.opcode == ops.JUMP_FORWARD:
                    # find the block we would fall through
                    target = None
                    for j in range(i + 1, len(blocks)):
                        target = blocks[j]
                        if target.marked:
                            break
                    assert target is not None
                    if target is lastop.jump:
                        lastop.opcode = ops.NOP
                        lastop.jump = None
                        block.next_block = blocks[i + 1]
            block.marked = 0
        # the last reachable block must have cant_add_instructions
        assert last_reachable is not None and last_reachable.cant_add_instructions

    def _finalize_blocks(self):
        # Unless it's interactive, every code object must end in a return.
        if self._debug_flag:
            import pdb; pdb.set_trace()
        if not self.current_block.cant_add_instructions:
            # the implicit return has no position info, unless the function
            # contains no bytecodes at all. in that case the RETURN_VALUE gets
            # the firstlineno as the position
            if (self.current_block is self.first_block and
                    len(self.current_block.instructions) == 0):
                self.position_info = (self.first_lineno, -1, -1, -1)
            else:
                self.no_position_info() # will be duplicated by duplicate_exits_without_lineno
            if self.add_none_to_final_return:
                self.load_const(self.space.w_None)
            self.emit_op(ops.RETURN_VALUE)
            self.current_block.auto_inserted_return = True
        blocks = self.first_block.post_order()
        remove_redundant_nops(blocks)
        self.jump_thread(blocks)
        self.compute_predecessors_in_marked(blocks)
        self.duplicate_exits_without_lineno(blocks)
        self.propagate_positions(blocks)
        self.optimize_unreachable_code(blocks)
        mininum_lineno = remove_redundant_nops(blocks)
        # Set the first lineno if it is not already explicitly set.
        if self.first_lineno == -1:
            self.first_lineno = mininum_lineno
        size = self._resolve_block_targets(blocks)
        return blocks, size

    def assemble(self):
        """Build a PyCode object."""
        blocks, size = self._finalize_blocks()
        stack_depth = self._stacksize(blocks)
        positions = self._build_positions(blocks)
        consts_w = self.consts_w[:]
        names = _list_from_dict(self.names)
        var_names = _list_from_dict(self.var_names)
        cell_names = _list_from_dict(self.cell_vars)
        free_names = _list_from_dict(self.free_vars, len(cell_names))
        flags = self._get_code_flags()
        bytecode = self._build_code(blocks, size)
        # (Only) inherit compilerflags in PyCF_MASK
        flags |= (self.compile_info.flags & consts.PyCF_MASK)
        if not we_are_translated():
            self._final_blocks = blocks
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
                      positions,
                      free_names,
                      cell_names,
                      self.compile_info.hidden_applevel)

    def duplicate_exits_without_lineno(self, blocks):
        from pypy.interpreter.astcompiler.codegen import view
        def should_mark_block(block):
            for instr in block.instructions:
                if instr.position_info[0] != -1:
                    return False
                if instr.jump and (instr.jump.marked & 1) == 0:
                    return False
            if block.next_block and not block.cant_add_instructions:
                return (block.next_block.marked & 1) == 1
            return True
        # this is a bit of a mess. we want *two* pieces of info in marked, the
        # number of predecessors and the "do I need to duplicate". left-shift
        # marked to have a bit free for the latter
        for block in blocks:
            block.marked <<= 1

        # mark blocks that are paths to an exit without meeting an instruction
        # with a line number. uses the fact that blocks is a post-order
        any_mark = False
        for i in range(len(blocks) - 1, -1, -1):
            block = blocks[i]
            # mark block if all instructions in block have -1 as the lineno
            # *and* all target blocks are also marked
            mark = should_mark_block(block)
            block.marked |= mark
            any_mark |= mark

        i = 0
        if not any_mark:
            i = len(blocks)

        while i < len(blocks):
            block = blocks[i]
            i += 1
            if (block.marked >> 1) == 0:
                # dead block
                continue
            j = 0
            while j < len(block.instructions):
                op = block.instructions[j]
                j += 1
                if op.jump is None:
                    continue
                if op.opcode in (ops.SETUP_ASYNC_WITH, ops.SETUP_WITH, ops.SETUP_EXCEPT, ops.SETUP_FINALLY):
                    continue # don't do this for exception handlers
                target = op.jump
                # only do something if the target has no position info (lowest
                # bit set)
                if not target.marked & 1:
                    continue

                # path leading to automatically inserted return or reraise,
                # without line number

                # if it's an unconditional jump, duplicate it
                if op.opcode in (ops.JUMP_FORWARD, ops.JUMP_ABSOLUTE):
                    block.instructions.pop()
                    j -= 1
                    target.marked -= 2 # one fewer incoming links
                    for instr in target.instructions:
                        instr = instr.copy()
                        if instr.position_info[0] == -1:
                            instr.position_info = op.position_info
                        copy = instr.copy()
                        if copy.jump:
                            copy.jump.marked += 2
                        block.emit_instr(copy)
                elif (target.marked >> 1) > 1:
                    # copy the block, it has more than one predecessor
                    target.marked -= 2 # one fewer incoming links for old target
                    newtarget = target.copy()
                    newtarget.marked = 1 << 1 # new target has one incoming link
                    newtarget.instructions[0].position_info = op.position_info
                    # maintain marked correctly:
                    if newtarget.next_block:
                        newtarget.next_block.marked += 2
                    for copied_op in newtarget.instructions:
                        if copied_op.jump:
                            copied_op.jump.marked += 2
                    op.jump = newtarget
                    blocks.append(newtarget)

        for block in blocks:
            if (block.instructions and block.next_block and
                    not block.cant_add_instructions and
                    block.next_block.marked & 1):
                # now assign the linenumber to the "fallthrough" implicit
                # return block too
                block.next_block.instructions[0].position_info = block.instructions[-1].position_info
            block.marked >>= 1


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

    def next_case(self, position_node=None):
        # add the POP_TOP instructions to the cleanup blocks
        for index in range(len(self.cleanup_blocks) - 1, 0, -1):
            block = self.cleanup_blocks[index]
            self.codegen.use_next_block(block)
            if position_node:
                self.codegen.update_position(position_node)
            self.codegen.emit_op(ops.POP_TOP)
        self.codegen.use_next_block(self.next)
        self._reset_cleanup_blocks()
        self._init_names()

    def emit_fail_jump(self, op, cleanup=0):
        # emits a (conditional or unconditional) jump to the cleanup block (ie,
        # failure) with the right number of POP_TOPs
        cleanup += self.on_top + len(self.names_stored)
        while cleanup >= len(self.cleanup_blocks):
            self.cleanup_blocks.append(self.codegen.new_block())
        target = self.cleanup_blocks[cleanup]
        self.codegen.emit_jump(op, target)

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

def _remove_redundant_nops(block):
    mininum_lineno = sys.maxint
    prevlineno = -1
    source = 0
    dest = 0
    instructions = block.instructions
    while source < len(instructions):
        op = instructions[source]
        source += 1
        lineno = op.position_info[0]
        if 0 < lineno < mininum_lineno:
            mininum_lineno = lineno
        if op.opcode == ops.NOP:
            if lineno == -1 or lineno == prevlineno:
                continue
            if source < len(instructions):
                if lineno == instructions[source].position_info[0]:
                    continue
            else:
                # last instruction in block is a NOP, check the next block
                if (block.next_block.instructions and
                        lineno == block.next_block.instructions[0].position_info[0]):
                    continue
        prevlineno = lineno
        instructions[dest] = op
        dest += 1
    if dest != len(instructions):
        del instructions[dest:]
    return mininum_lineno

def remove_redundant_nops(blocks):
    mininum_lineno = sys.maxint
    for block in blocks:
        mininum_lineno = min(_remove_redundant_nops(block), mininum_lineno)
    if mininum_lineno == sys.maxint:
        mininum_lineno = 1
    return mininum_lineno

def _list_from_dict(d, offset=0):
    result = [None] * len(d)
    for obj, index in d.iteritems():
        result[index - offset] = obj
    return result


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


def _debug_print_blocks(blocks):
    labels = {block: i for (i, block) in enumerate(blocks)}
    for block in blocks:
        print "L%s:" % labels[block]
        for instruction in block.instructions:
            print instruction
