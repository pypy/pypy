
# some unit tests for the bytecode decoding

from pypy.jit.metainterp import pyjitpl, codewriter, resoperation, history
from pypy.jit.metainterp import jitprof
from pypy.jit.metainterp.history import AbstractFailDescr, BoxInt, ConstInt
from pypy.jit.metainterp.history import History
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.test.test_optimizeopt import equaloplists

def make_frame(code):
    bytecode = codewriter.JitCode("hello")
    bytecode.code = code
    bytecode.constants = None
    frame = pyjitpl.MIFrame(None, bytecode)
    frame.pc = 0
    return frame


def test_decode_big_int():
    for code, value in [("\x80\x01", 128), ("\x81\x81\x01", 1 + (1 << 7) + (1 << 14))]:
        frame = make_frame(code)
        val = frame.load_int()
        assert val == value
 
def test_decode_bool():
    frame = make_frame("\x00")
    assert not frame.load_bool()

    frame = make_frame("\x01")
    assert frame.load_bool()

def test_simple_opimpl_exist():
    rop = resoperation.rop
    for opnum, opname in resoperation.opname.items():
        if opnum in (rop.SAME_AS, rop.CALL_PURE, rop.OOSEND_PURE,
                     rop.FORCE_TOKEN):
            continue
        if rop._NOSIDEEFFECT_FIRST <= opnum <= rop._NOSIDEEFFECT_LAST:
            assert hasattr(pyjitpl.MIFrame, 'opimpl_' + opname.lower()), opname

def test_portal_trace_positions():
    jitcode = codewriter.JitCode("f")
    jitcode.code = jitcode.constants = None
    portal = codewriter.JitCode("portal")
    portal.code = portal.constants = None
    class FakeStaticData:
        cpu = None
        portal_code = portal

    metainterp = pyjitpl.MetaInterp(FakeStaticData())
    metainterp.framestack = []
    class FakeHistory:
        operations = []
    history = metainterp.history = FakeHistory()
    metainterp.newframe(portal, "green1")
    history.operations.append(1)
    metainterp.newframe(jitcode)
    history.operations.append(2)
    metainterp.newframe(portal, "green2")
    history.operations.append(3)
    metainterp.popframe()
    history.operations.append(4)
    metainterp.popframe()
    history.operations.append(5)
    metainterp.popframe()
    history.operations.append(6)
    assert metainterp.portal_trace_positions == [("green1", 0), ("green2", 2),
                                                 (None, 3), (None, 5)]
    assert metainterp.find_biggest_function() == "green1"

    metainterp.newframe(portal, "green3")
    history.operations.append(7)
    metainterp.newframe(jitcode)
    history.operations.append(8)
    assert metainterp.portal_trace_positions == [("green1", 0), ("green2", 2),
                                                 (None, 3), (None, 5), ("green3", 6)]
    assert metainterp.find_biggest_function() == "green1"

    history.operations.extend([9, 10, 11, 12])
    assert metainterp.find_biggest_function() == "green3"

def test_remove_consts_and_duplicates():
    class FakeStaticData:
        cpu = None
    def is_another_box_like(box, referencebox):
        assert box is not referencebox
        assert isinstance(box, referencebox.clonebox().__class__)
        assert box.value == referencebox.value
        return True
    metainterp = pyjitpl.MetaInterp(FakeStaticData())
    metainterp.history = History()
    b1 = BoxInt(1)
    b2 = BoxInt(2)
    c3 = ConstInt(3)
    boxes = [b1, b2, b1, c3]
    dup = {}
    metainterp.remove_consts_and_duplicates(boxes, 0, 4, dup)
    assert boxes[0] is b1
    assert boxes[1] is b2
    assert is_another_box_like(boxes[2], b1)
    assert is_another_box_like(boxes[3], c3)
    assert equaloplists(metainterp.history.operations, [
        ResOperation(rop.SAME_AS, [b1], boxes[2]),
        ResOperation(rop.SAME_AS, [c3], boxes[3]),
        ])
    assert dup == {b1: None, b2: None}
    #
    del metainterp.history.operations[:]
    b4 = BoxInt(4)
    boxes = ["something random", b2, b4, "something else"]
    metainterp.remove_consts_and_duplicates(boxes, 1, 3, dup)
    assert is_another_box_like(boxes[1], b2)
    assert boxes[2] is b4
    assert equaloplists(metainterp.history.operations, [
        ResOperation(rop.SAME_AS, [b2], boxes[1]),
        ])

def test_get_name_from_address():
    class FakeMetaInterpSd(pyjitpl.MetaInterpStaticData):
        def __init__(self):
            pass
    metainterp_sd = FakeMetaInterpSd()
    metainterp_sd.info_from_codewriter(None, None, None,
                                       [(123, "a"), (456, "b")],
                                       None)
    assert metainterp_sd.get_name_from_address(123) == 'a'
    assert metainterp_sd.get_name_from_address(456) == 'b'
    assert metainterp_sd.get_name_from_address(789) == ''

def test_initialize_state_from_guard_failure():
    from pypy.jit.metainterp.typesystem import llhelper        
    calls = []

    class FakeCPU:
        ts = llhelper

        def make_boxes_from_latest_values(self, faildescr):
            return [BoxInt(0), None, BoxInt(2), None, BoxInt(4)]
        
    class FakeStaticData:
        cpu = FakeCPU()
        profiler = jitprof.EmptyProfiler()

    metainterp = pyjitpl.MetaInterp(FakeStaticData())

    def rebuild_state_after_failure(descr, newboxes):
        calls.append(newboxes)
    metainterp.rebuild_state_after_failure = rebuild_state_after_failure
    
    class FakeResumeDescr:
        def must_compile(self, *args):
            return True
    resumedescr = FakeResumeDescr()
    metainterp.initialize_state_from_guard_failure(resumedescr)

    inp = metainterp.history.inputargs
    assert len(inp) == 3
    assert [box.value for box in inp] == [0, 2, 4]
    b0, b2, b4 = inp
    assert len(calls) == 1
    assert calls[0] == [b0, None, b2, None, b4]
