from pypy.module._demo import demo
from pypy.objspace.cpy.ann_policy import CPyAnnotatorPolicy
from pypy.objspace.cpy.objspace import CPyObjSpace
import pypy.rpython.rctypes.implementation


space = CPyObjSpace()

def entry_point(n, w_callable):
    return demo.measuretime(space, n, w_callable)

# _____ Define and setup target ___

def target(*args):
    return entry_point, [int, CPyObjSpace.W_Object], CPyAnnotatorPolicy()


if __name__ == '__main__':
    import sys
    if len(sys.argv) <= 1:
        N = 500000
    else:
        N = int(sys.argv[1])
    print 'Timing for %d iterations...' % N
    print entry_point(N, space.W_Object(int)), 'seconds'
