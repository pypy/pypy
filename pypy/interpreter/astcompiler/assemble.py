"""
Python control flow graph generation and bytecode assembly.
"""

from pypy.interpreter.astcompiler import ast, symtable
from pypy.interpreter import pycode
from pypy.tool import stdlib_opcode as ops

from pypy.interpreter.error import OperationError
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib import rfloat


class Instruction(object):
    """Represents a single opcode."""

    def __init__(self, opcode, arg=0):
        self.opcode = opcode
        self.arg = arg
        self.lineno = 0
        self.has_jump = False

    def size(self):
        """Return the size of bytes of this instruction when it is encoded."""
        if self.opcode >= ops.HAVE_ARGUMENT:
            if self.arg > 0xFFFF:
                return 6
            else:
                return 3
        else:
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

    It has one entry point and several possible exit points.  Its instructions
    may be jumps to other blocks, or if control flow reaches the end of the
    block, it continues to next_block.
    """

    def __init__(self):
        self.instructions = []
        self.next_block = None
        self.marked = False
        self.have_return = False

    def _post_order(self, blocks):
        if self.marked:
            return
        self.marked = True
        if self.next_block is not None:
            self.next_block._post_order(blocks)
        for instr in self.instructions:
            if instr.has_jump:
                instr.jump[0]._post_order(blocks)
        blocks.append(self)
        self.marked = True

    def post_order(self):
        """Return this block and its children in post order."""
        blocks = []
        self._post_order(blocks)
        blocks.reverse()
        return blocks

    def code_size(self):
        """Return the encoded size of all the instructions in this block."""
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


def _make_index_dict_filter(syms, flag):
    i = 0
    result = {}
    for name, scope in syms.iteritems():
        if scope == flag:
            result[name] = i
            i += 1
    return result

def _list_to_dict(l, offset=0):
    result = {}
    index = offset
    for i in range(len(l)):
        result[l[i]] = index
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
        self.var_names = _list_to_dict(scope.varnames)
        self.cell_vars = _make_index_dict_filter(scope.symbols,
                                                 symtable.SCOPE_CELL)
        self.free_vars = _list_to_dict(scope.free_vars, len(self.cell_vars))
        self.w_consts = space.newdict()
        self.argcount = 0
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
        # The reason for this loop is extended jumps.  EXTENDED_ARG extends the
        # bytecode size, so it might invalidate the offsets we've already given.
        # Thus we have to loop until the number of extended args is stable.  Any
        # extended jump at all is extremely rare, so performance is not too
        # concerning.
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
                                    # Replace JUMP_* to a RETURN into just a RETURN
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
            if extended_arg_count == last_extended_arg_count and not force_redo:
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
            except OperationError, e:
                if not e.match(space, space.w_StopIteration):
                    raise
                break
            w_index = space.getitem(w_consts, w_key)
            consts_w[space.int_w(w_index)] = space.getitem(w_key, first)
        return consts_w

    def _get_code_flags(self):
        """Get an extra flags that should be attached to the code object."""
        raise NotImplementedError

    def _stacksize(self, blocks):
        """Compute co_stacksize."""
        for block in blocks:
            block.marked = False
            block.initial_depth = -1000
        return self._recursive_stack_depth_walk(blocks[0], 0, 0)

    def _recursive_stack_depth_walk(self, block, depth, max_depth):
        if block.marked or block.initial_depth >= depth:
            return max_depth
        block.marked = True
        block.initial_depth = depth
        done = False
        for instr in block.instructions:
            depth += _opcode_stack_effect(instr.opcode, instr.arg)
            if depth >= max_depth:
                max_depth = depth
            if instr.has_jump:
                target_depth = depth
                jump_op = instr.opcode
                if jump_op == ops.FOR_ITER:
                    target_depth -= 2
                elif (jump_op == ops.SETUP_FINALLY or
                      jump_op == ops.SETUP_EXCEPT or
                      jump_op == ops.SETUP_WITH):
                    target_depth += 3
                    if target_depth > max_depth:
                        max_depth = target_depth
                max_depth = self._recursive_stack_depth_walk(instr.jump[0],
                                                             target_depth,
                                                             max_depth)
                if jump_op == ops.JUMP_ABSOLUTE or jump_op == ops.JUMP_FORWARD:
                    # Nothing more can occur.
                    done = True
                    break
        if block.next_block and not done:
            max_depth = self._recursive_stack_depth_walk(block.next_block,
                                                         depth, max_depth)
        block.marked = False
        return max_depth

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
                    assert line >= 0
                    addr = offset - current_off
                    # Python assumes that lineno always increases with
                    # increasing bytecode address (lnotab is unsigned char).
                    # Depending on when SET_LINENO instructions are emitted this
                    # is not always true.  Consider the code:
                    #     a = (1,
                    #          b)
                    # In the bytecode stream, the assignment to "a" occurs after
                    # the loading of "b".  This works with the C Python compiler
                    # because it only generates a SET_LINENO instruction for the
                    # assignment.
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
        flags = self._get_code_flags() | self.compile_info.flags
        bytecode = ''.join([block.get_code() for block in blocks])
        return pycode.PyCode(self.space,
                             self.argcount,
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
    ops.NOP : 0,
    ops.STOP_CODE : 0,

    ops.POP_TOP : -1,
    ops.ROT_TWO : 0,
    ops.ROT_THREE : 0,
    ops.ROT_FOUR : 0,
    ops.DUP_TOP : 1,

    ops.UNARY_POSITIVE : 0,
    ops.UNARY_NEGATIVE : 0,
    ops.UNARY_NOT : 0,
    ops.UNARY_CONVERT : 0,
    ops.UNARY_INVERT : 0,

    ops.LIST_APPEND : -1,
    ops.SET_ADD : -1,
    ops.MAP_ADD : -2,
    ops.STORE_MAP : -2,

    ops.BINARY_POWER : -1,
    ops.BINARY_MULTIPLY : -1,
    ops.BINARY_DIVIDE : -1,
    ops.BINARY_MODULO : -1,
    ops.BINARY_ADD : -1,
    ops.BINARY_SUBTRACT : -1,
    ops.BINARY_SUBSCR : -1,
    ops.BINARY_FLOOR_DIVIDE : -1,
    ops.BINARY_TRUE_DIVIDE : -1,
    ops.BINARY_LSHIFT : -1,
    ops.BINARY_RSHIFT : -1,
    ops.BINARY_AND : -1,
    ops.BINARY_OR : -1,
    ops.BINARY_XOR : -1,

    ops.INPLACE_FLOOR_DIVIDE : -1,
    ops.INPLACE_TRUE_DIVIDE : -1,
    ops.INPLACE_ADD : -1,
    ops.INPLACE_SUBTRACT : -1,
    ops.INPLACE_MULTIPLY : -1,
    ops.INPLACE_DIVIDE : -1,
    ops.INPLACE_MODULO : -1,
    ops.INPLACE_POWER : -1,
    ops.INPLACE_LSHIFT : -1,
    ops.INPLACE_RSHIFT : -1,
    ops.INPLACE_AND : -1,
    ops.INPLACE_OR : -1,
    ops.INPLACE_XOR : -1,

    ops.SLICE+0 : 1,
    ops.SLICE+1 : 0,
    ops.SLICE+2 : 0,
    ops.SLICE+3 : -1,
    ops.STORE_SLICE+0 : -2,
    ops.STORE_SLICE+1 : -3,
    ops.STORE_SLICE+2 : -3,
    ops.STORE_SLICE+3 : -4,
    ops.DELETE_SLICE+0 : -1,
    ops.DELETE_SLICE+1 : -2,
    ops.DELETE_SLICE+2 : -2,
    ops.DELETE_SLICE+3 : -3,

    ops.STORE_SUBSCR : -2,
    ops.DELETE_SUBSCR : -2,

    ops.GET_ITER : 0,
    ops.FOR_ITER : 1,
    ops.BREAK_LOOP : 0,
    ops.CONTINUE_LOOP : 0,
    ops.SETUP_LOOP : 0,

    ops.PRINT_EXPR : -1,
    ops.PRINT_ITEM : -1,
    ops.PRINT_NEWLINE : 0,
    ops.PRINT_ITEM_TO : -2,
    ops.PRINT_NEWLINE_TO : -1,

    ops.WITH_CLEANUP : -1,
    ops.POP_BLOCK : 0,
    ops.END_FINALLY : -3,
    ops.SETUP_WITH : 1,
    ops.SETUP_FINALLY : 0,
    ops.SETUP_EXCEPT : 0,

    ops.LOAD_LOCALS : 1,
    ops.RETURN_VALUE : -1,
    ops.EXEC_STMT : -3,
    ops.YIELD_VALUE : 0,
    ops.BUILD_CLASS : -2,
    ops.BUILD_MAP : 1,
    ops.BUILD_SET : 1,
    ops.COMPARE_OP : -1,

    ops.LOOKUP_METHOD : 1,

    ops.LOAD_NAME : 1,
    ops.STORE_NAME : -1,
    ops.DELETE_NAME : 0,

    ops.LOAD_FAST : 1,
    ops.STORE_FAST : -1,
    ops.DELETE_FAST : 0,

    ops.LOAD_ATTR : 0,
    ops.STORE_ATTR : -2,
    ops.DELETE_ATTR : -1,

    ops.LOAD_GLOBAL : 1,
    ops.STORE_GLOBAL : -1,
    ops.DELETE_GLOBAL : 0,

    ops.LOAD_CLOSURE : 1,
    ops.LOAD_DEREF : 1,
    ops.STORE_DEREF : -1,

    ops.LOAD_CONST : 1,

    ops.IMPORT_STAR : -1,
    ops.IMPORT_NAME : -1,
    ops.IMPORT_FROM : 1,

    ops.JUMP_FORWARD : 0,
    ops.JUMP_ABSOLUTE : 0,
    ops.JUMP_IF_TRUE_OR_POP : 0,
    ops.JUMP_IF_FALSE_OR_POP : 0,
    ops.POP_JUMP_IF_TRUE : -1,
    ops.POP_JUMP_IF_FALSE : -1,
}


def _compute_UNPACK_SEQUENCE(arg):
    return arg + 1

def _compute_DUP_TOPX(arg):
    return arg

def _compute_BUILD_TUPLE(arg):
    return 1 - arg

def _compute_BUILD_LIST(arg):
    return 1 - arg

def _compute_MAKE_CLOSURE(arg):
    return -arg - 1

def _compute_MAKE_FUNCTION(arg):
    return -arg

def _compute_BUILD_SLICE(arg):
    if arg == 3:
        return -2
    else:
        return -1

def _compute_RAISE_VARARGS(arg):
    return -arg

def _num_args(oparg):
    return (oparg % 256) + 2 * (oparg / 256)

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
            return _stack_effect_computers[op](arg)
