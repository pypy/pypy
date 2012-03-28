from pypy.rlib import jit


@jit.look_inside_iff(lambda s: jit.isconstant(len(s)))
def product(s):
    i = 1
    for x in s:
        i *= x
    return i