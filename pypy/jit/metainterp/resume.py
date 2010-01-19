import sys, os
from pypy.jit.metainterp.history import Box, Const, ConstInt, INT, REF
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp import jitprof
from pypy.rpython.lltypesystem import rffi
from pypy.rlib import rarithmetic
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.debug import have_debug_prints
from pypy.rlib.debug import debug_start, debug_stop, debug_print

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
    __slots__ = ('prev', 'jitcode', 'pc', 'exception_target')

    def __init__(self, prev, frame):
        self.prev = prev
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

def capture_resumedata(framestack, virtualizable_boxes, virtualref_boxes,
                       storage):
    n = len(framestack)-1
    top = framestack[n]
    _ensure_parent_resumedata(framestack, n)
    frame_info_list = FrameInfo(top.parent_resumedata_frame_info_list,
                                top)
    storage.rd_frame_info_list = frame_info_list
    snapshot = Snapshot(top.parent_resumedata_snapshot, top.env[:])
    snapshot = Snapshot(snapshot, virtualref_boxes[:]) # xxx for now
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

def tagged_list_eq(tl1, tl2):
    if len(tl1) != len(tl2):
        return False
    for i in range(len(tl1)):
        if not tagged_eq(tl1[i], tl2[i]):
            return False
    return True

TAGCONST    = 0
TAGINT      = 1
TAGBOX      = 2
TAGVIRTUAL  = 3

UNASSIGNED = tag(-1<<13, TAGBOX)
UNASSIGNEDVIRTUAL = tag(-1<<13, TAGVIRTUAL)
NULLREF = tag(-1, TAGCONST)


class ResumeDataLoopMemo(object):

    def __init__(self, metainterp_sd):
        self.metainterp_sd = metainterp_sd
        self.cpu = metainterp_sd.cpu
        self.consts = []
        self.large_ints = {}
        self.refs = self.cpu.ts.new_ref_dict_2()
        self.numberings = {}
        self.cached_boxes = {}
        self.cached_virtuals = {}
    
        self.nvirtuals = 0
        self.nvholes = 0
        self.nvreused = 0

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

    # env numbering

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
        self.clear_box_virtual_numbers()

    # caching for virtuals and boxes inside them

    def num_cached_boxes(self):
        return len(self.cached_boxes)

    def assign_number_to_box(self, box, boxes):
        # returns a negative number
        if box in self.cached_boxes:
            num = self.cached_boxes[box]
            boxes[-num-1] = box
        else:
            boxes.append(box)
            num = -len(boxes)
            self.cached_boxes[box] = num
        return num

    def num_cached_virtuals(self):
        return len(self.cached_virtuals)

    def assign_number_to_virtual(self, box):
        # returns a negative number
        if box in self.cached_virtuals:
            num = self.cached_virtuals[box]
        else:
            num = self.cached_virtuals[box] = -len(self.cached_virtuals) - 1
        return num

    def clear_box_virtual_numbers(self):
        self.cached_boxes.clear()
        self.cached_virtuals.clear()

    def update_counters(self, profiler):
        profiler.count(jitprof.NVIRTUALS, self.nvirtuals)
        profiler.count(jitprof.NVHOLES, self.nvholes)
        profiler.count(jitprof.NVREUSED, self.nvreused)

_frame_info_placeholder = (None, 0, 0)

class ResumeDataVirtualAdder(object):

    def __init__(self, storage, memo):
        self.storage = storage
        self.memo = memo

    def make_virtual(self, known_class, fielddescrs):
        return VirtualInfo(known_class, fielddescrs)

    def make_vstruct(self, typedescr, fielddescrs):
        return VStructInfo(typedescr, fielddescrs)

    def make_varray(self, arraydescr):
        return VArrayInfo(arraydescr)

    def register_virtual_fields(self, virtualbox, fieldboxes):
        tagged = self.liveboxes_from_env.get(virtualbox, UNASSIGNEDVIRTUAL)
        self.liveboxes[virtualbox] = tagged
        self.vfieldboxes[virtualbox] = fieldboxes
        self._register_boxes(fieldboxes)

    def register_box(self, box):
        if (isinstance(box, Box) and box not in self.liveboxes_from_env
                                 and box not in self.liveboxes):
            self.liveboxes[box] = UNASSIGNED

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

    def finish(self, values, pending_setfields=[]):
        # compute the numbering
        storage = self.storage
        # make sure that nobody attached resume data to this guard yet
        assert storage.rd_numb is None
        numb, liveboxes_from_env, v = self.memo.number(values,
                                                       storage.rd_snapshot)
        self.liveboxes_from_env = liveboxes_from_env
        self.liveboxes = {}
        storage.rd_numb = numb
        storage.rd_snapshot = None

        # collect liveboxes and virtuals
        n = len(liveboxes_from_env) - v
        liveboxes = [None]*n
        self.vfieldboxes = {}
        for box, tagged in liveboxes_from_env.iteritems():
            i, tagbits = untag(tagged)
            if tagbits == TAGBOX:
                liveboxes[i] = box
            else:
                assert tagbits == TAGVIRTUAL
                value = values[box]
                value.get_args_for_fail(self)

        for _, box, fieldbox in pending_setfields:
            self.register_box(box)
            self.register_box(fieldbox)
            value = values[fieldbox]
            value.get_args_for_fail(self)

        self._number_virtuals(liveboxes, values, v)
        self._add_pending_fields(pending_setfields)

        storage.rd_consts = self.memo.consts
        dump_storage(storage, liveboxes)
        return liveboxes[:]

    def _number_virtuals(self, liveboxes, values, num_env_virtuals):
        # !! 'liveboxes' is a list that is extend()ed in-place !!
        memo = self.memo
        new_liveboxes = [None] * memo.num_cached_boxes()
        count = 0
        # So far, self.liveboxes should contain 'tagged' values that are
        # either UNASSIGNED, UNASSIGNEDVIRTUAL, or a *non-negative* value
        # with the TAGVIRTUAL.  The following loop removes the UNASSIGNED
        # and UNASSIGNEDVIRTUAL entries, and replaces them with real
        # negative values.
        for box, tagged in self.liveboxes.iteritems():
            i, tagbits = untag(tagged)
            if tagbits == TAGBOX:
                assert box not in self.liveboxes_from_env
                assert tagged_eq(tagged, UNASSIGNED)
                index = memo.assign_number_to_box(box, new_liveboxes)
                self.liveboxes[box] = tag(index, TAGBOX)
                count += 1
            else:
                assert tagbits == TAGVIRTUAL
                if tagged_eq(tagged, UNASSIGNEDVIRTUAL):
                    assert box not in self.liveboxes_from_env
                    index = memo.assign_number_to_virtual(box)
                    self.liveboxes[box] = tag(index, TAGVIRTUAL)
                else:
                    assert i >= 0
        new_liveboxes.reverse()
        liveboxes.extend(new_liveboxes)
        nholes = len(new_liveboxes) - count

        storage = self.storage
        storage.rd_virtuals = None
        vfieldboxes = self.vfieldboxes
        if vfieldboxes:
            length = num_env_virtuals + memo.num_cached_virtuals()
            virtuals = storage.rd_virtuals = [None] * length
            memo.nvirtuals += length
            memo.nvholes += length - len(vfieldboxes)
            for virtualbox, fieldboxes in vfieldboxes.iteritems():
                num, _ = untag(self.liveboxes[virtualbox])
                value = values[virtualbox]
                fieldnums = [self._gettagged(box)
                             for box in fieldboxes]
                vinfo = value.make_virtual_info(self, fieldnums)
                # if a new vinfo instance is made, we get the fieldnums list we
                # pass in as an attribute. hackish.
                if vinfo.fieldnums is not fieldnums:
                    memo.nvreused += 1
                virtuals[num] = vinfo

        if self._invalidation_needed(len(liveboxes), nholes):
            memo.clear_box_virtual_numbers()           

    def _invalidation_needed(self, nliveboxes, nholes):
        memo = self.memo
        # xxx heuristic a bit out of thin air
        failargs_limit = memo.metainterp_sd.options.failargs_limit
        if nliveboxes > (failargs_limit // 2):
            if nholes > nliveboxes//3:
                return True
        return False

    def _add_pending_fields(self, pending_setfields):
        rd_pendingfields = None
        if pending_setfields:
            rd_pendingfields = []
            for descr, box, fieldbox in pending_setfields:
                num = self._gettagged(box)
                fieldnum = self._gettagged(fieldbox)
                rd_pendingfields.append((descr, num, fieldnum))
        self.storage.rd_pendingfields = rd_pendingfields

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
    def equals(self, fieldnums):
        return tagged_list_eq(self.fieldnums, fieldnums)
    def set_content(self, fieldnums):
        self.fieldnums = fieldnums


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

    def debug_prints(self):
        assert len(self.fielddescrs) == len(self.fieldnums)
        for i in range(len(self.fielddescrs)):
            debug_print("\t\t",
                        str(self.fielddescrs[i]),
                        str(untag(self.fieldnums[i])))

class VirtualInfo(AbstractVirtualStructInfo):
    def __init__(self, known_class, fielddescrs):
        AbstractVirtualStructInfo.__init__(self, fielddescrs)
        self.known_class = known_class

    def allocate(self, metainterp):
        return metainterp.execute_and_record(rop.NEW_WITH_VTABLE,
                                             None, self.known_class)

    def debug_prints(self):
        debug_print("\tvirtualinfo", self.known_class.repr_rpython())
        AbstractVirtualStructInfo.debug_prints(self)

class VStructInfo(AbstractVirtualStructInfo):
    def __init__(self, typedescr, fielddescrs):
        AbstractVirtualStructInfo.__init__(self, fielddescrs)
        self.typedescr = typedescr

    def allocate(self, metainterp):
        return metainterp.execute_and_record(rop.NEW, self.typedescr)

    def debug_prints(self):
        debug_print("\tvstructinfo", self.typedescr.repr_rpython())
        AbstractVirtualStructInfo.debug_prints(self)

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

    def debug_prints(self):
        debug_print("\tvarrayinfo", self.arraydescr)
        for i in self.fieldnums:
            debug_print("\t\t", str(untag(i)))


def rebuild_from_resumedata(metainterp, newboxes, storage,
                            expects_virtualizables):
    resumereader = ResumeDataReader(storage, newboxes, metainterp)
    virtualizable_boxes = None
    if expects_virtualizables:
        virtualizable_boxes = resumereader.consume_boxes()
    virtualref_boxes = resumereader.consume_boxes()
    frameinfo = storage.rd_frame_info_list
    while True:
        env = resumereader.consume_boxes()
        f = metainterp.newframe(frameinfo.jitcode)
        f.setup_resume_at_op(frameinfo.pc, frameinfo.exception_target, env)
        frameinfo = frameinfo.prev
        if frameinfo is None:
            break
    metainterp.framestack.reverse()
    return virtualizable_boxes, virtualref_boxes

def force_from_resumedata(metainterp, newboxes, storage,
                          expects_virtualizables):
    resumereader = ResumeDataReader(storage, newboxes, metainterp)
    virtualizable_boxes = None
    if expects_virtualizables:
        virtualizable_boxes = resumereader.consume_boxes()
    virtualref_boxes = resumereader.consume_boxes()
    return virtualizable_boxes, virtualref_boxes, resumereader.virtuals


class ResumeDataReader(object):
    virtuals = None

    def __init__(self, storage, liveboxes, metainterp=None):
        self.cur_numb = storage.rd_numb
        self.consts = storage.rd_consts
        self.liveboxes = liveboxes
        self.cpu = metainterp.cpu
        self._prepare_virtuals(metainterp, storage.rd_virtuals)
        self._prepare_pendingfields(metainterp, storage.rd_pendingfields)

    def _prepare_virtuals(self, metainterp, virtuals):
        if virtuals:
            v = metainterp._already_allocated_resume_virtuals
            if v is not None:
                self.virtuals = v
                return
            self.virtuals = [None] * len(virtuals)
            for i in range(len(virtuals)):
                vinfo = virtuals[i]
                if vinfo is not None:
                    self.virtuals[i] = vinfo.allocate(metainterp)
            for i in range(len(virtuals)):
                vinfo = virtuals[i]
                if vinfo is not None:
                    vinfo.setfields(metainterp, self.virtuals[i],
                                    self._decode_box)

    def _prepare_pendingfields(self, metainterp, pendingfields):
        if pendingfields:
            if metainterp._already_allocated_resume_virtuals is not None:
                return
            for descr, num, fieldnum in pendingfields:
                box = self._decode_box(num)
                fieldbox = self._decode_box(fieldnum)
                metainterp.execute_and_record(rop.SETFIELD_GC,
                                              descr, box, fieldbox)

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

def dump_storage(storage, liveboxes):
    "For profiling only."
    from pypy.rlib.objectmodel import compute_unique_id
    debug_start("jit-resume")
    if have_debug_prints():
        debug_print('Log storage', compute_unique_id(storage))
        frameinfo = storage.rd_frame_info_list
        while frameinfo is not None:
            try:
                jitcodename = frameinfo.jitcode.name
            except AttributeError:
                jitcodename = str(compute_unique_id(frameinfo.jitcode))
            debug_print('\tjitcode/pc', jitcodename,
                        frameinfo.pc, frameinfo.exception_target,
                        'at', compute_unique_id(frameinfo))
            frameinfo = frameinfo.prev
        numb = storage.rd_numb
        while numb is not None:
            debug_print('\tnumb', str([untag(i) for i in numb.nums]),
                        'at', compute_unique_id(numb))
            numb = numb.prev
        for const in storage.rd_consts:
            debug_print('\tconst', const.repr_rpython())
        for box in liveboxes:
            if box is None:
                debug_print('\tbox', 'None')
            else:
                debug_print('\tbox', box.repr_rpython())
        if storage.rd_virtuals is not None:
            for virtual in storage.rd_virtuals:
                if virtual is None:
                    debug_print('\t\t', 'None')
                else:
                    virtual.debug_prints()
    debug_stop("jit-resume")
