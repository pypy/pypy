from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL, Py_ssize_t
from pypy.module.cpyext.pyobject import PyObject
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.tool.sourcetools import func_with_new_name

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyIndex_Check(space, w_obj):
    """Returns True if o is an index integer (has the nb_index slot of the
    tp_as_number structure filled in).
    """
    try:
        space.index(w_obj)
        return 1
    except OperationError:
        return 0

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyNumber_Check(space, w_obj):
    """Returns 1 if the object o provides numeric protocols, and false otherwise.
    This function always succeeds."""
    try:
        space.float_w(w_obj)
        return 1
    except OperationError:
        return 0

@cpython_api([PyObject, PyObject], Py_ssize_t, error=-1)
def PyNumber_AsSsize_t(space, w_obj, w_exc):
    """Returns o converted to a Py_ssize_t value if o can be interpreted as an
    integer. If o can be converted to a Python int or long but the attempt to
    convert to a Py_ssize_t value would raise an OverflowError, then the
    exc argument is the type of exception that will be raised (usually
    IndexError or OverflowError).  If exc is NULL, then the
    exception is cleared and the value is clipped to PY_SSIZE_T_MIN for a negative
    integer or PY_SSIZE_T_MAX for a positive integer.
    """
    return space.int_w(w_obj) #XXX: this is wrong on win64

@cpython_api([PyObject], PyObject)
def PyNumber_Int(space, w_obj):
    """Returns the o converted to an integer object on success, or NULL on failure.
    This is the equivalent of the Python expression int(o)."""
    return space.int(w_obj)

@cpython_api([PyObject], PyObject)
def PyNumber_Long(space, w_obj):
    """Returns the o converted to a long integer object on success, or NULL on
    failure.  This is the equivalent of the Python expression long(o)."""
    return space.long(w_obj)

def func_rename(newname):
    return lambda func: func_with_new_name(func, newname)

def make_numbermethod(name, spacemeth):
    @cpython_api([PyObject, PyObject], PyObject)
    @func_rename('PyNumber_%s' % (name,))
    def PyNumber_Method(space, w_o1, w_o2):
        meth = getattr(space, spacemeth)
        return meth(w_o1, w_o2)

def make_unary_numbermethod(name, spacemeth):
    @cpython_api([PyObject], PyObject)
    @func_rename('PyNumber_%s' % (name,))
    def PyNumber_Method(space, w_o1):
        meth = getattr(space, spacemeth)
        return meth(w_o1)

def make_inplace_numbermethod(name, spacemeth):
    spacemeth = 'inplace_' + spacemeth.rstrip('_')
    @cpython_api([PyObject, PyObject], PyObject)
    @func_rename('PyNumber_InPlace%s' % (name,))
    def PyNumber_Method(space, w_o1, w_o2):
        meth = getattr(space, spacemeth)
        return meth(w_o1, w_o2)

for name, spacemeth in [
    ('Add', 'add'),
    ('Subtract', 'sub'),
    ('Multiply', 'mul'),
    ('Divide', 'div'),
    ('FloorDivide', 'floordiv'),
    ('TrueDivide', 'truediv'),
    ('Remainder', 'mod'),
    ('Lshift', 'lshift'),
    ('Rshift', 'rshift'),
    ('And', 'and_'),
    ('Xor', 'xor'),
    ('Or', 'or_'),
    ('Divmod', 'divmod'),
    ]:
    make_numbermethod(name, spacemeth)
    if name != 'Divmod':
        make_inplace_numbermethod(name, spacemeth)

for name, spacemeth in [
    ('Negative', 'neg'),
    ('Positive', 'pos'),
    ('Absolute', 'abs'),
    ('Invert', 'invert')]:
    make_unary_numbermethod(name, spacemeth)

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyNumber_Power(space, w_o1, w_o2, w_o3):
    return space.pow(w_o1, w_o2, w_o3)

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyNumber_InPlacePower(space, w_o1, w_o2, w_o3):
    if not space.is_w(w_o3, space.w_None):
        raise OperationError(space.w_ValueError, space.wrap(
            "PyNumber_InPlacePower with non-None modulus is not supported"))
    return space.inplace_pow(w_o1, w_o2)

