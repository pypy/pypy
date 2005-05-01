import buildcache2
from pypy.objspace.std.objspace import StdObjSpace, W_Object
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std import stdtypedef

# __________  Entry point  __________

def entry_point():
    w_a = W_IntObject(space, -7)
    w_b = W_IntObject(space, -6)
    ret_mul = mmentrypoints["mul"](space, w_a, w_b)
    ret_add = mmentrypoints["add"](space, w_a, w_b)
    ret_sub = mmentrypoints["sub"](space, w_a, w_b)
    return ret_mul, ret_add, ret_sub

# _____ Define and setup target _____
def target():
    global space, mmentrypoints
    # disable translation of the whole of classobjinterp.py
    StdObjSpace.setup_old_style_classes = lambda self: None
    space = StdObjSpace()
    # call cache filling code
    buildcache2.buildcache(space)

    # ------------------------------------------------------------
    mmentrypoints = {}
    for name in "mul add sub".split():
        mm = getattr(space.MM, name)
        exprargs, expr, miniglobals, fallback = (
            mm.install_not_sliced(space.model.typeorder, baked_perform_call=False))
        func = stdtypedef.make_perform_trampoline('__mm_'+name,
                                                  exprargs, expr, miniglobals,
                                                  mm)
        mmentrypoints[name] = func
    # ------------------------------------------------------------

    # further call the entry_point once to trigger building remaining
    # caches (as far as analyzing the entry_point is concerned)
    entry_point()

    return entry_point, []

# _____ Run translated _____

def run(c_entry_point):
    res_w = c_entry_point()
    res = tuple([each.intval for each in res_w])
    print res
    assert res == (-7 * -6, -7 + -6, -7 - -6)
    