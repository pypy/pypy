
""" This is a set of tools for standalone compiling of numpy expressions.
It should not be imported by the module itself
"""

from pypy.module.micronumpy.interp_numarray import FloatWrapper, SingleDimArray
from pypy.rlib.objectmodel import specialize

class BogusBytecode(Exception):
    pass

def create_array(size):
    a = SingleDimArray(size)
    for i in range(size):
        a.storage[i] = float(i % 10)
    return a

class TrivialSpace(object):
    w_ValueError = None

    @specialize.argtype(1)
    def wrap(self, w_obj):
        return w_obj


def numpy_compile(bytecode, array_size):
    space = TrivialSpace()
    stack = []
    i = 0
    for b in bytecode:
        if b == 'a':
            stack.append(create_array(array_size))
            i += 1
        elif b == 'f':
            stack.append(FloatWrapper(1.2))
        elif b == '+':
            right = stack.pop()
            stack.append(stack.pop().descr_add(space, right))
        elif b == '-':
            right = stack.pop()
            stack.append(stack.pop().descr_sub(space, right))
        elif b == '*':
            right = stack.pop()
            stack.append(stack.pop().descr_mul(space, right))
        elif b == '/':
            right = stack.pop()
            stack.append(stack.pop().descr_div(space, right))
        elif b == '%':
            right = stack.pop()
            stack.append(stack.pop().descr_mod(space, right))
        elif b == '|':
            stack.append(stack.pop().descr_abs(space))
        else:
            print "Unknown opcode: %s" % b
            raise BogusBytecode()
    if len(stack) != 1:
        print "Bogus bytecode, uneven stack length"
        raise BogusBytecode()
    return stack[0]
