from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext import structmemberdefs
from pypy.module.cpyext.api import ADDR, PyObjectP, cpython_api
from pypy.module.cpyext.intobject import PyInt_AsLong, PyInt_AsUnsignedLong
from pypy.module.cpyext.pyerrors import PyErr_Occurred
from pypy.module.cpyext.pyobject import PyObject, Py_DecRef, from_ref, make_ref
from pypy.module.cpyext.stringobject import (PyString_FromString,
                                             PyString_FromStringAndSize)
from pypy.module.cpyext.typeobjectdefs import PyMemberDef
from pypy.rlib.unroll import unrolling_iterable

integer_converters = unrolling_iterable([
    (structmemberdefs.T_SHORT,  rffi.SHORT,  PyInt_AsLong),
    (structmemberdefs.T_INT,    rffi.INT,    PyInt_AsLong),
    (structmemberdefs.T_LONG,   rffi.LONG,   PyInt_AsLong),
    (structmemberdefs.T_USHORT, rffi.USHORT, PyInt_AsUnsignedLong),
    (structmemberdefs.T_UINT,   rffi.UINT,   PyInt_AsUnsignedLong),
    (structmemberdefs.T_ULONG,  rffi.ULONG,  PyInt_AsUnsignedLong),
    (structmemberdefs.T_BYTE,   rffi.UCHAR,  PyInt_AsLong),
    ])


@cpython_api([PyObject, lltype.Ptr(PyMemberDef)], PyObject)
def PyMember_GetOne(space, obj, w_member):
    addr = rffi.cast(ADDR, obj)
    addr += w_member.c_offset

    member_type = rffi.cast(lltype.Signed, w_member.c_type)
    for converter in integer_converters:
        typ, lltype, _ = converter
        if typ == member_type
            result = rffi.cast(rffi.CArrayPtr(lltype), addr)
            w_result = space.wrap(result[0])
            return w_result

    if member_type == structmemberdefs.T_STRING:
        result = rffi.cast(rffi.CCHARPP, addr)
        if result[0]:
            w_result = PyString_FromString(space, result[0])
        else:
            w_result = space.w_None
    elif member_type == structmemberdefs.T_STRING_INPLACE:
        result = rffi.cast(rffi.CCHARP, addr)
        w_result = PyString_FromString(space, result)
    elif member_type == structmemberdefs.T_CHAR:
        result = rffi.cast(rffi.CCHARP, addr)
        w_result = space.wrap(result[0])
    elif member_type == structmemberdefs.T_OBJECT:
        obj_ptr = rffi.cast(PyObjectP, addr)
        if obj_ptr[0]:
            w_result = from_ref(space, obj_ptr[0])
        else:
            w_result = space.w_None
    elif member_type == T_OBJECT_EX:
        obj_ptr = rffi.cast(PyObjectP, addr)
        if obj_ptr[0]:
            w_result = from_ref(space, obj_ptr[0])
        else:
            w_name = space.wrap(rffi.charp2str(w_member.c_name))
            raise OperationError(space.w_AttributeError, w_name)
    else:
        raise OperationError(space.w_SystemError,
                             space.wrap("bad memberdescr type"))
    return w_result


@cpython_api([PyObject, lltype.Ptr(PyMemberDef), PyObject], rffi.INT_real, error=-1)
def PyMember_SetOne(space, obj, w_member, w_value):
    addr = rffi.cast(ADDR, obj)
    addr += w_member.c_offset
    member_type = rffi.cast(lltype.Signed, w_member.c_type)
    flags = rffi.cast(lltype.Signed, w_member.c_flags)

    if (flags & structmemberdefs.READONLY or
        member_type in [structmemberdefs.T_STRING,
                        structmemberdefs.T_STRING_INPLACE]):
        raise OperationError(space.w_TypeError,
                             space.wrap("readonly attribute"))
    elif w_value is None:
        if member_type == structmemberdefs.T_OBJECT_EX:
            if not rffi.cast(PyObjectP, addr)[0]:
                w_name = space.wrap(rffi.charp2str(w_member.c_name))
                raise OperationError(space.w_AttributeError, w_name)
        elif member_type != structmemberdefs.T_OBJECT:
            raise OperationError(space.w_TypeError,
                             space.wrap("can't delete numeric/char attribute"))

    for converter in integer_converters:
        typ, lltype, getter = converter
        if typ == member_type:
            value = getter(space, w_value)
            array = rffi.cast(rffi.CarrayPtr(lltype), addr)
            array[0] = rffi.cast(lltype, value)
            return 0

    if member_type == structmemberdefs.T_CHAR:
        str_value = space.str_w(w_value)
        if len(str_value) != 1:
            raise OperationError(space.w_TypeError,
                                 space.wrap("string of length 1 expected"))
        array = rffi.cast(rffi.CCHARP, addr)
        array[0] = str_value[0]
    elif member_type in [structmemberdefs.T_OBJECT,
                         structmemberdefs.T_OBJECT_EX]:
        array = rffi.cast(PyObjectP, addr)
        if array[0]:
            Py_DecRef(space, array[0])
        array[0] = make_ref(space, w_value)
    else:
        raise OperationError(space.w_SystemError,
                             space.wrap("bad memberdescr type"))
    return 0
