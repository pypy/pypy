import py
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.jit.metainterp.resume import *
from pypy.jit.metainterp.history import BoxInt, BoxPtr, ConstInt, ConstAddr
from pypy.jit.metainterp.history import ConstPtr, ConstFloat
from pypy.jit.metainterp.test.test_optimizefindnode import LLtypeMixin
from pypy.jit.metainterp import executor

class Storage:
    pass

def test_tag():
    assert tag(3, 1) == rffi.r_short(3<<2|1)
    assert tag(-3, 2) == rffi.r_short(-3<<2|2)
    assert tag((1<<13)-1, 3) == rffi.r_short(((1<<15)-1)|3)
    assert tag(-1<<13, 3) == rffi.r_short((-1<<15)|3)
    py.test.raises(ValueError, tag, 3, 5)
    py.test.raises(ValueError, tag, 1<<13, 0)
    py.test.raises(ValueError, tag, (1<<13)+1, 0)    
    py.test.raises(ValueError, tag, (-1<<13)-1, 0)
    py.test.raises(ValueError, tag, (-1<<13)-5, 0)        

def test_untag():
    assert untag(tag(3, 1)) == (3, 1)
    assert untag(tag(-3, 2)) == (-3, 2)
    assert untag(tag((1<<13)-1, 3)) == ((1<<13)-1, 3)
    assert untag(tag(-1<<13, 3)) == (-1<<13, 3)

def test_tagged_eq():
    assert tagged_eq(NEXTFRAME, NEXTFRAME)
    assert not tagged_eq(NEXTFRAME, UNASSIGNED)

def test_simple_read():
    b1, b2, b3 = [BoxInt(), BoxPtr(), BoxInt()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]
    storage = Storage()
    storage.rd_frame_infos = []
    storage.rd_consts = [c1, c2, c3]
    storage.rd_nums = [tag(0, TAGBOX),
                       tag(0, TAGCONST),
                       tag(0, TAGBOX),
                       tag(1, TAGBOX),
                       NEXTFRAME,
                       tag(1, TAGCONST),
                       tag(2, TAGCONST),
                       NEXTFRAME,
                       tag(0, TAGBOX),
                       tag(1, TAGBOX),
                       tag(2, TAGBOX),
                       NEXTFRAME
                       ]
    storage.rd_virtuals = None
    b1s, b2s, b3s = [BoxInt(), BoxPtr(), BoxInt()]
    assert b1s != b3s
    reader = ResumeDataReader(storage, [b1s, b2s, b3s])
    lst = reader.consume_boxes()
    assert lst == [b1s, ConstInt(1), b1s, b2s]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert lst == [b1s, b2s, b3s]

def test_simple_read_tagged_ints():
    b1, b2, b3 = [BoxInt(), BoxPtr(), BoxInt()]
    storage = Storage()
    storage.rd_frame_infos = []
    storage.rd_consts = []
    storage.rd_nums = [tag(0, TAGBOX),
                       tag(1, TAGINT),
                       tag(0, TAGBOX),
                       tag(1, TAGBOX),
                       NEXTFRAME,
                       tag(2, TAGINT),
                       tag(3, TAGINT),
                       NEXTFRAME,
                       tag(0, TAGBOX),
                       tag(1, TAGBOX),
                       tag(2, TAGBOX),
                       NEXTFRAME
                       ]
    storage.rd_virtuals = None
    b1s, b2s, b3s = [BoxInt(), BoxPtr(), BoxInt()]
    assert b1s != b3s
    reader = ResumeDataReader(storage, [b1s, b2s, b3s])
    lst = reader.consume_boxes()
    assert lst == [b1s, ConstInt(1), b1s, b2s]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert lst == [b1s, b2s, b3s]

    # ____________________________________________________________



class FakeFrame(object):
    parent_resumedata_snapshot = None
    parent_resumedata_frame_info_list = None

    def __init__(self, code, pc, exc_target, *boxes):
        self.jitcode = code
        self.pc = pc
        self.exception_target = exc_target
        self.env = list(boxes)

    def setup_resume_at_op(self, pc, exception_target, env):
        self.__init__(self.jitcode, pc, exception_target, *env)
    
    def __eq__(self, other):
        return self.__dict__ == other.__dict__
    def __ne__(self, other):
        return self.__dict__ != other.__dict__

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

def test_rebuild_from_resumedata():
    class FakeMetaInterp(object):
        def __init__(self):
            self.framestack = []
        def newframe(self, jitcode):
            frame = FakeFrame(jitcode, -1, -1)
            self.framestack.append(frame)
            return frame
    b1, b2, b3 = [BoxInt(), BoxPtr(), BoxInt()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]    
    storage = Storage()
    fs = [FakeFrame("code0", 0, -1, b1, c1, b2),
          FakeFrame("code1", 3, 7, b3, c2, b1),
          FakeFrame("code2", 9, -1, c3, b2)]
    capture_resumedata(fs, None, storage)
    memo = ResumeDataLoopMemo(None)
    modifier = ResumeDataVirtualAdder(storage, memo)
    modifier.walk_snapshots({})
    liveboxes = modifier.finish({})
    metainterp = FakeMetaInterp()

    b1t, b2t, b3t = [BoxInt(), BoxPtr(), BoxInt()]
    newboxes = _resume_remap(liveboxes, [b1, b2, b3], b1t, b2t, b3t)

    result = rebuild_from_resumedata(metainterp, newboxes, storage,
                                     False)
    assert result is None
    fs2 = [FakeFrame("code0", 0, -1, b1t, c1, b2t),
           FakeFrame("code1", 3, 7, b3t, c2, b1t),
           FakeFrame("code2", 9, -1, c3, b2t)]
    assert metainterp.framestack == fs2

def test_rebuild_from_resumedata_with_virtualizable():
    class FakeMetaInterp(object):
        def __init__(self):
            self.framestack = []
        def newframe(self, jitcode):
            frame = FakeFrame(jitcode, -1, -1)
            self.framestack.append(frame)
            return frame
    b1, b2, b3, b4 = [BoxInt(), BoxPtr(), BoxInt(), BoxPtr()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]    
    storage = Storage()
    fs = [FakeFrame("code0", 0, -1, b1, c1, b2),
          FakeFrame("code1", 3, 7, b3, c2, b1),
          FakeFrame("code2", 9, -1, c3, b2)]
    capture_resumedata(fs, [b4], storage)
    memo = ResumeDataLoopMemo(None)
    modifier = ResumeDataVirtualAdder(storage, memo)
    modifier.walk_snapshots({})
    liveboxes = modifier.finish({})
    metainterp = FakeMetaInterp()

    b1t, b2t, b3t, b4t = [BoxInt(), BoxPtr(), BoxInt(), BoxPtr()]
    newboxes = _resume_remap(liveboxes, [b1, b2, b3, b4], b1t, b2t, b3t, b4t)

    result = rebuild_from_resumedata(metainterp, newboxes, storage,
                                     True)
    assert result == [b4t]
    fs2 = [FakeFrame("code0", 0, -1, b1t, c1, b2t),
           FakeFrame("code1", 3, 7, b3t, c2, b1t),
           FakeFrame("code2", 9, -1, c3, b2t)]
    assert metainterp.framestack == fs2
# ____________________________________________________________

def test_walk_snapshots():
    b1, b2, b3 = [BoxInt(), BoxInt(), BoxInt()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]    

    env = [b1, c1, b2, b1, c2]
    snap = Snapshot(None, env)
    env1 = [c3, b3, b1, c1]
    snap1 = Snapshot(snap, env1)

    storage = Storage()
    storage.rd_snapshot = snap1

    modifier = ResumeDataVirtualAdder(storage, None)
    modifier.walk_snapshots({})

    assert modifier.liveboxes == {b1: UNASSIGNED, b2: UNASSIGNED,
                                  b3: UNASSIGNED}
    assert modifier.nnums == len(env)+1+len(env1)+1

    b1_2 = BoxInt()
    class FakeValue(object):

        def register_value(self, modifier):
            modifier.register_box(b1_2)
    val = FakeValue()

    storage = Storage()
    storage.rd_snapshot = snap1

    modifier = ResumeDataVirtualAdder(storage, None)
    modifier.walk_snapshots({b1: val, b2: val})    

    assert modifier.liveboxes == {b1_2: UNASSIGNED, b3: UNASSIGNED}
    assert modifier.nnums == len(env)+1+len(env1)+1

def test_flatten_frame_info():
    frame = FakeFrame("JITCODE", 1, 2)    
    fi = FrameInfo(None, frame)
    frame1 = FakeFrame("JITCODE1", 3, 4)    
    fi1 = FrameInfo(fi, frame1)

    storage = Storage()
    storage.rd_frame_info_list = fi1

    modifier = ResumeDataVirtualAdder(storage, None)
    modifier._flatten_frame_info()
    assert storage.rd_frame_info_list is None

    assert storage.rd_frame_infos == [("JITCODE", 1, 2),
                                      ("JITCODE1", 3, 4)]


def test_ResumeDataLoopMemo_ints():
    memo = ResumeDataLoopMemo(None)
    tagged = memo.getconst(ConstInt(44))
    assert untag(tagged) == (44, TAGINT)
    tagged = memo.getconst(ConstInt(-3))
    assert untag(tagged) == (-3, TAGINT)
    const = ConstInt(50000)
    tagged = memo.getconst(const)
    index, tagbits = untag(tagged)
    assert tagbits == TAGCONST
    assert memo.consts[index] is const
    tagged = memo.getconst(ConstInt(50000))
    index2, tagbits = untag(tagged)
    assert tagbits == TAGCONST
    assert index2 == index

demo55 = lltype.malloc(LLtypeMixin.NODE)
demo55o = lltype.cast_opaque_ptr(llmemory.GCREF, demo55)
demo66 = lltype.malloc(LLtypeMixin.NODE)
demo66o = lltype.cast_opaque_ptr(llmemory.GCREF, demo66)
    
def test_ResumeDataLoopMemo_refs():
    cpu = LLtypeMixin.cpu
    memo = ResumeDataLoopMemo(cpu)
    const = cpu.ts.ConstRef(demo55o)
    tagged = memo.getconst(const)
    index, tagbits = untag(tagged)
    assert tagbits == TAGCONST
    assert memo.consts[index] is const    
    tagged = memo.getconst(cpu.ts.ConstRef(demo55o))
    index2, tagbits = untag(tagged)
    assert tagbits == TAGCONST
    assert index2 == index
    tagged = memo.getconst(cpu.ts.ConstRef(demo66o))
    index3, tagbits = untag(tagged)
    assert tagbits == TAGCONST
    assert index3 != index    

def test_ResumeDataLoopMemo_other():
    memo = ResumeDataLoopMemo(None)
    const = ConstFloat(-1.0)
    tagged = memo.getconst(const)
    index, tagbits = untag(tagged)
    assert tagbits == TAGCONST
    assert memo.consts[index] is const

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

def _resume_remap(liveboxes, expected, *newvalues):
    newboxes = []
    for box in liveboxes:
        i = expected.index(box)
        newboxes.append(newvalues[i])
    assert len(newboxes) == len(expected)
    return newboxes

def make_storage(b1, b2, b3):
    storage = Storage()
    snapshot = Snapshot(None, [b1, ConstInt(1), b1, b2])
    snapshot = Snapshot(snapshot, [ConstInt(2), ConstInt(3)])
    snapshot = Snapshot(snapshot, [b1, b2, b3])    
    storage.rd_snapshot = snapshot
    # just to placate _flatten_frame_info
    storage.rd_frame_info_list = FrameInfo(None, FakeFrame("", 0, -1))
    return storage

def test_virtual_adder_no_op():
    b1s, b2s, b3s = [BoxInt(1), BoxPtr(), BoxInt(3)]
    storage = make_storage(b1s, b2s, b3s)
    memo = ResumeDataLoopMemo(LLtypeMixin.cpu)    
    modifier = ResumeDataVirtualAdder(storage, memo)
    modifier.walk_snapshots({})
    assert not modifier.is_virtual(b1s)
    assert not modifier.is_virtual(b2s)
    assert not modifier.is_virtual(b3s)
    # done
    liveboxes = modifier.finish({})
    assert storage.rd_snapshot is None
    b1t, b2t, b3t = [BoxInt(11), BoxPtr(demo55o), BoxInt(33)]
    newboxes = _resume_remap(liveboxes, [b1s, b2s, b3s], b1t, b2t, b3t)
    metainterp = MyMetaInterp(LLtypeMixin.cpu)
    reader = ResumeDataReader(storage, newboxes, metainterp)
    lst = reader.consume_boxes()
    assert lst == [b1t, b2t, b3t]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert lst == [b1t, ConstInt(1), b1t, b2t]
    assert metainterp.trace == []

def test_virtual_adder_int_constants():
    b1s, b2s, b3s = [ConstInt(sys.maxint), ConstInt(2**16), ConstInt(-65)]
    storage = make_storage(b1s, b2s, b3s)
    memo = ResumeDataLoopMemo(LLtypeMixin.cpu)    
    modifier = ResumeDataVirtualAdder(storage, memo)
    modifier.walk_snapshots({})
    liveboxes = modifier.finish({})
    assert storage.rd_snapshot is None
    metainterp = MyMetaInterp(LLtypeMixin.cpu)
    reader = ResumeDataReader(storage, [], metainterp)
    lst = reader.consume_boxes()
    assert lst == [b1s, b2s, b3s]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(sys.maxint), ConstInt(1), ConstInt(sys.maxint),
                   ConstInt(2**16)]
    assert metainterp.trace == []


def test_virtual_adder_memo_const_sharing():
    b1s, b2s, b3s = [ConstInt(sys.maxint), ConstInt(2**16), ConstInt(-65)]
    storage = make_storage(b1s, b2s, b3s)
    memo = ResumeDataLoopMemo(LLtypeMixin.cpu)
    modifier = ResumeDataVirtualAdder(storage, memo)
    modifier.walk_snapshots({})
    modifier.finish({})
    assert len(memo.consts) == 2
    assert storage.rd_consts is memo.consts

    b1s, b2s, b3s = [ConstInt(sys.maxint), ConstInt(2**17), ConstInt(-65)]
    storage2 = make_storage(b1s, b2s, b3s)
    modifier2 = ResumeDataVirtualAdder(storage2, memo)
    modifier2.walk_snapshots({})
    modifier2.finish({})
    assert len(memo.consts) == 3    
    assert storage2.rd_consts is memo.consts


def test_virtual_adder_no_op_renaming():
    b1s, b2s, b3s = [BoxInt(1), BoxInt(2), BoxInt(3)]
    storage = make_storage(b1s, b2s, b3s)
    memo = ResumeDataLoopMemo(LLtypeMixin.cpu)
    modifier = ResumeDataVirtualAdder(storage, memo)
    b1_2 = BoxInt()
    class FakeValue(object):

        def register_value(self, modifier):
            modifier.register_box(b1_2)

        def get_key_box(self):
            return b1_2

    val = FakeValue()
    values = {b1s: val, b2s: val}  
    modifier.walk_snapshots(values)
    assert not modifier.is_virtual(b1_2)
    assert not modifier.is_virtual(b3s)
    # done
    liveboxes = modifier.finish(values)
    assert storage.rd_snapshot is None
    b1t, b3t = [BoxInt(11), BoxInt(33)]
    newboxes = _resume_remap(liveboxes, [b1_2, b3s], b1t, b3t)
    metainterp = MyMetaInterp(LLtypeMixin.cpu)
    reader = ResumeDataReader(storage, newboxes, metainterp)
    lst = reader.consume_boxes()
    assert lst == [b1t, b1t, b3t]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert lst == [b1t, ConstInt(1), b1t, b1t]
    assert metainterp.trace == []    

def test_virtual_adder_make_virtual():
    b1s, b2s, b3s, b4s, b5s = [BoxInt(1), BoxPtr(), BoxInt(3),
                               BoxPtr(), BoxPtr()]  
    c1s = ConstInt(111)
    storage = make_storage(b1s, b2s, b3s)
    memo = ResumeDataLoopMemo(LLtypeMixin.cpu)    
    modifier = ResumeDataVirtualAdder(storage, memo)
    modifier.walk_snapshots({})
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
    liveboxes = modifier.finish({})
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
    trace = metainterp.trace[:]
    del metainterp.trace[:]
    lst = reader.consume_boxes()
    b2t = lst[1]
    assert lst == [b1t, b2t, b3t]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert metainterp.trace == []
    assert lst == [b1t, ConstInt(1), b1t, b2t]
    b4tx = b2t.value._obj.container._as_ptr().next
    b4tx = lltype.cast_opaque_ptr(llmemory.GCREF, b4tx)
    assert trace == [
        (rop.NEW_WITH_VTABLE, [LLtypeMixin.node_vtable_adr], b2t.value, None),
        (rop.NEW_WITH_VTABLE, [LLtypeMixin.node_vtable_adr2], b4tx, None),
        (rop.SETFIELD_GC, [b2t.value, b4tx],     None, LLtypeMixin.nextdescr),
        (rop.SETFIELD_GC, [b2t.value, c1s.value],None, LLtypeMixin.valuedescr),
        (rop.SETFIELD_GC, [b4tx, b2t.value],     None, LLtypeMixin.nextdescr),
        (rop.SETFIELD_GC, [b4tx, b3t.value],     None, LLtypeMixin.valuedescr),
        (rop.SETFIELD_GC, [b4tx, b5t.value],     None, LLtypeMixin.otherdescr),
        ]
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
        b1s, b2s, b3s = [BoxInt(1), BoxPtr(), BoxInt(3)]
        if testnumber == 0:
            # I. making a constant by directly specifying a constant in
            #    the list of liveboxes
            b1s = ConstInt(111)
        storage = make_storage(b1s, b2s, b3s)
        memo = ResumeDataLoopMemo(LLtypeMixin.cpu)        
        modifier = ResumeDataVirtualAdder(storage, memo)
        modifier.walk_snapshots({})

        if testnumber == 1:
            # II. making a constant with make_constant()
            modifier.make_constant(b1s, ConstInt(111))
            assert not modifier.is_virtual(b1s)

        assert not modifier.is_virtual(b2s)
        assert not modifier.is_virtual(b3s)
        # done
        liveboxes = modifier.finish({})
        b2t, b3t = [BoxPtr(demo55o), BoxInt(33)]
        newboxes = _resume_remap(liveboxes, [b2s, b3s], b2t, b3t)
        metainterp = MyMetaInterp(LLtypeMixin.cpu)
        reader = ResumeDataReader(storage, newboxes, metainterp)
        lst = reader.consume_boxes()
        c1t = ConstInt(111)
        assert lst == [c1t, b2t, b3t]
        lst = reader.consume_boxes()
        assert lst == [ConstInt(2), ConstInt(3)]
        lst = reader.consume_boxes()
        assert lst == [c1t, ConstInt(1), c1t, b2t]
        assert metainterp.trace == []


def test_virtual_adder_make_varray():
    b1s, b2s, b3s, b4s = [BoxInt(1), BoxPtr(), BoxInt(3), BoxInt(4)]
    c1s = ConstInt(111)
    storage = make_storage(b1s, b2s, b3s)
    memo = ResumeDataLoopMemo(LLtypeMixin.cpu)
    modifier = ResumeDataVirtualAdder(storage, memo)
    modifier.walk_snapshots({})    
    modifier.make_varray(b2s,
                         LLtypeMixin.arraydescr,
                         [b4s, c1s])   # new fields
    assert not modifier.is_virtual(b1s)
    assert     modifier.is_virtual(b2s)
    assert not modifier.is_virtual(b3s)
    assert not modifier.is_virtual(b4s)
    # done
    liveboxes = modifier.finish({})
    b1t, b3t, b4t = [BoxInt(11), BoxInt(33), BoxInt(44)]
    newboxes = _resume_remap(liveboxes, [b1s,
                                          #b2s -- virtual
                                          b3s,
                                          b4s],
                                          b1t, b3t, b4t)
    #
    metainterp = MyMetaInterp(LLtypeMixin.cpu)
    reader = ResumeDataReader(storage, newboxes, metainterp)
    trace = metainterp.trace[:]
    del metainterp.trace[:]
    lst = reader.consume_boxes()
    b2t = lst[1]
    assert lst == [b1t, b2t, b3t]
    assert trace == [
        (rop.NEW_ARRAY, [2], b2t.value,                LLtypeMixin.arraydescr),
        (rop.SETARRAYITEM_GC, [b2t.value,0,44],  None, LLtypeMixin.arraydescr),
        (rop.SETARRAYITEM_GC, [b2t.value,1,111], None, LLtypeMixin.arraydescr),
        ]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    assert metainterp.trace == []
    lst = reader.consume_boxes()
    assert lst == [b1t, ConstInt(1), b1t, b2t]
    assert metainterp.trace == []
    #
    ptr = b2t.value._obj.container._as_ptr()
    assert lltype.typeOf(ptr) == lltype.Ptr(lltype.GcArray(lltype.Signed))
    assert len(ptr) == 2
    assert ptr[0] == 44
    assert ptr[1] == 111


def test_virtual_adder_make_vstruct():
    b1s, b2s, b3s, b4s = [BoxInt(1), BoxPtr(), BoxInt(3), BoxPtr()]
    c1s = ConstInt(111)
    storage = make_storage(b1s, b2s, b3s)
    memo = ResumeDataLoopMemo(LLtypeMixin.cpu)    
    modifier = ResumeDataVirtualAdder(storage, memo)
    modifier.walk_snapshots({})
    modifier.make_vstruct(b2s,
                          LLtypeMixin.ssize,
                          [LLtypeMixin.adescr, LLtypeMixin.bdescr],
                          [c1s, b4s])   # new fields
    assert not modifier.is_virtual(b1s)
    assert     modifier.is_virtual(b2s)
    assert not modifier.is_virtual(b3s)
    assert not modifier.is_virtual(b4s)
    # done
    liveboxes = modifier.finish({})
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
    trace = metainterp.trace[:]
    del metainterp.trace[:]
    b2t = lst[1]
    assert lst == [b1t, b2t, b3t]
    assert trace == [
        (rop.NEW, [], b2t.value, LLtypeMixin.ssize),
        (rop.SETFIELD_GC, [b2t.value, 111],  None, LLtypeMixin.adescr),
        (rop.SETFIELD_GC, [b2t.value, NULL], None, LLtypeMixin.bdescr),
        ]
    del metainterp.trace[:]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    assert metainterp.trace == []
    lst = reader.consume_boxes()
    assert lst == [b1t, ConstInt(1), b1t, b2t]
    assert metainterp.trace == []
    #
    ptr = b2t.value._obj.container._as_ptr()
    assert lltype.typeOf(ptr) == lltype.Ptr(LLtypeMixin.S)
    assert ptr.a == 111
    assert ptr.b == lltype.nullptr(LLtypeMixin.NODE)
