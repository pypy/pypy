from pypy.rlib import jit


@jit.unroll_safe
def product(s):
    i = 1
    for x in s:
        i *= x
    return i
