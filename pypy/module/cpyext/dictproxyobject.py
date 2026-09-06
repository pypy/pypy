from pypy.interpreter.error import oefmt
from pypy.objspace.std.dictproxyobject import W_DictProxyObject
from pypy.module.cpyext.api import cpython_api, build_type_checkers
from pypy.module.cpyext.pyobject import PyObject

PyDictProxy_Check, PyDictProxy_CheckExact = build_type_checkers(
    "DictProxy", W_DictProxyObject)

@cpython_api([PyObject], PyObject, abi3=True)
def PyDictProxy_New(space, w_dict):
    """Return a proxy object for mapping which enforces read-only
    behavior. Normally used to create a proxy to prevent modification of
    the dictionary for non-dynamic class types."""
    # matches CPython: any mapping (i.e. anything with __getitem__)
    # except list/tuple, even though those also have __getitem__
    if (space.lookup(w_dict, '__getitem__') is None or
            space.isinstance_w(w_dict, space.w_list) or
            space.isinstance_w(w_dict, space.w_tuple)):
        raise oefmt(space.w_TypeError,
            "mappingproxy() argument must be a mapping, not %T", w_dict)
    return W_DictProxyObject(w_dict)
