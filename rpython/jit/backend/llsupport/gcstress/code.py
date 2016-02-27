
import struct

class ByteCode(object):
    def encode(self, ctx):
        ctx.append_byte(self.BYTE_CODE)

_c = 0

LIST_TYP = 'l'
INT_TYP = 'i'
OBJ_TYP = 'o'
STR_TYP = 's'
VAL_TYP = 'v' # either one of the earlier

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

def requires_stack(*types):
    def method(clazz):
        clazz._stack_types = tuple(types)
        return clazz

    return method

@requires_stack()
class CondJump(ByteCode):
    BYTE_CODE = unique_code()

    COND_EQ = 0
    COND_LT = 1
    COND_GT = 2
    COND_LE = 3
    COND_GE = 4

    def __init__(self, cond):
        self.cond = cond
    def encode(self, ctx):
        ctx.append_byte(self.BYTE_CODE)
        ctx.append_byte(self.cond)

@requires_stack()
class Jump(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self):
        pass

@requires_stack()
class LoadStr(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self, string):
        self.string = string
    def encode(self, ctx):
        ctx.append_byte(self.BYTE_CODE)
        ctx.const_str(self.string)

@requires_stack(STR_TYP, STR_TYP)
class AddStr(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self):
        pass

@requires_stack(LIST_TYP, LIST_TYP)
class AddList(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self):
        pass

@requires_stack()
class CreateList(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self, size=8):
        self.size = size
    def encode(self, ctx):
        ctx.append_byte(self.BYTE_CODE)
        ctx.append_short(self.size)

@requires_stack()
class PutInt(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self, value):
        self.integral = value
    def encode(self, ctx):
        ctx.append_byte(self.BYTE_CODE)
        ctx.append_short(self.integral)

@requires_stack(LIST_TYP, INT_TYP, VAL_TYP)
class InsertList(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self, index):
        self.index = index
    def encode(self, ctx):
        ctx.append_byte(self.BYTE_CODE)
        ctx.append_int(self.index)

@requires_stack(LIST_TYP, INT_TYP)
class DelList(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self, index):
        self.index = index
    def encode(self, ctx):
        ctx.append_byte(self.BYTE_CODE)
        ctx.append_int(self.index)

@requires_stack(LIST_TYP, INT_TYP, VAL_TYP)
class AppendList(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self):
        pass

@requires_stack(LIST_TYP)
class LenList(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self):
        self.required_stack('l')

@requires_stack(INT_TYP, INT_TYP)
class CompareInt(ByteCode):
    BYTE_CODE = unique_code()
    def __init__(self):
        pass
