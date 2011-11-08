from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib import clibffi
from pypy.rlib import libffi
from pypy.rlib import jit
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import operationerrfmt
from pypy.objspace.std.typetype import type_typedef
from pypy.module._ffi.interp_ffitype import W_FFIType, app_types

class W_Field(Wrappable):

    def __init__(self, name, w_ffitype):
        self.name = name
        self.w_ffitype = w_ffitype
        self.offset = -1

    def __repr__(self):
        return '<Field %s %s>' % (self.name, self.w_ffitype.name)

@unwrap_spec(name=str)
def descr_new_field(space, w_type, name, w_ffitype):
    w_ffitype = space.interp_w(W_FFIType, w_ffitype)
    return W_Field(name, w_ffitype)

W_Field.typedef = TypeDef(
    'Field',
    __new__ = interp2app(descr_new_field),
    name = interp_attrproperty('name', W_Field),
    ffitype = interp_attrproperty('w_ffitype', W_Field),
    offset = interp_attrproperty('offset', W_Field),
    )


# ==============================================================================

class W__StructDescr(Wrappable):

    def __init__(self, space, name, fields_w, ffistruct):
        self.space = space
        self.ffistruct = ffistruct
        self.w_ffitype = W_FFIType('struct %s' % name, ffistruct.ffistruct, None)
        self.fields_w = fields_w
        self.name2w_field = {}
        for w_field in fields_w:
            self.name2w_field[w_field.name] = w_field

    def allocate(self, space):
        return W__StructInstance(self)

    @jit.elidable_promote('0')
    def get_type_and_offset_for_field(self, name):
        try:
            w_field = self.name2w_field[name]
        except KeyError:
            raise operationerrfmt(self.space.w_AttributeError, '%s', name)

        return w_field.w_ffitype, w_field.offset

    def __del__(self):
        if self.ffistruct:
            lltype.free(self.ffistruct, flavor='raw')


@unwrap_spec(name=str)
def descr_new_structdescr(space, w_type, name, w_fields):
    fields_w = space.fixedview(w_fields)
    # note that the fields_w returned by compute_size_and_alignement has a
    # different annotation than the original: list(W_Root) vs list(W_Field)
    size, alignment, fields_w = compute_size_and_alignement(space, fields_w)
    field_types = [] # clibffi's types
    for w_field in fields_w:
        field_types.append(w_field.w_ffitype.ffitype)
    ffistruct = clibffi.make_struct_ffitype_e(size, alignment, field_types)
    return W__StructDescr(space, name, fields_w, ffistruct)

def round_up(size, alignment):
    return (size + alignment - 1) & -alignment

def compute_size_and_alignement(space, fields_w):
    size = 0
    alignment = 1
    fields_w2 = []
    for w_field in fields_w:
        w_field = space.interp_w(W_Field, w_field)
        fieldsize = w_field.w_ffitype.sizeof()
        fieldalignment = w_field.w_ffitype.get_alignment()
        alignment = max(alignment, fieldalignment)
        size = round_up(size, fieldalignment)
        w_field.offset = size
        size += fieldsize
        fields_w2.append(w_field)
    #
    size = round_up(size, alignment)
    return size, alignment, fields_w2



W__StructDescr.typedef = TypeDef(
    '_StructDescr',
    __new__ = interp2app(descr_new_structdescr),
    ffitype = interp_attrproperty('w_ffitype', W__StructDescr),
    allocate = interp2app(W__StructDescr.allocate),
    )


# ==============================================================================

class W__StructInstance(Wrappable):

    _immutable_fields_ = ['structdescr', 'rawmem']

    def __init__(self, structdescr):
        self.structdescr = structdescr
        size = structdescr.w_ffitype.sizeof()
        self.rawmem = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw',
                                    zero=True, add_memory_pressure=True)

    def __del__(self):
        if self.rawmem:
            lltype.free(self.rawmem, flavor='raw')
            self.rawmem = lltype.nullptr(rffi.VOIDP.TO)

    def getaddr(self, space):
        addr = rffi.cast(rffi.ULONG, self.rawmem)
        return space.wrap(addr)

    @unwrap_spec(name=str)
    def getfield(self, space, name):
        w_ffitype, offset = self.structdescr.get_type_and_offset_for_field(name)
        value = libffi.struct_getfield_int(w_ffitype.ffitype, self.rawmem, offset)
        return space.wrap(value)

    @unwrap_spec(name=str)
    def setfield(self, space, name, w_value):
        w_ffitype, offset = self.structdescr.get_type_and_offset_for_field(name)
        # XXX: add support for long long
        if w_ffitype.is_signed() or w_ffitype.is_unsigned():
            value = rffi.cast(rffi.LONG, space.uint_w(w_value))
        #
        libffi.struct_setfield_int(w_ffitype.ffitype, self.rawmem, offset, value)



W__StructInstance.typedef = TypeDef(
    '_StructInstance',
    getaddr  = interp2app(W__StructInstance.getaddr),
    getfield = interp2app(W__StructInstance.getfield),
    setfield = interp2app(W__StructInstance.setfield),
    )
