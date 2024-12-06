from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.rarithmetic import widen
from pypy.module.cpyext.structmemberdefs import *
from pypy.module.cpyext.api import PyObjectP, cpython_api, CONST_STRING
from pypy.module.cpyext.longobject import PyLong_AsLong, PyLong_AsUnsignedLong
from pypy.module.cpyext.pyerrors import PyErr_Occurred
from pypy.module.cpyext.pyobject import PyObject, decref, from_ref, make_ref
from pypy.module.cpyext.unicodeobject import PyUnicode_FromString
from pypy.module.cpyext.floatobject import PyFloat_AsDouble
from pypy.module.cpyext.longobject import (
    PyLong_AsLongLong, PyLong_AsUnsignedLongLong, PyLong_AsSsize_t)
from pypy.module.cpyext.typeobjectdefs import PyMemberDef
from rpython.rlib.unroll import unrolling_iterable
from pypy.objspace.std.longobject import W_LongObject
from rpython.rlib.objectmodel import specialize

def convert_bool(space, w_obj):
    if space.is_w(w_obj, space.w_False):
        return False
    if space.is_w(w_obj, space.w_True):
        return True
    raise oefmt(space.w_TypeError, "attribute value type must be bool")

integer_converters = unrolling_iterable([ # range checking, unsigned
    (T_SHORT,  rffi.SHORT),
    (T_INT,    rffi.INT),
    (T_LONG,   rffi.LONG),
    (T_USHORT, rffi.USHORT),
    (T_UINT,   rffi.UINT),
    (T_ULONG,  rffi.ULONG),
    (T_BYTE,   rffi.SIGNEDCHAR),
    (T_UBYTE,  rffi.UCHAR),
    (T_BOOL,   rffi.UCHAR),
    (T_FLOAT,  rffi.FLOAT),
    (T_DOUBLE, rffi.DOUBLE),
    (T_LONGLONG,  rffi.LONGLONG),
    (T_ULONGLONG, rffi.ULONGLONG),
    (T_PYSSIZET, rffi.SSIZE_T),
    ])

_HEADER = 'pypy_structmember_decl.h'


@cpython_api([CONST_STRING, lltype.Ptr(PyMemberDef)], PyObject, header=_HEADER)
def PyMember_GetOne(space, obj, w_member):
    addr = rffi.ptradd(obj, w_member.c_offset)
    member_type = rffi.cast(lltype.Signed, w_member.c_type)
    for converter in integer_converters:
        typ, lltyp = converter
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
            w_result = PyUnicode_FromString(space, result[0])
        else:
            w_result = space.w_None
    elif member_type == T_STRING_INPLACE:
        result = rffi.cast(rffi.CCHARP, addr)
        w_result = PyUnicode_FromString(space, result)
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
            s = rffi.constcharp2str(w_member.c_name)
            w_name = space.newtext(s)
            raise OperationError(space.w_AttributeError, w_name)
    else:
        raise oefmt(space.w_SystemError, "bad memberdescr type")
    return w_result


@cpython_api([rffi.CCHARP, lltype.Ptr(PyMemberDef), PyObject], rffi.INT_real,
             error=-1, header=_HEADER)
def PyMember_SetOne(space, obj, w_member, w_value):
    addr = rffi.ptradd(obj, w_member.c_offset)
    member_type = widen(w_member.c_type)
    flags = widen(w_member.c_flags)

    if flags & READONLY:
        raise oefmt(space.w_AttributeError, "readonly attribute")
    elif w_value is None:
        if member_type == T_OBJECT_EX:
            if not rffi.cast(PyObjectP, addr)[0]:
                s = rffi.constcharp2str(w_member.c_name)
                w_name = space.newtext(s)
                raise OperationError(space.w_AttributeError, w_name)
        elif member_type != T_OBJECT:
            raise oefmt(space.w_TypeError,
                        "can't delete numeric/char attribute")
    if member_type == T_BOOL:
        value = convert_bool(space, w_value)
        array = rffi.cast(rffi.CArrayPtr(rffi.UCHAR), addr)
        casted = rffi.cast(rffi.UCHAR, value)
        array[0] = casted
    elif member_type == T_BYTE:
        value = PyLong_AsLong(space, w_value)
        array = rffi.cast(rffi.CArrayPtr(rffi.SIGNEDCHAR), addr)
        casted = rffi.cast(rffi.SIGNEDCHAR, value)
        if rffi.cast(lltype.typeOf(value), casted) != widen(value):
            space.warn(
                space.newtext("Truncation of value to char"),
                space.w_RuntimeWarning)
        array[0] = casted
    elif member_type == T_UBYTE:
        value = PyLong_AsLong(space, w_value)
        array = rffi.cast(rffi.CArrayPtr(rffi.UCHAR), addr)
        casted = rffi.cast(rffi.UCHAR, value)
        if rffi.cast(lltype.typeOf(value), casted) != widen(value):
            space.warn(
                space.newtext("Truncation of value to unsigned char"),
                space.w_RuntimeWarning)
        array[0] = casted
    elif member_type == T_SHORT:
        value = PyLong_AsLong(space, w_value)
        array = rffi.cast(rffi.CArrayPtr(rffi.SHORT), addr)
        casted = rffi.cast(rffi.SHORT, value)
        if rffi.cast(lltype.typeOf(value), casted) != widen(value):
            space.warn(
                space.newtext("Truncation of value to short"),
                space.w_RuntimeWarning)
        array[0] = casted
    elif member_type == T_USHORT:
        # Does not warn on negative assignment
        value = PyLong_AsLong(space, w_value)
        array = rffi.cast(rffi.CArrayPtr(rffi.USHORT), addr)
        casted = rffi.cast(rffi.USHORT, value)
        if rffi.cast(lltype.typeOf(value), casted) != widen(value):
            space.warn(
                space.newtext("Truncation of value to unsigned short"),
                space.w_RuntimeWarning)
        array[0] = casted
    elif member_type == T_INT:
        w_value = space.index(w_value)
        value = PyLong_AsLong(space, w_value)
        array = rffi.cast(rffi.CArrayPtr(rffi.INT), addr)
        casted = rffi.cast(rffi.INT, value)
        if rffi.cast(lltype.typeOf(value), casted) != widen(value):
            space.warn(
                space.newtext("Truncation of value to int"),
                space.w_RuntimeWarning)
        array[0] = casted
    elif member_type == T_UINT:
        w_value = space.index(w_value)
        array = rffi.cast(rffi.CArrayPtr(rffi.UINT), addr)
        if space.is_true(space.lt(w_value, space.newint(0))):
            value = PyLong_AsLong(space, w_value)
            casted = rffi.cast(rffi.UINT, value)
            space.warn(
                space.newtext("Writing negative value into unsigned field"),
                space.w_RuntimeWarning)
        else:
            value = PyLong_AsUnsignedLong(space, w_value)
            casted = rffi.cast(rffi.UINT, value)
            if rffi.cast(lltype.typeOf(value), casted) != widen(value):
                space.warn(
                    space.newtext("Truncation of value to unsigned int"),
                    space.w_RuntimeWarning)
        array[0] = casted
    elif member_type == T_LONG:
        value = PyLong_AsLong(space, w_value)
        array = rffi.cast(rffi.CArrayPtr(rffi.LONG), addr)
        casted = rffi.cast(rffi.LONG, value)
        array[0] = casted
    elif member_type == T_ULONG:
        array = rffi.cast(rffi.CArrayPtr(rffi.ULONG), addr)
        if space.is_true(space.lt(w_value, space.newint(0))):
            value = PyLong_AsLong(space, w_value)
            casted = rffi.cast(rffi.ULONG, value)
            space.warn(
                space.newtext("Writing negative value into unsigned field"),
                space.w_RuntimeWarning)
        else:
            value = PyLong_AsUnsignedLong(space, w_value)
            casted = rffi.cast(rffi.ULONG, value)
        array[0] = casted
    elif member_type == T_PYSSIZET:
        value = PyLong_AsSsize_t(space, w_value)
        array = rffi.cast(rffi.CArrayPtr(rffi.SSIZE_T), addr)
        casted = rffi.cast(rffi.SSIZE_T, value)
        array[0] = casted
    elif member_type == T_FLOAT:
        value = PyFloat_AsDouble(space, w_value)
        array = rffi.cast(rffi.CArrayPtr(rffi.FLOAT), addr)
        casted = rffi.cast(rffi.FLOAT, value)
        array[0] = casted
    elif member_type == T_DOUBLE:
        value = PyFloat_AsDouble(space, w_value)
        array = rffi.cast(rffi.CArrayPtr(rffi.DOUBLE), addr)
        casted = rffi.cast(rffi.DOUBLE, value)
        array[0] = casted
    elif member_type == T_LONGLONG:
        value = PyLong_AsLongLong(space, w_value)
        array = rffi.cast(rffi.CArrayPtr(rffi.LONGLONG), addr)
        casted = rffi.cast(rffi.LONGLONG, value)
        array[0] = casted
    elif member_type == T_ULONGLONG:
        w_value = space.index(w_value)
        array = rffi.cast(rffi.CArrayPtr(rffi.ULONGLONG), addr)
        if space.is_true(space.lt(w_value, space.newint(0))):
            value = PyLong_AsLong(space, w_value)
            casted = rffi.cast(rffi.ULONGLONG, value)
            space.warn(
                space.newtext("Writing negative value into unsigned field"),
                space.w_RuntimeWarning)
        else:
            value = PyLong_AsUnsignedLongLong(space, w_value)
            casted = rffi.cast(rffi.ULONGLONG, value)
            array[0] = casted
    elif member_type == T_CHAR:
        str_value = space.text_w(w_value)
        if len(str_value) != 1:
            raise oefmt(space.w_TypeError, "string of length 1 expected")
        array = rffi.cast(rffi.CCHARP, addr)
        array[0] = str_value[0]
    elif member_type in [T_OBJECT, T_OBJECT_EX]:
        array = rffi.cast(PyObjectP, addr)
        if array[0]:
            decref(space, array[0])
        array[0] = make_ref(space, w_value)
    elif member_type in [T_STRING, T_STRING_INPLACE]:
        raise oefmt(space.w_TypeError, "readonly attribute")
    else:
        raise oefmt(space.w_SystemError, "bad memberdescr type")
    return 0
