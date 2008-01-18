from pypy.rpython.lltypesystem import lltype
from pypy.jit.timeshifter import rvalue, rcontainer
from pypy.jit.timeshifter.test.support import *


class TestVirtualStruct:

    def make_virtual_struct(self):
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
        self.jitstate = jitstate
        self.V42 = V42
        self.STRUCT = STRUCT
        self.fielddesc = desc
        return box

    def test_virtualstruct_get_set_field(self):
        box = self.make_virtual_struct()
        jitstate = self.jitstate
        box2 = box.op_getfield(jitstate, self.fielddesc)
        assert box2.genvar is self.V42
        assert jitstate.curbuilder.ops == []

    def test_virtualstruct_escape(self):
        box = self.make_virtual_struct()
        jitstate = self.jitstate
        V1 = box.getgenvar(jitstate)     # forcing
        assert jitstate.curbuilder.ops == [
            ('malloc_fixedsize', (('alloc', self.STRUCT),), V1),
            ('setfield', (('field', self.STRUCT, 'foo'), V1, self.V42), None)]
