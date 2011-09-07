from pypy.rpython.lltypesystem import lltype
from pypy.rlib import clibffi
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.objspace.std.typetype import type_typedef
from pypy.module._ffi.interp_ffitype import W_FFIType

class W_Field(Wrappable):

    def __init__(self, name, w_ffitype):
        self.name = name
        self.w_ffitype = w_ffitype
        self.offset = -1

    @staticmethod
    @unwrap_spec(name=str)
    def descr_new(space, w_type, name, w_ffitype):
        w_ffitype = space.interp_w(W_FFIType, w_ffitype)
        return W_Field(name, w_ffitype)

W_Field.typedef = TypeDef(
    'Field',
    __new__ = interp2app(W_Field.descr_new),
    name = interp_attrproperty('name', W_Field),
    ffitype = interp_attrproperty('w_ffitype', W_Field),
    offset = interp_attrproperty('offset', W_Field),
    )


# ==============================================================================


class W__StructDescr(Wrappable):

    def __init__(self, name, ffistruct):
        self.ffistruct = ffistruct
        self.ffitype = W_FFIType('struct %s' % name, ffistruct.ffistruct, 'fixme')

    @staticmethod
    @unwrap_spec(name=str)
    def descr_new(space, w_type, name, w_fields):
        size = 0
        alignment = 0 # XXX
        fields_w = space.fixedview(w_fields)
        field_types = []
        for w_field in fields_w:
            w_field = space.interp_w(W_Field, w_field)
            w_field.offset = size # XXX: alignment!
            size += w_field.w_ffitype.sizeof()
            field_types.append(w_field.w_ffitype.ffitype)
        #
        ffistruct = clibffi.make_struct_ffitype_e(size, alignment, field_types)
        return W__StructDescr(name, ffistruct)

    def __del__(self):
        if self.ffistruct:
            lltype.free(self.ffistruct, flavor='raw')


W__StructDescr.typedef = TypeDef(
    '_StructDescr',
    __new__ = interp2app(W__StructDescr.descr_new),
    ffitype = interp_attrproperty('ffitype', W__StructDescr),
    )

