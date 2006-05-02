from pypy.module._demo import Module, demo
from pypy.objspace.cpy.ann_policy import CPyAnnotatorPolicy
from pypy.objspace.cpy.objspace import CPyObjSpace
import pypy.rpython.rctypes.implementation


space = CPyObjSpace()
module = Module(space, space.wrap('_demo'))
w_moduledict = module.getdict()

def __init__(mod):
    w_mod = CPyObjSpace.W_Object(mod)
    w_dict = space.getattr(w_mod, space.wrap('__dict__'))
    space.call_method(w_dict, 'update', w_moduledict)
__init__.allow_someobjects = True

# _____ Define and setup target ___

def target(driver, args):
    driver.exe_name = '_demo'
    return __init__, [object], CPyAnnotatorPolicy(space)


if __name__ == '__main__':
    import sys
    if len(sys.argv) <= 1:
        N = 500000
    else:
        N = int(sys.argv[1])
    print 'Timing for %d iterations...' % N
    print demo.measuretime(space, N, space.W_Object(int)), 'seconds'
