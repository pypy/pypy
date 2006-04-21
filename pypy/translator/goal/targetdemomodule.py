from pypy.module._demo import demo
from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy
from pypy.rpython.rctypes.tool.cpyobjspace import CPyObjSpace
import pypy.rpython.rctypes.implementation


space = CPyObjSpace()

def entry_point(n, w_callable):
    return demo.measuretime(space, n, w_callable)

# _____ Define and setup target ___

def target(*args):
    return entry_point, [int, CPyObjSpace.W_Object], PyPyAnnotatorPolicy()


if __name__ == '__main__':
    import sys
    if len(sys.argv) <= 1:
        N = 500000
    else:
        N = int(sys.argv[1])
    print 'Timing for %d iterations...' % N
    print entry_point(N, int), 'seconds'
