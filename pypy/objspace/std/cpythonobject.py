from pypy.objspace.std.objspace import *
from stringobject import W_StringObject


class W_CPythonObject:
    "Temporary class!  This one wraps *any* CPython object."

    delegate_once = {}
    
    def __init__(w_self, cpyobj):
        w_self.cpyobj = cpyobj

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "wrap(%r)" % (w_self.cpyobj,)


def cpython_unwrap(space, w_obj):
    return w_obj.cpyobj

StdObjSpace.unwrap.register(cpython_unwrap, W_CPythonObject)

def cpython_id(space, w_obj):
    return space.wrap(id(w_obj.cpyobj))

StdObjSpace.id.register(cpython_id, W_CPythonObject)

def cpython_getattr(space, w_obj, w_attrname):
    attributevalue = getattr(w_obj.cpyobj, w_attrname.value)
    return space.wrap(attributevalue)

StdObjSpace.getattr.register(cpython_getattr, W_CPythonObject, W_StringObject)

def cpython_call(space, w_obj, w_arguments, w_keywords):
    # XXX temporary hack similar to objspace.trivial.call()
    # XXX keywords are ignored
    callable = space.unwrap(w_obj)
    args = space.unwrap(w_arguments)
    try:
        result = apply(callable, args)
    except:
        raise OperationError(*sys.exc_info()[:2])
    return space.wrap(result)

StdObjSpace.call.register(cpython_call, W_CPythonObject, W_ANY, W_ANY)
