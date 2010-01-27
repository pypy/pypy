import py
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.jit.metainterp.optimizeopt import VirtualValue, OptValue, VArrayValue
from pypy.jit.metainterp.optimizeopt import VStructValue
from pypy.jit.metainterp.resume import *
from pypy.jit.metainterp.history import BoxInt, BoxPtr, ConstInt, ConstAddr
from pypy.jit.metainterp.history import ConstPtr, ConstFloat
from pypy.jit.metainterp.test.test_optimizefindnode import LLtypeMixin
from pypy.jit.metainterp import executor

class Storage:
    rd_frame_info_list = None
    rd_numb = None
    rd_consts = []
    rd_virtuals = None
    rd_pendingfields = None

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
    assert tagged_eq(UNASSIGNED, UNASSIGNED)
    assert not tagged_eq(tag(1, TAGBOX), UNASSIGNED)

def test_tagged_list_eq():
    assert tagged_list_eq([UNASSIGNED, tag(1, TAGBOX), tag(-2, TAGVIRTUAL)],
                          [UNASSIGNED, tag(1, TAGBOX), tag(-2, TAGVIRTUAL)])
    assert not tagged_list_eq([tag(1, TAGBOX)], [tag(-2, TAGBOX)])
    assert not tagged_list_eq([tag(1, TAGBOX), tag(-2, TAGBOX)], [tag(1, TAGBOX)])

def test_vinfo():
    v1 = AbstractVirtualInfo()
    v1.set_content([1, 2, 4])
    assert v1.equals([1, 2, 4])
    assert not v1.equals([1, 2, 6])

class MyMetaInterp:
    _already_allocated_resume_virtuals = None

    def __init__(self, cpu=None):
        if cpu is None:
            cpu = LLtypeMixin.cpu
        self.cpu = cpu
        self.trace = []
        self.framestack = []
        self.resboxes = []

    def newframe(self, jitcode):
        frame = FakeFrame(jitcode, -1, -1)
        self.framestack.append(frame)
        return frame    

    def execute_and_record(self, opnum, descr, *argboxes):
        resbox = executor.execute(self.cpu, opnum, descr, *argboxes)
        self.trace.append((opnum,
                           list(argboxes),
                           resbox,
                           descr))
        if resbox is not None:
            self.resboxes.append(resbox)
        return resbox


def test_simple_read():
    b1, b2, b3 = [BoxInt(), BoxPtr(), BoxInt()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]
    storage = Storage()
    storage.rd_consts = [c1, c2, c3]
    numb = Numbering(None, [tag(0, TAGBOX), tag(1, TAGBOX), tag(2, TAGBOX)])
    numb = Numbering(numb, [tag(1, TAGCONST), tag(2, TAGCONST)])
    numb = Numbering(numb, [tag(0, TAGBOX),
                            tag(0, TAGCONST),
                            NULLREF,
                            tag(0, TAGBOX),
                            tag(1, TAGBOX)])
    storage.rd_numb = numb

    b1s, b2s, b3s = [BoxInt(), BoxPtr(), BoxInt()]
    assert b1s != b3s
    reader = ResumeDataReader(storage, [b1s, b2s, b3s], MyMetaInterp())
    lst = reader.consume_boxes()
    assert lst == [b1s, ConstInt(1), LLtypeMixin.cpu.ts.CONST_NULL, b1s, b2s]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert lst == [b1s, b2s, b3s]

def test_simple_read_tagged_ints():
    b1, b2, b3 = [BoxInt(), BoxPtr(), BoxInt()]
    storage = Storage()
    storage.rd_consts = []
    numb = Numbering(None, [tag(0, TAGBOX), tag(1, TAGBOX), tag(2, TAGBOX)])
    numb = Numbering(numb, [tag(2, TAGINT), tag(3, TAGINT)])
    numb = Numbering(numb, [tag(0, TAGBOX),
                            tag(1, TAGINT),
                            tag(0, TAGBOX),
                            tag(1, TAGBOX)])
    storage.rd_numb = numb
    b1s, b2s, b3s = [BoxInt(), BoxPtr(), BoxInt()]
    assert b1s != b3s
    reader = ResumeDataReader(storage, [b1s, b2s, b3s], MyMetaInterp())
    lst = reader.consume_boxes()
    assert lst == [b1s, ConstInt(1), b1s, b2s]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert lst == [b1s, b2s, b3s]


def test_prepare_virtuals():
    class FakeVinfo(object):
        def allocate(self, metainterp):
            return "allocated"
        def setfields(self, metainterp, virtual, func):
            assert virtual == "allocated"
    class FakeStorage(object):
        rd_virtuals = [FakeVinfo(), None]
        rd_numb = []
        rd_consts = []
        rd_pendingfields = None
    class FakeMetainterp(object):
        _already_allocated_resume_virtuals = None
        cpu = None
    reader = ResumeDataReader(FakeStorage(), [], FakeMetainterp())
    assert reader.virtuals == ["allocated", None]

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
    def __repr__(self):
        return "<FF %s %s %s %s>" % (self.jitcode, self.pc,
                                     self.exception_target, self.env)

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

    jitcode1 = "JITCODE1"
    frame1 = FakeFrame(jitcode, 3, 4)
    fi1 = FrameInfo(fi, frame1)
    assert fi1.prev is fi
    assert fi1.jitcode is jitcode
    assert fi1.pc == 3
    assert fi1.exception_target == 4

def test_Numbering_create():
    l = [1, 2]
    numb = Numbering(None, l)
    assert numb.prev is None
    assert numb.nums is l

    l1 = ['b3']
    numb1 = Numbering(numb, l1)
    assert numb1.prev is numb
    assert numb1.nums is l1

def test_capture_resumedata():
    b1, b2, b3 = [BoxInt(), BoxPtr(), BoxInt()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]
    fs = [FakeFrame("code0", 0, -1, b1, c1, b2)]

    storage = Storage()
    capture_resumedata(fs, None, [], storage)

    assert fs[0].parent_resumedata_snapshot is None
    assert fs[0].parent_resumedata_frame_info_list is None

    assert storage.rd_frame_info_list.prev is None
    assert storage.rd_frame_info_list.jitcode == 'code0'
    assert storage.rd_snapshot.boxes == []    # for virtualrefs
    snapshot = storage.rd_snapshot.prev
    assert snapshot.prev is None
    assert snapshot.boxes == fs[0].env
    assert snapshot.boxes is not fs[0].env

    storage = Storage()
    fs = [FakeFrame("code0", 0, -1, b1, c1, b2),
          FakeFrame("code1", 3, 7, b3, c2, b1),
          FakeFrame("code2", 9, -1, c3, b2)]
    capture_resumedata(fs, None, [], storage)

    frame_info_list = storage.rd_frame_info_list
    assert frame_info_list.prev is fs[2].parent_resumedata_frame_info_list
    assert frame_info_list.jitcode == 'code2'
    assert frame_info_list.pc == 9

    assert storage.rd_snapshot.boxes == []    # for virtualrefs
    snapshot = storage.rd_snapshot.prev
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
    vrs = [b3]
    capture_resumedata(fs, vbs, vrs, storage)

    frame_info_list = storage.rd_frame_info_list
    assert frame_info_list.prev is fs[2].parent_resumedata_frame_info_list
    assert frame_info_list.jitcode == 'code2'
    assert frame_info_list.pc == 15

    snapshot = storage.rd_snapshot
    assert snapshot.boxes == vbs
    assert snapshot.boxes is not vbs

    snapshot = snapshot.prev
    assert snapshot.boxes == vrs
    assert snapshot.boxes is not vrs

    snapshot = snapshot.prev
    assert snapshot.prev is fs[2].parent_resumedata_snapshot
    assert snapshot.boxes == fs[2].env


class FakeMetaInterpStaticData:
    cpu = LLtypeMixin.cpu

    class options:
        failargs_limit = 100

def test_rebuild_from_resumedata():
    b1, b2, b3 = [BoxInt(), BoxPtr(), BoxInt()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]    
    storage = Storage()
    fs = [FakeFrame("code0", 0, -1, b1, c1, b2),
          FakeFrame("code1", 3, 7, b3, c2, b1),
          FakeFrame("code2", 9, -1, c3, b2)]
    capture_resumedata(fs, None, [], storage)
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(storage, memo)
    liveboxes = modifier.finish({})
    metainterp = MyMetaInterp()

    b1t, b2t, b3t = [BoxInt(), BoxPtr(), BoxInt()]
    newboxes = _resume_remap(liveboxes, [b1, b2, b3], b1t, b2t, b3t)

    result = rebuild_from_resumedata(metainterp, newboxes, storage,
                                     False)
    assert result == (None, [])
    fs2 = [FakeFrame("code0", 0, -1, b1t, c1, b2t),
           FakeFrame("code1", 3, 7, b3t, c2, b1t),
           FakeFrame("code2", 9, -1, c3, b2t)]
    assert metainterp.framestack == fs2

def test_rebuild_from_resumedata_with_virtualizable():
    b1, b2, b3, b4 = [BoxInt(), BoxPtr(), BoxInt(), BoxPtr()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]    
    storage = Storage()
    fs = [FakeFrame("code0", 0, -1, b1, c1, b2),
          FakeFrame("code1", 3, 7, b3, c2, b1),
          FakeFrame("code2", 9, -1, c3, b2)]
    capture_resumedata(fs, [b4], [], storage)
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(storage, memo)
    liveboxes = modifier.finish({})
    metainterp = MyMetaInterp()

    b1t, b2t, b3t, b4t = [BoxInt(), BoxPtr(), BoxInt(), BoxPtr()]
    newboxes = _resume_remap(liveboxes, [b1, b2, b3, b4], b1t, b2t, b3t, b4t)

    result = rebuild_from_resumedata(metainterp, newboxes, storage,
                                     True)
    assert result == ([b4t], [])
    fs2 = [FakeFrame("code0", 0, -1, b1t, c1, b2t),
           FakeFrame("code1", 3, 7, b3t, c2, b1t),
           FakeFrame("code2", 9, -1, c3, b2t)]
    assert metainterp.framestack == fs2

def test_rebuild_from_resumedata_two_guards():
    b1, b2, b3, b4 = [BoxInt(), BoxPtr(), BoxInt(), BoxInt()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]    
    storage = Storage()
    fs = [FakeFrame("code0", 0, -1, b1, c1, b2),
          FakeFrame("code1", 3, 7, b3, c2, b1),
          FakeFrame("code2", 9, -1, c3, b2)]
    capture_resumedata(fs, None, [], storage)
    storage2 = Storage()
    fs = fs[:-1] + [FakeFrame("code2", 10, -1, c3, b2, b4)]
    capture_resumedata(fs, None, [], storage2)
    
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(storage, memo)
    liveboxes = modifier.finish({})

    modifier = ResumeDataVirtualAdder(storage2, memo)
    liveboxes2 = modifier.finish({})

    metainterp = MyMetaInterp()

    b1t, b2t, b3t, b4t = [BoxInt(), BoxPtr(), BoxInt(), BoxInt()]
    newboxes = _resume_remap(liveboxes, [b1, b2, b3], b1t, b2t, b3t)

    result = rebuild_from_resumedata(metainterp, newboxes, storage,
                                     False)
    assert result == (None, [])
    fs2 = [FakeFrame("code0", 0, -1, b1t, c1, b2t),
           FakeFrame("code1", 3, 7, b3t, c2, b1t),
           FakeFrame("code2", 9, -1, c3, b2t)]
    assert metainterp.framestack == fs2

    newboxes = _resume_remap(liveboxes2, [b1, b2, b3, b4], b1t, b2t, b3t, b4t)

    metainterp.framestack = []
    result = rebuild_from_resumedata(metainterp, newboxes, storage2,
                                     False)
    assert result == (None, [])
    fs2 = fs2[:-1] + [FakeFrame("code2", 10, -1, c3, b2t, b4t)]
    assert metainterp.framestack == fs2


class FakeOptimizer_VirtualValue(object):
    class cpu:
        pass
fakeoptimizer = FakeOptimizer_VirtualValue()

def virtual_value(keybox, value, next):
    vv = VirtualValue(fakeoptimizer, ConstAddr(LLtypeMixin.node_vtable_adr,
                                     LLtypeMixin.cpu), keybox)
    if not isinstance(next, OptValue):
        next = OptValue(next)
    vv.setfield(LLtypeMixin.valuedescr, OptValue(value))
    vv.setfield(LLtypeMixin.nextdescr, next)
    return vv

def test_rebuild_from_resumedata_two_guards_w_virtuals():
    
    b1, b2, b3, b4, b5 = [BoxInt(), BoxPtr(), BoxInt(), BoxInt(), BoxInt()]
    c1, c2, c3, c4 = [ConstInt(1), ConstInt(2), ConstInt(3),
                      LLtypeMixin.nodebox.constbox()]
    storage = Storage()
    fs = [FakeFrame("code0", 0, -1, b1, c1, b2),
          FakeFrame("code1", 3, 7, b3, c2, b1),
          FakeFrame("code2", 9, -1, c3, b2)]
    capture_resumedata(fs, None, [], storage)
    storage2 = Storage()
    fs = fs[:-1] + [FakeFrame("code2", 10, -1, c3, b2, b4)]
    capture_resumedata(fs, None, [], storage2)
    
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    values = {b2: virtual_value(b2, b5, c4)}
    modifier = ResumeDataVirtualAdder(storage, memo)
    liveboxes = modifier.finish(values)
    assert len(storage.rd_virtuals) == 1
    assert storage.rd_virtuals[0].fieldnums == [tag(-1, TAGBOX),
                                                tag(0, TAGCONST)]

    b6 = BoxPtr()
    v6 = virtual_value(b6, c2, None)
    v6.setfield(LLtypeMixin.nextdescr, v6)    
    values = {b2: virtual_value(b2, b4, v6), b6: v6}
    memo.clear_box_virtual_numbers()
    modifier = ResumeDataVirtualAdder(storage2, memo)
    liveboxes2 = modifier.finish(values)
    assert len(storage2.rd_virtuals) == 2    
    assert storage2.rd_virtuals[0].fieldnums == [tag(len(liveboxes2)-1, TAGBOX),
                                                 tag(-1, TAGVIRTUAL)]
    assert storage2.rd_virtuals[1].fieldnums == [tag(2, TAGINT),
                                                 tag(-1, TAGVIRTUAL)]

    # now on to resuming
    metainterp = MyMetaInterp()

    b1t, b3t, b4t, b5t = [BoxInt(), BoxInt(), BoxInt(), BoxInt()]
    newboxes = _resume_remap(liveboxes, [b1, b3, b5], b1t, b3t, b5t)

    result = rebuild_from_resumedata(metainterp, newboxes, storage,
                                     False)

    b2t = metainterp.resboxes[0]
    fs2 = [FakeFrame("code0", 0, -1, b1t, c1, b2t),
           FakeFrame("code1", 3, 7, b3t, c2, b1t),
           FakeFrame("code2", 9, -1, c3, b2t)]
    assert metainterp.framestack == fs2

    newboxes = _resume_remap(liveboxes2, [b1, b3, b4], b1t, b3t, b4t)

    metainterp = MyMetaInterp()
    result = rebuild_from_resumedata(metainterp, newboxes, storage2,
                                     False)
    b2t = metainterp.resboxes[0]
    assert len(metainterp.resboxes) == 2
    fs2 = [FakeFrame("code0", 0, -1, b1t, c1, b2t),
           FakeFrame("code1", 3, 7, b3t, c2, b1t),
           FakeFrame("code2", 10, -1, c3, b2t, b4t)]
    assert metainterp.framestack == fs2    

def test_rebuild_from_resumedata_two_guards_w_shared_virtuals():
    b1, b2, b3, b4, b5, b6 = [BoxPtr(), BoxPtr(), BoxInt(), BoxPtr(), BoxInt(), BoxInt()]
    c1, c2, c3, c4 = [ConstInt(1), ConstInt(2), ConstInt(3),
                      LLtypeMixin.nodebox.constbox()]
    storage = Storage()
    fs = [FakeFrame("code0", 0, -1, c1, b2, b3)]
    capture_resumedata(fs, None, [], storage)
    
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    values = {b2: virtual_value(b2, b5, c4)}
    modifier = ResumeDataVirtualAdder(storage, memo)
    liveboxes = modifier.finish(values)
    assert len(storage.rd_virtuals) == 1
    assert storage.rd_virtuals[0].fieldnums == [tag(-1, TAGBOX),
                                                tag(0, TAGCONST)]

    storage2 = Storage()
    fs = [FakeFrame("code0", 0, -1, b1, b4, b2)]
    capture_resumedata(fs, None, [], storage2)
    values[b4] = virtual_value(b4, b6, c4)
    modifier = ResumeDataVirtualAdder(storage2, memo)
    liveboxes = modifier.finish(values)
    assert len(storage2.rd_virtuals) == 2
    assert storage2.rd_virtuals[1].fieldnums == storage.rd_virtuals[0].fieldnums
    assert storage2.rd_virtuals[1] is storage.rd_virtuals[0]
    

def test_resumedata_top_recursive_virtuals():
    b1, b2, b3 = [BoxPtr(), BoxPtr(), BoxInt()]
    storage = Storage()
    fs = [FakeFrame("code0", 0, -1, b1, b2)]
    capture_resumedata(fs, None, [], storage)
    
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    v1 = virtual_value(b1, b3, None)
    v2 = virtual_value(b2, b3, v1)
    v1.setfield(LLtypeMixin.nextdescr, v2)
    values = {b1: v1, b2: v2}
    modifier = ResumeDataVirtualAdder(storage, memo)
    liveboxes = modifier.finish(values)
    assert liveboxes == [b3]
    assert len(storage.rd_virtuals) == 2
    assert storage.rd_virtuals[0].fieldnums == [tag(-1, TAGBOX),
                                                tag(1, TAGVIRTUAL)]
    assert storage.rd_virtuals[1].fieldnums == [tag(-1, TAGBOX),
                                                tag(0, TAGVIRTUAL)]    


# ____________________________________________________________


def test_ResumeDataLoopMemo_ints():
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
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
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
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
    tagged = memo.getconst(cpu.ts.CONST_NULL)
    assert tagged == NULLREF

def test_ResumeDataLoopMemo_other():
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    const = ConstFloat(-1.0)
    tagged = memo.getconst(const)
    index, tagbits = untag(tagged)
    assert tagbits == TAGCONST
    assert memo.consts[index] is const

def test_ResumeDataLoopMemo_number():
    b1, b2, b3, b4, b5 = [BoxInt(), BoxInt(), BoxInt(), BoxPtr(), BoxPtr()]
    c1, c2, c3, c4 = [ConstInt(1), ConstInt(2), ConstInt(3), ConstInt(4)]    

    env = [b1, c1, b2, b1, c2]
    snap = Snapshot(None, env)
    env1 = [c3, b3, b1, c1]
    snap1 = Snapshot(snap, env1)
    env2 = [c3, b3, b1, c3]
    snap2 = Snapshot(snap, env2)

    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())

    numb, liveboxes, v = memo.number({}, snap1)
    assert v == 0

    assert liveboxes == {b1: tag(0, TAGBOX), b2: tag(1, TAGBOX),
                         b3: tag(2, TAGBOX)}
    assert numb.nums == [tag(3, TAGINT), tag(2, TAGBOX), tag(0, TAGBOX),
                         tag(1, TAGINT)]
    assert numb.prev.nums == [tag(0, TAGBOX), tag(1, TAGINT), tag(1, TAGBOX),
                              tag(0, TAGBOX), tag(2, TAGINT)]
    assert numb.prev.prev is None

    numb2, liveboxes2, v = memo.number({}, snap2)
    assert v == 0
    
    assert liveboxes2 == {b1: tag(0, TAGBOX), b2: tag(1, TAGBOX),
                         b3: tag(2, TAGBOX)}
    assert liveboxes2 is not liveboxes
    assert numb2.nums == [tag(3, TAGINT), tag(2, TAGBOX), tag(0, TAGBOX),
                         tag(3, TAGINT)]
    assert numb2.prev is numb.prev

    env3 = [c3, b3, b1, c3]
    snap3 = Snapshot(snap, env3)

    class FakeValue(object):
        def __init__(self, virt, box):
            self.virt = virt
            self.valuebox = box

        def get_key_box(self):
            return self.valuebox

        def is_virtual(self):
            return self.virt

    # renamed
    numb3, liveboxes3, v = memo.number({b3: FakeValue(False, c4)}, snap3)
    assert v == 0
    
    assert liveboxes3 == {b1: tag(0, TAGBOX), b2: tag(1, TAGBOX)}
    assert numb3.nums == [tag(3, TAGINT), tag(4, TAGINT), tag(0, TAGBOX),
                          tag(3, TAGINT)]
    assert numb3.prev is numb.prev

    # virtual
    env4 = [c3, b4, b1, c3]
    snap4 = Snapshot(snap, env4)    

    numb4, liveboxes4, v = memo.number({b4: FakeValue(True, b4)}, snap4)
    assert v == 1
    
    assert liveboxes4 == {b1: tag(0, TAGBOX), b2: tag(1, TAGBOX),
                          b4: tag(0, TAGVIRTUAL)}
    assert numb4.nums == [tag(3, TAGINT), tag(0, TAGVIRTUAL), tag(0, TAGBOX),
                          tag(3, TAGINT)]
    assert numb4.prev is numb.prev

    env5 = [b1, b4, b5]
    snap5 = Snapshot(snap4, env5)    

    numb5, liveboxes5, v = memo.number({b4: FakeValue(True, b4),
                                        b5: FakeValue(True, b5)}, snap5)
    assert v == 2
    
    assert liveboxes5 == {b1: tag(0, TAGBOX), b2: tag(1, TAGBOX),
                          b4: tag(0, TAGVIRTUAL), b5: tag(1, TAGVIRTUAL)}
    assert numb5.nums == [tag(0, TAGBOX), tag(0, TAGVIRTUAL),
                                          tag(1, TAGVIRTUAL)]
    assert numb5.prev is numb4

def test_ResumeDataLoopMemo_number_boxes():
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    b1, b2 = [BoxInt(), BoxInt()]
    assert memo.num_cached_boxes() == 0
    boxes = []
    num = memo.assign_number_to_box(b1, boxes)
    assert num == -1
    assert boxes == [b1]
    assert memo.num_cached_boxes() == 1
    boxes = [None]
    num = memo.assign_number_to_box(b1, boxes)
    assert num == -1
    assert boxes == [b1]
    num = memo.assign_number_to_box(b2, boxes)
    assert num == -2
    assert boxes == [b1, b2]

    assert memo.num_cached_boxes() == 2
    boxes = [None, None]
    num = memo.assign_number_to_box(b2, boxes)
    assert num == -2
    assert boxes == [None, b2]
    num = memo.assign_number_to_box(b1, boxes)
    assert num == -1
    assert boxes == [b1, b2]

    memo.clear_box_virtual_numbers()
    assert memo.num_cached_boxes() == 0

def test_ResumeDataLoopMemo_number_virtuals():
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    b1, b2 = [BoxInt(), BoxInt()]
    assert memo.num_cached_virtuals() == 0
    num = memo.assign_number_to_virtual(b1)
    assert num == -1
    assert memo.num_cached_virtuals() == 1
    num = memo.assign_number_to_virtual(b1)
    assert num == -1
    num = memo.assign_number_to_virtual(b2)
    assert num == -2

    assert memo.num_cached_virtuals() == 2
    num = memo.assign_number_to_virtual(b2)
    assert num == -2
    num = memo.assign_number_to_virtual(b1)
    assert num == -1

    memo.clear_box_virtual_numbers()
    assert memo.num_cached_virtuals() == 0

def test_register_virtual_fields():
    b1, b2 = BoxInt(), BoxInt()
    vbox = BoxPtr()
    modifier = ResumeDataVirtualAdder(None, None)
    modifier.liveboxes_from_env = {}
    modifier.liveboxes = {}
    modifier.vfieldboxes = {}
    modifier.register_virtual_fields(vbox, [b1, b2])
    assert modifier.liveboxes == {vbox: UNASSIGNEDVIRTUAL, b1: UNASSIGNED,
                                  b2: UNASSIGNED}
    assert modifier.vfieldboxes == {vbox: [b1, b2]}

    modifier = ResumeDataVirtualAdder(None, None)
    modifier.liveboxes_from_env = {vbox: tag(0, TAGVIRTUAL)}
    modifier.liveboxes = {}
    modifier.vfieldboxes = {}
    modifier.register_virtual_fields(vbox, [b1, b2, vbox])
    assert modifier.liveboxes == {b1: UNASSIGNED, b2: UNASSIGNED,
                                  vbox: tag(0, TAGVIRTUAL)}
    assert modifier.vfieldboxes == {vbox: [b1, b2, vbox]}

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
    storage.rd_frame_info_list = None
    return storage

def test_virtual_adder_int_constants():
    b1s, b2s, b3s = [ConstInt(sys.maxint), ConstInt(2**16), ConstInt(-65)]
    storage = make_storage(b1s, b2s, b3s)
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())    
    modifier = ResumeDataVirtualAdder(storage, memo)
    liveboxes = modifier.finish({})
    assert storage.rd_snapshot is None
    metainterp = MyMetaInterp()
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
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(storage, memo)
    modifier.finish({})
    assert len(memo.consts) == 2
    assert storage.rd_consts is memo.consts

    b1s, b2s, b3s = [ConstInt(sys.maxint), ConstInt(2**17), ConstInt(-65)]
    storage2 = make_storage(b1s, b2s, b3s)
    modifier2 = ResumeDataVirtualAdder(storage2, memo)
    modifier2.finish({})
    assert len(memo.consts) == 3    
    assert storage2.rd_consts is memo.consts


def test_virtual_adder_no_op_renaming():
    b1s, b2s, b3s = [BoxInt(1), BoxInt(2), BoxInt(3)]
    storage = make_storage(b1s, b2s, b3s)
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(storage, memo)
    b1_2 = BoxInt()
    class FakeValue(object):

        def is_virtual(self):
            return False

        def get_key_box(self):
            return b1_2

    val = FakeValue()
    values = {b1s: val, b2s: val}  
    liveboxes = modifier.finish(values)
    assert storage.rd_snapshot is None
    b1t, b3t = [BoxInt(11), BoxInt(33)]
    newboxes = _resume_remap(liveboxes, [b1_2, b3s], b1t, b3t)
    metainterp = MyMetaInterp()
    reader = ResumeDataReader(storage, newboxes, metainterp)
    lst = reader.consume_boxes()
    assert lst == [b1t, b1t, b3t]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert lst == [b1t, ConstInt(1), b1t, b1t]
    assert metainterp.trace == []    


def test_virtual_adder_make_constant():
    b1s, b2s, b3s = [BoxInt(1), BoxPtr(), BoxInt(3)]
    b1s = ConstInt(111)
    storage = make_storage(b1s, b2s, b3s)
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())        
    modifier = ResumeDataVirtualAdder(storage, memo)
    liveboxes = modifier.finish({})
    b2t, b3t = [BoxPtr(demo55o), BoxInt(33)]
    newboxes = _resume_remap(liveboxes, [b2s, b3s], b2t, b3t)
    metainterp = MyMetaInterp()
    reader = ResumeDataReader(storage, newboxes, metainterp)
    lst = reader.consume_boxes()
    c1t = ConstInt(111)
    assert lst == [c1t, b2t, b3t]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert lst == [c1t, ConstInt(1), c1t, b2t]
    assert metainterp.trace == []


def test_virtual_adder_make_virtual():
    b2s, b3s, b4s, b5s = [BoxPtr(), BoxInt(3), BoxPtr(), BoxPtr()]  
    c1s = ConstInt(111)
    storage = Storage()
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(storage, memo)
    modifier.liveboxes_from_env = {}
    modifier.liveboxes = {}
    modifier.vfieldboxes = {}

    v4 = VirtualValue(fakeoptimizer, ConstAddr(LLtypeMixin.node_vtable_adr2,
                                                LLtypeMixin.cpu), b4s)
    v4.setfield(LLtypeMixin.nextdescr, OptValue(b2s))
    v4.setfield(LLtypeMixin.valuedescr, OptValue(b3s))
    v4.setfield(LLtypeMixin.otherdescr, OptValue(b5s))
    v4._cached_sorted_fields = [LLtypeMixin.nextdescr, LLtypeMixin.valuedescr,
                                LLtypeMixin.otherdescr]
    v2 = VirtualValue(fakeoptimizer, ConstAddr(LLtypeMixin.node_vtable_adr,
                                                LLtypeMixin.cpu), b2s)
    v2.setfield(LLtypeMixin.nextdescr, v4)
    v2.setfield(LLtypeMixin.valuedescr, OptValue(c1s))
    v2._cached_sorted_fields = [LLtypeMixin.nextdescr, LLtypeMixin.valuedescr]

    modifier.register_virtual_fields(b2s, [b4s, c1s])
    modifier.register_virtual_fields(b4s, [b2s, b3s, b5s])
    values = {b2s: v2, b4s: v4}

    liveboxes = []
    modifier._number_virtuals(liveboxes, values, 0)
    storage.rd_consts = memo.consts[:]
    storage.rd_numb = None
    # resume
    b3t, b5t = [BoxInt(33), BoxPtr(demo55o)]
    newboxes = _resume_remap(liveboxes, [#b2s -- virtual
                                         b3s,
                                         #b4s -- virtual
                                         #b2s -- again, shared
                                         #b3s -- again, shared
                                         b5s], b3t, b5t)

    metainterp = MyMetaInterp()
    reader = ResumeDataReader(storage, newboxes, metainterp)
    assert len(reader.virtuals) == 2
    b2t = reader._decode_box(modifier._gettagged(b2s))
    b4t = reader._decode_box(modifier._gettagged(b4s))
    trace = metainterp.trace
    b2new = (rop.NEW_WITH_VTABLE, [ConstAddr(LLtypeMixin.node_vtable_adr,
                                         LLtypeMixin.cpu)],
                              b2t, None)
    b4new = (rop.NEW_WITH_VTABLE, [ConstAddr(LLtypeMixin.node_vtable_adr2,
                                         LLtypeMixin.cpu)],
                              b4t, None)
    b2set = [(rop.SETFIELD_GC, [b2t, b4t],      None, LLtypeMixin.nextdescr),
             (rop.SETFIELD_GC, [b2t, c1s],      None, LLtypeMixin.valuedescr)]
    b4set = [(rop.SETFIELD_GC, [b4t, b2t],     None, LLtypeMixin.nextdescr),
             (rop.SETFIELD_GC, [b4t, b3t],     None, LLtypeMixin.valuedescr),
             (rop.SETFIELD_GC, [b4t, b5t],     None, LLtypeMixin.otherdescr)]
    if untag(modifier._gettagged(b2s))[0] == -2:
        expected = [b2new, b4new] + b2set + b4set
    else:
        expected = [b4new, b2new] + b4set + b2set
        
    for x, y in zip(expected, trace):
        assert x == y
    ptr = b2t.value._obj.container._as_ptr()
    assert lltype.typeOf(ptr) == lltype.Ptr(LLtypeMixin.NODE)
    assert ptr.value == 111
    ptr2 = ptr.next
    ptr2 = lltype.cast_pointer(lltype.Ptr(LLtypeMixin.NODE2), ptr2)
    assert ptr2.other == demo55
    assert ptr2.parent.value == 33
    assert ptr2.parent.next == ptr

def test_virtual_adder_make_varray():
    b2s, b4s = [BoxPtr(), BoxInt(4)]
    c1s = ConstInt(111)
    storage = Storage()
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(storage, memo)
    modifier.liveboxes_from_env = {}
    modifier.liveboxes = {}
    modifier.vfieldboxes = {}

    class FakeOptimizer(object):
        class cpu:
            pass
        def new_const_item(self, descr):
            return None
    v2 = VArrayValue(FakeOptimizer(), LLtypeMixin.arraydescr, 2, b2s)
    v2._items = [b4s, c1s]
    modifier.register_virtual_fields(b2s, [b4s, c1s])
    liveboxes = []
    values = {b2s: v2}
    modifier._number_virtuals(liveboxes, values, 0)
    dump_storage(storage, liveboxes)
    storage.rd_consts = memo.consts[:]
    storage.rd_numb = None
    # resume
    b1t, b3t, b4t = [BoxInt(11), BoxInt(33), BoxInt(44)]
    newboxes = _resume_remap(liveboxes, [#b2s -- virtual
                                         b4s],
                                         b4t)
    # resume
    metainterp = MyMetaInterp()
    reader = ResumeDataReader(storage, newboxes, metainterp)
    assert len(reader.virtuals) == 1
    b2t = reader._decode_box(tag(0, TAGVIRTUAL))
    trace = metainterp.trace
    expected = [
        (rop.NEW_ARRAY, [ConstInt(2)], b2t, LLtypeMixin.arraydescr),
        (rop.SETARRAYITEM_GC, [b2t,ConstInt(0), b4t],None,
                              LLtypeMixin.arraydescr),
        (rop.SETARRAYITEM_GC, [b2t,ConstInt(1), c1s], None,
                              LLtypeMixin.arraydescr),
        ]
    for x, y in zip(expected, trace):
        assert x == y
    #
    ptr = b2t.value._obj.container._as_ptr()
    assert lltype.typeOf(ptr) == lltype.Ptr(lltype.GcArray(lltype.Signed))
    assert len(ptr) == 2
    assert ptr[0] == 44
    assert ptr[1] == 111


def test_virtual_adder_make_vstruct():
    b2s, b4s = [BoxPtr(), BoxPtr()]
    c1s = ConstInt(111)
    storage = Storage()
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(storage, memo)
    modifier.liveboxes_from_env = {}
    modifier.liveboxes = {}
    modifier.vfieldboxes = {}
    v2 = VStructValue(fakeoptimizer, LLtypeMixin.ssize, b2s)
    v2.setfield(LLtypeMixin.adescr, OptValue(c1s))
    v2.setfield(LLtypeMixin.bdescr, OptValue(b4s))
    modifier.register_virtual_fields(b2s, [c1s, b4s])
    liveboxes = []
    modifier._number_virtuals(liveboxes, {b2s: v2}, 0)
    dump_storage(storage, liveboxes)
    storage.rd_consts = memo.consts[:]
    storage.rd_numb = None
    b4t = BoxPtr()
    newboxes = _resume_remap(liveboxes, [#b2s -- virtual
                                         b4s], b4t)
    #
    NULL = ConstPtr.value
    metainterp = MyMetaInterp()
    reader = ResumeDataReader(storage, newboxes, metainterp)
    assert len(reader.virtuals) == 1
    b2t = reader._decode_box(tag(0, TAGVIRTUAL))

    trace = metainterp.trace
    expected = [
        (rop.NEW, [], b2t, LLtypeMixin.ssize),
        (rop.SETFIELD_GC, [b2t, c1s],  None, LLtypeMixin.adescr),
        (rop.SETFIELD_GC, [b2t, b4t], None, LLtypeMixin.bdescr),
        ]
    for x, y in zip(expected, trace):
        assert x == y
    #
    ptr = b2t.value._obj.container._as_ptr()
    assert lltype.typeOf(ptr) == lltype.Ptr(LLtypeMixin.S)
    assert ptr.a == 111
    assert ptr.b == lltype.nullptr(LLtypeMixin.NODE)


def test_virtual_adder_pending_fields():
    b2s, b4s = [BoxPtr(), BoxPtr()]
    storage = Storage()
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(storage, memo)
    modifier.liveboxes_from_env = {}
    modifier.liveboxes = {}
    modifier.vfieldboxes = {}

    v2 = OptValue(b2s)
    v4 = OptValue(b4s)
    modifier.register_box(b2s)
    modifier.register_box(b4s)

    values = {b4s: v4, b2s: v2}
    liveboxes = []
    modifier._number_virtuals(liveboxes, values, 0)
    assert liveboxes == [b2s, b4s] or liveboxes == [b4s, b2s]
    modifier._add_pending_fields([(LLtypeMixin.nextdescr, b2s, b4s)])
    storage.rd_consts = memo.consts[:]
    storage.rd_numb = None
    # resume
    demo55.next = lltype.nullptr(LLtypeMixin.NODE)
    b2t = BoxPtr(demo55o)
    b4t = BoxPtr(demo66o)
    newboxes = _resume_remap(liveboxes, [b2s, b4s], b2t, b4t)

    metainterp = MyMetaInterp()
    reader = ResumeDataReader(storage, newboxes, metainterp)
    assert reader.virtuals is None
    trace = metainterp.trace
    b2set = (rop.SETFIELD_GC, [b2t, b4t], None, LLtypeMixin.nextdescr)
    expected = [b2set]

    for x, y in zip(expected, trace):
        assert x == y
    assert len(expected) == len(trace)
    assert demo55.next == demo66


def test_invalidation_needed():
    class options:
        failargs_limit = 10
        
    metainterp_sd = FakeMetaInterpStaticData()
    metainterp_sd.options = options
    memo = ResumeDataLoopMemo(metainterp_sd)
    modifier = ResumeDataVirtualAdder(None, memo)

    for i in range(5):
        assert not modifier._invalidation_needed(5, i)

    assert not modifier._invalidation_needed(7, 2)
    assert modifier._invalidation_needed(7, 3)

    assert not modifier._invalidation_needed(10, 2)
    assert not modifier._invalidation_needed(10, 3)
    assert modifier._invalidation_needed(10, 4)        
    
