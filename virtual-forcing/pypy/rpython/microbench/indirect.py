from pypy.rpython.microbench.microbench import MetaBench

def f1(x):
    return x

def f2(x):
    return x+1

def f3(x):
    return x+2

def f4(x):
    return x+3

FUNCS = [f1, f2, f3, f4]

class indirect__call:
    __metaclass__ = MetaBench

    def init():
        return FUNCS
    args = ['obj', 'i']
    def loop(obj, i):
        return obj[i%4](i)
