import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.metainterp.resume import *
from pypy.jit.metainterp.history import BoxInt, BoxPtr, ConstInt, ConstAddr
from pypy.jit.metainterp.history import ConstPtr
from pypy.jit.metainterp.test.test_optimizefindnode import LLtypeMixin
from pypy.jit.metainterp import executor

class Storage:
    pass

def make_demo_storage():
    b1, b2, b3 = [BoxInt(), BoxPtr(), BoxInt()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]
    storage = Storage()
    storage.rd_frame_infos = []
    storage.rd_virtuals = None
    storage.rd_consts = [c1, c2, c3]
    storage.rd_nums = [0, -2, 0, 1, -1,
                       -3, -4, -1,
                       0, 1, 2, -1
                       ]
    return storage

def test_simple():
    storage = make_demo_storage()
    b1s, b2s, b3s = [BoxInt(), BoxPtr(), BoxInt()]
    assert b1s != b3s
    reader = ResumeDataReader(storage, [b1s, b2s, b3s])
    lst = reader.consume_boxes()
    assert lst == [b1s, ConstInt(1), b1s, b2s]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert lst == [b1s, b2s, b3s]


def test_frame_info():
    storage = Storage()
    storage.rd_frame_infos = [(1, 2, 5), (3, 4, 7)]
    storage.rd_consts = []
    storage.rd_nums = []
    storage.rd_virtuals = None
    #
    reader = ResumeDataReader(storage, [])
    assert reader.has_more_frame_infos()
    fi = reader.consume_frame_info()
    assert fi == (1, 2, 5)
    assert reader.has_more_frame_infos()
    fi = reader.consume_frame_info()
    assert fi == (3, 4, 7)
    assert not reader.has_more_frame_infos()

# ____________________________________________________________



class FakeFrame(object):
    parent_resumedata_snapshot = None
    parent_resumedata_frame_info_list = None

    def __init__(self, code, pc, exc_target, *boxes):
        self.jitcode = code
        self.pc = pc
        self.exception_target = exc_target
        self.env = list(boxes)

def test_Snapshot_create():
    l = ['b0', 'b1']
    snap = Snapshot(None, l)
    assert snap.prev is None
    assert snap.boxes is l

    l1 = ['b3']
    snap1 = Snapshot(snap, l1)
    assert snap1.prev is snap
    assert snap1.boxes is l1

def test_FrameInfo_create():
    jitcode = "JITCODE"
    frame = FakeFrame(jitcode, 1, 2)    
    fi = FrameInfo(None, frame)
    assert fi.prev is None
    assert fi.jitcode is jitcode
    assert fi.pc == 1
    assert fi.exception_target == 2
    assert fi.level == 1

    jitcode1 = "JITCODE1"
    frame1 = FakeFrame(jitcode, 3, 4)    
    fi1 = FrameInfo(fi, frame1)
    assert fi1.prev is fi
    assert fi1.jitcode is jitcode
    assert fi1.pc == 3
    assert fi1.exception_target == 4
    assert fi1.level == 2

def test_flatten_resumedata():
    # temporary "expensive" mean to go from the new to the old world
    b1, b2, b3 = [BoxInt(), BoxPtr(), BoxInt()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]    

    env = [b1, c1, b2, b1, c2]
    snap = Snapshot(None, env)
    frame = FakeFrame("JITCODE", 1, 2)    
    fi = FrameInfo(None, frame)
    env1 = [c3, b3, b1, c1]
    snap1 = Snapshot(snap, env1)
    frame1 = FakeFrame("JITCODE1", 3, 4)    
    fi1 = FrameInfo(fi, frame1)

    storage = Storage()
    storage.rd_snapshot = snap1
    storage.rd_frame_info_list = fi1

    liveboxes = flatten_resumedata(storage)
    assert storage.rd_snapshot is None
    assert storage.rd_frame_info_list is None

    assert storage.rd_frame_infos == [("JITCODE", 1, 2),
                                      ("JITCODE1", 3, 4)]
    assert storage.rd_virtuals is None
    assert liveboxes == [b1, b2, b3]
    assert storage.rd_consts == [c1, c2, c3, c1]
    # check with reading
    reader = ResumeDataReader(storage, liveboxes)
    l = reader.consume_boxes()
    assert l == env
    l = reader.consume_boxes()
    assert l == env1

def test_capture_resumedata():
    b1, b2, b3 = [BoxInt(), BoxPtr(), BoxInt()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]    
    fs = [FakeFrame("code0", 0, -1, b1, c1, b2)]

    storage = Storage()
    capture_resumedata(fs, None, storage)

    assert fs[0].parent_resumedata_snapshot is None
    assert fs[0].parent_resumedata_frame_info_list is None

    assert storage.rd_frame_info_list.prev is None
    assert storage.rd_frame_info_list.jitcode == 'code0'
    assert storage.rd_snapshot.prev is None
    assert storage.rd_snapshot.boxes == fs[0].env
    assert storage.rd_snapshot.boxes is not fs[0].env    

    storage = Storage()
    fs = [FakeFrame("code0", 0, -1, b1, c1, b2),
          FakeFrame("code1", 3, 7, b3, c2, b1),
          FakeFrame("code2", 9, -1, c3, b2)]
    capture_resumedata(fs, None, storage)

    frame_info_list = storage.rd_frame_info_list
    assert frame_info_list.prev is fs[2].parent_resumedata_frame_info_list
    assert frame_info_list.jitcode == 'code2'
    assert frame_info_list.pc == 9
    
    snapshot = storage.rd_snapshot
    assert snapshot.prev is fs[2].parent_resumedata_snapshot
    assert snapshot.boxes == fs[2].env
    assert snapshot.boxes is not fs[2].env

    frame_info_list = frame_info_list.prev
    assert frame_info_list.prev is fs[1].parent_resumedata_frame_info_list
    assert frame_info_list.jitcode == 'code1'
    snapshot = snapshot.prev
    assert snapshot.prev is fs[1].parent_resumedata_snapshot
    assert snapshot.boxes == fs[1].env
    assert snapshot.boxes is not fs[1].env

    frame_info_list = frame_info_list.prev
    assert frame_info_list.prev is None
    assert frame_info_list.jitcode == 'code0'
    snapshot = snapshot.prev
    assert snapshot.prev is None
    assert snapshot.boxes == fs[0].env
    assert snapshot.boxes is not fs[0].env

    fs[2].env = [b2, b3]
    fs[2].pc = 15
    vbs = [b1, b2]
    capture_resumedata(fs, vbs, storage)
       
    frame_info_list = storage.rd_frame_info_list
    assert frame_info_list.prev is fs[2].parent_resumedata_frame_info_list
    assert frame_info_list.jitcode == 'code2'
    assert frame_info_list.pc == 15

    snapshot = storage.rd_snapshot
    assert snapshot.boxes == vbs
    assert snapshot.boxes is not vbs

    snapshot = snapshot.prev
    assert snapshot.prev is fs[2].parent_resumedata_snapshot
    assert snapshot.boxes == fs[2].env

# ____________________________________________________________

class MyMetaInterp:
    def __init__(self, cpu):
        self.cpu = cpu
        self.trace = []
    def execute_and_record(self, opnum, descr, *argboxes):
        resbox = executor.execute(self.cpu, opnum, descr, *argboxes)
        self.trace.append((opnum,
                           [box.value for box in argboxes],
                           resbox and resbox.value,
                           descr))
        return resbox

demo55 = lltype.malloc(LLtypeMixin.NODE)
demo55o = lltype.cast_opaque_ptr(llmemory.GCREF, demo55)

def _resume_remap(liveboxes, expected, *newvalues):
    newboxes = []
    for box in liveboxes:
        i = expected.index(box)
        newboxes.append(newvalues[i])
    assert len(newboxes) == len(expected)
    return newboxes

def test_virtual_adder_no_op():
    storage = make_demo_storage()
    b1s, b2s, b3s = [BoxInt(1), BoxPtr(), BoxInt(3)]
    modifier = ResumeDataVirtualAdder(storage, [b1s, b2s, b3s])
    assert not modifier.is_virtual(b1s)
    assert not modifier.is_virtual(b2s)
    assert not modifier.is_virtual(b3s)
    # done
    liveboxes = modifier.finish()
    b1t, b2t, b3t = [BoxInt(11), BoxPtr(demo55o), BoxInt(33)]
    newboxes = _resume_remap(liveboxes, [b1s, b2s, b3s], b1t, b2t, b3t)
    metainterp = MyMetaInterp(LLtypeMixin.cpu)
    reader = ResumeDataReader(storage, newboxes, metainterp)
    lst = reader.consume_boxes()
    assert lst == [b1t, ConstInt(1), b1t, b2t]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert lst == [b1t, b2t, b3t]
    assert metainterp.trace == []


def test_virtual_adder_make_virtual():
    storage = make_demo_storage()
    b1s, b2s, b3s, b4s, b5s = [BoxInt(1), BoxPtr(), BoxInt(3),
                               BoxPtr(), BoxPtr()]
    c1s = ConstInt(111)
    modifier = ResumeDataVirtualAdder(storage, [b1s, b2s, b3s])
    assert not modifier.is_virtual(b1s)
    assert not modifier.is_virtual(b2s)
    assert not modifier.is_virtual(b3s)
    modifier.make_virtual(b2s,
                          ConstAddr(LLtypeMixin.node_vtable_adr,
                                    LLtypeMixin.cpu),
                          [LLtypeMixin.nextdescr, LLtypeMixin.valuedescr],
                          [b4s, c1s])   # new fields
    modifier.make_virtual(b4s,
                          ConstAddr(LLtypeMixin.node_vtable_adr2,
                                    LLtypeMixin.cpu),
                          [LLtypeMixin.nextdescr, LLtypeMixin.valuedescr,
                                                  LLtypeMixin.otherdescr],
                          [b2s, b3s, b5s])  # new fields
    assert not modifier.is_virtual(b1s)
    assert     modifier.is_virtual(b2s)
    assert not modifier.is_virtual(b3s)
    assert     modifier.is_virtual(b4s)
    assert not modifier.is_virtual(b5s)
    # done
    liveboxes = modifier.finish()
    b1t, b3t, b5t = [BoxInt(11), BoxInt(33), BoxPtr(demo55o)]
    newboxes = _resume_remap(liveboxes, [b1s,
                                          #b2s -- virtual
                                          b3s,
                                          #b4s -- virtual
                                          #b2s -- again, shared
                                          #b3s -- again, shared
                                          b5s], b1t, b3t, b5t)
    #
    metainterp = MyMetaInterp(LLtypeMixin.cpu)
    reader = ResumeDataReader(storage, newboxes, metainterp)
    lst = reader.consume_boxes()
    b2t = lst[-1]
    assert lst == [b1t, ConstInt(1), b1t, b2t]
    b4tx = b2t.value._obj.container._as_ptr().next
    b4tx = lltype.cast_opaque_ptr(llmemory.GCREF, b4tx)
    assert metainterp.trace == [
        (rop.NEW_WITH_VTABLE, [LLtypeMixin.node_vtable_adr], b2t.value, None),
        (rop.NEW_WITH_VTABLE, [LLtypeMixin.node_vtable_adr2], b4tx, None),
        (rop.SETFIELD_GC, [b2t.value, b4tx],     None, LLtypeMixin.nextdescr),
        (rop.SETFIELD_GC, [b2t.value, c1s.value],None, LLtypeMixin.valuedescr),
        (rop.SETFIELD_GC, [b4tx, b2t.value],     None, LLtypeMixin.nextdescr),
        (rop.SETFIELD_GC, [b4tx, b3t.value],     None, LLtypeMixin.valuedescr),
        (rop.SETFIELD_GC, [b4tx, b5t.value],     None, LLtypeMixin.otherdescr),
        ]
    del metainterp.trace[:]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    assert metainterp.trace == []
    lst = reader.consume_boxes()
    assert lst == [b1t, b2t, b3t]
    assert metainterp.trace == []
    #
    ptr = b2t.value._obj.container._as_ptr()
    assert lltype.typeOf(ptr) == lltype.Ptr(LLtypeMixin.NODE)
    assert ptr.value == 111
    ptr2 = ptr.next
    ptr2 = lltype.cast_pointer(lltype.Ptr(LLtypeMixin.NODE2), ptr2)
    assert ptr2.other == demo55
    assert ptr2.parent.value == 33
    assert ptr2.parent.next == ptr


def test_virtual_adder_make_constant():
    for testnumber in [0, 1]:
        storage = make_demo_storage()
        b1s, b2s, b3s = [BoxInt(1), BoxPtr(), BoxInt(3)]
        if testnumber == 0:
            # I. making a constant with make_constant()
            modifier = ResumeDataVirtualAdder(storage, [b1s, b2s, b3s])
            modifier.make_constant(b1s, ConstInt(111))
            assert not modifier.is_virtual(b1s)
        else:
            # II. making a constant by directly specifying a constant in
            #     the list of liveboxes
            b1s = ConstInt(111)
            modifier = ResumeDataVirtualAdder(storage, [b1s, b2s, b3s])
        assert not modifier.is_virtual(b2s)
        assert not modifier.is_virtual(b3s)
        # done
        liveboxes = modifier.finish()
        b2t, b3t = [BoxPtr(demo55o), BoxInt(33)]
        newboxes = _resume_remap(liveboxes, [b2s, b3s], b2t, b3t)
        metainterp = MyMetaInterp(LLtypeMixin.cpu)
        reader = ResumeDataReader(storage, newboxes, metainterp)
        lst = reader.consume_boxes()
        c1t = ConstInt(111)
        assert lst == [c1t, ConstInt(1), c1t, b2t]
        lst = reader.consume_boxes()
        assert lst == [ConstInt(2), ConstInt(3)]
        lst = reader.consume_boxes()
        assert lst == [c1t, b2t, b3t]
        assert metainterp.trace == []


def test_virtual_adder_make_varray():
    storage = make_demo_storage()
    b1s, b2s, b3s, b4s = [BoxInt(1), BoxPtr(), BoxInt(3), BoxInt(4)]
    c1s = ConstInt(111)
    modifier = ResumeDataVirtualAdder(storage, [b1s, b2s, b3s])
    assert not modifier.is_virtual(b1s)
    assert not modifier.is_virtual(b2s)
    assert not modifier.is_virtual(b3s)
    modifier.make_varray(b2s,
                         LLtypeMixin.arraydescr,
                         [b4s, c1s])   # new fields
    assert not modifier.is_virtual(b1s)
    assert     modifier.is_virtual(b2s)
    assert not modifier.is_virtual(b3s)
    assert not modifier.is_virtual(b4s)
    # done
    liveboxes = modifier.finish()
    b1t, b3t, b4t = [BoxInt(11), BoxInt(33), BoxInt(44)]
    newboxes = _resume_remap(liveboxes, [b1s,
                                          #b2s -- virtual
                                          b3s,
                                          b4s],
                                          b1t, b3t, b4t)
    #
    metainterp = MyMetaInterp(LLtypeMixin.cpu)
    reader = ResumeDataReader(storage, newboxes, metainterp)
    lst = reader.consume_boxes()
    b2t = lst[-1]
    assert lst == [b1t, ConstInt(1), b1t, b2t]
    assert metainterp.trace == [
        (rop.NEW_ARRAY, [2], b2t.value,                LLtypeMixin.arraydescr),
        (rop.SETARRAYITEM_GC, [b2t.value,0,44],  None, LLtypeMixin.arraydescr),
        (rop.SETARRAYITEM_GC, [b2t.value,1,111], None, LLtypeMixin.arraydescr),
        ]
    del metainterp.trace[:]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    assert metainterp.trace == []
    lst = reader.consume_boxes()
    assert lst == [b1t, b2t, b3t]
    assert metainterp.trace == []
    #
    ptr = b2t.value._obj.container._as_ptr()
    assert lltype.typeOf(ptr) == lltype.Ptr(lltype.GcArray(lltype.Signed))
    assert len(ptr) == 2
    assert ptr[0] == 44
    assert ptr[1] == 111


def test_virtual_adder_make_vstruct():
    storage = make_demo_storage()
    b1s, b2s, b3s, b4s = [BoxInt(1), BoxPtr(), BoxInt(3), BoxPtr()]
    c1s = ConstInt(111)
    modifier = ResumeDataVirtualAdder(storage, [b1s, b2s, b3s])
    assert not modifier.is_virtual(b1s)
    assert not modifier.is_virtual(b2s)
    assert not modifier.is_virtual(b3s)
    modifier.make_vstruct(b2s,
                          LLtypeMixin.ssize,
                          [LLtypeMixin.adescr, LLtypeMixin.bdescr],
                          [c1s, b4s])   # new fields
    assert not modifier.is_virtual(b1s)
    assert     modifier.is_virtual(b2s)
    assert not modifier.is_virtual(b3s)
    assert not modifier.is_virtual(b4s)
    # done
    liveboxes = modifier.finish()
    b1t, b3t, b4t = [BoxInt(11), BoxInt(33), BoxPtr()]
    newboxes = _resume_remap(liveboxes, [b1s,
                                          #b2s -- virtual
                                          b3s,
                                          b4s],
                                         b1t, b3t, b4t)
    #
    NULL = ConstPtr.value
    metainterp = MyMetaInterp(LLtypeMixin.cpu)
    reader = ResumeDataReader(storage, newboxes, metainterp)
    lst = reader.consume_boxes()
    b2t = lst[-1]
    assert lst == [b1t, ConstInt(1), b1t, b2t]
    assert metainterp.trace == [
        (rop.NEW, [], b2t.value, LLtypeMixin.ssize),
        (rop.SETFIELD_GC, [b2t.value, 111],  None, LLtypeMixin.adescr),
        (rop.SETFIELD_GC, [b2t.value, NULL], None, LLtypeMixin.bdescr),
        ]
    del metainterp.trace[:]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    assert metainterp.trace == []
    lst = reader.consume_boxes()
    assert lst == [b1t, b2t, b3t]
    assert metainterp.trace == []
    #
    ptr = b2t.value._obj.container._as_ptr()
    assert lltype.typeOf(ptr) == lltype.Ptr(LLtypeMixin.S)
    assert ptr.a == 111
    assert ptr.b == lltype.nullptr(LLtypeMixin.NODE)
