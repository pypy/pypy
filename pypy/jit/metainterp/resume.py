import sys, os
from pypy.jit.metainterp.history import Box, Const, ConstInt, INT, REF
from pypy.jit.metainterp.resoperation import rop
from pypy.rpython.lltypesystem import rffi
from pypy.rlib import rarithmetic
from pypy.rlib.objectmodel import we_are_translated

# Logic to encode the chain of frames and the state of the boxes at a
# guard operation, and to decode it again.  This is a bit advanced,
# because it needs to support optimize.py which encodes virtuals with
# arbitrary cycles and also to compress the information

class Snapshot(object):
    __slots__ = ('prev', 'boxes')

    def __init__(self, prev, boxes):
        self.prev = prev
        self.boxes = boxes

class FrameInfo(object):
    __slots__ = ('prev', 'jitcode', 'pc', 'exception_target', 'level')

    def __init__(self, prev, frame):
        self.prev = prev
        if prev is None:
            level = 1
        else:
            level = prev.level + 1
        self.level = level
        self.jitcode = frame.jitcode
        self.pc = frame.pc
        self.exception_target = frame.exception_target

def _ensure_parent_resumedata(framestack, n):
    target = framestack[n]
    if n == 0 or target.parent_resumedata_frame_info_list is not None:
        return
    _ensure_parent_resumedata(framestack, n-1)
    back = framestack[n-1]
    target.parent_resumedata_frame_info_list = FrameInfo(
                                         back.parent_resumedata_frame_info_list,
                                         back)
    target.parent_resumedata_snapshot = Snapshot(
                                         back.parent_resumedata_snapshot,
                                         back.env[:])

def capture_resumedata(framestack, virtualizable_boxes, storage):
    n = len(framestack)-1
    top = framestack[n]
    _ensure_parent_resumedata(framestack, n)
    frame_info_list = FrameInfo(top.parent_resumedata_frame_info_list,
                                top)
    storage.rd_frame_info_list = frame_info_list
    snapshot = Snapshot(top.parent_resumedata_snapshot, top.env[:])
    if virtualizable_boxes is not None:
        snapshot = Snapshot(snapshot, virtualizable_boxes[:]) # xxx for now
    storage.rd_snapshot = snapshot

class Numbering(object):
    __slots__ = ('prev', 'nums')

    def __init__(self, prev, nums):
        self.prev = prev
        self.nums = nums

TAGMASK = 3

def tag(value, tagbits):
    if tagbits >> 2:
        raise ValueError
    sx = value >> 13
    if sx != 0 and sx != -1:
        raise ValueError
    return rffi.r_short(value<<2|tagbits)

def untag(value):
    value = rarithmetic.widen(value)
    tagbits = value&TAGMASK
    return value>>2, tagbits

def tagged_eq(x, y):
    # please rpython :(
    return rarithmetic.widen(x) == rarithmetic.widen(y)

TAGCONST    = 0
TAGINT      = 1
TAGBOX      = 2
TAGVIRTUAL  = 3

UNASSIGNED = tag(-1, TAGBOX)
NULLREF = tag(-1, TAGCONST)


class ResumeDataLoopMemo(object):

    def __init__(self, cpu):
        self.cpu = cpu
        self.consts = []
        self.large_ints = {}
        self.refs = cpu.ts.new_ref_dict_2()
        self.numberings = {}

    def getconst(self, const):
        if const.type == INT:
            val = const.getint()
            if not we_are_translated() and not isinstance(val, int):
                # unhappiness, probably a symbolic
                return self._newconst(const)
            try:
                return tag(val, TAGINT)
            except ValueError:
                pass
            tagged = self.large_ints.get(val, UNASSIGNED)
            if not tagged_eq(tagged, UNASSIGNED):
                return tagged
            tagged = self._newconst(const)
            self.large_ints[val] = tagged
            return tagged
        elif const.type == REF:
            val = const.getref_base()
            if not val:
                return NULLREF
            tagged = self.refs.get(val, UNASSIGNED)
            if not tagged_eq(tagged, UNASSIGNED):
                return tagged
            tagged = self._newconst(const)
            self.refs[val] = tagged
            return tagged
        return self._newconst(const)

    def _newconst(self, const):
        result = tag(len(self.consts), TAGCONST)
        self.consts.append(const)
        return result

    def number(self, values, snapshot):
        if snapshot is None:
            return None, {}, 0
        if snapshot in self.numberings:
             numb, liveboxes, v = self.numberings[snapshot]
             return numb, liveboxes.copy(), v

        numb1, liveboxes, v = self.number(values, snapshot.prev)
        n = len(liveboxes)-v
        boxes = snapshot.boxes
        length = len(boxes)
        nums = [UNASSIGNED] * length
        for i in range(length):
            box = boxes[i]
            value = values.get(box, None)
            if value is not None:
                box = value.get_key_box()

            if isinstance(box, Const):
                tagged = self.getconst(box)
            elif box in liveboxes:
                tagged = liveboxes[box]
            else:
                if value is not None and value.is_virtual():
                    tagged = tag(v, TAGVIRTUAL)
                    v += 1
                else:
                    tagged = tag(n, TAGBOX)
                    n += 1
                liveboxes[box] = tagged
            nums[i] = tagged
        numb = Numbering(numb1, nums)
        self.numberings[snapshot] = numb, liveboxes, v
        return numb, liveboxes.copy(), v

    def forget_numberings(self, virtualbox):
        # XXX ideally clear only the affected numberings
        self.numberings.clear()


_frame_info_placeholder = (None, 0, 0)

class ResumeDataVirtualAdder(object):

    def __init__(self, storage, memo, debug_storage=None):
        self.storage = storage
        self.memo = memo
        self.debug_storage = debug_storage
        #self.virtuals = []
        #self.vfieldboxes = []

    def make_virtual(self, virtualbox, known_class, fielddescrs, fieldboxes):
        vinfo = VirtualInfo(known_class, fielddescrs)
        self._make_virtual(virtualbox, vinfo, fieldboxes)

    def make_vstruct(self, virtualbox, typedescr, fielddescrs, fieldboxes):
        vinfo = VStructInfo(typedescr, fielddescrs)
        self._make_virtual(virtualbox, vinfo, fieldboxes)

    def make_varray(self, virtualbox, arraydescr, itemboxes):
        vinfo = VArrayInfo(arraydescr)
        self._make_virtual(virtualbox, vinfo, itemboxes)

    def _make_virtual(self, virtualbox, vinfo, fieldboxes):
        if virtualbox in self.liveboxes_from_env:
            tagged = self.liveboxes_from_env[virtualbox]
            i, _ = untag(tagged)
            assert self.virtuals[i] is None
            self.virtuals[i] = vinfo
            self.vfieldboxes[i] = fieldboxes
        else:
            tagged = tag(len(self.virtuals), TAGVIRTUAL)
            self.virtuals.append(vinfo)
            self.vfieldboxes.append(fieldboxes)
        self.liveboxes[virtualbox] = tagged
        self._register_boxes(fieldboxes)

    def register_box(self, box):
        if (isinstance(box, Box) and box not in self.liveboxes_from_env
                                 and box not in self.liveboxes):
            self.liveboxes[box] = UNASSIGNED
            return True
        return False

    def _register_boxes(self, boxes):
        for box in boxes:
            self.register_box(box)

    def already_seen_virtual(self, virtualbox):
        if virtualbox not in self.liveboxes:
            assert virtualbox in self.liveboxes_from_env
            assert untag(self.liveboxes_from_env[virtualbox])[1] == TAGVIRTUAL
            return False
        tagged = self.liveboxes[virtualbox]
        _, tagbits = untag(tagged)
        return tagbits == TAGVIRTUAL

    def finish(self, values):
        # compute the numbering
        storage = self.storage
        numb, liveboxes_from_env, v = self.memo.number(values, storage.rd_snapshot)
        self.liveboxes_from_env = liveboxes_from_env
        self.liveboxes = {}
        storage.rd_numb = numb
        storage.rd_snapshot = None

        # collect liveboxes and virtuals
        n = len(liveboxes_from_env) - v
        liveboxes = [None]*n
        self.virtuals = [None]*v
        self.vfieldboxes = [None]*v
        for box, tagged in liveboxes_from_env.iteritems():
            i, tagbits = untag(tagged)
            if tagbits == TAGBOX:
                liveboxes[i] = box
            else:
                assert tagbits == TAGVIRTUAL
                value = values[box]
                value.get_args_for_fail(self)

        self._number_virtuals(liveboxes)

        storage.rd_consts = self.memo.consts
        if self.debug_storage:
            dump_storage(self.debug_storage, storage, liveboxes)
        return liveboxes[:]

    def _number_virtuals(self, liveboxes):
        for box, tagged in self.liveboxes.iteritems():
            i, tagbits = untag(tagged)
            if tagbits == TAGBOX:
                assert tagged_eq(tagged, UNASSIGNED)
                self.liveboxes[box] = tag(len(liveboxes), TAGBOX)
                liveboxes.append(box)
            else:
                assert tagbits == TAGVIRTUAL

        storage = self.storage
        storage.rd_virtuals = None
        if len(self.virtuals) > 0:
            storage.rd_virtuals = self.virtuals[:]
            for i in range(len(storage.rd_virtuals)):
                vinfo = storage.rd_virtuals[i]
                fieldboxes = self.vfieldboxes[i]
                vinfo.fieldnums = [self._gettagged(box)
                                   for box in fieldboxes]

    def _gettagged(self, box):
        if isinstance(box, Const):
            return self.memo.getconst(box)
        else:
            if box in self.liveboxes_from_env:
                return self.liveboxes_from_env[box]
            return self.liveboxes[box]

class AbstractVirtualInfo(object):
    def allocate(self, metainterp):
        raise NotImplementedError
    def setfields(self, metainterp, box, fn_decode_box):
        raise NotImplementedError


class AbstractVirtualStructInfo(AbstractVirtualInfo):
    def __init__(self, fielddescrs):
        self.fielddescrs = fielddescrs
        #self.fieldnums = ...

    def setfields(self, metainterp, box, fn_decode_box):
        for i in range(len(self.fielddescrs)):
            fieldbox = fn_decode_box(self.fieldnums[i])
            metainterp.execute_and_record(rop.SETFIELD_GC,
                                          self.fielddescrs[i],
                                          box, fieldbox)

class VirtualInfo(AbstractVirtualStructInfo):
    def __init__(self, known_class, fielddescrs):
        AbstractVirtualStructInfo.__init__(self, fielddescrs)
        self.known_class = known_class

    def allocate(self, metainterp):
        return metainterp.execute_and_record(rop.NEW_WITH_VTABLE,
                                             None, self.known_class)

    def repr_rpython(self):
        return 'VirtualInfo("%s", %s, %s)' % (
            self.known_class,
            ['"%s"' % (fd,) for fd in self.fielddescrs],
            [untag(i) for i in self.fieldnums])

class VStructInfo(AbstractVirtualStructInfo):
    def __init__(self, typedescr, fielddescrs):
        AbstractVirtualStructInfo.__init__(self, fielddescrs)
        self.typedescr = typedescr

    def allocate(self, metainterp):
        return metainterp.execute_and_record(rop.NEW, self.typedescr)

    def repr_rpython(self):
        return 'VStructInfo("%s", %s, %s)' % (
            self.typedescr,
            ['"%s"' % (fd,) for fd in self.fielddescrs],
            [untag(i) for i in self.fieldnums])

class VArrayInfo(AbstractVirtualInfo):
    def __init__(self, arraydescr):
        self.arraydescr = arraydescr
        #self.fieldnums = ...

    def allocate(self, metainterp):
        length = len(self.fieldnums)
        return metainterp.execute_and_record(rop.NEW_ARRAY,
                                             self.arraydescr,
                                             ConstInt(length))

    def setfields(self, metainterp, box, fn_decode_box):
        for i in range(len(self.fieldnums)):
            itembox = fn_decode_box(self.fieldnums[i])
            metainterp.execute_and_record(rop.SETARRAYITEM_GC,
                                          self.arraydescr,
                                          box, ConstInt(i), itembox)

    def repr_rpython(self):
        return 'VArrayInfo("%s", %s)' % (
            self.arraydescr,
            [untag(i) for i in self.fieldnums])


def rebuild_from_resumedata(metainterp, newboxes, storage, expects_virtualizables):
    resumereader = ResumeDataReader(storage, newboxes, metainterp)
    virtualizable_boxes = None
    if expects_virtualizables:
        virtualizable_boxes = resumereader.consume_boxes()
    frameinfo = storage.rd_frame_info_list
    while True:
        env = resumereader.consume_boxes()
        f = metainterp.newframe(frameinfo.jitcode)
        f.setup_resume_at_op(frameinfo.pc, frameinfo.exception_target, env)
        frameinfo = frameinfo.prev
        if frameinfo is None:
            break
    metainterp.framestack.reverse()
    return virtualizable_boxes


class ResumeDataReader(object):
    virtuals = None

    def __init__(self, storage, liveboxes, metainterp=None):
        self.cur_numb = storage.rd_numb
        self.consts = storage.rd_consts
        self.liveboxes = liveboxes
        self.cpu = metainterp.cpu
        self._prepare_virtuals(metainterp, storage.rd_virtuals)

    def _prepare_virtuals(self, metainterp, virtuals):
        if virtuals:
            self.virtuals = [vinfo.allocate(metainterp) for vinfo in virtuals]
            for i in range(len(virtuals)):
                vinfo = virtuals[i]
                vinfo.setfields(metainterp, self.virtuals[i], self._decode_box)

    def consume_boxes(self):
        numb = self.cur_numb
        assert numb is not None
        nums = numb.nums
        n = len(nums)
        boxes = [None] * n
        for i in range(n):
            boxes[i] = self._decode_box(nums[i])
        self.cur_numb = numb.prev
        return boxes

    def _decode_box(self, tagged):
        num, tag = untag(tagged)
        if tag == TAGCONST:
            if tagged_eq(tagged, NULLREF):
                return self.cpu.ts.CONST_NULL
            return self.consts[num]
        elif tag == TAGVIRTUAL:
            virtuals = self.virtuals
            assert virtuals is not None
            return virtuals[num]
        elif tag == TAGINT:
            return ConstInt(num)
        else:
            assert tag == TAGBOX
            return self.liveboxes[num]

# ____________________________________________________________

def dump_storage(logname, storage, liveboxes):
    "For profiling only."
    import os
    from pypy.rlib import objectmodel
    assert logname is not None    # annotator hack
    fd = os.open(logname, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0666)
    os.write(fd, 'Log(%d, [\n' % objectmodel.compute_unique_id(storage))
    frameinfo = storage.rd_frame_info_list
    while True:
        os.write(fd, '\t("%s", %d, %d) at %xd,\n' % (
            frameinfo.jitcode, frameinfo.pc, frameinfo.exception_target,
            objectmodel.compute_unique_id(frameinfo)))
        frameinfo = frameinfo.prev
        if frameinfo is None:
            break
    os.write(fd, '\t],\n\t[\n')
    numb = storage.rd_numb
    while True:
        os.write(fd, '\t\t%s at %xd,\n' % ([untag(i) for i in numb.nums],
                                           objectmodel.compute_unique_id(numb)))
        numb = numb.prev
        if numb is None:
            break
    os.write(fd, '\t], [\n')
    for const in storage.rd_consts:
        os.write(fd, '\t"%s",\n' % (const.repr_rpython(),))
    os.write(fd, '\t], [\n')
    for box in liveboxes:
        os.write(fd, '\t"%s",\n' % (box.repr_rpython(),))
    os.write(fd, '\t], [\n')
    if storage.rd_virtuals is not None:
        for virtual in storage.rd_virtuals:
            os.write(fd, '\t%s,\n' % (virtual.repr_rpython(),))
    os.write(fd, '\t])\n')
    os.close(fd)
