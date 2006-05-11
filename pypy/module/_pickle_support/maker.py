from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.function import Function, Method
from pypy.interpreter.module import Module
from pypy.rpython.objectmodel import instantiate
from pypy.interpreter.argument import Arguments
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.objspace.std.dicttype import dictiter_typedef
from pypy.objspace.std.itertype import iter_typedef as seqiter_typedef


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

#XXX this does not work yet
def dictiter_new(space, w_dictitertype, __args__):
    print "dictiter_new here 1)", space, w_dictitertype
    #w_type = space.gettypeobject(dictiter_typedef)
    #print "dictiter_new here 2)", w_type
    #a = space.call_args(w_type, __args__)
    #print "dictiter_new here 3)", a
    #return a
    from pypy.objspace.std.dictobject import W_DictIterObject
    w_obj = space.allocate_instance(W_DictIterObject, w_dictitertype)
    print "dictiter_new here 2)", w_obj
    W_DictIterObject.__init__(w_obj, space)
    print "dictiter_new here 3)", w_obj
    return w_obj
dictiter_new.unwrap_spec = [ObjSpace, W_Root, Arguments]

#XXX this doesn't work either
def seqiter_new(space, w_seqitertype, __args__):
    raise 'No seqiter_new (pickle support) yet'
    print "seqiter_new here 1)", space, __args__
    w_type = space.gettypeobject(seqiter_typedef)
    print "seqiter_new here 2)", w_type
    a = space.call_args(w_type, __args__)
    print "seqiter_new here 3)", a
    return a
seqiter_new.unwrap_spec = [ObjSpace, W_Root, Arguments]
