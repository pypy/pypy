"""Python control flow graph generation and bytecode assembly."""

import os
from rpython.rlib import rfloat
from rpython.rlib.objectmodel import specialize, we_are_translated

from pypy.interpreter.astcompiler import ast, consts, misc, symtable
from pypy.interpreter.error import OperationError
from pypy.interpreter.pycode import PyCode
from pypy.tool import stdlib_opcode as ops


class StackDepthComputationError(Exception):
    pass


class Instruction(object):
    """Represents a single opcode."""

    def __init__(self, opcode, arg=0):
        self.opcode = opcode
        self.arg = arg
        self.lineno = 0
        self.has_jump = False

    def size(self):
        """Return the size of bytes of this instruction when it is
        encoded.
        """
        if self.opcode >= ops.HAVE_ARGUMENT:
            return (6 if self.arg > 0xFFFF else 3)
        return 1

    def jump_to(self, target, absolute=False):
        """Indicate the target this jump instruction.

        The opcode must be a JUMP opcode.
        """
        self.jump = (target, absolute)
        self.has_jump = True

    def __repr__(self):
        data = [ops.opname[self.opcode]]
        template = "<%s"
        if self.opcode >= ops.HAVE_ARGUMENT:
            data.append(self.arg)
            template += " %i"
            if self.has_jump:
                data.append(self.jump[0])
                template += " %s"
        template += ">"
        return template % tuple(data)


class Block(object):
    """A basic control flow block.

    It has one entry point and several possible exit points.  Its
    instructions may be jumps to other blocks, or if control flow
    reaches the end of the block, it continues to next_block.
    """

    marked = False
    have_return = False
    auto_inserted_return = False

    def __init__(self):
        self.instructions = []
        self.next_block = None

    def _post_order_see(self, stack, nextblock):
        if nextblock.marked == 0:
            nextblock.marked = 1
            stack.append(nextblock)

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
                    self._post_order_see(stack, current.next_block)
            else:
                i = current.marked - 2
                assert i >= 0
                while i < len(current.instructions):
                    instr = current.instructions[i]
                    i += 1
                    if instr.has_jump:
                        current.marked = i + 2
                        self._post_order_see(stack, instr.jump[0])
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

    def get_code(self):
        """Encode the instructions in this block into bytecode."""
        code = []
        for instr in self.instructions:
            opcode = instr.opcode
            if opcode >= ops.HAVE_ARGUMENT:
                arg = instr.arg
                if instr.arg > 0xFFFF:
                    ext = arg >> 16
                    code.append(chr(ops.EXTENDED_ARG))
                    code.append(chr(ext & 0xFF))
                    code.append(chr(ext >> 8))
                    arg &= 0xFFFF
                code.append(chr(opcode))
                code.append(chr(arg & 0xFF))
                code.append(chr(arg >> 8))
            else:
                code.append(chr(opcode))
        return ''.join(code)


def _make_index_dict_filter(syms, flag1, flag2):
    i = 0
    result = {}
    for name, scope in syms.iteritems():
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
        self.use_block(self.first_block)
        self.names = {}
        self.var_names = _iter_to_dict(scope.varnames)
        self.cell_vars = _make_index_dict_filter(scope.symbols,
                                                 symtable.SCOPE_CELL,
                                                 symtable.SCOPE_CELL_CLASS)
        self.free_vars = _iter_to_dict(scope.free_vars, len(self.cell_vars))
        self.w_consts = space.newdict()
        self.argcount = 0
        self.kwonlyargcount = 0
        self.lineno_set = False
        self.lineno = 0
        self.add_none_to_final_return = True

    def new_block(self):
        return Block()

    def use_block(self, block):
        """Start emitting bytecode into block."""
        self.current_block = block
        self.instrs = block.instructions

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
        # currently only True after a RETURN_VALUE.
        return self.current_block.have_return

    def emit_op(self, op):
        """Emit an opcode without an argument."""
        instr = Instruction(op)
        if not self.lineno_set:
            instr.lineno = self.lineno
            self.lineno_set = True
        if not self.is_dead_code():
            self.instrs.append(instr)
            if op == ops.RETURN_VALUE:
                self.current_block.have_return = True
        return instr

    def emit_op_arg(self, op, arg):
        """Emit an opcode with an integer argument."""
        instr = Instruction(op, arg)
        if not self.lineno_set:
            instr.lineno = self.lineno
            self.lineno_set = True
        if not self.is_dead_code():
            self.instrs.append(instr)

    def emit_op_name(self, op, container, name):
        """Emit an opcode referencing a name."""
        self.emit_op_arg(op, self.add_name(container, name))

    def emit_jump(self, op, block_to, absolute=False):
        """Emit a jump opcode to another block."""
        self.emit_op(op).jump_to(block_to, absolute)

    def add_name(self, container, name):
        """Get the index of a name in container."""
        name = self.scope.mangle(name)
        try:
            index = container[name]
        except KeyError:
            index = len(container)
            container[name] = index
        return index

    def add_const(self, obj):
        """Add a W_Root to the constant array and return its location."""
        space = self.space
        # To avoid confusing equal but separate types, we hash store the type
        # of the constant in the dictionary.  Moreover, we have to keep the
        # difference between -0.0 and 0.0 floats, and this recursively in
        # tuples.
        w_key = self._make_key(obj)

        w_len = space.finditem(self.w_consts, w_key)
        if w_len is None:
            w_len = space.len(self.w_consts)
            space.setitem(self.w_consts, w_key, w_len)
        if space.int_w(w_len) == 0:
            self.scope.doc_removable = False
        return space.int_w(w_len)

    def _make_key(self, obj):
        # see the tests 'test_zeros_not_mixed*' in ../test/test_compiler.py
        space = self.space
        w_type = space.type(obj)
        if space.is_w(w_type, space.w_float):
            val = space.float_w(obj)
            if val == 0.0 and rfloat.copysign(1., val) < 0:
                w_key = space.newtuple([obj, space.w_float, space.w_None])
            else:
                w_key = space.newtuple([obj, space.w_float])
        elif space.is_w(w_type, space.w_complex):
            w_real = space.getattr(obj, space.wrap("real"))
            w_imag = space.getattr(obj, space.wrap("imag"))
            real = space.float_w(w_real)
            imag = space.float_w(w_imag)
            real_negzero = (real == 0.0 and
                            rfloat.copysign(1., real) < 0)
            imag_negzero = (imag == 0.0 and
                            rfloat.copysign(1., imag) < 0)
            if real_negzero and imag_negzero:
                tup = [obj, space.w_complex, space.w_None, space.w_None,
                       space.w_None]
            elif imag_negzero:
                tup = [obj, space.w_complex, space.w_None, space.w_None]
            elif real_negzero:
                tup = [obj, space.w_complex, space.w_None]
            else:
                tup = [obj, space.w_complex]
            w_key = space.newtuple(tup)
        elif space.is_w(w_type, space.w_tuple):
            result_w = [obj, w_type]
            for w_item in space.fixedview(obj):
                result_w.append(self._make_key(w_item))
            w_key = space.newtuple(result_w[:])
        elif isinstance(obj, PyCode):
            w_key = space.newtuple([obj, w_type, space.id(obj)])
        else:
            w_key = space.newtuple([obj, w_type])
        return w_key

    def load_const(self, obj):
        index = self.add_const(obj)
        self.emit_op_arg(ops.LOAD_CONST, index)

    def update_position(self, lineno, force=False):
        """Possibly change the lineno for the next instructions."""
        if force or lineno > self.lineno:
            self.lineno = lineno
            self.lineno_set = False

    def _resolve_block_targets(self, blocks):
        """Compute the arguments of jump instructions."""
        last_extended_arg_count = 0
        # The reason for this loop is extended jumps.  EXTENDED_ARG
        # extends the bytecode size, so it might invalidate the offsets
        # we've already given.  Thus we have to loop until the number of
        # extended args is stable.  Any extended jump at all is
        # extremely rare, so performance is not too concerning.
        while True:
            extended_arg_count = 0
            offset = 0
            force_redo = False
            # Calculate the code offset of each block.
            for block in blocks:
                block.offset = offset
                offset += block.code_size()
            for block in blocks:
                offset = block.offset
                for instr in block.instructions:
                    offset += instr.size()
                    if instr.has_jump:
                        target, absolute = instr.jump
                        op = instr.opcode
                        # Optimize an unconditional jump going to another
                        # unconditional jump.
                        if op == ops.JUMP_ABSOLUTE or op == ops.JUMP_FORWARD:
                            if target.instructions:
                                target_op = target.instructions[0].opcode
                                if target_op == ops.JUMP_ABSOLUTE:
                                    target = target.instructions[0].jump[0]
                                    instr.opcode = ops.JUMP_ABSOLUTE
                                    absolute = True
                                elif target_op == ops.RETURN_VALUE:
                                    # Replace JUMP_* to a RETURN into
                                    # just a RETURN
                                    instr.opcode = ops.RETURN_VALUE
                                    instr.arg = 0
                                    instr.has_jump = False
                                    # The size of the code changed,
                                    # we have to trigger another pass
                                    force_redo = True
                                    continue
                        if absolute:
                            jump_arg = target.offset
                        else:
                            jump_arg = target.offset - offset
                        instr.arg = jump_arg
                        if jump_arg > 0xFFFF:
                            extended_arg_count += 1
            if (extended_arg_count == last_extended_arg_count and
                not force_redo):
                break
            else:
                last_extended_arg_count = extended_arg_count

    def _build_consts_array(self):
        """Turn the applevel constants dictionary into a list."""
        w_consts = self.w_consts
        space = self.space
        consts_w = [space.w_None] * space.len_w(w_consts)
        w_iter = space.iter(w_consts)
        first = space.wrap(0)
        while True:
            try:
                w_key = space.next(w_iter)
            except OperationError as e:
                if not e.match(space, space.w_StopIteration):
                    raise
                break
            w_index = space.getitem(w_consts, w_key)
            w_constant = space.getitem(w_key, first)
            w_constant = misc.intern_if_common_string(space, w_constant)
            consts_w[space.int_w(w_index)] = w_constant
        return consts_w

    def _get_code_flags(self):
        """Get an extra flags that should be attached to the code object."""
        raise NotImplementedError

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
            depth = self._do_stack_depth_walk(block)
            if block.auto_inserted_return and depth != 0:
                # This case occurs if this code object uses some
                # construction for which the stack depth computation
                # is wrong (too high).  If you get here while working
                # on the astcompiler, then you should at first ignore
                # the error, and comment out the 'raise' below.  Such
                # an error is not really bad: it is just a bit
                # wasteful.  For release-ready versions, though, we'd
                # like not to be wasteful. :-)
                os.write(2, "StackDepthComputationError(POS) in %s at %s:%s\n"
                  % (self.compile_info.filename, self.name, self.first_lineno))
                raise StackDepthComputationError   # would-be-nice-not-to-have
        return self._max_depth

    def _next_stack_depth_walk(self, nextblock, depth):
        if depth > nextblock.initial_depth:
            nextblock.initial_depth = depth

    def _do_stack_depth_walk(self, block):
        depth = block.initial_depth
        if depth == -99:     # this block is never reached, skip
             return 0
        for instr in block.instructions:
            depth += _opcode_stack_effect(instr.opcode, instr.arg)
            if depth < 0:
                # This is really a fatal error, don't comment out this
                # 'raise'.  It means that the stack depth computation
                # thinks there is a path that yields a negative stack
                # depth, which means that it underestimates the space
                # needed and it would crash when interpreting this
                # code.
                os.write(2, "StackDepthComputationError(NEG) in %s at %s:%s\n"
                  % (self.compile_info.filename, self.name, self.first_lineno))
                raise StackDepthComputationError   # really fatal error
            if depth >= self._max_depth:
                self._max_depth = depth
            jump_op = instr.opcode
            if instr.has_jump:
                target_depth = depth
                if jump_op == ops.FOR_ITER:
                    target_depth -= 2
                elif (jump_op == ops.SETUP_FINALLY or
                      jump_op == ops.SETUP_EXCEPT or
                      jump_op == ops.SETUP_WITH or
                      jump_op == ops.SETUP_ASYNC_WITH):
                    if jump_op == ops.SETUP_FINALLY:
                        target_depth += 4
                    elif jump_op == ops.SETUP_EXCEPT:
                        target_depth += 4
                    elif jump_op == ops.SETUP_WITH:
                        target_depth += 3
                    elif jump_op == ops.SETUP_ASYNC_WITH:
                        target_depth += 3
                    if target_depth > self._max_depth:
                        self._max_depth = target_depth
                elif (jump_op == ops.JUMP_IF_TRUE_OR_POP or
                      jump_op == ops.JUMP_IF_FALSE_OR_POP):
                    depth -= 1
                self._next_stack_depth_walk(instr.jump[0], target_depth)
                if jump_op == ops.JUMP_ABSOLUTE or jump_op == ops.JUMP_FORWARD:
                    # Nothing more can occur.
                    break
            elif jump_op == ops.RETURN_VALUE or jump_op == ops.RAISE_VARARGS:
                # Nothing more can occur.
                break
        else:
            if block.next_block:
                self._next_stack_depth_walk(block.next_block, depth)
        return depth

    def _build_lnotab(self, blocks):
        """Build the line number table for tracebacks and tracing."""
        current_line = self.first_lineno
        current_off = 0
        table = []
        push = table.append
        for block in blocks:
            offset = block.offset
            for instr in block.instructions:
                if instr.lineno:
                    # compute deltas
                    line = instr.lineno - current_line
                    if line < 0:
                        continue
                    addr = offset - current_off
                    # Python assumes that lineno always increases with
                    # increasing bytecode address (lnotab is unsigned
                    # char).  Depending on when SET_LINENO instructions
                    # are emitted this is not always true.  Consider the
                    # code:
                    #     a = (1,
                    #          b)
                    # In the bytecode stream, the assignment to "a"
                    # occurs after the loading of "b".  This works with
                    # the C Python compiler because it only generates a
                    # SET_LINENO instruction for the assignment.
                    if line or addr:
                        while addr > 255:
                            push(chr(255))
                            push(chr(0))
                            addr -= 255
                        while line > 255:
                            push(chr(addr))
                            push(chr(255))
                            line -= 255
                            addr = 0
                        push(chr(addr))
                        push(chr(line))
                        current_line = instr.lineno
                        current_off = offset
                offset += instr.size()
        return ''.join(table)

    def assemble(self):
        """Build a PyCode object."""
        # Unless it's interactive, every code object must end in a return.
        if not self.current_block.have_return:
            self.use_next_block()
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
        self._resolve_block_targets(blocks)
        lnotab = self._build_lnotab(blocks)
        stack_depth = self._stacksize(blocks)
        consts_w = self._build_consts_array()
        names = _list_from_dict(self.names)
        var_names = _list_from_dict(self.var_names)
        cell_names = _list_from_dict(self.cell_vars)
        free_names = _list_from_dict(self.free_vars, len(cell_names))
        flags = self._get_code_flags()
        # (Only) inherit compilerflags in PyCF_MASK
        flags |= (self.compile_info.flags & consts.PyCF_MASK)
        bytecode = ''.join([block.get_code() for block in blocks])
        return PyCode(self.space,
                      self.argcount,
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
    ops.DUP_TOP: 1,
    ops.DUP_TOP_TWO: 2,

    ops.UNARY_POSITIVE: 0,
    ops.UNARY_NEGATIVE: 0,
    ops.UNARY_NOT: 0,
    ops.UNARY_INVERT: 0,

    ops.LIST_APPEND: -1,
    ops.SET_ADD: -1,
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
    ops.BREAK_LOOP: 0,
    ops.CONTINUE_LOOP: 0,
    ops.SETUP_LOOP: 0,

    ops.PRINT_EXPR: -1,

    ops.WITH_CLEANUP_START: 0,
    ops.WITH_CLEANUP_FINISH: -1,
    ops.LOAD_BUILD_CLASS: 1,
    ops.POP_BLOCK: 0,
    ops.POP_EXCEPT: -1,
    ops.END_FINALLY: -4,     # assume always 4: we pretend that SETUP_FINALLY
                             # pushes 4.  In truth, it would only push 1 and
                             # the corresponding END_FINALLY only pops 1.
    ops.SETUP_WITH: 1,
    ops.SETUP_FINALLY: 0,
    ops.SETUP_EXCEPT: 0,

    ops.RETURN_VALUE: -1,
    ops.YIELD_VALUE: 0,
    ops.YIELD_FROM: -1,
    ops.COMPARE_OP: -1,

    ops.LOOKUP_METHOD: 1,

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

    ops.LOAD_CONST: 1,

    ops.IMPORT_STAR: -1,
    ops.IMPORT_NAME: -1,
    ops.IMPORT_FROM: 1,

    ops.JUMP_FORWARD: 0,
    ops.JUMP_ABSOLUTE: 0,
    ops.JUMP_IF_TRUE_OR_POP: 0,
    ops.JUMP_IF_FALSE_OR_POP: 0,
    ops.POP_JUMP_IF_TRUE: -1,
    ops.POP_JUMP_IF_FALSE: -1,
    ops.JUMP_IF_NOT_DEBUG: 0,

    # TODO
    ops.BUILD_LIST_FROM_ARG: 1,

    ops.LOAD_CLASSDEREF: 1,
}


def _compute_UNPACK_SEQUENCE(arg):
    return arg - 1

def _compute_UNPACK_EX(arg):
    return (arg & 0xFF) + (arg >> 8)

def _compute_BUILD_TUPLE(arg):
    return 1 - arg

def _compute_BUILD_TUPLE_UNPACK(arg):
    return 1 - arg

def _compute_BUILD_LIST(arg):
    return 1 - arg

def _compute_BUILD_LIST_UNPACK(arg):
    return 1 - arg

def _compute_BUILD_SET(arg):
    return 1 - arg

def _compute_BUILD_SET_UNPACK(arg):
    return 1 - arg

def _compute_BUILD_MAP(arg):
    return 1 - 2 * arg

def _compute_BUILD_MAP_UNPACK(arg):
    return 1 - arg

def _compute_BUILD_MAP_UNPACK_WITH_CALL(arg):
    return 1 - (arg & 0xFF)

def _compute_MAKE_CLOSURE(arg):
    return -2 - _num_args(arg) - ((arg >> 16) & 0xFFFF)

def _compute_MAKE_FUNCTION(arg):
    return -1 - _num_args(arg) - ((arg >> 16) & 0xFFFF)

def _compute_BUILD_SLICE(arg):
    if arg == 3:
        return -2
    else:
        return -1

def _compute_RAISE_VARARGS(arg):
    return -arg

def _num_args(oparg):
    return (oparg % 256) + 2 * ((oparg // 256) % 256)

def _compute_CALL_FUNCTION(arg):
    return -_num_args(arg)

def _compute_CALL_FUNCTION_VAR(arg):
    return -_num_args(arg) - 1

def _compute_CALL_FUNCTION_KW(arg):
    return -_num_args(arg) - 1

def _compute_CALL_FUNCTION_VAR_KW(arg):
    return -_num_args(arg) - 2

def _compute_CALL_METHOD(arg):
    return -_num_args(arg) - 1

def _compute_FORMAT_VALUE(arg):
    if (arg & consts.FVS_MASK) == consts.FVS_HAVE_SPEC:
        return -1
    return 0

def _compute_BUILD_STRING(arg):
    return 1 - arg


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
            raise AssertionError("unknown opcode: %s" % (op,))
    else:
        try:
            return _static_opcode_stack_effects[op]
        except KeyError:
            try:
                return _stack_effect_computers[op](arg)
            except KeyError:
                raise KeyError("Unknown stack effect for %s (%s)" %
                               (ops.opname[op], op))
