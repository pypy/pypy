
import struct

class ByteCode(object):
    def encode(self, ctx):
        ctx.append_byte(self.BYTE_CODE)

    @classmethod
    def create_from(self, draw, get_strategy_for):
        pt = getattr(self.__init__, '_param_types', [])
        return self(*[draw(get_strategy_for(t)) for t in pt])

_c = 0

LIST_TYP = 'l'
INT_TYP = 'i'
SHORT_TYP = 'h'
BYTE_TYP = 'b'
OBJ_TYP = 'o'
STR_TYP = 's'
COND_TYP = 'c'
VAL_TYP = 'v' # either one of the earlier

all_types = [INT_TYP, LIST_TYP, STR_TYP]


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


# remove comment one by one!

#@requires_stack()
#@leaves_on_stack(INT_TYP)
#class CondJump(ByteCode):
#    BYTE_CODE = unique_code()
#
#    COND_EQ = 0
#    COND_LT = 1
#    COND_GT = 2
#    COND_LE = 3
#    COND_GE = 4
#
#    @requires_param(COND_TYP)
#    def __init__(self, cond):
#        self.cond = cond
#
#    def encode(self, ctx):
#        ctx.append_byte(self.BYTE_CODE)
#        ctx.append_byte(self.cond)
#
#@requires_stack()
#@leaves_on_stack()
#class Jump(ByteCode):
#    BYTE_CODE = unique_code()
#    def __init__(self):
#        pass
#

#@requires_stack(LIST_TYP, INT_TYP, INT_TYP) # TODO VAL_TYP
#class InsertList(ByteCode):
#    BYTE_CODE = unique_code()
#    @requires_param(INT_TYP)
#    def __init__(self, index):
#        self.index = index
#    def encode(self, ctx):
#        ctx.append_byte(self.BYTE_CODE)
#        ctx.append_int(self.index)
#
#@requires_stack(LIST_TYP, INT_TYP)
#@leaves_on_stack(LIST_TYP)
#class DelList(ByteCode):
#    BYTE_CODE = unique_code()
#    @requires_param(INT_TYP)
#    def __init__(self, index):
#        self.index = index
#    def encode(self, ctx):
#        ctx.append_byte(self.BYTE_CODE)
#        ctx.append_int(self.index)
#
#@requires_stack(LIST_TYP, INT_TYP, INT_TYP) # TODO VAL_TYP)
#class AppendList(ByteCode):
#    BYTE_CODE = unique_code()
#    def __init__(self):
#        pass
#
#@requires_stack(LIST_TYP)
#@leaves_on_stack(LIST_TYP, INT_TYP)
#class LenList(ByteCode):
#    BYTE_CODE = unique_code()
#    def __init__(self):
#        pass
#
#
#@requires_stack(INT_TYP) # TODO VAL_TYP)
#@leaves_on_stack()
#class ReturnFrame(ByteCode):
#    BYTE_CODE = unique_code()
#    def __init__(self):
#        pass
#
