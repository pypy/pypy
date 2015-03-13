
from rpython.jit.metainterp.resoperation import AbstractValue, ResOperation,\
     rop
from rpython.jit.metainterp.history import ConstInt

""" The tag field on PtrOptInfo has a following meaning:

lower two bits are LEVEL
"""


MODE_ARRAY   = '\x00'
MODE_STR     = '\x01'
MODE_UNICODE = '\x02'
MODE_INSTANCE = '\x03'
MODE_STRUCT = '\x04'

INFO_NULL = 0
INFO_NONNULL = 1
INFO_UNKNOWN = 2

FLAG_VIRTUAL = 1

class AbstractInfo(AbstractValue):
    is_info_class = True

    def force_box(self, op, optforce):
        return op

    
class PtrInfo(AbstractInfo):
    _attrs_ = ()

    def is_nonnull(self):
        return False

    def is_null(self):
        return False

    def is_virtual(self):
        return False

    def getnullness(self):
        if self.is_null():
            return INFO_NULL
        elif self.is_nonnull():
            return INFO_NONNULL
        return INFO_UNKNOWN

    
class NonNullPtrInfo(PtrInfo):
    _attrs_ = ()

    def is_nonnull(self):
        return True

class AbstractVirtualPtrInfo(NonNullPtrInfo):
    _attrs_ = ('flags',)

    flags = 0

    def force_box(self, op, optforce):
        if self.is_virtual():
            op.set_forwarded(None)
            optforce.emit_operation(op)
            newop = optforce.getlastop()
            op.set_forwarded(newop)
            newop.set_forwarded(self)
            self.flags &= ~FLAG_VIRTUAL # clean the virtual flag
            self._force_elements(newop, optforce)
            return newop
        return op

    def is_virtual(self):
        return self.flags & FLAG_VIRTUAL

class AbstractStructPtrInfo(AbstractVirtualPtrInfo):
    _attrs_ = ('_fields',)

    def init_fields(self, descr):
        self._fields = [None] * len(descr.all_fielddescrs)

    def clear_cache(self):
        assert self.flags & FLAG_VIRTUAL == 0
        self.flags = 0
        self._fields = [None] * len(self._fields)

    def setfield(self, descr, op, optheap=None):
        if not self.is_virtual():
            if self._fields[descr.index] is not None:
                assert optheap is not None
                # we should only call it with virtuals without optheap
                optheap.register_dirty_field(descr, self)
        self._fields[descr.index] = op

    def getfield(self, descr, optheap=None):
        return self._fields[descr.index]

    def _force_elements(self, op, optforce):
        if self._fields is None:
            return 0
        descr = op.getdescr()
        count = 0
        for i, flddescr in enumerate(descr.all_fielddescrs):
            fld = self._fields[i]
            if fld is not None:
                subbox = optforce.force_box(fld)
                setfieldop = ResOperation(rop.SETFIELD_GC, [op, subbox],
                                          descr=flddescr)
                optforce.emit_operation(setfieldop)
                optforce.optheap.register_dirty_field(flddescr, self)
                count += 1
        return count

class InstancePtrInfo(AbstractStructPtrInfo):
    _attrs_ = ('_known_class')
    _fields = None

    def __init__(self, known_class=None, is_virtual=False):
        self._known_class = known_class
        if is_virtual:
            self.flags = FLAG_VIRTUAL

    def get_known_class(self, cpu):
        return self._known_class
    
class StructPtrInfo(AbstractStructPtrInfo):
    def __init__(self, is_virtual=False):
        if is_virtual:
            self.flags = FLAG_VIRTUAL
    
class ArrayPtrInfo(AbstractVirtualPtrInfo):
    _attrs_ = ('length', '_items', '_descr')

    def __init__(self, descr, const, size, clear, is_virtual):
        if is_virtual:
            self.flags = FLAG_VIRTUAL
        self.length = size
        if clear:
            self._items = [const] * size
        else:
            self._items = [None] * size

    def _force_elements(self, op, optforce):
        arraydescr = op.getdescr()
        count = 0
        for i in range(self.length):
            item = self._items[i]
            if item is not None:
                subbox = optforce.force_box(item)
                setop = ResOperation(rop.SETARRAYITEM_GC,
                                     [op, ConstInt(i), subbox],
                                      descr=arraydescr)
                optforce.emit_operation(setop)
                # xxxx optforce.optheap
                count += 1
        return count

    def setitem_virtual(self, index, item):
        self._items[index] = item

    def getitem_virtual(self, index):
        return self._items[index]

    def getlength(self):
        return self.length

class ArrayStructInfo(ArrayPtrInfo):
    def __init__(self, descr, size, is_virtual):
        self.length = size
        lgt = len(descr.all_interiorfielddescrs)
        if is_virtual:
            self.flags = FLAG_VIRTUAL
        self._items = [None] * (size * lgt)

    def _compute_index(self, index, fielddescr):
        one_size = len(fielddescr.arraydescr.all_interiorfielddescrs)
        return index * one_size + fielddescr.fielddescr.index
        
    def setinteriorfield_virtual(self, index, fielddescr, fld):
        index = self._compute_index(index, fielddescr)
        self._items[index] = fld

    def getinteriorfield_virtual(self, index, fielddescr):
        index = self._compute_index(index, fielddescr)
        return self._items[index]

    def _force_elements(self, op, optforce):
        i = 0
        fielddescrs = op.getdescr().all_interiorfielddescrs
        count = 0
        for index in range(self.length):
            for flddescr in fielddescrs:
                fld = self._items[i]
                if fld is not None:
                    subbox = optforce.force_box(fld)
                    setfieldop = ResOperation(rop.SETINTERIORFIELD_GC,
                                              [op, ConstInt(index), subbox],
                                              descr=flddescr)
                    optforce.emit_operation(setfieldop)
                    # XXX optforce.optheap
                    count += 1
                i += 1
        return count
    
class StrPtrInfo(NonNullPtrInfo):
    _attrs_ = ()


class ConstPtrInfo(PtrInfo):
    _attrs_ = ('_const',)
    
    def __init__(self, const):
        self._const = const

    def _get_info(self, descr, optheap):
        ref = self._const.getref_base()
        info = optheap.const_infos.get(ref, None)
        if info is None:
            info = StructPtrInfo()
            info.init_fields(descr.parent_descr)
            optheap.const_infos[ref] = info
        return info

    def getfield(self, descr, optheap=None):
        info = self._get_info(descr, optheap)
        return info.getfield(descr)

    def setfield(self, descr, op, optheap):
        info = self._get_info(descr, optheap)
        info.setfield(descr, op, optheap)

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
    
class XPtrOptInfo(AbstractInfo):
    _attrs_ = ('_tag', 'known_class', 'last_guard_pos', 'lenbound')
    is_info_class = True

    _tag = 0
    known_class = None
    last_guard_pos = -1
    lenbound = None

    #def __init__(self, level=None, known_class=None, intbound=None):
    #    OptValue.__init__(self, box, level, None, intbound)
    #    if not isinstance(box, Const):
    #        self.known_class = known_class

    def getlevel(self):
        return self._tag & 0x3

    def setlevel(self, level):
        self._tag = (self._tag & (~0x3)) | level

    def __repr__(self):
        level = {LEVEL_UNKNOWN: 'UNKNOWN',
                 LEVEL_NONNULL: 'NONNULL',
                 LEVEL_KNOWNCLASS: 'KNOWNCLASS',
                 LEVEL_CONSTANT: 'CONSTANT'}.get(self.getlevel(),
                                                 self.getlevel())
        return '<%s %s %s>' % (
            self.__class__.__name__,
            level,
            self.box)

    def make_len_gt(self, mode, descr, val):
        if self.lenbound:
            if self.lenbound.mode != mode or self.lenbound.descr != descr:
                # XXX a rare case?  it seems to occur sometimes when
                # running lib-python's test_io.py in PyPy on Linux 32...
                from rpython.jit.metainterp.optimize import InvalidLoop
                raise InvalidLoop("bad mode/descr")
            self.lenbound.bound.make_gt(IntBound(val, val))
        else:
            self.lenbound = LenBound(mode, descr, IntLowerBound(val + 1))

    def make_nonnull(self, optimizer):
        assert self.getlevel() < LEVEL_NONNULL
        self.setlevel(LEVEL_NONNULL)
        if optimizer is not None:
            self.last_guard_pos = len(optimizer._newoperations) - 1
            assert self.get_last_guard(optimizer).is_guard()

    def make_constant_class(self, optimizer, classbox):
        assert self.getlevel() < LEVEL_KNOWNCLASS
        self.known_class = classbox
        self.setlevel(LEVEL_KNOWNCLASS)
        if optimizer is not None:
            self.last_guard_pos = len(optimizer._newoperations) - 1
            assert self.get_last_guard(optimizer).is_guard()

    def import_from(self, other, optimizer):
        OptValue.import_from(self, other, optimizer)
        if self.getlevel() != LEVEL_CONSTANT:
            if other.getlenbound():
                if self.lenbound:
                    assert other.getlenbound().mode == self.lenbound.mode
                    assert other.getlenbound().descr == self.lenbound.descr
                    self.lenbound.bound.intersect(other.getlenbound().bound)
                else:
                    self.lenbound = other.getlenbound().clone()

    def make_guards(self, box):
        guards = []
        level = self.getlevel()
        if level == LEVEL_CONSTANT:
            op = ResOperation(rop.GUARD_VALUE, [box, self.box], None)
            guards.append(op)
        elif level == LEVEL_KNOWNCLASS:
            op = ResOperation(rop.GUARD_NONNULL_CLASS,
                              [box, self.known_class], None)
            guards.append(op)
        else:
            if level == LEVEL_NONNULL:
                op = ResOperation(rop.GUARD_NONNULL, [box], None)
                guards.append(op)
            if self.lenbound:
                lenbox = BoxInt()
                if self.lenbound.mode == MODE_ARRAY:
                    op = ResOperation(rop.ARRAYLEN_GC, [box], lenbox, self.lenbound.descr)
                elif self.lenbound.mode == MODE_STR:
                    op = ResOperation(rop.STRLEN, [box], lenbox, self.lenbound.descr)
                elif self.lenbound.mode == MODE_UNICODE:
                    op = ResOperation(rop.UNICODELEN, [box], lenbox, self.lenbound.descr)
                else:
                    debug_print("Unknown lenbound mode")
                    assert False
                guards.append(op)
                self.lenbound.bound.make_guards(lenbox, guards)
        return guards

    def get_constant_class(self, cpu):
        level = self.getlevel()
        if level == LEVEL_KNOWNCLASS:
            return self.known_class
        elif level == LEVEL_CONSTANT and not self.is_null():
            return cpu.ts.cls_of_box(self.box)
        else:
            return None

    def getlenbound(self):
        return self.lenbound

    def get_last_guard(self, optimizer):
        if self.last_guard_pos == -1:
            return None
        return optimizer._newoperations[self.last_guard_pos]

    def get_known_class(self):
        return self.known_class
