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
        # check that frozenbox matches oldbox exactly
        outgoingvarboxes = []
        res = frozenbox.exactmatch(oldbox, outgoingvarboxes,
                                   rvalue.exactmatch_memo())
        assert res
        fieldbox = oldbox.content.op_getfield(self.jitstate, self.fielddesc)
        assert outgoingvarboxes == [fieldbox]
        #       ^^^ the live box corresponding to the FrozenVar

        newbox = self.make_virtual_struct()
        constbox = rvalue.IntRedBox("dummy kind", FakeGenConst(23))
        newbox.content.op_setfield(self.jitstate, self.fielddesc, constbox)
        # check that frozenbox also matches newbox exactly
        outgoingvarboxes = []
        res = frozenbox.exactmatch(newbox, outgoingvarboxes,
                                   rvalue.exactmatch_memo())
        assert res
        assert outgoingvarboxes == [constbox]
        #       ^^^ the live box corresponding to the FrozenVar

    def test_simple_merge_generalize(self):
        oldbox = self.make_virtual_struct()
        oldconstbox = rvalue.IntRedBox("dummy kind", FakeGenConst(20))
        oldbox.content.op_setfield(self.jitstate, self.fielddesc, oldconstbox)
        frozenbox = oldbox.freeze(rvalue.freeze_memo())
        # check that frozenbox matches oldbox exactly
        outgoingvarboxes = []
        res = frozenbox.exactmatch(oldbox, outgoingvarboxes,
                                   rvalue.exactmatch_memo())
        assert res
        assert outgoingvarboxes == []     # there is no FrozenVar

        newbox = self.make_virtual_struct()
        C23 = FakeGenConst(23)
        constbox = rvalue.IntRedBox("dummy kind", C23)
        newbox.content.op_setfield(self.jitstate, self.fielddesc, constbox)
        # non-exact match: a different constant box in the virtual struct field
        outgoingvarboxes = []
        res = frozenbox.exactmatch(newbox, outgoingvarboxes,
                                   rvalue.exactmatch_memo())
        assert not res
        assert outgoingvarboxes == [constbox]
        #       ^^^ the constbox is what should be generalized with forcevar()
        #           in order to get something that is at least as general as
        #           both oldbox and newbox

        assert self.jitstate.curbuilder.ops == []
        replace_memo = rvalue.copy_memo()
        forcedbox = constbox.forcevar(self.jitstate, replace_memo, False)
        assert not forcedbox.is_constant()
        assert self.jitstate.curbuilder.ops == [
            ('same_as', ("dummy kind", C23), forcedbox.genvar)]
        assert replace_memo.boxes == {constbox: forcedbox}

        # change constbox to forcedbox inside newbox
        newbox.replace(replace_memo)
        assert (newbox.content.op_getfield(self.jitstate, self.fielddesc) is
                forcedbox)

        # check that now newbox really generalizes oldbox
        newfrozenbox = newbox.freeze(rvalue.freeze_memo())
        outgoingvarboxes = []
        res = newfrozenbox.exactmatch(oldbox, outgoingvarboxes,
                                      rvalue.exactmatch_memo())
        assert res
        assert outgoingvarboxes == [oldconstbox]
        #       ^^^ the FrozenVar() in newfrozenbox corresponds to
        #           oldconstbox in oldbox.
