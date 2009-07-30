import sys
from pypy.jit.metainterp.history import Box, Const, ConstInt
from pypy.jit.metainterp.resoperation import rop

# Logic to encode the chain of frames and the state of the boxes at a
# FAIL operation, and to decode it again.  This is a bit advanced,
# because it needs to support optimize.py which encodes virtuals with
# arbitrary cycles.

# XXX I guess that building the data so that it is compact as possible
# on the 'storage' object would be a big win.


class ResumeDataBuilder(object):

    def __init__(self):
        self.memo = {}
        self.liveboxes = []
        self.consts = []
        self.nums = []
        self.frame_infos = []

    def generate_boxes(self, boxes):
        for box in boxes:
            assert box is not None
            if isinstance(box, Box):
                try:
                    num = self.memo[box]
                except KeyError:
                    num = len(self.liveboxes)
                    self.liveboxes.append(box)
                    self.memo[box] = num
            else:
                num = -2 - len(self.consts)
                self.consts.append(box)
            self.nums.append(num)
        self.nums.append(-1)

    def generate_frame_info(self, *frame_info):
        self.frame_infos.append(frame_info)

    def finish(self, storage):
        storage.rd_frame_infos = self.frame_infos[:]
        storage.rd_nums = self.nums[:]
        storage.rd_consts = self.consts[:]
        storage.rd_virtuals = None
        return self.liveboxes


VIRTUAL_FLAG = int((sys.maxint+1) // 2)
assert not (VIRTUAL_FLAG & (VIRTUAL_FLAG-1))    # a power of two

class ResumeDataVirtualAdder(object):

    def __init__(self, storage, liveboxes):
        self.storage = storage
        self.nums = storage.rd_nums[:]
        self.consts = storage.rd_consts[:]
        assert storage.rd_virtuals is None
        self.original_liveboxes = liveboxes
        self.liveboxes = {}
        self.liveboxes_order = []
        self._register_boxes(liveboxes)
        self.virtuals = []
        self.vfieldboxes = []

    def make_constant(self, box, const):
        # this part of the interface is not used so far by optimizeopt.py
        if self.liveboxes[box] == 0:
            self.liveboxes[box] = self._getconstindex(const)

    def make_virtual(self, virtualbox, known_class, fielddescrs, fieldboxes):
        vinfo = VirtualInfo(known_class, fielddescrs)
        self._make_virtual(virtualbox, vinfo, fieldboxes)

    def make_vstruct(self, virtualbox, typedescr, fielddescrs, fieldboxes):
        vinfo = VStructInfo(typedescr, fielddescrs)
        self._make_virtual(virtualbox, vinfo, fieldboxes)

    def make_varray(self, virtualbox, arraydescr, itemboxes):
        vinfo = VArrayInfo(arraydescr, len(itemboxes))
        self._make_virtual(virtualbox, vinfo, itemboxes)

    def _make_virtual(self, virtualbox, vinfo, fieldboxes):
        assert self.liveboxes[virtualbox] == 0
        self.liveboxes[virtualbox] = len(self.virtuals) | VIRTUAL_FLAG
        self.virtuals.append(vinfo)
        self.vfieldboxes.append(fieldboxes)
        self._register_boxes(fieldboxes)

    def _register_boxes(self, boxes):
        for box in boxes:
            if isinstance(box, Box) and box not in self.liveboxes:
                self.liveboxes[box] = 0
                self.liveboxes_order.append(box)

    def is_virtual(self, virtualbox):
        return self.liveboxes[virtualbox] >= VIRTUAL_FLAG

    def finish(self):
        storage = self.storage
        liveboxes = []
        for box in self.liveboxes_order:
            if self.liveboxes[box] == 0:
                self.liveboxes[box] = len(liveboxes)
                liveboxes.append(box)
        for i in range(len(storage.rd_nums)):
            num = storage.rd_nums[i]
            if num >= 0:
                box = self.original_liveboxes[num]
                storage.rd_nums[i] = self._getboxindex(box)
        storage.rd_virtuals = self.virtuals[:]
        for i in range(len(storage.rd_virtuals)):
            vinfo = storage.rd_virtuals[i]
            fieldboxes = self.vfieldboxes[i]
            vinfo.fieldnums = [self._getboxindex(box) for box in fieldboxes]
        storage.rd_consts = self.consts[:]
        return liveboxes

    def _getboxindex(self, box):
        if isinstance(box, Const):
            return self._getconstindex(box)
        else:
            return self.liveboxes[box]

    def _getconstindex(self, const):
        result = -2 - len(self.consts)
        self.consts.append(const)
        return result


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
                                          [box, fieldbox],
                                          descr=self.fielddescrs[i])

class VirtualInfo(AbstractVirtualStructInfo):
    def __init__(self, known_class, fielddescrs):
        AbstractVirtualStructInfo.__init__(self, fielddescrs)
        self.known_class = known_class

    def allocate(self, metainterp):
        return metainterp.execute_and_record(rop.NEW_WITH_VTABLE,
                                             [self.known_class])

class VStructInfo(AbstractVirtualStructInfo):
    def __init__(self, typedescr, fielddescrs):
        AbstractVirtualStructInfo.__init__(self, fielddescrs)
        self.typedescr = typedescr

    def allocate(self, metainterp):
        return metainterp.execute_and_record(rop.NEW, [],
                                             descr=self.typedescr)

class VArrayInfo(AbstractVirtualInfo):
    def __init__(self, arraydescr, length):
        self.arraydescr = arraydescr
        self.length = length
        #self.fieldnums = ...

    def allocate(self, metainterp):
        return metainterp.execute_and_record(rop.NEW_ARRAY,
                                             [ConstInt(self.length)],
                                             descr=self.arraydescr)

    def setfields(self, metainterp, box, fn_decode_box):
        for i in range(self.length):
            itembox = fn_decode_box(self.fieldnums[i])
            metainterp.execute_and_record(rop.SETARRAYITEM_GC,
                                          [box, ConstInt(i), itembox],
                                          descr=self.arraydescr)


class ResumeDataReader(object):
    i_frame_infos = 0
    i_boxes = 0
    virtuals = None

    def __init__(self, storage, liveboxes, metainterp=None):
        self.frame_infos = storage.rd_frame_infos
        self.nums = storage.rd_nums
        self.consts = storage.rd_consts
        self.liveboxes = liveboxes
        self._prepare_virtuals(metainterp, storage.rd_virtuals)

    def _prepare_virtuals(self, metainterp, virtuals):
        if virtuals:
            self.virtuals = [vinfo.allocate(metainterp) for vinfo in virtuals]
            for i in range(len(virtuals)):
                vinfo = virtuals[i]
                vinfo.setfields(metainterp, self.virtuals[i], self._decode_box)

    def consume_boxes(self):
        boxes = []
        while True:
            num = self.nums[self.i_boxes]
            self.i_boxes += 1
            if num == -1:
                break
            boxes.append(self._decode_box(num))
        return boxes

    def _decode_box(self, num):
        if num < 0:
            return self.consts[-2 - num]
        elif num & VIRTUAL_FLAG:
            virtuals = self.virtuals
            assert virtuals is not None
            return virtuals[num - VIRTUAL_FLAG]
        else:
            return self.liveboxes[num]

    def has_more_frame_infos(self):
        return self.i_frame_infos < len(self.frame_infos)

    def consume_frame_info(self):
        frame_info = self.frame_infos[self.i_frame_infos]
        self.i_frame_infos += 1
        return frame_info
