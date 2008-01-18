from pypy.rpython.lltypesystem import lltype
from pypy.jit.timeshifter import rvalue, rcontainer
from pypy.jit.timeshifter.test.support import *


class TestVirtualStruct:

    def setup_class(cls):
        cls.STRUCT = lltype.Struct("dummy", ("foo", lltype.Signed))
        cls.structdesc = rcontainer.StructTypeDesc(FakeHRTyper(), cls.STRUCT)
        cls.fielddesc = rcontainer.StructFieldDesc(FakeHRTyper(),
                                                   lltype.Ptr(cls.STRUCT),
                                                   "foo", 0)

    def make_virtual_struct(self):
        jitstate = FakeJITState()

        box = self.structdesc.factory()
        assert box.known_nonzero

        V42 = FakeGenVar(42)
        valuebox = rvalue.IntRedBox("dummy kind", V42)
        box.op_setfield(jitstate, self.fielddesc, valuebox)
        assert jitstate.curbuilder.ops == []
        self.jitstate = jitstate
        self.V42 = V42
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

    def test_simple_merge(self):
        oldbox = self.make_virtual_struct()
        frozenbox = oldbox.freeze(rvalue.freeze_memo())
        outgoingvarboxes = []
        res = frozenbox.exactmatch(oldbox, outgoingvarboxes,
                                   rvalue.exactmatch_memo())
        assert res
        fieldbox = oldbox.content.op_getfield(self.jitstate, self.fielddesc)
        assert outgoingvarboxes == [fieldbox]

        newbox = self.make_virtual_struct()
        constbox = rvalue.IntRedBox("dummy kind", FakeGenConst(23))
        newbox.content.op_setfield(self.jitstate, self.fielddesc, constbox)
        outgoingvarboxes = []
        res = frozenbox.exactmatch(newbox, outgoingvarboxes,
                                   rvalue.exactmatch_memo())
        assert res
        assert outgoingvarboxes == [constbox]
