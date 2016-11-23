"""
These are the default implementation for type slots that we put
in user-defined app-level Python classes, if the class implements
the corresponding '__xxx__' special method.  It should mostly just
call back the general version of the space operation.

This is only approximately correct.  One problem is that some
details are likely subtly wrong.  Another problem is that we don't
track changes to an app-level Python class (addition or removal of
'__xxx__' special methods) after initalization of the PyTypeObject.
"""

from pypy.interpreter.error import oefmt
from pypy.interpreter.argument import Arguments
from pypy.module.cpyext.api import cpython_api, PyObject, Py_ssize_t
from pypy.module.cpyext.api import PyTypeObjectPtr
from rpython.rtyper.lltypesystem import rffi, lltype

@cpython_api([PyObject], Py_ssize_t, error=-1, header=None)
def slot_sq_length(space, w_obj):
    return space.int_w(space.len(w_obj))

@cpython_api([PyObject], lltype.Signed, header=None, error=-1)
def slot_tp_hash(space, w_obj):
    return space.int_w(space.hash(w_obj))

@cpython_api([PyObject, Py_ssize_t], PyObject, header=None)
def slot_sq_item(space, w_obj, index):
    return space.getitem(w_obj, space.wrap(index))

@cpython_api([PyTypeObjectPtr, PyObject, PyObject], PyObject, header=None)
def slot_tp_new(space, w_type, w_args, w_kwds):
    # XXX problem - we need to find the actual __new__ function to call.
    #     but we have no 'self' argument. Theoretically, self will be
    #     w_type, but if w_type is a subclass of self, and w_type has a
    #     __new__ function that calls super().__new__, and that call ends
    #     up here, we will get infinite recursion. Prevent the recursion
    #     in the simple case (from cython) where w_type is a cpytype, but
    #     we know (since we are in this function) that self is not a cpytype
    from pypy.module.cpyext.typeobject import W_PyCTypeObject
    w_type0 = w_type
    mro_w = space.listview(space.getattr(w_type0, space.wrap('__mro__')))
    for w_m in mro_w[1:]:
        if not w_type0.is_cpytype():
            break
        w_type0 = w_m
    w_impl = space.getattr(w_type0, space.wrap('__new__'))
    args = Arguments(space, [w_type],
                     w_stararg=w_args, w_starstararg=w_kwds)
    return space.call_args(w_impl, args)

# unary functions

@cpython_api([PyObject], PyObject, header=None)
def slot_tp_str(space, w_obj):
    return space.str(w_obj)

@cpython_api([PyObject], PyObject, header=None)
def slot_tp_repr(space, w_obj):
    return space.repr(w_obj)

#binary functions

@cpython_api([PyObject, PyObject], PyObject, header=None)
def slot_nb_add(space, w_obj1, w_obj2):
    return space.add(w_obj1, w_obj2)

@cpython_api([PyObject, PyObject], PyObject, header=None)
def slot_nb_subtract(space, w_obj1, w_obj2):
    return space.add(w_obj1, w_obj2)

@cpython_api([PyObject, PyObject], PyObject, header=None)
def slot_nb_multiply(space, w_obj1, w_obj2):
    return space.add(w_obj1, w_obj2)

@cpython_api([PyObject, PyObject], PyObject, header=None)
def slot_nb_divide(space, w_obj1, w_obj2):
    return space.add(w_obj1, w_obj2)

@cpython_api([PyObject, PyObject], PyObject, header=None)
def slot_nb_inplace_add(space, w_obj1, w_obj2):
    return space.add(w_obj1, w_obj2)

@cpython_api([PyObject, PyObject], PyObject, header=None)
def slot_nb_inplace_subtract(space, w_obj1, w_obj2):
    return space.add(w_obj1, w_obj2)

@cpython_api([PyObject, PyObject], PyObject, header=None)
def slot_nb_inplace_multiply(space, w_obj1, w_obj2):
    return space.add(w_obj1, w_obj2)

@cpython_api([PyObject, PyObject], PyObject, header=None)
def slot_nb_inplace_divide(space, w_obj1, w_obj2):
    return space.add(w_obj1, w_obj2)

@cpython_api([PyObject, PyObject], PyObject, header=None)
def slot_sq_concat(space, w_obj1, w_obj2):
    return space.add(w_obj1, w_obj2)

@cpython_api([PyObject, PyObject], PyObject, header=None)
def slot_sq_inplace_concat(space, w_obj1, w_obj2):
    return space.add(w_obj1, w_obj2)

@cpython_api([PyObject, PyObject], PyObject, header=None)
def slot_mp_subscript(space, w_obj1, w_obj2):
    return space.add(w_obj1, w_obj2)

@cpython_api([PyObject, PyObject], PyObject, header=None)
def slot_tp_getattr(space, w_obj1, w_obj2):
    return space.getattr(w_obj1, w_obj2)


