#
#  
#

import autopath

from pypy.objspace.std.objspace import StdObjSpace, W_Object
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.restricted_int import r_int
from pypy.translator.translator import Translator
from pypy.annotation import model as annmodel


# __________  Entry point  __________

space = StdObjSpace()

def entry_point():
    w_a = W_IntObject(space, -6)
    w_b = W_IntObject(space, -7)
    return space.mul(w_a, w_b)


# __________  Special cases  __________

def special_immutablevalue(x):
    if x is r_int:
        x = int
    return general_immutablevalue(x)

general_immutablevalue = annmodel.immutablevalue
annmodel.immutablevalue = special_immutablevalue

# __________  Main  __________

if __name__ == '__main__':
    # 2.3 specific
    import os
    os.putenv("PYTHONINSPECT", "1")

    t = Translator(entry_point, verbose=True)
    t.simplify()
    a = t.annotate([])
    a.simplify()
