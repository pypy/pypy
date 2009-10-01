import sys
from pypy.jit.metainterp.history import Box, Const, ConstInt
from pypy.jit.metainterp.resoperation import rop

# Logic to encode the chain of frames and the state of the boxes at a
# guard operation, and to decode it again.  This is a bit advanced,
# because it needs to support optimize.py which encodes virtuals with
# arbitrary cycles.

# XXX I guess that building the data so that it is as compact as possible
# on the 'storage' object would be a big win.

debug = False

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

 
VIRTUAL_FLAG = int((sys.maxint+1) // 2)
assert not (VIRTUAL_FLAG & (VIRTUAL_FLAG-1))    # a power of two

_frame_info_placeholder = (None, 0, 0)

class ResumeDataVirtualAdder(object):

    def __init__(self, storage):
        self.storage = storage
        self.liveboxes = {}
        self.consts = []
        self.virtuals = []
        self.vfieldboxes = []

    def walk_snapshots(self, values):
        nnums = 0
        snapshot = self.storage.rd_snapshot
        assert snapshot
        while True: # at least one
            boxes = snapshot.boxes
            nnums += len(boxes)+1
            for box in boxes:
                if box in values:
                    value = values[box]
                    value.register_value(self)
                else:
                    self.register_box(box)
            snapshot = snapshot.prev
            if snapshot is None:
                break
        self.nnums = nnums

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
        vinfo = VArrayInfo(arraydescr)
        self._make_virtual(virtualbox, vinfo, itemboxes)

    def _make_virtual(self, virtualbox, vinfo, fieldboxes):
        assert self.liveboxes[virtualbox] == 0
        self.liveboxes[virtualbox] = len(self.virtuals) | VIRTUAL_FLAG
        self.virtuals.append(vinfo)
        self.vfieldboxes.append(fieldboxes)
        self._register_boxes(fieldboxes)

    def register_box(self, box):
        if isinstance(box, Box) and box not in self.liveboxes:
            self.liveboxes[box] = 0
            return True
        return False
                
    def _register_boxes(self, boxes):
        for box in boxes:
            self.register_box(box)

    def is_virtual(self, virtualbox):
        return self.liveboxes[virtualbox] >= VIRTUAL_FLAG

    def _flatten_frame_info(self):
        storage = self.storage        
        frame_info_list = storage.rd_frame_info_list
        storage.rd_frame_info_list = None
        j = frame_info_list.level
        frame_infos = [_frame_info_placeholder]*j
        j -= 1
        while True: # at least one
            frame_infos[j] = (frame_info_list.jitcode, frame_info_list.pc,
                              frame_info_list.exception_target)
            frame_info_list = frame_info_list.prev
            if frame_info_list is None:
                break
            j -= 1
        storage.rd_frame_infos = frame_infos        

    def finish(self, values):
        self._flatten_frame_info()
        storage = self.storage
        liveboxes = []
        for box in self.liveboxes.iterkeys():
            if self.liveboxes[box] == 0:
                self.liveboxes[box] = len(liveboxes)
                liveboxes.append(box)
        nums = storage.rd_nums = [0]*self.nnums
        i = self.nnums-1
        snapshot = self.storage.rd_snapshot
        while True: # at least one
            boxes = snapshot.boxes
            nums[i] = -1
            i -= 1
            for j in range(len(boxes)-1, -1, -1):
                box = boxes[j]
                if box in values:
                    box = values[box].get_key_box()
                nums[i] = self._getboxindex(box)
                i -= 1
            snapshot = snapshot.prev
            if snapshot is None:
                break
        storage.rd_virtuals = None
        if len(self.virtuals) > 0:
            storage.rd_virtuals = self.virtuals[:]
            for i in range(len(storage.rd_virtuals)):
                vinfo = storage.rd_virtuals[i]
                fieldboxes = self.vfieldboxes[i]
                vinfo.fieldnums = [self._getboxindex(box)
                                   for box in fieldboxes]
        storage.rd_consts = self.consts[:]
        storage.rd_snapshot = None
        if debug:
            dump_storage(storage)
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
            self.fieldnums)

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
            self.fieldnums)

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
        return 'VArrayInfo("%s", %s)' % (self.arraydescr,
                                         self.fieldnums)


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

# ____________________________________________________________

def dump_storage(storage):
    "For profiling only."
    import os
    from pypy.rlib import objectmodel
    fd = os.open('log.storage', os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0666)
    os.write(fd, 'Log(%d, [\n' % objectmodel.compute_unique_id(storage))
    for frame_info in storage.rd_frame_infos:
        os.write(fd, '\t("%s", %d, %d),\n' % frame_info)
    os.write(fd, '\t],\n\t%s,\n' % (storage.rd_nums,))
    os.write(fd, '\t[\n')
    for const in storage.rd_consts:
        os.write(fd, '\t"%s",\n' % (const.repr_rpython(),))
    os.write(fd, '\t], [\n')
    if storage.rd_virtuals is not None:
        for virtual in storage.rd_virtuals:
            os.write(fd, '\t%s,\n' % (virtual.repr_rpython(),))
    os.write(fd, '\t])\n')
    os.close(fd)
