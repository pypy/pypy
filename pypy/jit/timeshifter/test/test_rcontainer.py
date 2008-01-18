from pypy.rpython.lltypesystem import lltype
from pypy.jit.timeshifter import rvalue, rcontainer
from pypy.jit.timeshifter.test.support import *


def test_virtualstruct_get_set_field():
    jitstate = FakeJITState()
    STRUCT = lltype.Struct("dummy", ("foo", lltype.Signed))
    structdesc = rcontainer.StructTypeDesc(FakeHRTyper(), STRUCT)
    desc = rcontainer.StructFieldDesc(FakeHRTyper(), lltype.Ptr(STRUCT), "foo", 0)

    box = structdesc.factory()
    assert box.known_nonzero

    V42 = FakeGenVar(42)
    valuebox = rvalue.IntRedBox("dummy kind", V42)
    box.op_setfield(jitstate, desc, valuebox)
    assert jitstate.curbuilder.ops == []

    box2 = box.op_getfield(jitstate, desc)
    assert box2.genvar is V42
    assert jitstate.curbuilder.ops == []
