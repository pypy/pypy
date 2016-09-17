
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import oefmt
from pypy.module.cpyext.api import (
    cpython_api, cpython_struct, build_type_checkers, bootstrap_function,
    PyObject, PyObjectFields, CONST_STRING, CANNOT_FAIL, Py_ssize_t)
from pypy.module.cpyext.pyobject import (
    make_typedescr, track_reference, from_ref)
from rpython.rlib.rarithmetic import r_uint, intmask, LONG_TEST, r_ulonglong
from pypy.objspace.std.intobject import W_IntObject
import sys

PyIntObjectStruct = lltype.ForwardReference()
PyIntObject = lltype.Ptr(PyIntObjectStruct)
PyIntObjectFields = PyObjectFields + \
    (("ob_ival", rffi.LONG),)
cpython_struct("PyIntObject", PyIntObjectFields, PyIntObjectStruct)

@bootstrap_function
def init_intobject(space):
    "Type description of PyIntObject"
    make_typedescr(space.w_int.layout.typedef,
                   basestruct=PyIntObject.TO,
                   attach=int_attach,
                   realize=int_realize)

def int_attach(space, py_obj, w_obj):
    """
    Fills a newly allocated PyIntObject with the given int object. The
    value must not be modified.
    """
    py_int = rffi.cast(PyIntObject, py_obj)
    py_int.c_ob_ival = space.int_w(w_obj)

def int_realize(space, obj):
    intval = rffi.cast(lltype.Signed, rffi.cast(PyIntObject, obj).c_ob_ival)
    w_type = from_ref(space, rffi.cast(PyObject, obj.c_ob_type))
    w_obj = space.allocate_instance(W_IntObject, w_type)
    w_obj.__init__(intval)
    track_reference(space, obj, w_obj)
    return w_obj

PyInt_Check, PyInt_CheckExact = build_type_checkers("Int")

@cpython_api([], lltype.Signed, error=CANNOT_FAIL)
def PyInt_GetMax(space):
    """Return the system's idea of the largest integer it can handle (LONG_MAX,
    as defined in the system header files)."""
    return sys.maxint

@cpython_api([lltype.Signed], PyObject)
def PyInt_FromLong(space, ival):
    """Create a new integer object with a value of ival.

    """
    return space.wrap(ival)

@cpython_api([PyObject], lltype.Signed, error=-1)
def PyInt_AsLong(space, w_obj):
    """Will first attempt to cast the object to a PyIntObject, if it is not
    already one, and then return its value. If there is an error, -1 is
    returned, and the caller should check PyErr_Occurred() to find out whether
    there was an error, or whether the value just happened to be -1."""
    if w_obj is None:
        raise oefmt(space.w_TypeError, "an integer is required, got NULL")
    return space.int_w(space.int(w_obj))

@cpython_api([PyObject], lltype.Unsigned, error=-1)
def PyInt_AsUnsignedLong(space, w_obj):
    """Return a C unsigned long representation of the contents of pylong.
    If pylong is greater than ULONG_MAX, an OverflowError is
    raised."""
    if w_obj is None:
        raise oefmt(space.w_TypeError, "an integer is required, got NULL")
    return space.uint_w(space.int(w_obj))


@cpython_api([PyObject], rffi.ULONG, error=-1)
def PyInt_AsUnsignedLongMask(space, w_obj):
    """Will first attempt to cast the object to a PyIntObject or
    PyLongObject, if it is not already one, and then return its value as
    unsigned long.  This function does not check for overflow.
    """
    w_int = space.int(w_obj)
    if space.isinstance_w(w_int, space.w_int):
        num = space.int_w(w_int)
        return r_uint(num)
    else:
        num = space.bigint_w(w_int)
        return num.uintmask()


@cpython_api([PyObject], rffi.ULONGLONG, error=-1)
def PyInt_AsUnsignedLongLongMask(space, w_obj):
    """Will first attempt to cast the object to a PyIntObject or
    PyLongObject, if it is not already one, and then return its value as
    unsigned long long, without checking for overflow.
    """
    w_int = space.int(w_obj)
    if space.isinstance_w(w_int, space.w_int):
        num = space.int_w(w_int)
        return r_ulonglong(num)
    else:
        num = space.bigint_w(w_int)
        return num.ulonglongmask()

@cpython_api([rffi.VOIDP], lltype.Signed, error=CANNOT_FAIL)
def PyInt_AS_LONG(space, w_int):
    """Return the value of the object w_int. No error checking is performed."""
    return space.int_w(w_int)

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyInt_AsSsize_t(space, w_obj):
    """Will first attempt to cast the object to a PyIntObject or
    PyLongObject, if it is not already one, and then return its value as
    Py_ssize_t.
    """
    if w_obj is None:
        raise oefmt(space.w_TypeError, "an integer is required, got NULL")
    return space.int_w(w_obj) # XXX this is wrong on win64

LONG_MAX = int(LONG_TEST - 1)

@cpython_api([rffi.SIZE_T], PyObject)
def PyInt_FromSize_t(space, ival):
    """Create a new integer object with a value of ival. If the value exceeds
    LONG_MAX, a long integer object is returned.
    """
    if ival <= LONG_MAX:
        return space.wrap(intmask(ival))
    return space.wrap(ival)

@cpython_api([Py_ssize_t], PyObject)
def PyInt_FromSsize_t(space, ival):
    """Create a new integer object with a value of ival. If the value is larger
    than LONG_MAX or smaller than LONG_MIN, a long integer object is
    returned.
    """
    return space.wrap(ival)

@cpython_api([CONST_STRING, rffi.CCHARPP, rffi.INT_real], PyObject)
def PyInt_FromString(space, str, pend, base):
    """Return a new PyIntObject or PyLongObject based on the string
    value in str, which is interpreted according to the radix in base.  If
    pend is non-NULL, *pend will point to the first character in str which
    follows the representation of the number.  If base is 0, the radix will be
    determined based on the leading characters of str: if str starts with
    '0x' or '0X', radix 16 will be used; if str starts with '0', radix
    8 will be used; otherwise radix 10 will be used.  If base is not 0, it
    must be between 2 and 36, inclusive.  Leading spaces are ignored.  If
    there are no digits, ValueError will be raised.  If the string represents
    a number too large to be contained within the machine's long int type
    and overflow warnings are being suppressed, a PyLongObject will be
    returned.  If overflow warnings are not being suppressed, NULL will be
    returned in this case."""
    s = rffi.charp2str(str)
    w_str = space.wrap(s)
    w_base = space.wrap(rffi.cast(lltype.Signed, base))
    if pend:
        pend[0] = rffi.ptradd(str, len(s))
    return space.call_function(space.w_int, w_str, w_base)
