from pypy.objspace import dummy
from pypy.interpreter.pycode import PyCode

# __________  Entry point  __________

def entry_point(code, w_loc):
    code2 = PyCode(space)
    code2 = code2._from_code(code)
    code2.exec_code(space, space.wrap({}), w_loc)

# _____ Define and setup target _____

def target():
    global space
    space = dummy.DummyObjSpace()

    from pypy.interpreter import pycode

    pycode.setup_frame_classes()

    from pypy.interpreter import pyopcode

    # cheat
    space._gatewaycache.content[pyopcode.app] =  space.newdict([])

    return entry_point,[object, dummy.W_Obj]

# _____ Run translated _____

def run(c_entry_point):
    w_result = c_entry_point(compile("a+b","<stuff>","eval"),dummy.W_Obj())
    print w_result

