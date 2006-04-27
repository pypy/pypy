from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.function import Function
from pypy.rpython.objectmodel import instantiate
from pypy.interpreter.argument import Arguments
from pypy.interpreter.baseobjspace import ObjSpace


#note: for now we don't use the actual value when creating the Cell.
#      (i.e. we assume it will be handled by __setstate__)
#      Stackless does use this so it might be needed here as well.

def cell_new(space):
    return space.wrap(instantiate(Cell))

def code_new(space, __args__):
    w_type = space.gettypeobject(PyCode.typedef)
    return space.call_args(w_type, __args__)
code_new.unwrap_spec = [ObjSpace, Arguments]

def func_new(space, __args__):
    w_type = space.gettypeobject(Function.typedef)
    return space.call_args(w_type, __args__)
func_new.unwrap_spec = [ObjSpace, Arguments]
