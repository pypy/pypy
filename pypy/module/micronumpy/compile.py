
""" This is a set of tools for standalone compiling of numpy expressions.
It should not be imported by the module itself
"""

from pypy.interpreter.baseobjspace import InternalSpaceCache, W_Root
from pypy.module.micronumpy.interp_dtype import W_Float64Dtype
from pypy.module.micronumpy.interp_numarray import Scalar, SingleDimArray, BaseArray
from pypy.rlib.objectmodel import specialize


class BogusBytecode(Exception):
    pass

def create_array(dtype, size):
    a = SingleDimArray(size, dtype=dtype)
    for i in range(size):
        dtype.setitem(a.storage, i, dtype.box(float(i % 10)))
    return a

class FakeSpace(object):
    w_ValueError = None
    w_TypeError = None

    def __init__(self):
        """NOT_RPYTHON"""
        self.fromcache = InternalSpaceCache(self).getorbuild

    def issequence_w(self, w_obj):
        return True

    @specialize.argtype(1)
    def wrap(self, obj):
        if isinstance(obj, float):
            return FloatObject(obj)
        elif isinstance(obj, bool):
            return BoolObject(obj)
        elif isinstance(obj, int):
            return IntObject(obj)
        raise Exception

    def float(self, w_obj):
        assert isinstance(w_obj, FloatObject)
        return w_obj

    def float_w(self, w_obj):
        return w_obj.floatval


class FloatObject(W_Root):
    def __init__(self, floatval):
        self.floatval = floatval

class BoolObject(W_Root):
    def __init__(self, boolval):
        self.boolval = boolval

class IntObject(W_Root):
    def __init__(self, intval):
        self.intval = intval


space = FakeSpace()

def numpy_compile(bytecode, array_size):
    stack = []
    i = 0
    dtype = space.fromcache(W_Float64Dtype)
    for b in bytecode:
        if b == 'a':
            stack.append(create_array(dtype, array_size))
            i += 1
        elif b == 'f':
            stack.append(Scalar(dtype, dtype.box(1.2)))
        elif b == '+':
            right = stack.pop()
            res = stack.pop().descr_add(space, right)
            assert isinstance(res, BaseArray)
            stack.append(res)
        elif b == '-':
            right = stack.pop()
            res = stack.pop().descr_sub(space, right)
            assert isinstance(res, BaseArray)
            stack.append(res)
        elif b == '*':
            right = stack.pop()
            res = stack.pop().descr_mul(space, right)
            assert isinstance(res, BaseArray)
            stack.append(res)
        elif b == '/':
            right = stack.pop()
            res = stack.pop().descr_div(space, right)
            assert isinstance(res, BaseArray)
            stack.append(res)
        elif b == '%':
            right = stack.pop()
            res = stack.pop().descr_mod(space, right)
            assert isinstance(res, BaseArray)
            stack.append(res)
        elif b == '|':
            res = stack.pop().descr_abs(space)
            assert isinstance(res, BaseArray)
            stack.append(res)
        else:
            print "Unknown opcode: %s" % b
            raise BogusBytecode()
    if len(stack) != 1:
        print "Bogus bytecode, uneven stack length"
        raise BogusBytecode()
    return stack[0]
