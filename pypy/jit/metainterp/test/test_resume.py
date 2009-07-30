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
    builder = ResumeDataBuilder()
    builder.generate_boxes([b1, c1, b1, b2])
    builder.generate_boxes([c2, c3])
    builder.generate_boxes([b1, b2, b3])
    liveboxes = builder.finish(storage)
    assert liveboxes == [b1, b2, b3]
    return storage

# ____________________________________________________________


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
    #
    builder = ResumeDataBuilder()
    builder.generate_frame_info(1, 2)
    builder.generate_frame_info(3, 4)
    liveboxes = builder.finish(storage)
    assert liveboxes == []
    #
    reader = ResumeDataReader(storage, liveboxes)
    assert reader.has_more_frame_infos()
    fi = reader.consume_frame_info()
    assert fi == (1, 2)
    assert reader.has_more_frame_infos()
    fi = reader.consume_frame_info()
    assert fi == (3, 4)
    assert not reader.has_more_frame_infos()


class MyMetaInterp:
    def __init__(self, cpu):
        self.cpu = cpu
        self.trace = []
    def execute_and_record(self, opnum, argboxes, descr=None):
        resbox = executor.execute(self.cpu, opnum, argboxes, descr)
        self.trace.append((opnum,
                           [box.value for box in argboxes],
                           resbox and resbox.value,
                           descr))
        return resbox

demo55 = lltype.malloc(LLtypeMixin.NODE)
demo55o = lltype.cast_opaque_ptr(llmemory.GCREF, demo55)


def test_virtual_adder_no_op():
    storage = make_demo_storage()
    b1s, b2s, b3s = [BoxInt(1), BoxPtr(), BoxInt(3)]
    modifier = ResumeDataVirtualAdder(storage, [b1s, b2s, b3s])
    assert not modifier.is_virtual(b1s)
    assert not modifier.is_virtual(b2s)
    assert not modifier.is_virtual(b3s)
    # done
    liveboxes = modifier.finish()
    assert liveboxes == [b1s, b2s, b3s]
    #
    b1t, b2t, b3t = [BoxInt(11), BoxPtr(demo55o), BoxInt(33)]
    metainterp = MyMetaInterp(LLtypeMixin.cpu)
    reader = ResumeDataReader(storage, [b1t, b2t, b3t], metainterp)
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
    assert liveboxes == [b1s,
                         #b2s -- virtual
                         b3s,
                         #b4s -- virtual
                         #b2s -- again, shared
                         #b3s -- again, shared
                         b5s]
    #
    b1t, b3t, b5t = [BoxInt(11), BoxInt(33), BoxPtr(demo55o)]
    metainterp = MyMetaInterp(LLtypeMixin.cpu)
    reader = ResumeDataReader(storage, [b1t, b3t, b5t], metainterp)
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
        assert liveboxes == [b2s, b3s]
        #
        b2t, b3t = [BoxPtr(demo55o), BoxInt(33)]
        metainterp = MyMetaInterp(LLtypeMixin.cpu)
        reader = ResumeDataReader(storage, [b2t, b3t], metainterp)
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
    assert liveboxes == [b1s,
                         #b2s -- virtual
                         b3s,
                         b4s]
    #
    b1t, b3t, b4t = [BoxInt(11), BoxInt(33), BoxInt(44)]
    metainterp = MyMetaInterp(LLtypeMixin.cpu)
    reader = ResumeDataReader(storage, [b1t, b3t, b4t], metainterp)
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
    assert liveboxes == [b1s,
                         #b2s -- virtual
                         b3s,
                         b4s]
    #
    NULL = ConstPtr.value
    b1t, b3t, b4t = [BoxInt(11), BoxInt(33), BoxPtr()]
    metainterp = MyMetaInterp(LLtypeMixin.cpu)
    reader = ResumeDataReader(storage, [b1t, b3t, b4t], metainterp)
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
