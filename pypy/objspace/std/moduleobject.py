from pypy.objspace.std.objspace import *
from moduletype import W_ModuleType
from dictobject import W_DictObject


class W_ModuleObject(W_Object):
    delegate_once = {}
    statictype = W_ModuleType

    def __init__(w_self, space, w_name):
        W_Object.__init__(w_self, space)
        w_key_name = space.wrap('__name__')
        w_key_doc  = space.wrap('__doc__')
        items = [(w_key_name, w_name),
                 (w_key_doc,  space.w_None)]
        w_self.w_dict = W_DictObject(w_self.space, items)


def getattr_module_any(space, w_module, w_attr):
    if space.is_true(space.eq(w_attr, space.wrap('__dict__'))):
        return w_module.w_dict
    else:
        try:
            return space.getitem(w_module.w_dict, w_attr)
        except OperationError, e:
            if e.match(space, space.w_KeyError):
                raise FailedToImplement(space.w_AttributeError)
            else:
                raise

def setattr_module_any_any(space, w_module, w_attr, w_value):
    if space.is_true(space.eq(w_attr, space.wrap('__dict__'))):
        raise OperationError(space.w_TypeError,
                             space.wrap("readonly attribute"))
    else:
        space.setitem(w_module.w_dict, w_attr, w_value)

def delattr_module_any(space, w_module, w_attr):
    if space.is_true(space.eq(w_attr, space.wrap('__dict__'))):
        raise OperationError(space.w_TypeError,
                             space.wrap("readonly attribute"))
    else:
        try:
            space.delitem(w_module.w_dict, w_attr)
        except OperationError, e:
            if e.match(space, space.w_KeyError):
                raise FailedToImplement(space.w_AttributeError)
            else:
                raise

StdObjSpace.getattr.register(getattr_module_any,     W_ModuleObject, W_ANY)
StdObjSpace.setattr.register(setattr_module_any_any, W_ModuleObject, W_ANY,W_ANY)
StdObjSpace.delattr.register(delattr_module_any,     W_ModuleObject, W_ANY)
