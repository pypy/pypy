import struct

from hypothesis.stateful import rule, precondition

class ByteCode(object):
    def encode(self, ctx):
        ctx.append_byte(self.BYTE_CODE)

    @classmethod
    def splits_control_flow(self):
        return False

    @classmethod
    def filter_bytecode(self, stack):
        """ filter this byte code if the stack does
            not contain the right values on the stack.
            This should only be used for values hypothesis
            cannot forsee (like list manipulation)
        """
        required_types = self._stack_types
        if len(required_types) > stack.size():
            # more needed types than available
            return False
        # each type should match the stack entry
        for i in range(len(required_types)):
            item = stack.peek(i)
            j = len(required_types) - i - 1
            rt = required_types[j]
            if not item.is_of_type(rt):
                return False
        return True

    def __repr__(self):
        name = self.__class__.__name__
        return name

_c = 0

LIST_TYP = 'l'
INT_TYP = 'i'
OBJ_TYP = 'o'
STR_TYP = 's'
VAL_TYP = 'v' # either one of the earlier

all_types = [INT_TYP, LIST_TYP, STR_TYP] # TODO OBJ_TYP

SHORT_TYP = 'h'
BYTE_TYP = 'b'
COND_TYP = 'c'
IDX_TYP = 'x'


def unique_code():
    global _c
    v = _c
    _c = v + 1
    return v

class Context(object):
    def __init__(self):
        self.consts = {}
        self.const_idx = 0
        self.bytecode = []

    def append_byte(self, byte):
        self.bytecode.append(('b', byte))

    def get_byte(self, i):
        typ, byte = self.bytecode[i]
        assert typ == 'b'
        return byte

    def get_short(self, i):
        typ, int = self.bytecode[i]
        assert typ == 'h'
        return int

    def append_short(self, byte):
        self.bytecode.append(('h', byte))

    def append_int(self, byte):
        self.bytecode.append(('i', byte))

    def const_str(self, str):
        self.consts[self.const_idx] = str
        self.append_short(self.const_idx)
        self.const_idx += 1

    def to_string(self):
        code = []
        for typ, nmr in self.bytecode:
            code.append(struct.pack(typ, nmr))
        return ''.join(code)

    def transform_blocks(self, blocks):
        for block in blocks:
            for code_obj in block.opcodes:
                code_obj.encode(self)
        return self.to_string(), self.consts

    def transform(self, code_objs):
        for code_obj in code_objs:
            code_obj.encode(self)

        return self.to_string(), self.consts


def requires_stack(*types):
    def method(clazz):
        clazz._stack_types = tuple(types)
        return clazz
    return method

def leaves_on_stack(*types):
    def method(clazz):
        clazz._return_on_stack_types = tuple(types)
        return clazz
    return method


def requires_param(*types):
    def method(m):
        m._param_types = tuple(types)
        return m
    return method

@requires_stack()
@leaves_on_stack(INT_TYP)
class PutInt(ByteCode):
    BYTE_CODE = unique_code()
    @requires_param(INT_TYP)
    def __init__(self, value):
        self.integral = value
    def encode(self, ctx):
        ctx.append_byte(self.BYTE_CODE)
        ctx.append_int(self.integral)

@requires_stack(INT_TYP, INT_TYP)
@leaves_on_stack(INT_TYP)
class CompareInt(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self):
        pass

@requires_stack()
@leaves_on_stack(STR_TYP)
class LoadStr(ByteCode):
    BYTE_CODE = unique_code()
    @requires_param(STR_TYP)
    def __init__(self, string):
        self.string = string
    def encode(self, ctx):
        ctx.append_byte(self.BYTE_CODE)
        ctx.const_str(self.string)

@requires_stack(STR_TYP, STR_TYP)
@leaves_on_stack(STR_TYP)
class AddStr(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self):
        pass

@requires_stack(LIST_TYP, LIST_TYP)
@leaves_on_stack(LIST_TYP)
class AddList(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self):
        pass

@requires_stack()
@leaves_on_stack(LIST_TYP)
class CreateList(ByteCode):
    BYTE_CODE = unique_code()
    @requires_param(BYTE_TYP)
    def __init__(self, size=8):
        self.size = size

    def encode(self, ctx):
        ctx.append_byte(self.BYTE_CODE)
        ctx.append_short(self.size)

@requires_stack(LIST_TYP, IDX_TYP, INT_TYP) # TODO VAL_TYP
@leaves_on_stack(LIST_TYP)
class InsertList(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self):
        pass
    @classmethod
    def filter_bytecode(self, stack):
        if not ByteCode.filter_bytecode.im_func(self, stack):
            return False
        w_idx = stack.peek(1)
        w_list = stack.peek(2)
        if w_idx.value >= len(w_list.items) or \
           w_idx.value < 0:
            return False
        return True

@requires_stack(LIST_TYP, IDX_TYP)
@leaves_on_stack(LIST_TYP)
class DelList(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self):
        pass
    @classmethod
    def filter_bytecode(self, stack):
        if not ByteCode.filter_bytecode.im_func(self, stack):
            return False
        w_idx = stack.peek(0)
        w_list = stack.peek(1)
        if w_idx.value >= len(w_list.items) or \
           w_idx.value < 0:
            return False
        return True

@requires_stack(LIST_TYP, INT_TYP) # TODO VAL_TYP)
@leaves_on_stack(LIST_TYP)
class AppendList(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self):
        pass

@requires_stack(INT_TYP)
@leaves_on_stack()
class CondJump(ByteCode):
    BYTE_CODE = unique_code()

    COND_EQ = 0
    COND_LT = 1
    COND_GT = 2
    COND_LE = 3
    COND_GE = 4
    COND_ANY = 5

    @requires_param(COND_TYP, INT_TYP)
    def __init__(self, cond, offset):
        self.cond = cond
        self.offset = offset

    def encode(self, ctx):
        ctx.append_byte(self.BYTE_CODE)
        ctx.append_byte(self.cond)
        ctx.append_int(self.offset)

    def splits_control_flow(self):
        return True

    @staticmethod
    def should_jump(cond, value):
        # TODO
        if value == 0 and cond == 0:
            return True
        return False


@requires_stack(LIST_TYP)
@leaves_on_stack(LIST_TYP, INT_TYP)
class LenList(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self):
        pass


#@requires_stack(INT_TYP) # TODO VAL_TYP)
#@leaves_on_stack()
#class ReturnFrame(ByteCode):
#    BYTE_CODE = unique_code()
#    def __init__(self):
#        pass
#

BC_CLASSES = []
BC_NUM_TO_CLASS = {}

for name, clazz in locals().items():
    if hasattr(clazz, 'BYTE_CODE'):
        BC_CLASSES.append(clazz)
        assert clazz.BYTE_CODE not in BC_NUM_TO_CLASS
        BC_NUM_TO_CLASS[clazz.BYTE_CODE] = clazz

BC_CLASSES.remove(CondJump)

# control flow byte codes
BC_CF_CLASSES = [CondJump]

class ByteCodeBlock(object):
    def __init__(self, stack):
        self.init_stack = stack.copy()
        self.exit_stack = None
        self.opcodes = []

    def interp_steps(self):
        return len(self.opcodes)

class ByteCodeControlFlow(object):
    # see the deterministic control flow search startegy in
    # test/code_strategies.py for what steps & byte_codes mean
    def __init__(self):
        self.blocks = []
        self.steps = 0
        self.byte_codes = 0

    def interp_steps(self):
        """ how many steps does the interpreter perform to
            reach the end of the current control flow?
        """
        return self.steps

    def linearize(self):
        from rpython.jit.backend.llsupport.tl import code
        ctx = code.Context()
        bytecode, consts = ctx.transform_blocks(self.blocks)
        return bytecode, consts

    def generate_block(self, data, last_block, strat):
        if last_block:
            stack = last_block.init_stack
        else:
            from rpython.jit.backend.llsupport.tl.stack import Stack
            stack = Stack(0)

        bcb = ByteCodeBlock(stack)
        opcodes = data.draw(strat.draw_from(stack, self))
        if not opcodes:
            return None
        bcb.exit_stack = stack.copy()
        bcb.opcodes = opcodes
        self.steps += bcb.interp_steps()
        self.byte_codes += len(opcodes)
        self.blocks.append(bcb)
        return bcb


