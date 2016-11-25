from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.structmemberdefs import *
from pypy.module.cpyext.api import ADDR, PyObjectP, cpython_api, CONST_STRING
from pypy.module.cpyext.intobject import PyInt_AsLong, PyInt_AsUnsignedLong
from pypy.module.cpyext.pyerrors import PyErr_Occurred
from pypy.module.cpyext.pyobject import PyObject, Py_DecRef, from_ref, make_ref
from pypy.module.cpyext.bytesobject import (
    PyString_FromString, PyString_FromStringAndSize)
from pypy.module.cpyext.floatobject import PyFloat_AsDouble
from pypy.module.cpyext.longobject import (
    PyLong_AsLongLong, PyLong_AsUnsignedLongLong, PyLong_AsSsize_t)
from pypy.module.cpyext.typeobjectdefs import PyMemberDef
from rpython.rlib.unroll import unrolling_iterable

integer_converters = unrolling_iterable([
    (T_SHORT,  rffi.SHORT,  PyInt_AsLong),
    (T_INT,    rffi.INT,    PyInt_AsLong),
    (T_LONG,   rffi.LONG,   PyInt_AsLong),
    (T_USHORT, rffi.USHORT, PyInt_AsUnsignedLong),
    (T_UINT,   rffi.UINT,   PyInt_AsUnsignedLong),
    (T_ULONG,  rffi.ULONG,  PyInt_AsUnsignedLong),
    (T_BYTE,   rffi.SIGNEDCHAR, PyInt_AsLong),
    (T_UBYTE,  rffi.UCHAR,  PyInt_AsUnsignedLong),
    (T_BOOL,   rffi.UCHAR,  PyInt_AsLong),
    (T_FLOAT,  rffi.FLOAT,  PyFloat_AsDouble),
    (T_DOUBLE, rffi.DOUBLE, PyFloat_AsDouble),
    (T_LONGLONG,  rffi.LONGLONG,  PyLong_AsLongLong),
    (T_ULONGLONG, rffi.ULONGLONG, PyLong_AsUnsignedLongLong),
    (T_PYSSIZET, rffi.SSIZE_T, PyLong_AsSsize_t),
    ])

_HEADER = 'pypy_structmember_decl.h'


@cpython_api([CONST_STRING, lltype.Ptr(PyMemberDef)], PyObject, header=_HEADER)
def PyMember_GetOne(space, obj, w_member):
    addr = rffi.cast(ADDR, obj)
    addr += w_member.c_offset

    member_type = rffi.cast(lltype.Signed, w_member.c_type)
    for converter in integer_converters:
        typ, lltyp, _ = converter
        if typ == member_type:
            result = rffi.cast(rffi.CArrayPtr(lltyp), addr)
            if lltyp is rffi.FLOAT:
                w_result = space.newfloat(lltype.cast_primitive(lltype.Float,
                                                            result[0]))
            elif typ == T_BOOL:
                x = rffi.cast(lltype.Signed, result[0])
                w_result = space.newbool(x != 0)
            elif typ == T_DOUBLE:
                w_result = space.newfloat(result[0])
            else:
                w_result = space.newint(result[0])
            return w_result

    if member_type == T_STRING:
        result = rffi.cast(rffi.CCHARPP, addr)
        if result[0]:
            w_result = PyString_FromString(space, result[0])
        else:
            w_result = space.w_None
    elif member_type == T_STRING_INPLACE:
        result = rffi.cast(rffi.CCHARP, addr)
        w_result = PyString_FromString(space, result)
    elif member_type == T_CHAR:
        result = rffi.cast(rffi.CCHARP, addr)
        w_result = space.newtext(result[0])
    elif member_type == T_OBJECT:
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
            w_name = space.newtext(rffi.charp2str(w_member.c_name))
            raise OperationError(space.w_AttributeError, w_name)
    else:
        raise oefmt(space.w_SystemError, "bad memberdescr type")
    return w_result


@cpython_api([rffi.CCHARP, lltype.Ptr(PyMemberDef), PyObject], rffi.INT_real,
             error=-1, header=_HEADER)
def PyMember_SetOne(space, obj, w_member, w_value):
    addr = rffi.cast(ADDR, obj)
    addr += w_member.c_offset
    member_type = rffi.cast(lltype.Signed, w_member.c_type)
    flags = rffi.cast(lltype.Signed, w_member.c_flags)

    if (flags & READONLY or
        member_type in [T_STRING, T_STRING_INPLACE]):
        raise oefmt(space.w_TypeError, "readonly attribute")
    elif w_value is None:
        if member_type == T_OBJECT_EX:
            if not rffi.cast(PyObjectP, addr)[0]:
                w_name = space.newtext(rffi.charp2str(w_member.c_name))
                raise OperationError(space.w_AttributeError, w_name)
        elif member_type != T_OBJECT:
            raise oefmt(space.w_TypeError,
                        "can't delete numeric/char attribute")

    for converter in integer_converters:
        typ, lltyp, getter = converter
        if typ == member_type:
            value = getter(space, w_value)
            array = rffi.cast(rffi.CArrayPtr(lltyp), addr)
            array[0] = rffi.cast(lltyp, value)
            return 0

    if member_type == T_CHAR:
        str_value = space.str_w(w_value)
        if len(str_value) != 1:
            raise oefmt(space.w_TypeError, "string of length 1 expected")
        array = rffi.cast(rffi.CCHARP, addr)
        array[0] = str_value[0]
    elif member_type in [T_OBJECT, T_OBJECT_EX]:
        array = rffi.cast(PyObjectP, addr)
        if array[0]:
            Py_DecRef(space, array[0])
        array[0] = make_ref(space, w_value)
    else:
        raise oefmt(space.w_SystemError, "bad memberdescr type")
    return 0
