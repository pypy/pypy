
from rpython.jit.metainterp.resoperation import AbstractValue, ResOperation,\
     rop

""" The tag field on PtrOptInfo has a following meaning:

lower two bits are LEVEL
"""

LEVEL_UNKNOWN    = 0
LEVEL_NONNULL    = 1
LEVEL_KNOWNCLASS = 2     # might also mean KNOWNARRAYDESCR, for arrays
LEVEL_CONSTANT   = 3

MODE_ARRAY   = '\x00'
MODE_STR     = '\x01'
MODE_UNICODE = '\x02'

INFO_NULL = 0
INFO_NONNULL = 1
INFO_UNKNOWN = 2

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


class AbstractStructPtrInfo(NonNullPtrInfo):
    _attrs_ = ('_is_virtual', '_fields')

    def force_box(self, op, optforce):
        if self._is_virtual:
            op.set_forwarded(None)
            optforce.emit_operation(op)
            newop = optforce.getlastop()
            op.set_forwarded(newop)
            newop.set_forwarded(self)
            self._is_virtual = False
            if self._fields is not None:
                descr = op.getdescr()
                for i, flddescr in enumerate(descr.all_fielddescrs):
                    fld = self._fields[i]
                    if fld is not None:
                        subbox = optforce.force_box(fld)
                        op = ResOperation(rop.SETFIELD_GC, [op, subbox],
                                          descr=flddescr)
                        optforce.emit_operation(op)
            return newop
        return op

    def init_fields(self, descr):
        self._fields = [None] * len(descr.all_fielddescrs)

    def setfield_virtual(self, descr, op):
        self._fields[descr.index] = op

    def getfield_virtual(self, descr):
        return self._fields[descr.index]

    def is_virtual(self):
        return self._is_virtual

class InstancePtrInfo(AbstractStructPtrInfo):
    _attrs_ = ('_known_class')
    _fields = None

    def __init__(self, known_class=None, is_virtual=False):
        self._known_class = known_class
        self._is_virtual = is_virtual

    def get_known_class(self, cpu):
        return self._known_class
    
class StructPtrInfo(NonNullPtrInfo):
    _attrs_ = ('is_virtual', '_fields')

    
class ArrayPtrInfo(NonNullPtrInfo):
    _attrs_ = ('is_virtual', 'length', '_items')

    
class StrPtrInfo(NonNullPtrInfo):
    _attrs_ = ()


class ConstPtrInfo(PtrInfo):
    _attrs_ = ('_const',)
    
    def __init__(self, const):
        self._const = const

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
