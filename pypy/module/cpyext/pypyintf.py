from pypy.module.cpyext.api import cpython_api
from pypy.module.cpyext.pyobject import PyObject, borrow_from


@cpython_api([PyObject, PyObject], PyObject)
def PyPy_Borrow(space, w_parentobj, w_obj):
    """Returns a borrowed reference to 'obj', borrowing from the 'parentobj'.
    """
    return borrow_from(w_parentobj, w_obj)
