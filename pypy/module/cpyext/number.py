from pypy.interpreter.error import OperationError, oefmt
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL, Py_ssize_t
from pypy.module.cpyext.pyobject import PyObject, PyObjectP, from_ref, make_ref, Py_DecRef
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.tool.sourcetools import func_with_new_name
from pypy.module.cpyext.state import State

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
    # According to CPython, this means: w_obj is not None, and
    # the type of w_obj has got a method __int__ or __float__.
    if w_obj is None:
        return 0
    if space.lookup(w_obj, '__int__') or space.lookup(w_obj, '__float__'):
        return 1
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
    return space.call_function(space.w_int, w_obj)

@cpython_api([PyObject], PyObject)
def PyNumber_Long(space, w_obj):
    """Returns the o converted to a long integer object on success, or NULL on
    failure.  This is the equivalent of the Python expression long(o)."""
    return space.call_function(space.w_long, w_obj)

@cpython_api([PyObject], PyObject)
def PyNumber_Index(space, w_obj):
    """Returns the o converted to a Python int or long on success or NULL with a
    TypeError exception raised on failure.
    """
    return space.index(w_obj)

@cpython_api([PyObjectP, PyObjectP], rffi.INT_real, error=CANNOT_FAIL)
def PyNumber_CoerceEx(space, pp1, pp2):
    """This function is similar to PyNumber_Coerce(), except that it returns
    1 when the conversion is not possible and when no error is raised.
    Reference counts are still not increased in this case."""
    retVal = PyNumber_Coerce(space, pp1, pp2)
    if retVal != 0:
        return 1
    return 0

@cpython_api([PyObjectP, PyObjectP], rffi.INT_real, error=CANNOT_FAIL)
def PyNumber_Coerce(space, pp1, pp2):
    """This function takes the addresses of two variables of type PyObject*.  If
    the objects pointed to by *p1 and *p2 have the same type, increment their
    reference count and return 0 (success). If the objects can be converted to a
    common numeric type, replace *p1 and *p2 by their converted value (with
    'new' reference counts), and return 0. If no conversion is possible, or if
    some other error occurs, return -1 (failure) and don't increment the
    reference counts.  The call PyNumber_Coerce(&o1, &o2) is equivalent to the
    Python statement o1, o2 = coerce(o1, o2)."""
    w_obj1 = from_ref(space, pp1[0])
    w_obj2 = from_ref(space, pp2[0])
    try:
        w_res = space.coerce(w_obj1, w_obj2)
    except (TypeError, OperationError):
        state = space.fromcache(State)
        state.clear_exception()
        return -1
    w_res1, w_res2 = space.unpackiterable(w_res, 2)
    pp1[0] = make_ref(space, w_res1)
    pp2[0] = make_ref(space, w_res2)
    return 0

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
        raise oefmt(space.w_ValueError,
                    "PyNumber_InPlacePower with non-None modulus is not "
                    "supported")
    return space.inplace_pow(w_o1, w_o2)

