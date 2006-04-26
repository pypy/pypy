from pypy.module._demo import Module, demo
from pypy.objspace.cpy.ann_policy import CPyAnnotatorPolicy
from pypy.objspace.cpy.objspace import CPyObjSpace
import pypy.rpython.rctypes.implementation


space = CPyObjSpace()
Module.appleveldefs.clear()   # XXX! for now
module = Module(space, space.wrap('_demo'))
w_moduledict = module.getdict()

def getdict():
    return w_moduledict

# _____ Define and setup target ___

def target(*args):
    return getdict, [], CPyAnnotatorPolicy(space)


if __name__ == '__main__':
    import sys
    if len(sys.argv) <= 1:
        N = 500000
    else:
        N = int(sys.argv[1])
    print 'Timing for %d iterations...' % N
    print demo.measuretime(space, N, space.W_Object(int)), 'seconds'
