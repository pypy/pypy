from pypy.interpreter.baseobjspace import Wrappable, W_Root
from pypy.interpreter.argument import Arguments
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.rpython.objectmodel import cast_address_to_object, cast_object_to_address
from pypy.rpython.lltypesystem.llmemory import NULL

W_Weakrefable = W_Root
W_Weakrefable.__lifeline__ = None

class W_Weakref(Wrappable):
    def __init__(w_self, space, lifeline, index, w_obj, w_callable):
        w_self.space = space
        w_self.address = cast_object_to_address(w_obj)
        w_self.w_callable = w_callable
        w_self.addr_lifeline = cast_object_to_address(lifeline)
        w_self.index = index
    
    def descr__call__(self):
        return cast_address_to_object(self.address, W_Weakrefable)

    def invalidate(w_self):
        w_self.address = NULL

    def activate_callback(w_self):
        import os
        if not w_self.space.is_w(w_self.w_callable, w_self.space.w_None):
            try:
                w_self.space.call_function(w_self.w_callable, w_self)
            except OperationError, e:
                e.write_unraisable(w_self.space, 'function', w_self.w_callable)

    def __del__(w_self):
        if w_self.address != NULL:
            lifeline = cast_address_to_object(w_self.addr_lifeline,
                                              WeakrefLifeline)
            lifeline.ref_is_dead(w_self.index)

class WeakrefLifeline(object):
    def __init__(self):
        self.addr_refs = []
        
    def __del__(self):
        for i in range(len(self.addr_refs) - 1, -1, -1):
            addr_ref = self.addr_refs[i]
            if addr_ref != NULL:
                w_ref = cast_address_to_object(addr_ref, W_Weakref)
                w_ref.invalidate()
        for i in range(len(self.addr_refs) - 1, -1, -1):
            addr_ref = self.addr_refs[i]
            if addr_ref != NULL:
                w_ref = cast_address_to_object(addr_ref, W_Weakref)
                w_ref.activate_callback()
    
    def get_weakref(self, space, w_subtype, w_obj, w_callable):
        w_ref = space.allocate_instance(W_Weakref, w_subtype)
        W_Weakref.__init__(w_ref, space, self, len(self.addr_refs),
                           w_obj, w_callable)
        self.addr_refs.append(cast_object_to_address(w_ref))
        return w_ref

    def ref_is_dead(self, index):
        self.addr_refs[index] = NULL

def getweakrefcount(space, w_obj):
    if not isinstance(w_obj, W_Weakrefable):
        return space.wrap(0)
    if w_obj.__lifeline__ is None:
        return space.wrap(0)
    else:
        lifeline = w_obj.__lifeline__
        result = 0
        for i in range(len(lifeline.addr_refs)):
            if lifeline.addr_refs[i] != NULL:
                result += 1
        return space.wrap(result)

def getweakrefs(space, w_obj):
    if not isinstance(w_obj, W_Weakrefable):
        return space.newlist([])
    if w_obj.__lifeline__ is None:
        return space.newlist([])
    else:
        lifeline = w_obj.__lifeline__
        result = []
        for i in range(len(lifeline.addr_refs)):
            addr = lifeline.addr_refs[i]
            if addr != NULL:
                result.append(cast_address_to_object(addr, W_Weakref))
        return space.newlist(result)

def descr__new__(space, w_subtype, w_obj, w_callable=None):
    assert isinstance(w_obj, W_Weakrefable)
    if w_obj.__lifeline__ is None:
        w_obj.__lifeline__ = WeakrefLifeline()
    return w_obj.__lifeline__.get_weakref(space, w_subtype, w_obj, w_callable)

W_Weakref.typedef = TypeDef("weakref",
    __new__ = interp2app(descr__new__),
    __call__ = interp2app(W_Weakref.descr__call__, unwrap_spec=['self'])
)

