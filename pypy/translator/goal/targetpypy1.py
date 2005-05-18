from pypy.objspace.std.objspace import StdObjSpace, W_Object
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std import stdtypedef

# __________  Entry point  __________

operations = "mul add sub div mod lshift rshift floordiv truediv ".split()

def entry_point():
    w_a = W_IntObject(space, -7)
    w_b = W_IntObject(space, 6)
    results_w = [mmentrypoints[op](space, w_a, w_b) for op in operations]
    return [space.unwrap(each) for each in resuls_w]

# flatten the above code, to get a nicer look
def make_flat_code():
    g = globals()
    # make globals constants from the operations
    code = """def entry_point():
    import sys
    w_a = W_IntObject(space, -7)
    # -sys.maxint-1 crashes: genc problem with OP_SUB and int constant
    # when implementing lshift_Long_Long and rshift__Long_Long
    w_b = W_IntObject(space,  6)
    results_w = []
    append = results_w.append
"""
    for op in operations:
        g["op_%s" % op] = mmentrypoints[op]
        line = "    append(op_%s(space, w_a, w_b))" % op
        code += line + '\n'
    code += "    return [space.unwrap(each) for each in results_w]\n"
    print code
    exec code in g
    
# _____ Define and setup target _____
def target():
    global space, mmentrypoints
    # disable translation of the whole of classobjinterp.py
    StdObjSpace.setup_old_style_classes = lambda self: None
    space = StdObjSpace()
    # call cache filling code *not* needed here

    # ------------------------------------------------------------
    mmentrypoints = {}
    for name in operations:
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
    make_flat_code()
    entry_point()

    return entry_point, []

# _____ Run translated _____

def run(c_entry_point):
    res = c_entry_point()
    print res
    import operator
    assert res == [getattr(operator, name)(-7, 6) for name in operations]

if __name__ == "__main__":
    # just run it without translation
    target()
    run(entry_point)
    