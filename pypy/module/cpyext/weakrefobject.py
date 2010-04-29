from pypy.module.cpyext.api import cpython_api
from pypy.module.cpyext.pyobject import PyObject, register_container
from pypy.module._weakref.interp__weakref import W_Weakref

@cpython_api([PyObject, PyObject], PyObject)
def PyWeakref_NewRef(space, w_obj, w_callback):
    """Return a weak reference object for the object ob.  This will always return
    a new reference, but is not guaranteed to create a new object; an existing
    reference object may be returned.  The second parameter, callback, can be a
    callable object that receives notification when ob is garbage collected; it
    should accept a single parameter, which will be the weak reference object
    itself. callback may also be None or NULL.  If ob is not a
    weakly-referencable object, or if callback is not callable, None, or
    NULL, this will return NULL and raise TypeError.
    """
    w_weakref = space.gettypeobject(W_Weakref.typedef)
    return space.call_function(w_weakref, w_obj, w_callback)

@cpython_api([PyObject], PyObject, borrowed=True)
def PyWeakref_GetObject(space, w_ref):
    """Return the referenced object from a weak reference, ref.  If the referent is
    no longer live, returns None.
    """
    register_container(space, w_ref)
    return space.call_function(w_ref)

