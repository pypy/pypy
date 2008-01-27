import py, os
from pypy.rlib.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.rarithmetic import intmask
from pypy.jit.codegen.model import GenVar, GenConst
from pypy.jit.codegen.llvm.logger import logger
from pypy.jit.codegen.llvm.compatibility import i1, i8, i16, i32, f64


pi8  = i8  + '*'
pi32 = i32 + '*'
u32  = i32


class Count(object):
    n_vars = 0
    n_labels = 0

    def newlabel(self):
        label = 'L%d' % (self.n_labels,)
        self.n_labels += 1
        return label

count = Count()


class Var(GenVar):

    def __init__(self, type):
        self.n = count.n_vars
        self.type = type
        self.signed = type is i32 or type is f64
        count.n_vars += 1

    def operand(self):
        return '%s %s' % (self.type, self.operand2())

    def operand2(self):
        return '%%v%d' % (self.n,)


class GenericConst(GenConst):

    def operand(self):
        return '%s %s' % (self.type, self.operand2())

    @specialize.arg(1)
    def revealconst(self, T):
        if isinstance(T, lltype.Ptr):
            return lltype.cast_int_to_ptr(T, self.get_integer_value())
        elif T is llmemory.Address:
            return llmemory.cast_int_to_adr(self.get_integer_value())
        else:
            return lltype.cast_primitive(T, self.get_integer_value())


class BoolConst(GenericConst):
    type = i1
    signed = False

    def __init__(self, value):
        self.value = bool(value)

    def operand2(self):
        if self.value:
            return 'true'
        else:
            return 'false'

    def get_integer_value(self):
        return int(self.value)


class CharConst(GenericConst):
    type = i8
    signed = False

    def __init__(self, value):
        self.value = ord(value)

    def operand2(self):
        return '%d' % self.value

    def get_integer_value(self):
        return self.value


class UniCharConst(GenericConst):
    type = i32
    signed = True

    def __init__(self, value):
        self.value = unicode(value)

    def operand2(self):
        return '%s' % self.value

    def get_integer_value(self):
        return int(self.value)


class IntConst(GenericConst):
    type = i32
    signed = True

    def __init__(self, value):
        self.value = int(value)

    def operand2(self):
        return str(self.value)

    def get_integer_value(self):
        return self.value


class UIntConst(GenericConst):
    type = u32
    signed = False

    def __init__(self, value):
        self.value = value

    def operand2(self):
        return str(self.value)

    def get_integer_value(self):
        return intmask(self.value)


class FloatConst(GenericConst):
    type = f64
    signed = True

    def __init__(self, value):
        self.value = float(value)

    def operand2(self):
        return str(self.value)

    @specialize.arg(1)
    def revealconst(self, T):
        assert T is lltype.Float
        return self.value


class AddrConst(GenConst):
    type = pi8
    signed = False
    addr = llmemory.NULL #have 'addr' even when not instantiated

    def __init__(self, addr):
        self.addr = addr

    def operand(self):
        return '%s %s' % (self.type, self.operand2())

    def operand2(self):
        addr = self.addr
        s = str(llmemory.cast_adr_to_int(addr))
        if s == '0':
            s = 'null'
        return s

    @specialize.arg(1)
    def revealconst(self, T):
        if T is llmemory.Address:
            return self.addr
        elif isinstance(T, lltype.Ptr):
            return llmemory.cast_adr_to_ptr(self.addr, T)
        elif T is lltype.Signed:
            return llmemory.cast_adr_to_int(self.addr)
        else:
            msg = 'XXX not implemented'
            logger.dump(msg)
            assert 0, msg
