"""
Implements HPy attribute descriptors, i.e members and getsets.
"""
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.unroll import unrolling_iterable
from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import DescrMismatch
from pypy.interpreter.typedef import (
    GetSetProperty, TypeDef, interp_attrproperty, interp2app)
from pypy.module._hpy_universal import llapi, handles
from pypy.module._hpy_universal.state import State
from pypy.module._hpy_universal.apiset import API

ADDRESS = lltype.Signed

def check_descr(space, w_obj, w_type):
    if not space.isinstance_w(w_obj, w_type):
        raise DescrMismatch()

# ======== HPyDef_Kind_Member ========

converter_data = [                     # range checking
    ('SHORT',  rffi.SHORT,                      True),
    ('INT',    rffi.INT,                       True),
    ('LONG',   rffi.LONG,                       False),
    ('USHORT', rffi.USHORT,             True),
    ('UINT',   rffi.UINT,               True),
    ('ULONG',  rffi.ULONG,              False),
    ('BYTE',   rffi.SIGNEDCHAR,                 True),
    ('UBYTE',  rffi.UCHAR,              True),
    #('BOOL',   rffi.UCHAR,  convert_bool,                     False),
    #('FLOAT',  rffi.FLOAT,  PyFloat_AsDouble,                 False),
    #('DOUBLE', rffi.DOUBLE, PyFloat_AsDouble,                 False),
    ('LONGLONG',  rffi.LONGLONG,            False),
    ('ULONGLONG', rffi.ULONGLONG,   False),
    ('HPYSSIZET', rffi.SSIZE_T,               False),
    ]
Enum = llapi.cts.gettype('HPyMember_FieldType')
converters = unrolling_iterable([
    (getattr(Enum, 'HPyMember_' + name), typ) for name, typ, _ in converter_data])

def member_get(w_descr, space, w_obj):
    from .interp_type import W_HPyObject
    assert isinstance(w_descr, W_HPyMemberDescriptor)
    check_descr(space, w_obj, w_descr.w_type)
    assert isinstance(w_obj, W_HPyObject)
    addr = rffi.cast(ADDRESS, w_obj.hpy_data) + w_descr.offset
    kind = w_descr.kind
    for num, typ in converters:
        if kind == num:
            return space.newint(rffi.cast(rffi.CArrayPtr(typ), addr)[0])
    if kind == Enum.HPyMember_FLOAT:
        value = rffi.cast(rffi.CArrayPtr(rffi.FLOAT), addr)[0]
        return space.newfloat(rffi.cast(rffi.DOUBLE, value))
    elif kind == Enum.HPyMember_DOUBLE:
        value = rffi.cast(rffi.CArrayPtr(rffi.DOUBLE), addr)[0]
        return space.newfloat(value)
    elif kind == Enum.HPyMember_BOOL:
        value = rffi.cast(rffi.CArrayPtr(rffi.UCHAR), addr)[0]
        w_result = space.newbool(bool(value))
    else:
        # missing: STRING, STRING_INPLACE, OBJECT, OBJECT_EX, NONE
        raise oefmt(space.w_NotImplementedError, '...')


def member_set(w_descr, space, w_obj, w_value):
    from .interp_type import W_HPyObject
    assert isinstance(w_descr, W_HPyMemberDescriptor)
    check_descr(space, w_obj, w_descr.w_type)
    assert isinstance(w_obj, W_HPyObject)
    addr = rffi.cast(ADDRESS, w_obj.hpy_data) + w_descr.offset
    kind = w_descr.kind
    for num, typ in converters:
        if kind == num:
            # XXX: this is wrong!
            value = space.int_w(w_value)
            ptr = rffi.cast(rffi.CArrayPtr(typ), addr)
            ptr[0] = rffi.cast(typ, value)
            return
    if kind == Enum.HPyMember_FLOAT:
        value = space.float_w(w_value)
        ptr = rffi.cast(rffi.CArrayPtr(rffi.FLOAT), addr)
        ptr[0] = rffi.cast(rffi.FLOAT, value)
        return
    elif kind == Enum.HPyMember_DOUBLE:
        value = space.float_w(w_value)
        ptr = rffi.cast(rffi.CArrayPtr(rffi.DOUBLE), addr)
        ptr[0] = value
        return
    elif kind == Enum.HPyMember_BOOL:
        if space.is_w(w_obj, space.w_False):
            value = False
        elif space.is_w(w_obj, space.w_True):
            value = True
        else:
            raise oefmt(space.w_TypeError, "attribute value type must be bool")
        ptr = rffi.cast(rffi.CArrayPtr(rffi.UCHAR), addr)
        ptr[0] = rffi.cast(rffi.UCHAR, value)
        return
    else:
        raise oefmt(space.w_NotImplementedError, '...')

def member_del(w_descr, space, w_obj):
    check_descr(space, w_obj, w_descr.w_type)
    raise oefmt(space.w_TypeError,
                "can't delete numeric/char attribute")


class W_HPyMemberDescriptor(GetSetProperty):
    def __init__(self, w_type, kind, name, doc, offset):
        self.kind = kind
        self.name = name
        self.w_type = w_type
        self.offset = offset
        setter = member_set
        GetSetProperty.__init__(
            self, member_get, setter, member_del, doc,
            cls=None, use_closure=True, tag="hpy_member")

    def readonly_attribute(self, space):   # overwritten
        # XXX write a test
        raise oefmt(space.w_AttributeError,
            "attribute '%s' of '%N' objects is not writable",
            self.name, self.w_type)


W_HPyMemberDescriptor.typedef = TypeDef(
    "hpy_member_descriptor",
    __get__=interp2app(GetSetProperty.descr_property_get),
    __set__=interp2app(GetSetProperty.descr_property_set),
    __delete__=interp2app(GetSetProperty.descr_property_del),
    __name__=interp_attrproperty('name', cls=GetSetProperty,
        wrapfn="newtext_or_none"),
    __objclass__=GetSetProperty(GetSetProperty.descr_get_objclass),
    __doc__=interp_attrproperty('doc', cls=GetSetProperty,
        wrapfn="newtext_or_none"),
    )
assert not W_HPyMemberDescriptor.typedef.acceptable_as_base_class  # no __new__

def add_member(space, w_type, hpymember):
    name = rffi.constcharp2str(hpymember.c_name)
    doc = rffi.constcharp2str(hpymember.c_doc) if hpymember.c_doc else None
    offset = rffi.cast(lltype.Signed, hpymember.c_offset)
    kind = rffi.cast(lltype.Signed, hpymember.c_type)
    w_descr = W_HPyMemberDescriptor(w_type, kind, name, doc, offset)
    w_type.setdictvalue(space, name, w_descr)


# ======== HPyDef_Kind_GetSet ========

def getset_get(w_getset, space, w_self):
    state = space.fromcache(State)
    cfuncptr = w_getset.hpygetset.c_getter_impl
    func = llapi.cts.cast('HPyFunc_getter', cfuncptr)
    with handles.using(space, w_self) as h_self:
        h_result = func(state.ctx, h_self, w_getset.hpygetset.c_closure)
    return handles.consume(space, h_result)
    
def getset_set(w_getset, space, w_self, w_value):
    state = space.fromcache(State)
    cfuncptr = w_getset.hpygetset.c_setter_impl
    func = llapi.cts.cast('HPyFunc_setter', cfuncptr)
    with handles.using(space, w_self) as h_self:
        with handles.using(space, w_value) as h_value:
            h_result = func(state.ctx, h_self, h_value, w_getset.hpygetset.c_closure)
    return API.int(0)


class W_HPyGetSetProperty(GetSetProperty):
    def __init__(self, w_type, hpygetset):
        self.hpygetset = hpygetset
        self.w_type = w_type
        #
        name = rffi.constcharp2str(hpygetset.c_name)
        doc = fset = fget = fdel = None
        if hpygetset.c_doc:
            doc = rffi.constcharp2str(hpygetset.c_doc)
        if hpygetset.c_getter_impl:
            fget = getset_get
        if hpygetset.c_setter_impl:
            fset = getset_set
            # XXX: write a test to check that 'del' works
            #fdel = ...
        GetSetProperty.__init__(self, fget, fset, fdel, doc,
                                cls=None, use_closure=True,
                                tag="hpy_getset", name=name)

    def readonly_attribute(self, space):   # overwritten
        raise NotImplementedError # XXX write a test
        ## raise oefmt(space.w_AttributeError,
        ##     "attribute '%s' of '%N' objects is not writable",
        ##     self.name, self.w_type)



def add_getset(space, w_type, hpygetset):
    w_descr = W_HPyGetSetProperty(w_type, hpygetset)
    w_type.setdictvalue(space, w_descr.name, w_descr)
