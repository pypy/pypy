
""" Interpreter-level implementation of structure, exposing ll-structure
to app-level with apropriate interface
"""

from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable,\
     Arguments
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, wrap_oserror
# XXX we've got the very same info in two places - one is native_fmttable
# the other one is in rlib/libffi, we should refactor it to reuse the same
# logic, I'll not touch it by now, and refactor it later
from pypy.module.struct.nativefmttable import native_fmttable
from pypy.module._ffi.interp_ffi import wrap_result

def unpack_fields(space, w_fields):
    fields_w = space.unpackiterable(w_fields)
    fields = []
    for w_tup in fields_w:
        l_w = space.unpackiterable(w_tup)
        if not len(l_w) == 2:
            raise OperationError(space.w_ValueError, space.wrap(
                "Expected list of 2-size tuples"))
        fields.append((space.str_w(l_w[0]), space.str_w(l_w[1])))
    return fields

def size_and_pos(fields):
    size = native_fmttable[fields[0][1]]['size']
    pos = [0]
    for i in range(1, len(fields)):
        field_desc = native_fmttable[fields[i][1]]
        missing = size % field_desc.get('alignment', 1)
        if missing:
            size += field_desc['alignment'] - missing
        pos.append(size)
        size += field_desc['size']
    return size, pos

class W_StructureInstance(Wrappable):
    def __init__(self, space, w_shape, w_address, w_fieldinits):
        if space.is_true(w_fieldinits):
            raise OperationError(space.w_ValueError, space.wrap(
                "Fields should be not initialized with values by now"))
        w_fields = space.getattr(w_shape, space.wrap('fields'))
        fields = unpack_fields(space, w_fields)
        size, pos = size_and_pos(fields)
        self.fields = fields
        if space.is_true(w_address):
            self.free_afterwards = False
            self.ll_buffer = rffi.cast(rffi.VOIDP, space.int_w(w_address))
        else:
            self.free_afterwards = True
            self.ll_buffer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw',
                                           zero=True)
        self.ll_positions = pos
        self.next_pos = 0

    def cast_pos(self, ll_t):
        i = self.next_pos
        pos = rffi.ptradd(self.ll_buffer, self.ll_positions[i])
        TP = rffi.CArrayPtr(ll_t)
        return rffi.cast(TP, pos)[0]
    cast_pos._annspecialcase_ = 'specialize:arg(1)'

    def getattr(self, space, attr):
        if attr.startswith('tm'):
            pass
        for i in range(len(self.fields)):
            name, c = self.fields[i]
            if name == attr:
                # XXX RPython-trick for passing lambda around
                self.next_pos = i
                return wrap_result(space, c, self.cast_pos)
        raise OperationError(space.w_AttributeError, space.wrap(
            "C Structure has no attribute %s" % name))
    getattr.unwrap_spec = ['self', ObjSpace, str]

    def setattr(self, space, attr, value):
        # XXX value is now always int, needs fixing
        for i in range(len(self.fields)):
            name, c = self.fields[i]
            if name == attr:
                pos = rffi.ptradd(self.ll_buffer, self.ll_positions[i])
                TP = rffi.CArrayPtr(rffi.INT)
                rffi.cast(TP, pos)[0] = value
                return
    setattr.unwrap_spec = ['self', ObjSpace, str, int]

    def __del__(self):
        if self.free_afterwards:
            lltype.free(self.ll_buffer, flavor='raw')

def descr_new_structure_instance(space, w_type, w_shape, w_adr, w_fieldinits):
    return W_StructureInstance(space, w_shape, w_adr, w_fieldinits)

W_StructureInstance.typedef = TypeDef(
    'StructureInstance',
    __new__     = interp2app(descr_new_structure_instance),
    __getattr__ = interp2app(W_StructureInstance.getattr),
    __setattr__ = interp2app(W_StructureInstance.setattr),
)
