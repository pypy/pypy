
""" Interpreter-level implementation of structure, exposing ll-structure
to app-level with apropriate interface
"""

from pypy.interpreter.baseobjspace import W_Root, Wrappable
from pypy.interpreter.gateway import interp2app, ObjSpace
from pypy.interpreter.typedef import interp_attrproperty
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, wrap_oserror, operationerrfmt
from pypy.module._rawffi.interp_rawffi import segfault_exception
from pypy.module._rawffi.interp_rawffi import W_DataShape, W_DataInstance
from pypy.module._rawffi.interp_rawffi import wrap_value, unwrap_value
from pypy.module._rawffi.interp_rawffi import unpack_to_size_alignment
from pypy.rlib import libffi
from pypy.rlib.rarithmetic import intmask, r_uint

def unpack_fields(space, w_fields):
    fields_w = space.unpackiterable(w_fields)
    fields = []
    for w_tup in fields_w:
        l_w = space.unpackiterable(w_tup)
        if not len(l_w) == 2:
            raise OperationError(space.w_ValueError, space.wrap(
                "Expected list of 2-size tuples"))
        name = space.str_w(l_w[0])
        tp = unpack_to_size_alignment(space, l_w[1])
        fields.append((name, tp))
    return fields

def round_up(size, alignment):
    return (size + alignment - 1) & -alignment

def size_alignment_pos(fields):
    size = 0
    alignment = 1
    pos = []
    for fieldname, (letter, fieldsize, fieldalignment) in fields:
        size = round_up(size, fieldalignment)
        alignment = max(alignment, fieldalignment)
        pos.append(size)
        size += intmask(fieldsize)
    size = round_up(size, alignment)
    return size, alignment, pos


class W_Structure(W_DataShape):
    def __init__(self, space, fields, size, alignment):
        name_to_index = {}
        if fields is not None:
            for i in range(len(fields)):
                name, tp = fields[i]
                if name in name_to_index:
                    raise operationerrfmt(space.w_ValueError,
                        "duplicate field name %s", name)
                name_to_index[name] = i
            size, alignment, pos = size_alignment_pos(fields)
        else: # opaque case
            fields = []
            pos = []
        self.fields = fields
        self.size = size
        self.alignment = alignment                
        self.ll_positions = pos
        self.name_to_index = name_to_index

    def allocate(self, space, length, autofree=False):
        # length is ignored!
        if autofree:
            return W_StructureInstanceAutoFree(space, self)
        return W_StructureInstance(space, self, 0)

    def getindex(self, space, attr):
        try:
            return self.name_to_index[attr]
        except KeyError:
            raise operationerrfmt(space.w_AttributeError,
                "C Structure has no attribute %s", attr)

    def descr_call(self, space, autofree=False):
        return space.wrap(self.allocate(space, 1, autofree))
    descr_call.unwrap_spec = ['self', ObjSpace, int]

    def descr_repr(self, space):
        fieldnames = ' '.join(["'%s'" % name for name, _ in self.fields])
        return space.wrap("<_rawffi.Structure %s (%d, %d)>" % (fieldnames,
                                                               self.size,
                                                               self.alignment))
    descr_repr.unwrap_spec = ['self', ObjSpace]

    def fromaddress(self, space, address):
        return space.wrap(W_StructureInstance(space, self, address))
    fromaddress.unwrap_spec = ['self', ObjSpace, r_uint]

    def descr_fieldoffset(self, space, attr):
        index = self.getindex(space, attr)
        return space.wrap(self.ll_positions[index])
    descr_fieldoffset.unwrap_spec = ['self', ObjSpace, str]

    def _size_alignment(self):
        return self.size, self.alignment

    # get the corresponding ffi_type
    ffi_type = lltype.nullptr(libffi.FFI_TYPE_P.TO)

    def get_ffi_type(self):
        if not self.ffi_type:
            self.ffi_type = libffi.make_struct_ffitype(self.size,
                                                       self.alignment)
        return self.ffi_type
    
    def __del__(self):
        if self.ffi_type:
            lltype.free(self.ffi_type, flavor='raw')
    


def descr_new_structure(space, w_type, w_shapeinfo):
    if space.is_true(space.isinstance(w_shapeinfo, space.w_tuple)):
        w_size, w_alignment = space.fixedview(w_shapeinfo, expected_length=2)
        S = W_Structure(space, None, space.int_w(w_size),
                                     space.int_w(w_alignment))
    else:
        fields = unpack_fields(space, w_shapeinfo)
        S = W_Structure(space, fields, 0, 0)
    return space.wrap(S)

W_Structure.typedef = TypeDef(
    'Structure',
    __new__     = interp2app(descr_new_structure),
    __call__    = interp2app(W_Structure.descr_call),
    __repr__    = interp2app(W_Structure.descr_repr),
    fromaddress = interp2app(W_Structure.fromaddress),
    size        = interp_attrproperty('size', W_Structure),
    alignment   = interp_attrproperty('alignment', W_Structure),
    fieldoffset = interp2app(W_Structure.descr_fieldoffset),
    size_alignment = interp2app(W_Structure.descr_size_alignment)
)
W_Structure.typedef.acceptable_as_base_class = False

def push_field(self, num, value):
    ptr = rffi.ptradd(self.ll_buffer, self.shape.ll_positions[num])
    TP = lltype.typeOf(value)
    T = lltype.Ptr(rffi.CArray(TP))
    rffi.cast(T, ptr)[0] = value
push_field._annspecialcase_ = 'specialize:argtype(2)'
    
def cast_pos(self, i, ll_t):
    pos = rffi.ptradd(self.ll_buffer, self.shape.ll_positions[i])
    TP = lltype.Ptr(rffi.CArray(ll_t))
    return rffi.cast(TP, pos)[0]
cast_pos._annspecialcase_ = 'specialize:arg(2)'

class W_StructureInstance(W_DataInstance):
    def __init__(self, space, shape, address):
        W_DataInstance.__init__(self, space, shape.size, address)
        self.shape = shape

    def descr_repr(self, space):
        addr = rffi.cast(lltype.Unsigned, self.ll_buffer)
        return space.wrap("<_rawffi struct %x>" % (addr,))
    descr_repr.unwrap_spec = ['self', ObjSpace]

    def getattr(self, space, attr):
        if not self.ll_buffer:
            raise segfault_exception(space, "accessing NULL pointer")
        i = self.shape.getindex(space, attr)
        _, tp = self.shape.fields[i]
        return wrap_value(space, cast_pos, self, i, tp)
    getattr.unwrap_spec = ['self', ObjSpace, str]

    def setattr(self, space, attr, w_value):
        if not self.ll_buffer:
            raise segfault_exception(space, "accessing NULL pointer")
        i = self.shape.getindex(space, attr)
        _, tp = self.shape.fields[i]
        unwrap_value(space, push_field, self, i, tp[0], w_value)
    setattr.unwrap_spec = ['self', ObjSpace, str, W_Root]

    def descr_fieldaddress(self, space, attr):
        i = self.shape.getindex(space, attr)
        ptr = rffi.ptradd(self.ll_buffer, self.shape.ll_positions[i])
        return space.wrap(rffi.cast(lltype.Unsigned, ptr))
    descr_fieldaddress.unwrap_spec = ['self', ObjSpace, str]

    def getrawsize(self):
        return self.shape.size


W_StructureInstance.typedef = TypeDef(
    'StructureInstance',
    __repr__    = interp2app(W_StructureInstance.descr_repr),
    __getattr__ = interp2app(W_StructureInstance.getattr),
    __setattr__ = interp2app(W_StructureInstance.setattr),
    __buffer__  = interp2app(W_StructureInstance.descr_buffer),
    buffer      = GetSetProperty(W_StructureInstance.getbuffer),
    free        = interp2app(W_StructureInstance.free),
    shape       = interp_attrproperty('shape', W_StructureInstance),
    byptr       = interp2app(W_StructureInstance.byptr),
    fieldaddress= interp2app(W_StructureInstance.descr_fieldaddress),
)
W_StructureInstance.typedef.acceptable_as_base_class = False

class W_StructureInstanceAutoFree(W_StructureInstance):
    def __init__(self, space, shape):
        W_StructureInstance.__init__(self, space, shape, 0)

    def __del__(self):
        if self.ll_buffer:
            self._free()
        
W_StructureInstanceAutoFree.typedef = TypeDef(
    'StructureInstanceAutoFree',
    __repr__    = interp2app(W_StructureInstance.descr_repr),
    __getattr__ = interp2app(W_StructureInstance.getattr),
    __setattr__ = interp2app(W_StructureInstance.setattr),
    __buffer__  = interp2app(W_StructureInstance.descr_buffer),
    buffer      = GetSetProperty(W_StructureInstance.getbuffer),
    shape       = interp_attrproperty('shape', W_StructureInstance),
    byptr       = interp2app(W_StructureInstance.byptr),
    fieldaddress= interp2app(W_StructureInstance.descr_fieldaddress),
)
W_StructureInstanceAutoFree.typedef.acceptable_as_base_class = False
