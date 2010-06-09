from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext import structmemberdefs
from pypy.module.cpyext.api import ADDR, PyObjectP
from pypy.module.cpyext.gateway import cpython_api
from pypy.module.cpyext.intobject import PyInt_AsLong, PyInt_AsUnsignedLong
from pypy.module.cpyext.pyerrors import PyErr_Occurred
from pypy.module.cpyext.pyobject import PyObject, Py_DecRef, from_ref, make_ref
from pypy.module.cpyext.stringobject import (PyString_FromString,
                                             PyString_FromStringAndSize)
from pypy.module.cpyext.typeobjectdefs import PyMemberDef


@cpython_api([PyObject, lltype.Ptr(PyMemberDef)], PyObject)
def PyMember_GetOne(space, obj, w_member):
    addr = rffi.cast(ADDR, obj)
    addr += w_member.c_offset
    member_type = rffi.cast(lltype.Signed, w_member.c_type)
    if member_type == structmemberdefs.T_SHORT:
        result = rffi.cast(rffi.SHORTP, addr)
        w_result = space.wrap(result[0])
    elif member_type == structmemberdefs.T_INT:
        result = rffi.cast(rffi.INTP, addr)
        w_result = space.wrap(result[0])
    elif member_type == structmemberdefs.T_LONG:
        result = rffi.cast(rffi.LONGP, addr)
        w_result = space.wrap(result[0])
    elif member_type == structmemberdefs.T_USHORT:
        result = rffi.cast(rffi.USHORTP, addr)
        w_result = space.wrap(result[0])
    elif member_type == structmemberdefs.T_UINT:
        result = rffi.cast(rffi.UINTP, addr)
        w_result = space.wrap(result[0])
    elif member_type == structmemberdefs.T_ULONG:
        result = rffi.cast(rffi.ULONGP, addr)
        w_result = space.wrap(result[0])
    elif member_type == structmemberdefs.T_BYTE:
        result = rffi.cast(rffi.CCHARP, addr)
        w_result = space.wrap(result[0])
    elif member_type == structmemberdefs.T_STRING:
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
    elif member_type in [structmemberdefs.T_OBJECT,
                         structmemberdefs.T_OBJECT_EX]:
        obj_ptr = rffi.cast(PyObjectP, addr)
        if obj_ptr[0]:
            w_result = from_ref(space, obj_ptr[0])
        else:
            if member_type == structmemberdefs.T_OBJECT_EX:
                w_name = space.wrap(rffi.charp2str(w_member.c_name))
                raise OperationError(space.w_AttributeError, w_name)
            w_result = space.w_None
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

    if member_type == structmemberdefs.T_SHORT:
        w_long_value = PyInt_AsLong(space, w_value)
        array = rffi.cast(rffi.SHORTP, addr)
        array[0] = rffi.cast(rffi.SHORT, w_long_value)
    elif member_type == structmemberdefs.T_INT:
        w_long_value = PyInt_AsLong(space, w_value)
        array = rffi.cast(rffi.INTP, addr)
        array[0] = rffi.cast(rffi.INT, w_long_value)
    elif member_type == structmemberdefs.T_LONG:
        w_long_value = PyInt_AsLong(space, w_value)
        array = rffi.cast(rffi.LONGP, addr)
        array[0] = rffi.cast(rffi.LONG, w_long_value)
    elif member_type == structmemberdefs.T_USHORT:
        w_long_value = PyInt_AsUnsignedLong(space, w_value)
        array = rffi.cast(rffi.USHORTP, addr)
        array[0] = rffi.cast(rffi.USHORT, w_long_value)
    elif member_type == structmemberdefs.T_UINT:
        w_long_value = PyInt_AsUnsignedLong(space, w_value)
        array = rffi.cast(rffi.UINTP, addr)
        array[0] = rffi.cast(rffi.UINT, w_long_value)
    elif member_type == structmemberdefs.T_ULONG:
        w_long_value = PyInt_AsUnsignedLong(space, w_value)
        array = rffi.cast(rffi.ULONGP, addr)
        array[0] = rffi.cast(rffi.ULONG, w_long_value)
    elif member_type == structmemberdefs.T_BYTE:
        w_long_value = PyInt_AsLong(space, w_value)
        array = rffi.cast(rffi.CCHARP, addr)
        array[0] = rffi.cast(rffi.CHAR, w_long_value)
    elif member_type == structmemberdefs.T_CHAR:
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
