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


@cpython_api([PyObject], Py_ssize_t, error=-1, header=None)
def slot_sq_length(space, w_obj):
    return space.int_w(space.len(w_obj))

@cpython_api([PyObject, Py_ssize_t], PyObject, header=None)
def slot_sq_item(space, w_obj, index):
    return space.getitem(w_obj, space.wrap(index))

@cpython_api([PyObject, PyObject], PyObject, header=None)
def slot_nb_add(space, w_obj1, w_obj2):
    return space.add(w_obj1, w_obj2)

@cpython_api([PyTypeObjectPtr, PyObject, PyObject], PyObject, header=None)
def slot_tp_new(space, w_type, w_args, w_kwds):
    _, w_descr = space.lookup_in_type_where(w_type, '__new__')
    if w_descr is None:
        raise oefmt(space.w_RuntimeError, "cpyext: '__new__' not found")
    # w_descr is typically a StaticMethod
    args = Arguments(space, [w_type],
                     w_stararg=w_args, w_starstararg=w_kwds)
    return space.call_args(space.get(w_descr, w_type), args)
