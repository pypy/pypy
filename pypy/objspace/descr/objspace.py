from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import *


class DescrObjSpace(ObjSpace):

    def getattr(space,w_obj,w_name):
        w_descr = space.lookup(w_obj,'__getattribute__')
        try:
            return space.get_and_call_function(w_descr,w_obj,w_name)
        except OperatioError,e:
            if not e.match(space,space.w_AttributeError):
                raise
        w_descr = space.lookup(w_obj,'__getattr__')
        return space.get_and_call_function(w_descr,w_obj,w_name)

    def setattr(space,w_obj,w_name,w_val):
        w_descr = space.lookup(w_obj,'__setattr__')
        if w_descr is None:
            raise OperationError(space.w_AttributeError) # xxx error
        return space.get_and_call_function(w_descr,w_obj,w_name,w_val)

    def delattr(space,w_obj,w_name):
        w_descr = space.lookup(w_obj,'__delattr__')
        if w_descr is None:
            raise OperationError(space.w_AttributeError) # xxx error
        return space.get_and_call_function(w_descr,w_obj,w_name)

    def str(space,w_obj):
        w_descr = space.lookup(w_obj,'__str__')
        return space.get_and_call_function(w_descr,w_obj)

    def repr(space,w_obj):
        w_descr = space.lookup(w_obj,'__repr__')
        return space.get_and_call_function(w_descr,w_obj)

    def pos(space,w_obj):
        w_descr = space.lookup(w_obj,'__pos__')
        if w_descr is None:
            raise OperationError(space.w_TypeError) # xxx error
        return space.get_and_call_function(w_descr,w_obj)

    # xxx todo rest of 0 args methods
    # rest of 1 args methods
    # special cases
    
        
# regular methods def helpers
def _make_binary_impl(specialnames):
    left, right = specialnames
    def binary_impl(space,w_obj1,w_obj2):
        w_typ1 = space.type(w_obj1)
        w_typ2 = space.type(w_obj2)
        if space.issubtype(w_typ1,w_typ2):
            w_right_impl = space.lookup(w_obj2, right)
            if w_right_impl is not None:
                w_res = space.get_and_call_function(w_right_impl,w_obj2,w_obj1)
                if not space.is_true(space.is_(w_res.space.w_NotImplemented)):
                    return w_res
            w_left_impl = space.lookup(w_obj1, left)
            if w_left_impl is not None:
                w_res = space.get_and_call_function(w_left_impl,w_obj1,w_obj2)
                if not space.is_true(space.is_(w_res.space.w_NotImplemented)):
                    return w_res
        else:
            w_left_impl = space.lookup(w_obj1, left)
            if w_left_impl is not None:
                w_res = space.get_and_call_function(w_left_impl,w_obj1,w_obj2)
                if not space.is_true(space.is_(w_res.space.w_NotImplemented)):
                    return w_res
            w_right_impl = space.lookup(w_obj2, right)
            if w_right_impl is not None:
                w_res = space.get_and_call_function(w_right_impl,w_obj2,w_obj1)
                if not space.is_true(space.is_(w_res.space.w_NotImplemented)):
                    return w_res
        raise OperationError(space.w_TypeError) # xxx error
    return binary_impl
    
# add regular methods
for _name, _symbol, _arity, _specialnames in ObjSpace.MethodTable:
    if not hasattr(DescrObjSpace,_name):
        if _arity == 2: # binary
            setattr(DescrObjSpace,_name,_make_binary_impl(_specialnames))
        

 

