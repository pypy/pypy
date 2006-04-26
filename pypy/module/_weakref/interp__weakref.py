from pypy.interpreter.baseobjspace import Wrappable, W_Root
from pypy.interpreter.argument import Arguments
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.rpython.objectmodel import cast_address_to_object, cast_object_to_address
class W_Weakref(Wrappable):
    pass

W_Weakrefable = W_Root
W_Weakrefable.__lifeline__ = None

class W_Weakref(Wrappable):
    def __init__(w_self, space, w_obj, w_callable):
        w_self.space = space
        w_self.address = cast_object_to_address(w_obj)
        w_self.w_callable = w_callable
    
    def descr__call__(self):
        return cast_address_to_object(self.address, W_Weakrefable)

    def invalidate(w_self):
        from pypy.rpython.lltypesystem.llmemory import NULL
        import os
        w_self.address = NULL
        if not w_self.space.is_w(w_self.w_callable, w_self.space.w_None):
            try:
                w_self.space.call_function(w_self.w_callable, w_self)
            except OperationError, e:
                os.write(2, "XXX\n")

class WeakrefLifeline(object):
    def __init__(self):
        self.refs_w = []
        
    def __del__(self):
        for i in range(len(self.refs_w) - 1, -1, -1):
            w_ref = self.refs_w[i]
            w_ref.invalidate()
    
    def get_weakref(self, space, w_subtype, w_obj, w_callable):
        w_ref = space.allocate_instance(W_Weakref, w_subtype)
        W_Weakref.__init__(w_ref, space, w_obj, w_callable)
        self.refs_w.append(w_ref)
        return w_ref

def descr__new__(space, w_subtype, w_obj, w_callable=None):
    assert isinstance(w_obj, W_Weakrefable)
    if w_obj.__lifeline__ is None:
        w_obj.__lifeline__ = WeakrefLifeline()
    return w_obj.__lifeline__.get_weakref(space, w_subtype, w_obj, w_callable)

W_Weakref.typedef = TypeDef("weakref",
    __new__ = interp2app(descr__new__),
    __call__ = interp2app(W_Weakref.descr__call__, unwrap_spec=['self'])
)

