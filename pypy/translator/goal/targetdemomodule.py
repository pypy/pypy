from pypy.module._demo import Module, demo
from pypy.objspace.cpy.ann_policy import CPyAnnotatorPolicy
from pypy.objspace.cpy.objspace import CPyObjSpace
from pypy.objspace.cpy.wrappable import reraise
import pypy.rpython.rctypes.implementation
from pypy.interpreter.error import OperationError


space = CPyObjSpace()
module = Module(space, space.wrap('_demo'))
w_moduledict = module.getdict()

def __init__(mod):
    w_mod = CPyObjSpace.W_Object(mod)
    try:
##        space.appexec([w_mod, w_moduledict],
##            '''(mod, newdict):
##                   old = mod.__dict__.copy()
##                   mod.__dict__.clear()
##                   mod.__dict__['__rpython__'] = old
##                   for key in ['__name__', '__doc__', 'RPythonError']:
##                       if key in old:
##                           mod.__dict__[key] = old[key]
##                   mod.__dict__.update(newdict)
##            ''')

        # the same at interp-level:
        w_moddict = space.getattr(w_mod, space.wrap('__dict__'))
        w_old = space.call_method(w_moddict, 'copy')
        space.call_method(w_moddict, 'clear')
        space.setitem(w_moddict, space.wrap('__rpython__'), w_old)
        for key in ['__name__', '__doc__', 'RPythonError']:
            w_key = space.wrap(key)
            try:
                w1 = space.getitem(w_old, w_key)
            except OperationError:
                pass
            else:
                space.setitem(w_moddict, w_key, w1)
        space.call_method(w_moddict, 'update', w_moduledict)

    except OperationError, e:
        reraise(e)
__init__.allow_someobjects = True

# _____ Define and setup target ___

def target(driver, args):
    driver.extmod_name = '_demo'
    return __init__, [object], CPyAnnotatorPolicy(space)


if __name__ == '__main__':
    import sys
    if len(sys.argv) <= 1:
        N = 500000
    else:
        N = int(sys.argv[1])
    print 'Timing for %d iterations...' % N
    print demo.measuretime(space, N, space.W_Object(int)), 'seconds'
