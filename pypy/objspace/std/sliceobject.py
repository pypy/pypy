from pypy.objspace.std.objspace import *
from pypy.interpreter.appfile import AppFile
from pypy.interpreter.extmodule import make_builtin_func
from pypy.objspace.std.instmethobject import W_InstMethObject
from slicetype import W_SliceType

appfile = AppFile(__name__, ["objspace.std"])


class W_SliceObject(W_Object):
    statictype = W_SliceType
    
    def __init__(w_self, space, w_start, w_stop, w_step):
        W_Object.__init__(w_self, space)
        w_self.w_start = w_start
        w_self.w_stop = w_stop
        w_self.w_step = w_step
    def indices(w_self, w_length):
        w_ret = w_self.space.gethelper(appfile).call("sliceindices", [w_self, w_length])
        w_start, w_stop, w_step, w_slicelength = w_self.space.unpackiterable(w_ret, 4)
        return w_start, w_stop, w_step, w_slicelength
    def indices2(w_self, w_length):
        return w_self.space.newtuple(w_self.indices(w_length)[:-1])


registerimplementation(W_SliceObject)


def getattr_slice_any(space, w_slice, w_attr):
    if space.is_true(space.eq(w_attr, space.wrap('start'))):
        if w_slice.w_start is None:
            return space.w_None
        else:
            return w_slice.w_start
    if space.is_true(space.eq(w_attr, space.wrap('stop'))):
        if w_slice.w_stop is None:
            return space.w_None
        else:
            return w_slice.w_stop
    if space.is_true(space.eq(w_attr, space.wrap('step'))):
        if w_slice.w_step is None:
            return space.w_None
        else:
            return w_slice.w_step
    if space.is_true(space.eq(w_attr, space.wrap('indices'))):
        w_builtinfn = make_builtin_func(space, W_SliceObject.indices2)
        return W_InstMethObject(space, w_slice, w_builtinfn)
    
    raise FailedToImplement(space.w_AttributeError)

StdObjSpace.getattr.register(getattr_slice_any, W_SliceObject, W_ANY)
