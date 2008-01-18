from pypy.rpython.lltypesystem import lltype
from pypy.jit.timeshifter import rvalue, rcontainer
from pypy.jit.timeshifter.test.support import FakeJITState, FakeGenVar
from pypy.jit.timeshifter.test.support import FakeGenConst
from pypy.jit.timeshifter.test.support import fakehrtyper, signed_kind
from pypy.jit.timeshifter.test.support import vmalloc, makebox
from pypy.jit.timeshifter.test.support import getfielddesc


class TestVirtualStruct:

    def setup_class(cls):
        cls.STRUCT = lltype.Struct("dummy", ("foo", lltype.Signed))
        cls.fielddesc = getfielddesc(cls.STRUCT, "foo")

    def test_virtualstruct_get_set_field(self):
        V42 = FakeGenVar(42)
        box = vmalloc(self.STRUCT, makebox(V42))
        assert box.known_nonzero
        jitstate = FakeJITState()
        box2 = box.op_getfield(jitstate, self.fielddesc)
        assert box2.genvar is V42
        assert jitstate.curbuilder.ops == []

    def test_virtualstruct_escape(self):
        V42 = FakeGenVar(42)
        box = vmalloc(self.STRUCT, makebox(V42))
        jitstate = FakeJITState()
        V1 = box.getgenvar(jitstate)     # forcing
        assert jitstate.curbuilder.ops == [
            ('malloc_fixedsize', (('alloc', self.STRUCT),), V1),
            ('setfield', (('field', self.STRUCT, 'foo'), V1, V42), None)]

    def test_simple_merge(self):
        V42 = FakeGenVar(42)
        oldbox = vmalloc(self.STRUCT, makebox(V42))
        frozenbox = oldbox.freeze(rvalue.freeze_memo())
        # check that frozenbox matches oldbox exactly
        outgoingvarboxes = []
        res = frozenbox.exactmatch(oldbox, outgoingvarboxes,
                                   rvalue.exactmatch_memo())
        assert res
        jitstate = FakeJITState()
        fieldbox = oldbox.content.op_getfield(jitstate, self.fielddesc)
        assert outgoingvarboxes == [fieldbox]
        #       ^^^ the live box corresponding to the FrozenVar

        constbox23 = makebox(23)
        newbox = vmalloc(self.STRUCT, constbox23)
        # check that frozenbox also matches newbox exactly
        outgoingvarboxes = []
        res = frozenbox.exactmatch(newbox, outgoingvarboxes,
                                   rvalue.exactmatch_memo())
        assert res
        assert outgoingvarboxes == [constbox23]
        #       ^^^ the live box corresponding to the FrozenVar

    def test_simple_merge_generalize(self):
        S = self.STRUCT
        constbox20 = makebox(20)
        oldbox = vmalloc(S, constbox20)
        frozenbox = oldbox.freeze(rvalue.freeze_memo())
        # check that frozenbox matches oldbox exactly
        outgoingvarboxes = []
        res = frozenbox.exactmatch(oldbox, outgoingvarboxes,
                                   rvalue.exactmatch_memo())
        assert res
        assert outgoingvarboxes == []     # there is no FrozenVar

        constbox23 = makebox(23)
        newbox = vmalloc(S, constbox23)
        # non-exact match: a different constant box in the virtual struct field
        outgoingvarboxes = []
        res = frozenbox.exactmatch(newbox, outgoingvarboxes,
                                   rvalue.exactmatch_memo())
        assert not res
        assert outgoingvarboxes == [constbox23]
        #       ^^^ constbox23 is what should be generalized with forcevar()
        #           in order to get something that is at least as general as
        #           both oldbox and newbox

        jitstate = FakeJITState()
        replace_memo = rvalue.copy_memo()
        forcedbox = constbox23.forcevar(jitstate, replace_memo, False)
        assert not forcedbox.is_constant()
        assert jitstate.curbuilder.ops == [
            ('same_as', (signed_kind, constbox23.genvar), forcedbox.genvar)]
        assert replace_memo.boxes == {constbox23: forcedbox}

        # change constbox to forcedbox inside newbox
        newbox.replace(replace_memo)
        assert (newbox.content.op_getfield(jitstate, self.fielddesc) is
                forcedbox)

        # check that now newbox really generalizes oldbox
        newfrozenbox = newbox.freeze(rvalue.freeze_memo())
        outgoingvarboxes = []
        res = newfrozenbox.exactmatch(oldbox, outgoingvarboxes,
                                      rvalue.exactmatch_memo())
        assert res
        assert outgoingvarboxes == [constbox20]
        #       ^^^ the FrozenVar() in newfrozenbox corresponds to
        #           constbox20 in oldbox.
