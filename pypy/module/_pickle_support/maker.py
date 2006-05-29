from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.function import Function, Method
from pypy.interpreter.module import Module
from pypy.rpython.objectmodel import instantiate
from pypy.interpreter.argument import Arguments
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.objspace.std.dicttype import dictiter_typedef
from pypy.objspace.std.iterobject import W_SeqIterObject


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

def module_new(space, w_name, w_dict):
    new_mod = Module(space, w_name, w_dict)
    return space.wrap(new_mod)

def method_new(space, __args__):
    w_type = space.gettypeobject(Method.typedef)
    return space.call_args(w_type, __args__)
method_new.unwrap_spec = [ObjSpace, Arguments]

def dictiter_surrogate_new(space, w_lis):
    # we got a listobject.
    # simply create an iterator and that's it.
    return space.iter(w_lis)
dictiter_surrogate_new.unwrap_spec = [ObjSpace, W_Root]

def seqiter_new(space, w_seq, w_index):
    return W_SeqIterObject(w_seq, space.int_w(w_index))
