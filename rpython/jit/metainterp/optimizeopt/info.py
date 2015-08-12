
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.jit.metainterp.resoperation import AbstractValue, ResOperation,\
     rop, OpHelpers
from rpython.jit.metainterp.history import ConstInt, Const
from rpython.rtyper.lltypesystem import lltype
from rpython.jit.metainterp.optimizeopt.rawbuffer import RawBuffer, InvalidRawOperation


INFO_NULL = 0
INFO_NONNULL = 1
INFO_UNKNOWN = 2

class AbstractInfo(AbstractValue):
    _attrs_ = ()
    
    is_info_class = True

    def force_box(self, op, optforce):
        return op

    def getconst(self):
        raise Exception("not a constant")

    
class PtrInfo(AbstractInfo):
    _attrs_ = ()

    def is_nonnull(self):
        return False

    def is_null(self):
        return False

    def is_virtual(self):
        return False

    def get_known_class(self, cpu):
        return None

    def getnullness(self):
        if self.is_null():
            return INFO_NULL
        elif self.is_nonnull():
            return INFO_NONNULL
        return INFO_UNKNOWN

    def same_info(self, other):
        return self is other

    def getstrlen(self, op, string_optimizer, mode, create_ops=True):
        return None

    def copy_fields_to_const(self, constinfo, optheap):
        pass

    def make_guards(self, op, short):
        pass
    
class NonNullPtrInfo(PtrInfo):
    _attrs_ = ('last_guard_pos',)
    last_guard_pos = -1
    
    def is_nonnull(self):
        return True

    def get_known_class(self, cpu):
        return None

    def get_last_guard(self, optimizer):
        if self.last_guard_pos == -1:
            return None
        return optimizer._newoperations[self.last_guard_pos]

    def get_last_guard_pos(self):
        return self.last_guard_pos

    def reset_last_guard_pos(self):
        self.last_guard_pos = -1

    def mark_last_guard(self, optimizer):
        self.last_guard_pos = len(optimizer._newoperations) - 1
        assert self.get_last_guard(optimizer).is_guard()

    def visitor_walk_recursive(self, instbox, visitor, optimizer):
        if visitor.already_seen_virtual(instbox):
            return
        return self._visitor_walk_recursive(instbox, visitor, optimizer)

    def make_guards(self, op, short):
        op = ResOperation(rop.GUARD_NONNULL, [op], None)
        short.append(op)

class AbstractVirtualPtrInfo(NonNullPtrInfo):
    _attrs_ = ('_cached_vinfo', 'vdescr')
    # XXX merge _cached_vinfo with vdescr

    _cached_vinfo = None
    vdescr = None

    def force_box(self, op, optforce):
        if self.is_virtual():
            optforce.forget_numberings()
            op.set_forwarded(None)
            optforce._emit_operation(op)
            newop = optforce.getlastop()
            op.set_forwarded(newop)
            newop.set_forwarded(self)
            descr = self.vdescr
            self.vdescr = None
            self._force_elements(newop, optforce, descr)
            return newop
        return op

    def is_virtual(self):
        return self.vdescr is not None

class AbstractStructPtrInfo(AbstractVirtualPtrInfo):
    _attrs_ = ('_fields',)
    _fields = None

    def init_fields(self, descr, index):
        if self._fields is None:
            self._fields = [None] * len(descr.get_all_fielddescrs())
        if index >= len(self._fields):
            # we found out a subclass with more fields
            extra_len = len(descr.get_all_fielddescrs()) - len(self._fields)
            self._fields = self._fields + [None] * extra_len

    def clear_cache(self):
        assert not self.is_virtual()
        self._fields = [None] * len(self._fields)

    def copy_fields_to_const(self, constinfo, optheap):
        if self._fields is not None:
            info = constinfo._get_info(optheap)
            info._fields = self._fields[:]

    def all_items(self):
        return self._fields

    def setfield(self, descr, struct, op, optheap=None, cf=None):
        self.init_fields(descr.get_parent_descr(), descr.get_index())
        assert isinstance(op, AbstractValue)
        self._fields[descr.get_index()] = op
        if cf is not None:
            assert not self.is_virtual()
            assert struct is not None
            cf.register_dirty_field(struct, self)

    def getfield(self, descr, optheap=None):
        self.init_fields(descr.get_parent_descr(), descr.get_index())
        return self._fields[descr.get_index()]

    def _force_elements(self, op, optforce, descr):
        if self._fields is None:
            return
        for i, flddescr in enumerate(descr.get_all_fielddescrs()):
            fld = self._fields[i]
            if fld is not None:
                subbox = optforce.force_box(fld)
                setfieldop = ResOperation(rop.SETFIELD_GC, [op, subbox],
                                          descr=flddescr)
                optforce._emit_operation(setfieldop)
                if optforce.optheap is not None:
                    optforce.optheap.register_dirty_field(flddescr, op, self)

    def _visitor_walk_recursive(self, instbox, visitor, optimizer):
        lst = self.vdescr.get_all_fielddescrs()
        assert self.is_virtual()
        visitor.register_virtual_fields(instbox,
                                        [optimizer.get_box_replacement(box)
                                         for box in self._fields])
        for i in range(len(lst)):
            op = self._fields[i]
            if op:
                op = op.get_box_replacement()
                fieldinfo = optimizer.getptrinfo(op)
                if fieldinfo and fieldinfo.is_virtual():
                    fieldinfo.visitor_walk_recursive(op, visitor, optimizer)

    def produce_short_preamble_ops(self, structbox, descr, index, optimizer,
                                   shortboxes):
        op = optimizer.get_box_replacement(self._fields[descr.get_index()])
        opnum = OpHelpers.getfield_for_descr(descr)
        getfield_op = ResOperation(opnum, [structbox], descr=descr)
        shortboxes.add_heap_op(op, getfield_op)

class InstancePtrInfo(AbstractStructPtrInfo):
    _attrs_ = ('_known_class',)
    _fields = None

    def __init__(self, known_class=None, vdescr=None):
        self._known_class = known_class
        self.vdescr = vdescr

    def get_known_class(self, cpu):
        return self._known_class

    @specialize.argtype(1)
    def visitor_dispatch_virtual_type(self, visitor):
        fielddescrs = self.vdescr.get_all_fielddescrs()
        assert self.is_virtual()
        return visitor.visit_virtual(self.vdescr, fielddescrs)

    def make_guards(self, op, short):
        if self._known_class is not None:
            op = ResOperation(rop.GUARD_NONNULL_CLASS, [op, self._known_class],
                              None)
            short.append(op)
        else:
            AbstractStructPtrInfo.make_guards(self, op, short)

class StructPtrInfo(AbstractStructPtrInfo):
    def __init__(self, vdescr=None):
        self.vdescr = vdescr

    @specialize.argtype(1)
    def visitor_dispatch_virtual_type(self, visitor):
        fielddescrs = self.vdescr.get_all_fielddescrs()
        assert self.is_virtual()
        return visitor.visit_vstruct(self.vdescr, fielddescrs)

class AbstractRawPtrInfo(AbstractVirtualPtrInfo):
    def _visitor_walk_recursive(self, op, visitor, optimizer):
        raise NotImplementedError("abstract")

    @specialize.argtype(1)
    def visitor_dispatch_virtual_type(self, visitor):
        raise NotImplementedError("abstract")

class RawBufferPtrInfo(AbstractRawPtrInfo):
    buffer = None
    
    def __init__(self, cpu, size=-1):
        self.size = size
        if self.size != -1:
            self.buffer = RawBuffer(cpu, None)

    def getitem_raw(self, offset, itemsize, descr):
        if not self.is_virtual():
            raise InvalidRawOperation
            # see 'test_virtual_raw_buffer_forced_but_slice_not_forced'
            # for the test above: it's not enough to check is_virtual()
            # on the original object, because it might be a VRawSliceValue
            # instead.  If it is a virtual one, then we'll reach here anway.
        return self.buffer.read_value(offset, itemsize, descr)

    def setitem_raw(self, offset, itemsize, descr, itemop):
        if not self.is_virtual():
            raise InvalidRawOperation
        self.buffer.write_value(offset, itemsize, descr, itemop)

    def is_virtual(self):
        return self.size != -1

    def _force_elements(self, op, optforce, descr):
        self.size = -1
        for i in range(len(self.buffer.offsets)):
            # write the value
            offset = self.buffer.offsets[i]
            descr = self.buffer.descrs[i]
            itembox = self.buffer.values[i]
            setfield_op = ResOperation(rop.RAW_STORE,
                              [op, ConstInt(offset), itembox], descr=descr)
            optforce.emit_operation(setfield_op)

    def _visitor_walk_recursive(self, op, visitor, optimizer):
        itemboxes = self.buffer.values
        visitor.register_virtual_fields(op, itemboxes)
        # there can be no virtuals stored in raw buffer

    @specialize.argtype(1)
    def visitor_dispatch_virtual_type(self, visitor):
        return visitor.visit_vrawbuffer(self.size,
                                        self.buffer.offsets[:],
                                        self.buffer.descrs[:])

class RawStructPtrInfo(AbstractRawPtrInfo):
    def __init__(self):
        pass

    def is_virtual(self):
        return False

class RawSlicePtrInfo(AbstractRawPtrInfo):
    def __init__(self, offset, parent):
        self.offset = offset
        self.parent = parent

    def is_virtual(self):
        return self.parent is not None

    def getitem_raw(self, offset, itemsize, descr):
        return self.parent.getitem_raw(self.offset+offset, itemsize, descr)

    def setitem_raw(self, offset, itemsize, descr, itemop):
        self.parent.setitem_raw(self.offset+offset, itemsize, descr, itemop)
    
    def _force_elements(self, op, optforce, descr):
        if self.parent.is_virtual():
            self.parent._force_elements(op, optforce, descr)
        self.parent = None

    def _visitor_walk_recursive(self, op, visitor, optimizer):
        source_op = optimizer.get_box_replacement(op.getarg(0))
        visitor.register_virtual_fields(op, [source_op])
        self.parent.visitor_walk_recursive(source_op, visitor, optimizer)

    @specialize.argtype(1)
    def visitor_dispatch_virtual_type(self, visitor):
        return visitor.visit_vrawslice(self.offset)

class ArrayPtrInfo(AbstractVirtualPtrInfo):
    _attrs_ = ('length', '_items', 'lenbound', '_clear')

    _items = None
    lenbound = None
    length = -1

    def __init__(self, const=None, size=0, clear=False, vdescr=None):
        from rpython.jit.metainterp.optimizeopt import intutils
        self.vdescr = vdescr
        if vdescr is not None:
            self._init_items(const, size, clear)
            self.lenbound = intutils.ConstIntBound(size)
        self._clear = clear

    def getlenbound(self):
        from rpython.jit.metainterp.optimizeopt import intutils
        
        if self.lenbound is None:
            assert self.length == -1
            self.lenbound = intutils.IntLowerBound(0)
        return self.lenbound

    def _init_items(self, const, size, clear):
        self.length = size
        if clear:
            self._items = [const] * size
        else:
            self._items = [None] * size

    def all_items(self):
        return self._items

    def copy_fields_to_const(self, constinfo, optheap):
        if self._items is not None:
            info = constinfo._get_array_info(optheap)
            info._items = self._items[:]

    def _force_elements(self, op, optforce, descr):
        arraydescr = op.getdescr()
        for i in range(self.length):
            item = self._items[i]
            if item is not None:
                subbox = optforce.force_box(item)
                setop = ResOperation(rop.SETARRAYITEM_GC,
                                     [op, ConstInt(i), subbox],
                                      descr=arraydescr)
                optforce._emit_operation(setop)
                if optforce.optheap is not None:
                    optforce.optheap.register_dirty_array_field(op,
                        arraydescr, i, self)
        optforce.pure_from_args(rop.ARRAYLEN_GC, [op], ConstInt(len(self._items)))

    def setitem(self, index, struct_op, op, cf=None, optheap=None):
        if self._items is None:
            self._items = [None] * (index + 1)
        if index >= len(self._items):
            self._items = self._items + [None] * (index - len(self._items) + 1)
        self._items[index] = op
        if cf is not None:
            assert not self.is_virtual()
            cf.register_dirty_field(struct_op, self)

    def getitem(self, index, optheap=None):
        if self._items is None or index >= len(self._items):
            return None
        return self._items[index]

    def getlength(self):
        return self.length

    def _visitor_walk_recursive(self, instbox, visitor, optimizer):
        itemops = [optimizer.get_box_replacement(item)
                   for item in self._items]
        visitor.register_virtual_fields(instbox, itemops)
        for i in range(self.getlength()):
            itemop = self._items[i]
            if (itemop is not None and
                not isinstance(itemop, Const)):
                ptrinfo = optimizer.getptrinfo(itemop)
                if ptrinfo and ptrinfo.is_virtual():
                    ptrinfo.visitor_walk_recursive(itemop, visitor, optimizer)

    @specialize.argtype(1)
    def visitor_dispatch_virtual_type(self, visitor):
        return visitor.visit_varray(self.vdescr, self._clear)

    def produce_short_preamble_ops(self, structbox, descr, index, optimizer,
                                   shortboxes):
        item = self._items[index]
        if item is not None:
            op = optimizer.get_box_replacement(item)
            opnum = OpHelpers.getarrayitem_for_descr(descr)
            getarrayitem_op = ResOperation(opnum, [structbox, ConstInt(index)],
                                           descr=descr)
            shortboxes.add_heap_op(op, getarrayitem_op)

    def make_guards(self, op, short):
        AbstractVirtualPtrInfo.make_guards(self, op, short)
        if self.lenbound is not None:
            lenop = ResOperation(rop.ARRAYLEN_GC, [op])
            short.append(lenop)
            self.lenbound.make_guards(lenop, short)

class ArrayStructInfo(ArrayPtrInfo):
    def __init__(self, size, vdescr=None):
        self.length = size
        lgt = len(vdescr.get_all_fielddescrs())
        self.vdescr = vdescr
        self._items = [None] * (size * lgt)

    def _compute_index(self, index, fielddescr):
        all_fdescrs = fielddescr.get_arraydescr().get_all_fielddescrs()
        if all_fdescrs is None:
            return 0 # annotation hack
        one_size = len(all_fdescrs)
        return index * one_size + fielddescr.get_field_descr().get_index()
        
    def setinteriorfield_virtual(self, index, fielddescr, fld):
        index = self._compute_index(index, fielddescr)
        self._items[index] = fld

    def getinteriorfield_virtual(self, index, fielddescr):
        index = self._compute_index(index, fielddescr)
        return self._items[index]

    def _force_elements(self, op, optforce, descr):
        i = 0
        fielddescrs = op.getdescr().get_all_fielddescrs()
        for index in range(self.length):
            for flddescr in fielddescrs:
                fld = self._items[i]
                if fld is not None:
                    subbox = optforce.force_box(fld)
                    setfieldop = ResOperation(rop.SETINTERIORFIELD_GC,
                                              [op, ConstInt(index), subbox],
                                              descr=flddescr)
                    optforce._emit_operation(setfieldop)
                    # heapcache does not work for interiorfields
                    # if it does, we would need a fix here
                i += 1

    def _visitor_walk_recursive(self, instbox, visitor, optimizer):
        itemops = [optimizer.get_box_replacement(item)
                   for item in self._items]
        visitor.register_virtual_fields(instbox, itemops)
        fielddescrs = self.vdescr.get_all_fielddescrs()
        i = 0
        for index in range(self.getlength()):
            for flddescr in fielddescrs:
                itemop = self._items[i]
                if (itemop is not None and
                    not isinstance(itemop, Const)):
                    ptrinfo = optimizer.getptrinfo(itemop)
                    if ptrinfo and ptrinfo.is_virtual():
                        ptrinfo.visitor_walk_recursive(itemop, visitor,
                                                       optimizer)
                i += 1

    @specialize.argtype(1)
    def visitor_dispatch_virtual_type(self, visitor):
        flddescrs = self.vdescr.get_all_fielddescrs()
        return visitor.visit_varraystruct(self.vdescr, self.getlength(),
                                          flddescrs)

class ConstPtrInfo(PtrInfo):
    _attrs_ = ('_const',)
    
    def __init__(self, const):
        self._const = const

    def getconst(self):
        return self._const

    def _get_info(self, optheap):
        ref = self._const.getref_base()
        info = optheap.const_infos.get(ref, None)
        if info is None:
            info = StructPtrInfo()
            optheap.const_infos[ref] = info
        return info

    def _get_array_info(self, optheap):
        ref = self._const.getref_base()
        info = optheap.const_infos.get(ref, None)
        if info is None:
            info = ArrayPtrInfo()
            optheap.const_infos[ref] = info
        return info        

    def getfield(self, descr, optheap=None):
        info = self._get_info(optheap)
        return info.getfield(descr)

    def getitem(self, index, optheap=None):
        info = self._get_array_info(optheap)
        return info.getitem(index)

    def setitem(self, index, op, cf=None, optheap=None):
        info = self._get_array_info(optheap)
        info.setitem(index, op, cf)

    def setfield(self, descr, struct, op, optheap=None, cf=None):
        info = self._get_info(optheap)
        info.setfield(descr, struct, op, optheap, cf)

    def is_null(self):
        return not bool(self._const.getref_base())

    def is_nonnull(self):
        return bool(self._const.getref_base())

    def is_virtual(self):
        return False

    def get_known_class(self, cpu):
        if not self._const.nonnull():
            return None
        return cpu.ts.cls_of_box(self._const)

    def same_info(self, other):
        if not isinstance(other, ConstPtrInfo):
            return False
        return self._const.same_constant(other._const)

    def get_last_guard(self, optimizer):
        return None

    def is_constant(self):
        return True

    # --------------------- vstring -------------------

    @specialize.arg(1)
    def _unpack_str(self, mode):
        return mode.hlstr(lltype.cast_opaque_ptr(
            lltype.Ptr(mode.LLTYPE), self._const.getref_base()))

    @specialize.arg(2)
    def get_constant_string_spec(self, optforce, mode):
        return self._unpack_str(mode)

    def getlenbound(self, mode):
        from rpython.jit.metainterp.optimizeopt.intutils import ConstIntBound
        
        return ConstIntBound(self.getstrlen(None, None, mode).getint())
    
    def getstrlen(self, op, string_optimizer, mode, create_ops=True):
        from rpython.jit.metainterp.optimizeopt import vstring
        
        if mode is vstring.mode_string:
            s = self._unpack_str(vstring.mode_string)
            if s is None:
                return None
            return ConstInt(len(s))
        else:
            s = self._unpack_str(vstring.mode_unicode)            
            if s is None:
                return None
            return ConstInt(len(s))

    def string_copy_parts(self, op, string_optimizer, targetbox, offsetbox,
                          mode):
        from rpython.jit.metainterp.optimizeopt import vstring
        from rpython.jit.metainterp.optimizeopt.optimizer import CONST_0

        lgt = self.getstrlen(op, string_optimizer, mode, False)
        return vstring.copy_str_content(string_optimizer, self._const,
                                        targetbox, CONST_0, offsetbox,
                                        lgt, mode)

    
