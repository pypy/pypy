import buildcache2
from pypy.objspace.std.objspace import StdObjSpace, W_Object
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std import stdtypedef

# __________  Entry point  __________

def entry_point():
    w_a = W_IntObject(space, -6)
    w_b = W_IntObject(space, -7)
    return mmentrypoint(space, w_a, w_b)

# _____ Define and setup target _____
def target():
    global space, mmentrypoint
    # disable translation of the whole of classobjinterp.py
    StdObjSpace.setup_old_style_classes = lambda self: None
    space = StdObjSpace()
    # call cache filling code
    buildcache2.buildcache(space)

    # ------------------------------------------------------------
    name = 'mul'
    mm = space.MM.mul
    exprargs, expr, miniglobals, fallback = (
        mm.install_not_sliced(space.model.typeorder, baked_perform_call=False))
    func = stdtypedef.make_perform_trampoline('__mm_'+name,
                                              exprargs, expr, miniglobals,
                                              mm)
    mmentrypoint = func
    # ------------------------------------------------------------

    # further call the entry_point once to trigger building remaining
    # caches (as far as analyzing the entry_point is concerned)
    entry_point()

    return entry_point, []

# _____ Run translated _____

def run(c_entry_point):
    w_result = c_entry_point()
    print w_result
    print w_result.intval
    assert w_result.intval == 42
