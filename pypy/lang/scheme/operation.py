import autopath
from pypy.lang.scheme.object import *

def mul(ctx, args_lst):
    acc = 1
    for arg in args_lst:
        acc *= arg.to_number()

    return W_Fixnum(acc)

def add(ctx, args_lst):
    acc = 0
    for arg in args_lst:
        acc += arg.to_number()

    return W_Fixnum(acc)


