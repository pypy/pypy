import autopath
from pypy.lang.scheme.object import *

def mul(ctx, args_lst):
    acc = 1
    for arg in args_lst:
        acc *= arg.to_number()

    if isinstance(acc, int):
        return W_Fixnum(acc)
    else:
        return W_Float(acc)

def add(ctx, args_lst):
    acc = 0
    for arg in args_lst:
        acc += arg.to_number()

    if isinstance(acc, int):
        return W_Fixnum(acc)
    else:
        return W_Float(acc)


