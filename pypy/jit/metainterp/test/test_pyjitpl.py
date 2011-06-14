
# some unit tests for the bytecode decoding

from pypy.jit.metainterp import pyjitpl
from pypy.jit.metainterp import jitprof
from pypy.jit.metainterp.history import BoxInt, ConstInt
from pypy.jit.metainterp.history import History
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.optimizeopt.util import equaloplists
from pypy.jit.codewriter.jitcode import JitCode


def test_portal_trace_positions():
    jitcode = JitCode("f")
    jitcode.setup(None)
    portal = JitCode("portal")
    portal.setup(None)
    class FakeStaticData:
        cpu = None
        warmrunnerdesc = None
        mainjitcode = portal

    metainterp = pyjitpl.MetaInterp(FakeStaticData(), FakeStaticData())
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
        warmrunnerdesc = None
    def is_another_box_like(box, referencebox):
        assert box is not referencebox
        assert isinstance(box, referencebox.clonebox().__class__)
        assert box.value == referencebox.value
        return True
    metainterp = pyjitpl.MetaInterp(FakeStaticData(), None)
    metainterp.history = History()
    b1 = BoxInt(1)
    b2 = BoxInt(2)
    c3 = ConstInt(3)
    boxes = [b1, b2, b1, c3]
    dup = {}
    metainterp.remove_consts_and_duplicates(boxes, 4, dup)
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
    boxes = [b2, b4, "something random"]
    metainterp.remove_consts_and_duplicates(boxes, 2, dup)
    assert is_another_box_like(boxes[0], b2)
    assert boxes[1] is b4
    assert equaloplists(metainterp.history.operations, [
        ResOperation(rop.SAME_AS, [b2], boxes[0]),
        ])

def test_get_name_from_address():
    class FakeMetaInterpSd(pyjitpl.MetaInterpStaticData):
        def __init__(self):
            pass
    metainterp_sd = FakeMetaInterpSd()
    metainterp_sd.setup_list_of_addr2name([(123, 'a'), (456, 'b')])
    assert metainterp_sd.get_name_from_address(123) == 'a'
    assert metainterp_sd.get_name_from_address(456) == 'b'
    assert metainterp_sd.get_name_from_address(789) == ''
