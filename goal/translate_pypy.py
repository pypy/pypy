#
#  
#

import autopath

from pypy.objspace.std.objspace import StdObjSpace, W_Object
from pypy.objspace.std.intobject import W_IntObject
from pypy.translator.translator import Translator


# __________  Entry point  __________

space = StdObjSpace()

def entry_point():
    w_a = W_IntObject(space, -6)
    w_b = W_IntObject(space, -7)
    return space.mul(w_a, w_b)


# __________  Main  __________

if __name__ == '__main__':
    t = Translator(entry_point, verbose=True, simplifying=True)
    try:
        a = t.annotate([])
        #a.simplify()
    except:
        import sys, traceback
        exc, val, tb = sys.exc_info()
        print >> sys.stderr
        traceback.print_exception(exc, val, tb)
        print >> sys.stderr
        import pdb
        pdb.post_mortem(tb)
