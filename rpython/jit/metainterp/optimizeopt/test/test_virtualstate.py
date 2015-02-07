from __future__ import with_statement
import py
from rpython.jit.metainterp.optimizeopt.virtualstate import VirtualStateInfo, VStructStateInfo, \
     VArrayStateInfo, NotVirtualStateInfo, VirtualState, ShortBoxes, GenerateGuardState, \
     VirtualStatesCantMatch, VArrayStructStateInfo
from rpython.jit.metainterp.optimizeopt.optimizer import OptValue, PtrOptValue,\
      IntOptValue
from rpython.jit.metainterp.history import BoxInt, BoxFloat, BoxPtr, ConstInt, ConstPtr
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin, BaseTest, \
                                                           equaloplists
from rpython.jit.metainterp.optimizeopt.intutils import IntBound
from rpython.jit.metainterp.optimizeopt.virtualize import (VirtualValue,
        VArrayValue, VStructValue, VArrayStructValue)
from rpython.jit.metainterp.history import TreeLoop, JitCellToken
from rpython.jit.metainterp.optimizeopt.test.test_optimizeopt import FakeMetaInterpStaticData
from rpython.jit.metainterp.resoperation import ResOperation, rop
from rpython.jit.metainterp import resume

class BaseTestGenerateGuards(BaseTest):

    def _box_or_value(self, box_or_value=None):
        if box_or_value is None:
            return None, None
        elif isinstance(box_or_value, OptValue):
            value = box_or_value
            box = value.box
        else:
            box = box_or_value
            value = OptValue(box)
        return value, box

    def guards(self, info1, info2, box_or_value, expected, inputargs=None):
        value, box = self._box_or_value(box_or_value)
        if inputargs is None:
            inputargs = [box]
        info1.position = info2.position = 0
        state = GenerateGuardState(self.cpu)
        info1.generate_guards(info2, value, state)
        self.compare(state.extra_guards, expected, inputargs)

    def compare(self, guards, expected, inputargs):
        loop = self.parse(expected)
        boxmap = {}
        assert len(loop.inputargs) == len(inputargs)
        for a, b in zip(loop.inputargs, inputargs):
            boxmap[a] = b
        for op in loop.operations:
            if op.is_guard():
                op.setdescr(None)
        assert equaloplists(guards, loop.operations, False,
                            boxmap)

    def check_no_guards(self, info1, info2, box_or_value=None, state=None):
        value, _ = self._box_or_value(box_or_value)
        if info1.position == -1:
            info1.position = 0
        if info2.position == -1:
            info2.position = 0
        if state is None:
            state = GenerateGuardState(self.cpu)
        info1.generate_guards(info2, value, state)
        assert not state.extra_guards
        return state

    def check_invalid(self, info1, info2, box_or_value=None, state=None):
        value, _ = self._box_or_value(box_or_value)
        if info1.position == -1:
            info1.position = 0
        if info2.position == -1:
            info2.position = 0
        if state is None:
            state = GenerateGuardState(self.cpu)
        with py.test.raises(VirtualStatesCantMatch):
            info1.generate_guards(info2, value, state)


    def test_position_generalization(self):
        def postest(info1, info2):
            info1.position = 0
            self.check_no_guards(info1, info1)
            info2.position = 0
            self.check_no_guards(info1, info2)
            info2.position = 1
            state = self.check_no_guards(info1, info2)
            assert state.renum == {0:1}

            assert self.check_no_guards(info1, info2, state=state)

            # feed fake renums
            state.renum = {1: 1}
            self.check_no_guards(info1, info2, state=state)

            state.renum = {0: 0}
            self.check_invalid(info1, info2, state=state)
            assert info1 in state.bad and info2 in state.bad

        for BoxType in (BoxInt, BoxFloat, BoxPtr):
            info1 = NotVirtualStateInfo(OptValue(BoxType()))
            info2 = NotVirtualStateInfo(OptValue(BoxType()))
            postest(info1, info2)

        info1, info2 = VArrayStateInfo(42), VArrayStateInfo(42)
        info1.fieldstate = info2.fieldstate = []
        postest(info1, info2)

        info1, info2 = VStructStateInfo(42, []), VStructStateInfo(42, [])
        info1.fieldstate = info2.fieldstate = []
        postest(info1, info2)

        info1, info2 = VirtualStateInfo(ConstInt(42), []), VirtualStateInfo(ConstInt(42), [])
        info1.fieldstate = info2.fieldstate = []
        postest(info1, info2)

    def test_NotVirtualStateInfo_generalization(self):
        def isgeneral(value1, value2):
            info1 = NotVirtualStateInfo(value1)
            info1.position = 0
            info2 = NotVirtualStateInfo(value2)
            info2.position = 0
            return VirtualState([info1]).generalization_of(VirtualState([info2]), cpu=self.cpu)

        assert isgeneral(OptValue(BoxInt()), OptValue(ConstInt(7)))
        assert not isgeneral(OptValue(ConstInt(7)), OptValue(BoxInt()))

        ptr = PtrOptValue(BoxPtr())
        nonnull = PtrOptValue(BoxPtr())
        nonnull.make_nonnull(None)
        knownclass = PtrOptValue(BoxPtr())
        clsbox = self.cpu.ts.cls_of_box(BoxPtr(self.myptr))
        knownclass.make_constant_class(None, clsbox)
        const = PtrOptValue(BoxPtr)
        const.make_constant_class(None, clsbox)
        const.make_constant(ConstPtr(self.myptr))
        inorder = [ptr, nonnull, knownclass, const]
        for i in range(len(inorder)):
            for j in range(i, len(inorder)):
                assert isgeneral(inorder[i], inorder[j])
                if i != j:
                    assert not isgeneral(inorder[j], inorder[i])

        value1 = IntOptValue(BoxInt())
        value2 = IntOptValue(BoxInt())
        value2.intbound.make_lt(IntBound(10, 10))
        assert isgeneral(value1, value2)
        assert not isgeneral(value2, value1)

        assert isgeneral(OptValue(ConstInt(7)), OptValue(ConstInt(7)))
        S = lltype.GcStruct('S')
        foo = lltype.malloc(S)
        fooref = lltype.cast_opaque_ptr(llmemory.GCREF, foo)
        assert isgeneral(OptValue(ConstPtr(fooref)),
                         OptValue(ConstPtr(fooref)))

        value1 = PtrOptValue(BoxPtr())
        value1.make_nonnull(None)
        value2 = PtrOptValue(ConstPtr(self.nullptr))
        assert not isgeneral(value1, value2)

    def test_field_matching_generalization(self):
        const1 = NotVirtualStateInfo(OptValue(ConstInt(1)))
        const2 = NotVirtualStateInfo(OptValue(ConstInt(2)))
        const1.position = const2.position = 1
        self.check_invalid(const1, const2)
        self.check_invalid(const2, const1)

        def fldtst(info1, info2):
            info1.position = info2.position = 0
            info1.fieldstate = [const1]
            info2.fieldstate = [const2]
            self.check_invalid(info1, info2)
            self.check_invalid(info2, info1)
            self.check_no_guards(info1, info1)
            self.check_no_guards(info2, info2)
        fakedescr = object()
        fielddescr = object()
        fldtst(VArrayStateInfo(fakedescr), VArrayStateInfo(fakedescr))
        fldtst(VStructStateInfo(fakedescr, [fielddescr]), VStructStateInfo(fakedescr, [fielddescr]))
        fldtst(VirtualStateInfo(ConstInt(42), [fielddescr]), VirtualStateInfo(ConstInt(42), [fielddescr]))
        fldtst(VArrayStructStateInfo(fakedescr, [[fielddescr]]), VArrayStructStateInfo(fakedescr, [[fielddescr]]))

    def test_known_class_generalization(self):
        knownclass1 = PtrOptValue(BoxPtr())
        knownclass1.make_constant_class(None, ConstPtr(self.myptr))
        info1 = NotVirtualStateInfo(knownclass1)
        info1.position = 0
        knownclass2 = PtrOptValue(BoxPtr())
        knownclass2.make_constant_class(None, ConstPtr(self.myptr))
        info2 = NotVirtualStateInfo(knownclass2)
        info2.position = 0
        self.check_no_guards(info1, info2)
        self.check_no_guards(info2, info1)

        knownclass3 = PtrOptValue(BoxPtr())
        knownclass3.make_constant_class(None, ConstPtr(self.myptr2))
        info3 = NotVirtualStateInfo(knownclass3)
        info3.position = 0
        self.check_invalid(info1, info3)
        self.check_invalid(info2, info3)
        self.check_invalid(info3, info2)
        self.check_invalid(info3, info1)


    def test_circular_generalization(self):
        for info in (VArrayStateInfo(42), VStructStateInfo(42, [7]),
                     VirtualStateInfo(ConstInt(42), [7])):
            info.position = 0
            info.fieldstate = [info]
            self.check_no_guards(info, info)


    def test_generate_guards_nonvirtual_all_combinations(self):
        # set up infos
        unknown_val = PtrOptValue(self.nodebox)
        unknownnull_val = PtrOptValue(BoxPtr(self.nullptr))
        unknown_info = NotVirtualStateInfo(unknown_val)

        nonnull_val = PtrOptValue(self.nodebox)
        nonnull_val.make_nonnull(None)
        nonnull_info = NotVirtualStateInfo(nonnull_val)

        knownclass_val = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        knownclass_val.make_constant_class(None, classbox,)
        knownclass_info = NotVirtualStateInfo(knownclass_val)
        knownclass2_val = PtrOptValue(self.nodebox2)
        classbox = self.cpu.ts.cls_of_box(self.nodebox2)
        knownclass2_val.make_constant_class(None, classbox)
        knownclass2_info = NotVirtualStateInfo(knownclass2_val)

        constant_val = IntOptValue(BoxInt())
        constant_val.make_constant(ConstInt(1))
        constant_info = NotVirtualStateInfo(constant_val)
        constclass_val = PtrOptValue(self.nodebox)
        constclass_val.make_constant(self.nodebox.constbox())
        constclass_info = NotVirtualStateInfo(constclass_val)
        constclass2_val = PtrOptValue(self.nodebox)
        constclass2_val.make_constant(self.nodebox2.constbox())
        constclass2_info = NotVirtualStateInfo(constclass2_val)
        constantnull_val = PtrOptValue(ConstPtr(self.nullptr))
        constantnull_info = NotVirtualStateInfo(constantnull_val)

        # unknown unknown
        self.check_no_guards(unknown_info, unknown_info, unknown_val)
        self.check_no_guards(unknown_info, unknown_info)

        # unknown nonnull
        self.check_no_guards(unknown_info, nonnull_info, nonnull_val)
        self.check_no_guards(unknown_info, nonnull_info)

        # unknown knownclass
        self.check_no_guards(unknown_info, knownclass_info, knownclass_val)
        self.check_no_guards(unknown_info, knownclass_info)

        # unknown constant
        self.check_no_guards(unknown_info, constant_info, constant_val)
        self.check_no_guards(unknown_info, constant_info)


        # nonnull unknown
        expected = """
        [p0]
        guard_nonnull(p0) []
        """
        self.guards(nonnull_info, unknown_info, unknown_val, expected)
        self.check_invalid(nonnull_info, unknown_info, unknownnull_val)
        self.check_invalid(nonnull_info, unknown_info)
        self.check_invalid(nonnull_info, unknown_info)

        # nonnull nonnull
        self.check_no_guards(nonnull_info, nonnull_info, nonnull_val)
        self.check_no_guards(nonnull_info, nonnull_info, nonnull_val)

        # nonnull knownclass
        self.check_no_guards(nonnull_info, knownclass_info, knownclass_val)
        self.check_no_guards(nonnull_info, knownclass_info)

        # nonnull constant
        self.check_no_guards(nonnull_info, constant_info, constant_val)
        self.check_invalid(nonnull_info, constantnull_info, constantnull_val)
        self.check_no_guards(nonnull_info, constant_info)
        self.check_invalid(nonnull_info, constantnull_info)


        # knownclass unknown
        expected = """
        [p0]
        guard_nonnull_class(p0, ConstClass(node_vtable)) []
        """
        self.guards(knownclass_info, unknown_info, unknown_val, expected)
        self.check_invalid(knownclass_info, unknown_info, unknownnull_val)
        self.check_invalid(knownclass_info, unknown_info, knownclass2_val)
        self.check_invalid(knownclass_info, unknown_info)
        self.check_invalid(knownclass_info, unknown_info)
        self.check_invalid(knownclass_info, unknown_info)

        # knownclass nonnull
        expected = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        """
        self.guards(knownclass_info, nonnull_info, knownclass_val, expected)
        self.check_invalid(knownclass_info, nonnull_info, knownclass2_val)
        self.check_invalid(knownclass_info, nonnull_info)
        self.check_invalid(knownclass_info, nonnull_info)

        # knownclass knownclass
        self.check_no_guards(knownclass_info, knownclass_info, knownclass_val)
        self.check_invalid(knownclass_info, knownclass2_info, knownclass2_val)
        self.check_no_guards(knownclass_info, knownclass_info)
        self.check_invalid(knownclass_info, knownclass2_info)

        # knownclass constant
        self.check_invalid(knownclass_info, constantnull_info, constantnull_val)
        self.check_invalid(knownclass_info, constclass2_info, constclass2_val)
        self.check_invalid(knownclass_info, constantnull_info)
        self.check_invalid(knownclass_info, constclass2_info)


        # constant unknown
        expected = """
        [i0]
        guard_value(i0, 1) []
        """
        self.guards(constant_info, unknown_info, constant_val, expected)
        self.check_invalid(constant_info, unknown_info, unknownnull_val)
        self.check_invalid(constant_info, unknown_info)
        self.check_invalid(constant_info, unknown_info)

        # constant nonnull
        expected = """
        [i0]
        guard_value(i0, 1) []
        """
        self.guards(constant_info, nonnull_info, constant_val, expected)
        self.check_invalid(constant_info, nonnull_info, constclass2_val)
        self.check_invalid(constant_info, nonnull_info)
        self.check_invalid(constant_info, nonnull_info)

        # constant knownclass
        expected = """
        [i0]
        guard_value(i0, 1) []
        """
        self.guards(constant_info, knownclass_info, constant_val, expected)
        self.check_invalid(constant_info, knownclass_info, unknownnull_val)
        self.check_invalid(constant_info, knownclass_info)
        self.check_invalid(constant_info, knownclass_info)

        # constant constant
        self.check_no_guards(constant_info, constant_info, constant_val)
        self.check_invalid(constant_info, constantnull_info, constantnull_val)
        self.check_no_guards(constant_info, constant_info)
        self.check_invalid(constant_info, constantnull_info)


    def test_intbounds(self):
        value1 = IntOptValue(BoxInt(15))
        value1.intbound.make_ge(IntBound(0, 10))
        value1.intbound.make_le(IntBound(20, 30))
        info1 = NotVirtualStateInfo(value1)
        info2 = NotVirtualStateInfo(IntOptValue(BoxInt()))
        expected = """
        [i0]
        i1 = int_ge(i0, 0)
        guard_true(i1) []
        i2 = int_le(i0, 30)
        guard_true(i2) []
        """
        self.guards(info1, info2, value1, expected)
        self.check_invalid(info1, info2, BoxInt(50))

    def test_intbounds_constant(self):
        value1 = IntOptValue(BoxInt(15))
        value1.intbound.make_ge(IntBound(0, 10))
        value1.intbound.make_le(IntBound(20, 30))
        info1 = NotVirtualStateInfo(value1)
        info2 = NotVirtualStateInfo(IntOptValue(ConstInt(10000)))
        self.check_invalid(info1, info2)
        info1 = NotVirtualStateInfo(value1)
        info2 = NotVirtualStateInfo(IntOptValue(ConstInt(11)))
        self.check_no_guards(info1, info2)

    def test_known_class(self):
        value1 = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value1.make_constant_class(None, classbox)
        info1 = NotVirtualStateInfo(value1)
        info2 = NotVirtualStateInfo(PtrOptValue(self.nodebox))
        expected = """
        [p0]
        guard_nonnull_class(p0, ConstClass(node_vtable)) []        
        """
        self.guards(info1, info2, self.nodebox, expected)
        self.check_invalid(info1, info2, BoxPtr())

    def test_known_class_value(self):
        value1 = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value1.make_constant_class(None, classbox)
        box = self.nodebox
        guards = value1.make_guards(box)
        expected = """
        [p0]
        guard_nonnull_class(p0, ConstClass(node_vtable)) []
        """
        self.compare(guards, expected, [box])

    def test_known_value(self):
        value1 = PtrOptValue(self.nodebox)
        value1.make_constant(ConstInt(1))
        box = self.nodebox
        guards = value1.make_guards(box)
        expected = """
        [i0]
        guard_value(i0, 1) []
        """
        self.compare(guards, expected, [box])

    def test_equal_inputargs(self):
        value = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        vstate1 = VirtualState([knownclass_info, knownclass_info])
        assert vstate1.generalization_of(vstate1)

        unknown_info1 = NotVirtualStateInfo(PtrOptValue(self.nodebox))
        vstate2 = VirtualState([unknown_info1, unknown_info1])
        assert vstate2.generalization_of(vstate2)
        assert not vstate1.generalization_of(vstate2)
        assert vstate2.generalization_of(vstate1)

        unknown_info1 = NotVirtualStateInfo(PtrOptValue(self.nodebox))
        unknown_info2 = NotVirtualStateInfo(PtrOptValue(self.nodebox))
        vstate3 = VirtualState([unknown_info1, unknown_info2])
        assert vstate3.generalization_of(vstate2)
        assert vstate3.generalization_of(vstate1)
        assert not vstate2.generalization_of(vstate3)
        assert not vstate1.generalization_of(vstate3)

        expected = """
        [p0]
        guard_nonnull_class(p0, ConstClass(node_vtable)) []
        """
        state = vstate1.generate_guards(vstate2, [value, value], self.cpu)
        self.compare(state.extra_guards, expected, [self.nodebox])

        with py.test.raises(VirtualStatesCantMatch):
            vstate1.generate_guards(vstate3, [value, value],
                                    self.cpu)
        with py.test.raises(VirtualStatesCantMatch):
            vstate2.generate_guards(vstate3, [value, value],
                                    self.cpu)


    def test_generate_guards_on_virtual_fields_matches_array(self):
        innervalue1 = PtrOptValue(self.nodebox)
        constclassbox = self.cpu.ts.cls_of_box(self.nodebox)
        innervalue1.make_constant_class(None, constclassbox)
        innerinfo1 = NotVirtualStateInfo(innervalue1)
        innerinfo1.position = 1
        innerinfo2 = NotVirtualStateInfo(PtrOptValue(self.nodebox))
        innerinfo2.position = 1

        descr = object()

        info1 = VArrayStateInfo(descr)
        info1.fieldstate = [innerinfo1]

        info2 = VArrayStateInfo(descr)
        info2.fieldstate = [innerinfo2]

        value1 = VArrayValue(descr, None, 1, self.nodebox)
        value1._items[0] = PtrOptValue(self.nodebox)

        expected = """
        [p0]
        guard_nonnull_class(p0, ConstClass(node_vtable)) []
        """
        self.guards(info1, info2, value1, expected, [self.nodebox])

    def test_generate_guards_on_virtual_fields_matches_instance(self):
        innervalue1 = PtrOptValue(self.nodebox)
        constclassbox = self.cpu.ts.cls_of_box(self.nodebox)
        innervalue1.make_constant_class(None, constclassbox)
        innerinfo1 = NotVirtualStateInfo(innervalue1)
        innerinfo1.position = 1
        innerinfo2 = NotVirtualStateInfo(PtrOptValue(self.nodebox))
        innerinfo2.position = 1

        info1 = VirtualStateInfo(ConstInt(42), [1])
        info1.fieldstate = [innerinfo1]

        info2 = VirtualStateInfo(ConstInt(42), [1])
        info2.fieldstate = [innerinfo2]

        value1 = VirtualValue(self.cpu, constclassbox, self.nodebox)
        value1._fields = {1: PtrOptValue(self.nodebox)}

        expected = """
        [p0]
        guard_nonnull_class(p0, ConstClass(node_vtable)) []
        """
        self.guards(info1, info2, value1, expected, [self.nodebox])

    def test_generate_guards_on_virtual_fields_matches_struct(self):
        innervalue1 = PtrOptValue(self.nodebox)
        constclassbox = self.cpu.ts.cls_of_box(self.nodebox)
        innervalue1.make_constant_class(None, constclassbox)
        innerinfo1 = NotVirtualStateInfo(innervalue1)
        innerinfo1.position = 1
        innerinfo2 = NotVirtualStateInfo(PtrOptValue(self.nodebox))
        innerinfo2.position = 1

        structdescr = object()

        info1 = VStructStateInfo(structdescr, [1])
        info1.fieldstate = [innerinfo1]

        info2 = VStructStateInfo(structdescr, [1])
        info2.fieldstate = [innerinfo2]

        value1 = VStructValue(self.cpu, structdescr, self.nodebox)
        value1._fields = {1: PtrOptValue(self.nodebox)}

        expected = """
        [p0]
        guard_nonnull_class(p0, ConstClass(node_vtable)) []
        """
        self.guards(info1, info2, value1, expected, [self.nodebox])

    def test_generate_guards_on_virtual_fields_matches_arraystruct(self):
        innervalue1 = PtrOptValue(self.nodebox)
        constclassbox = self.cpu.ts.cls_of_box(self.nodebox)
        innervalue1.make_constant_class(None, constclassbox)
        innerinfo1 = NotVirtualStateInfo(innervalue1)
        innerinfo1.position = 1
        innerinfo2 = NotVirtualStateInfo(PtrOptValue(self.nodebox))
        innerinfo2.position = 1

        arraydescr = object()
        fielddescr = object()

        info1 = VArrayStructStateInfo(arraydescr, [[fielddescr]])
        info1.fieldstate = [innerinfo1]

        info2 = VArrayStructStateInfo(arraydescr, [[fielddescr]])
        info2.fieldstate = [innerinfo2]

        value1 = VArrayStructValue(arraydescr, 1, self.nodebox)
        value1._items[0][fielddescr] = PtrOptValue(self.nodebox)

        expected = """
        [p0]
        guard_nonnull_class(p0, ConstClass(node_vtable)) []
        """
        self.guards(info1, info2, value1, expected, [self.nodebox])

    # _________________________________________________________________________
    # the below tests don't really have anything to do with guard generation

    def test_virtuals_with_equal_fields(self):
        info1 = VirtualStateInfo(ConstInt(42), [1, 2])
        value = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = VirtualStateInfo(ConstInt(42), [1, 2])
        unknown_info1 = NotVirtualStateInfo(OptValue(self.nodebox))
        info2.fieldstate = [unknown_info1, unknown_info1]
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)
        assert not vstate1.generalization_of(vstate2)
        assert vstate2.generalization_of(vstate1)

        info3 = VirtualStateInfo(ConstInt(42), [1, 2])
        unknown_info1 = NotVirtualStateInfo(OptValue(self.nodebox))
        unknown_info2 = NotVirtualStateInfo(OptValue(self.nodebox))
        info3.fieldstate = [unknown_info1, unknown_info2]
        vstate3 = VirtualState([info3])        
        assert vstate3.generalization_of(vstate2)
        assert vstate3.generalization_of(vstate1)
        assert not vstate2.generalization_of(vstate3)
        assert not vstate1.generalization_of(vstate3)

    def test_virtuals_with_nonmatching_fields(self):
        info1 = VirtualStateInfo(ConstInt(42), [1, 2])
        value = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = VirtualStateInfo(ConstInt(42), [1, 2])
        value = PtrOptValue(self.nodebox2)
        classbox = self.cpu.ts.cls_of_box(self.nodebox2)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info2.fieldstate = [knownclass_info, knownclass_info]
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)

    def test_virtuals_with_nonmatching_descrs(self):
        info1 = VirtualStateInfo(ConstInt(42), [10, 20])
        value = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = VirtualStateInfo(ConstInt(42), [1, 2])
        value = PtrOptValue(self.nodebox2)
        classbox = self.cpu.ts.cls_of_box(self.nodebox2)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info2.fieldstate = [knownclass_info, knownclass_info]
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)
        
    def test_virtuals_with_nonmatching_classes(self):
        info1 = VirtualStateInfo(ConstInt(42), [1, 2])
        value = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = VirtualStateInfo(ConstInt(7), [1, 2])
        value = PtrOptValue(self.nodebox2)
        classbox = self.cpu.ts.cls_of_box(self.nodebox2)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info2.fieldstate = [knownclass_info, knownclass_info]
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)
        
    def test_nonvirtual_is_not_virtual(self):
        info1 = VirtualStateInfo(ConstInt(42), [1, 2])
        value = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = NotVirtualStateInfo(value)
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)

    def test_arrays_with_nonmatching_fields(self):
        info1 = VArrayStateInfo(42)
        value = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = VArrayStateInfo(42)
        value = PtrOptValue(self.nodebox2)
        classbox = self.cpu.ts.cls_of_box(self.nodebox2)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info2.fieldstate = [knownclass_info, knownclass_info]
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)

    def test_arrays_of_different_sizes(self):
        info1 = VArrayStateInfo(42)
        value = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = VArrayStateInfo(42)
        value = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info2.fieldstate = [knownclass_info]
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)

    def test_arrays_with_nonmatching_types(self):
        info1 = VArrayStateInfo(42)
        value = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = VArrayStateInfo(7)
        value = PtrOptValue(self.nodebox2)
        classbox = self.cpu.ts.cls_of_box(self.nodebox2)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info2.fieldstate = [knownclass_info, knownclass_info]
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)
        
    def test_nonvirtual_is_not_array(self):
        info1 = VArrayStateInfo(42)
        value = PtrOptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(None, classbox)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = NotVirtualStateInfo(value)
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)
        

    def test_crash_varay_clear(self):
        innervalue1 = PtrOptValue(self.nodebox)
        constclassbox = self.cpu.ts.cls_of_box(self.nodebox)
        innervalue1.make_constant_class(None, constclassbox)
        innerinfo1 = NotVirtualStateInfo(innervalue1)
        innerinfo1.position = 1
        innerinfo1.position_in_notvirtuals = 0

        descr = object()

        info1 = VArrayStateInfo(descr)
        info1.fieldstate = [innerinfo1]

        constvalue = self.cpu.ts.CVAL_NULLREF
        value1 = VArrayValue(descr, constvalue, 1, self.nodebox, clear=True)
        value1._items[0] = constvalue
        info1.enum_forced_boxes([None], value1, None)

class BaseTestBridges(BaseTest):
    enable_opts = "intbounds:rewrite:virtualize:string:pure:heap:unroll"

    def _do_optimize_bridge(self, bridge, call_pure_results):
        from rpython.jit.metainterp.optimizeopt import optimize_trace
        from rpython.jit.metainterp.optimizeopt.util import args_dict

        self.bridge = bridge
        bridge.call_pure_results = args_dict()
        if call_pure_results is not None:
            for k, v in call_pure_results.items():
                bridge.call_pure_results[list(k)] = v
        metainterp_sd = FakeMetaInterpStaticData(self.cpu)
        if hasattr(self, 'vrefinfo'):
            metainterp_sd.virtualref_info = self.vrefinfo
        if hasattr(self, 'callinfocollection'):
            metainterp_sd.callinfocollection = self.callinfocollection
        #
        optimize_trace(metainterp_sd, None, bridge, self.enable_opts)

        
    def optimize_bridge(self, loops, bridge, expected, expected_target='Loop', **boxvalues):
        if isinstance(loops, str):
            loops = (loops, )
        loops = [self.parse(loop, postprocess=self.postprocess)
                 for loop in loops]
        bridge = self.parse(bridge, postprocess=self.postprocess)
        self.add_guard_future_condition(bridge)
        for loop in loops:
            loop.preamble = self.unroll_and_optimize(loop)
        preamble = loops[0].preamble
        token = JitCellToken()
        token.target_tokens = [l.operations[0].getdescr() for l in [preamble] + loops]

        boxes = {}
        for b in bridge.inputargs + [op.result for op in bridge.operations]:
            boxes[str(b)] = b
        for b, v in boxvalues.items():
            boxes[b].value = v
        bridge.operations[-1].setdescr(token)
        self._do_optimize_bridge(bridge, None)
        if bridge.operations[-1].getopnum() == rop.LABEL:
            assert expected == 'RETRACE'
            return

        print '\n'.join([str(o) for o in bridge.operations])
        expected = self.parse(expected)
        self.assert_equal(bridge, expected)

        if expected_target == 'Preamble':
            assert bridge.operations[-1].getdescr() is preamble.operations[0].getdescr()
        elif expected_target == 'Loop':
            assert len(loops) == 1
            assert bridge.operations[-1].getdescr() is loops[0].operations[0].getdescr()
        elif expected_target.startswith('Loop'):
            n = int(expected_target[4:])
            assert bridge.operations[-1].getdescr() is loops[n].operations[0].getdescr()
        else:
            assert False

    def test_nonnull(self):
        loop = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        jump(p0)
        """
        bridge = """
        [p0]
        jump(p0)
        """
        expected = """
        [p0]
        guard_nonnull(p0) []
        jump(p0)
        """
        self.optimize_bridge(loop, bridge, 'RETRACE', p0=self.nullptr)
        self.optimize_bridge(loop, bridge, expected, p0=self.myptr)
        self.optimize_bridge(loop, expected, expected, p0=self.myptr)
        self.optimize_bridge(loop, expected, expected, p0=self.nullptr)

    def test_cached_nonnull(self):
        loop = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        guard_nonnull(p1) []
        call(p1, descr=nonwritedescr)
        jump(p0)
        """
        bridge = """
        [p0]
        jump(p0)
        """
        expected = """
        [p0]
        guard_nonnull(p0) []
        p1 = getfield_gc(p0, descr=nextdescr)
        guard_nonnull(p1) []
        jump(p0, p1)
        """
        self.optimize_bridge(loop, bridge, expected, p0=self.myptr)

    def test_cached_unused_nonnull(self):        
        loop = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        guard_nonnull(p1) []
        jump(p0)
        """
        bridge = """
        [p0]
        jump(p0)
        """
        expected = """
        [p0]
        guard_nonnull(p0) []
        p1 = getfield_gc(p0, descr=nextdescr)
        guard_nonnull(p1) []
        jump(p0)
        """        
        self.optimize_bridge(loop, bridge, expected, p0=self.myptr)

    def test_cached_invalid_nonnull(self):        
        loop = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        guard_nonnull(p1) []
        jump(p0)
        """
        bridge = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        guard_value(p1, ConstPtr(nullptr)) []        
        jump(p0)
        """
        self.optimize_bridge(loop, bridge, bridge, 'Preamble', p0=self.myptr)

    def test_multiple_nonnull(self):
        loops = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        jump(p0)
        """, """
        [p0]
        jump(p0)
        """
        bridge = """
        [p0]
        jump(p0)
        """
        expected = """
        [p0]
        jump(p0)
        """
        self.optimize_bridge(loops, bridge, expected, 'Loop1', p0=self.nullptr)
        expected = """
        [p0]
        guard_nonnull(p0) []
        jump(p0)
        """
        self.optimize_bridge(loops, bridge, expected, 'Loop0', p0=self.myptr)

    def test_constant(self):
        loops = """
        [i0]
        i1 = same_as(1)
        jump(i1)
        """, """
        [i0]
        i1 = same_as(2)
        jump(i1)
        """, """
        [i0]
        jump(i0)
        """
        expected = """
        [i0]
        jump()
        """
        self.optimize_bridge(loops, loops[0], expected, 'Loop0')
        self.optimize_bridge(loops, loops[1], expected, 'Loop1')
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_bridge(loops, loops[2], expected, 'Loop2')

    def test_cached_constant(self):
        loop = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        guard_value(p1, ConstPtr(myptr)) []
        jump(p0)
        """
        bridge = """
        [p0]
        jump(p0)
        """
        expected = """
        [p0]
        guard_nonnull(p0) []
        p1 = getfield_gc(p0, descr=nextdescr)
        guard_value(p1, ConstPtr(myptr)) []       
        jump(p0)
        """
        self.optimize_bridge(loop, bridge, expected, p0=self.myptr)

    def test_simple_virtual(self):
        loops = """
        [p0, p1]
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p2, p1, descr=nextdescr)
        setfield_gc(p2, 7, descr=adescr)
        setfield_gc(p2, 42, descr=bdescr)
        jump(p2, p1)
        ""","""
        [p0, p1]
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p2, p1, descr=nextdescr)
        setfield_gc(p2, 9, descr=adescr)
        jump(p2, p1)
        """
        expected = """
        [p0, p1]
        jump(p1)
        """
        self.optimize_bridge(loops, loops[0], expected, 'Loop0')
        self.optimize_bridge(loops, loops[1], expected, 'Loop1')
        bridge = """
        [p0, p1]
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p2, p1, descr=nextdescr)
        setfield_gc(p2, 42, descr=adescr)
        setfield_gc(p2, 7, descr=bdescr)
        jump(p2, p1)
        """
        self.optimize_bridge(loops, bridge, "RETRACE")
        bridge = """
        [p0, p1]
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p2, p1, descr=nextdescr)
        setfield_gc(p2, 7, descr=adescr)
        jump(p2, p1)
        """
        self.optimize_bridge(loops, bridge, "RETRACE")

    def test_known_class(self):
        loops = """
        [p0]
        guard_nonnull_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        ""","""
        [p0]
        guard_nonnull_class(p0, ConstClass(node_vtable2)) []
        jump(p0)
        """
        bridge = """
        [p0]
        jump(p0)
        """
        self.optimize_bridge(loops, bridge, loops[0], 'Loop0', p0=self.nodebox.value)
        self.optimize_bridge(loops, bridge, loops[1], 'Loop1', p0=self.nodebox2.value)
        self.optimize_bridge(loops[0], bridge, 'RETRACE', p0=self.nodebox2.value)
        self.optimize_bridge(loops, loops[0], loops[0], 'Loop0', p0=self.nullptr)
        self.optimize_bridge(loops, loops[1], loops[1], 'Loop1', p0=self.nullptr)

    def test_cached_known_class(self):
        loop = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        guard_class(p1, ConstClass(node_vtable)) []
        jump(p0)
        """
        bridge = """
        [p0]
        jump(p0)
        """
        expected = """
        [p0]
        guard_nonnull(p0) []
        p1 = getfield_gc(p0, descr=nextdescr)
        guard_nonnull_class(p1, ConstClass(node_vtable)) []
        jump(p0)        
        """
        self.optimize_bridge(loop, bridge, expected, p0=self.myptr)


    def test_lenbound_array(self):
        loop = """
        [p0]
        i2 = getarrayitem_gc(p0, 10, descr=arraydescr)
        call(i2, descr=nonwritedescr)
        jump(p0)
        """
        expected = """
        [p0]
        i2 = getarrayitem_gc(p0, 10, descr=arraydescr)
        call(i2, descr=nonwritedescr)
        jump(p0, i2)
        """
        self.optimize_bridge(loop, loop, expected, 'Loop0')
        bridge = """
        [p0]
        i2 = getarrayitem_gc(p0, 15, descr=arraydescr)
        jump(p0)
        """
        expected = """
        [p0]
        i2 = getarrayitem_gc(p0, 15, descr=arraydescr)
        i3 = getarrayitem_gc(p0, 10, descr=arraydescr)
        jump(p0, i3)
        """        
        self.optimize_bridge(loop, bridge, expected, 'Loop0')
        bridge = """
        [p0]
        i2 = getarrayitem_gc(p0, 5, descr=arraydescr)
        jump(p0)
        """
        self.optimize_bridge(loop, bridge, 'RETRACE')
        bridge = """
        [p0]
        jump(p0)
        """
        self.optimize_bridge(loop, bridge, 'RETRACE')

    def test_cached_lenbound_array(self):
        loop = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        i2 = getarrayitem_gc(p1, 10, descr=arraydescr)
        call(i2, descr=nonwritedescr)
        jump(p0)
        """
        expected = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        i2 = getarrayitem_gc(p1, 10, descr=arraydescr)
        call(i2, descr=nonwritedescr)
        i3 = arraylen_gc(p1, descr=arraydescr) # Should be killed by backend
        jump(p0, i2, p1)
        """
        self.optimize_bridge(loop, loop, expected)
        bridge = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        i2 = getarrayitem_gc(p1, 15, descr=arraydescr)
        jump(p0)
        """
        expected = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        i2 = getarrayitem_gc(p1, 15, descr=arraydescr)
        i3 = arraylen_gc(p1, descr=arraydescr) # Should be killed by backend        
        i4 = getarrayitem_gc(p1, 10, descr=arraydescr)
        jump(p0, i4, p1)
        """        
        self.optimize_bridge(loop, bridge, expected)
        bridge = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        i2 = getarrayitem_gc(p1, 5, descr=arraydescr)
        jump(p0)
        """
        expected = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        i2 = getarrayitem_gc(p1, 5, descr=arraydescr)
        i3 = arraylen_gc(p1, descr=arraydescr) # Should be killed by backend
        i4 = int_ge(i3, 11)
        guard_true(i4) []
        i5 = getarrayitem_gc(p1, 10, descr=arraydescr)
        jump(p0, i5, p1)
        """        
        self.optimize_bridge(loop, bridge, expected)
        bridge = """
        [p0]
        jump(p0)
        """
        expected = """
        [p0]
        guard_nonnull(p0) []
        p1 = getfield_gc(p0, descr=nextdescr)
        guard_nonnull(p1) []
        i3 = arraylen_gc(p1, descr=arraydescr) # Should be killed by backend
        i4 = int_ge(i3, 11)
        guard_true(i4) []
        i5 = getarrayitem_gc(p1, 10, descr=arraydescr)
        jump(p0, i5, p1)
        """        
        self.optimize_bridge(loop, bridge, expected, p0=self.myptr)

    def test_cached_setarrayitem_gc(self):
        loop = """
        [p0, p1]
        p2 = getfield_gc(p0, descr=nextdescr)
        pp = getarrayitem_gc(p2, 0, descr=arraydescr)
        call(pp, descr=nonwritedescr)
        p3 = getfield_gc(p1, descr=nextdescr)
        setarrayitem_gc(p2, 0, p3, descr=arraydescr)
        jump(p0, p3)
        """
        bridge = """
        [p0, p1]
        jump(p0, p1)
        """
        expected = """
        [p0, p1]
        guard_nonnull(p0) []
        p2 = getfield_gc(p0, descr=nextdescr)
        guard_nonnull(p2) []
        i5 = arraylen_gc(p2, descr=arraydescr)
        i6 = int_ge(i5, 1)
        guard_true(i6) []
        p3 = getarrayitem_gc(p2, 0, descr=arraydescr)
        jump(p0, p1, p3, p2)
        """
        self.optimize_bridge(loop, bridge, expected, p0=self.myptr)

    def test_cache_constant_setfield(self):
        loop = """
        [p5]
        i10 = getfield_gc(p5, descr=valuedescr)
        call(i10, descr=nonwritedescr) 
        setfield_gc(p5, 1, descr=valuedescr)
        jump(p5)
        """
        bridge = """
        [p0]
        jump(p0)
        """
        expected = """
        [p0]
        guard_nonnull(p0) []
        i10 = getfield_gc(p0, descr=valuedescr)
        guard_value(i10, 1) []
        jump(p0)
        """
        self.optimize_bridge(loop, bridge, expected, p0=self.myptr)        
        bridge = """
        [p0]
        setfield_gc(p0, 7, descr=valuedescr)
        jump(p0)
        """
        expected = """
        [p0]
        setfield_gc(p0, 7, descr=valuedescr)
        jump(p0)
        """
        self.optimize_bridge(loop, bridge, expected, 'Preamble', p0=self.myptr)

    def test_cached_equal_fields(self):
        loop = """
        [p5, p6]
        i10 = getfield_gc(p5, descr=valuedescr)
        i11 = getfield_gc(p6, descr=nextdescr)
        call(i10, i11, descr=nonwritedescr)
        setfield_gc(p6, i10, descr=nextdescr)        
        jump(p5, p6)
        """
        bridge = """
        [p5, p6]
        jump(p5, p6)
        """
        expected = """
        [p5, p6]
        guard_nonnull(p5) []
        guard_nonnull(p6) []
        i10 = getfield_gc(p5, descr=valuedescr)
        i11 = getfield_gc(p6, descr=nextdescr)
        jump(p5, p6, i10, i11)
        """
        self.optimize_bridge(loop, bridge, expected, p5=self.myptr, p6=self.myptr2)

    def test_licm_boxed_opaque_getitem(self):
        loop = """
        [p1]
        p2 = getfield_gc(p1, descr=nextdescr) 
        mark_opaque_ptr(p2)        
        guard_class(p2,  ConstClass(node_vtable)) []
        i3 = getfield_gc(p2, descr=otherdescr)
        i4 = call(i3, descr=nonwritedescr)
        jump(p1)
        """
        bridge = """
        [p1]
        guard_nonnull(p1) []
        jump(p1)
        """
        expected = """
        [p1]
        guard_nonnull(p1) []
        p2 = getfield_gc(p1, descr=nextdescr)
        jump(p1)
        """        
        self.optimize_bridge(loop, bridge, expected, 'Preamble')
        
        bridge = """
        [p1]
        p2 = getfield_gc(p1, descr=nextdescr) 
        guard_class(p2,  ConstClass(node_vtable2)) []
        jump(p1)
        """
        expected = """
        [p1]
        p2 = getfield_gc(p1, descr=nextdescr) 
        guard_class(p2,  ConstClass(node_vtable2)) []
        jump(p1)
        """
        self.optimize_bridge(loop, bridge, expected, 'Preamble')

        bridge = """
        [p1]
        p2 = getfield_gc(p1, descr=nextdescr) 
        guard_class(p2,  ConstClass(node_vtable)) []
        jump(p1)
        """
        expected = """
        [p1]
        p2 = getfield_gc(p1, descr=nextdescr) 
        guard_class(p2,  ConstClass(node_vtable)) []
        i3 = getfield_gc(p2, descr=otherdescr)
        jump(p1, i3)
        """
        self.optimize_bridge(loop, bridge, expected, 'Loop')

    def test_licm_unboxed_opaque_getitem(self):
        loop = """
        [p2]
        mark_opaque_ptr(p2)        
        guard_class(p2,  ConstClass(node_vtable)) []
        i3 = getfield_gc(p2, descr=otherdescr)
        i4 = call(i3, descr=nonwritedescr)
        jump(p2)
        """
        bridge = """
        [p1]
        guard_nonnull(p1) []
        jump(p1)
        """
        self.optimize_bridge(loop, bridge, 'RETRACE', p1=self.myptr)
        self.optimize_bridge(loop, bridge, 'RETRACE', p1=self.myptr2)
        
        bridge = """
        [p2]
        guard_class(p2,  ConstClass(node_vtable2)) []
        jump(p2)
        """
        self.optimize_bridge(loop, bridge, 'RETRACE')

        bridge = """
        [p2]
        guard_class(p2,  ConstClass(node_vtable)) []
        jump(p2)
        """
        expected = """
        [p2]
        guard_class(p2,  ConstClass(node_vtable)) []
        i3 = getfield_gc(p2, descr=otherdescr)
        jump(p2, i3)
        """
        self.optimize_bridge(loop, bridge, expected, 'Loop')

    def test_licm_virtual_opaque_getitem(self):
        loop = """
        [p1]
        p2 = getfield_gc(p1, descr=nextdescr) 
        mark_opaque_ptr(p2)        
        guard_class(p2,  ConstClass(node_vtable)) []
        i3 = getfield_gc(p2, descr=otherdescr)
        i4 = call(i3, descr=nonwritedescr)
        p3 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p3, p2, descr=nextdescr)
        jump(p3)
        """
        bridge = """
        [p1]
        p3 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p3, p1, descr=nextdescr)
        jump(p3)
        """
        self.optimize_bridge(loop, bridge, 'RETRACE', p1=self.myptr)
        self.optimize_bridge(loop, bridge, 'RETRACE', p1=self.myptr2)

        bridge = """
        [p1]
        p3 = new_with_vtable(ConstClass(node_vtable))
        guard_class(p1,  ConstClass(node_vtable2)) []
        setfield_gc(p3, p1, descr=nextdescr)
        jump(p3)
        """
        self.optimize_bridge(loop, bridge, 'RETRACE')

        bridge = """
        [p1]
        p3 = new_with_vtable(ConstClass(node_vtable))
        guard_class(p1,  ConstClass(node_vtable)) []
        setfield_gc(p3, p1, descr=nextdescr)
        jump(p3)
        """
        expected = """
        [p1]
        guard_class(p1,  ConstClass(node_vtable)) []
        i3 = getfield_gc(p1, descr=otherdescr)
        jump(p1, i3)
        """
        self.optimize_bridge(loop, bridge, expected)


class TestLLtypeGuards(BaseTestGenerateGuards, LLtypeMixin):
    pass

class TestLLtypeBridges(BaseTestBridges, LLtypeMixin):
    pass

class FakeOptimizer:
    def __init__(self):
        self.opaque_pointers = {}
        self.values = {}
    def make_equal_to(*args):
        pass
    def getvalue(*args):
        pass
    def emit_operation(*args):
        pass


class TestShortBoxes:
    p1 = BoxPtr()
    p2 = BoxPtr()
    p3 = BoxPtr()
    p4 = BoxPtr()
    i1 = BoxInt()
    i2 = BoxInt()
    i3 = BoxInt()
    i4 = BoxInt()
    
    def test_short_box_duplication_direct(self):
        class Optimizer(FakeOptimizer):
            def produce_potential_short_preamble_ops(_self, sb):
                sb.add_potential(ResOperation(rop.GETFIELD_GC, [self.p1], self.i1))
                sb.add_potential(ResOperation(rop.GETFIELD_GC, [self.p2], self.i1))
        sb = ShortBoxes(Optimizer(), [self.p1, self.p2])
        assert len(sb.short_boxes) == 4
        assert self.i1 in sb.short_boxes
        assert sum([op.result is self.i1 for op in sb.short_boxes.values() if op]) == 1

    def test_dont_duplicate_potential_boxes(self):
        class Optimizer(FakeOptimizer):
            def produce_potential_short_preamble_ops(_self, sb):
                sb.add_potential(ResOperation(rop.GETFIELD_GC, [self.p1], self.i1))
                sb.add_potential(ResOperation(rop.GETFIELD_GC, [BoxPtr()], self.i1))
                sb.add_potential(ResOperation(rop.INT_NEG, [self.i1], self.i2))
                sb.add_potential(ResOperation(rop.INT_ADD, [ConstInt(7), self.i2],
                                              self.i3))
        sb = ShortBoxes(Optimizer(), [self.p1, self.p2])
        assert len(sb.short_boxes) == 5

    def test_prioritize1(self):
        class Optimizer(FakeOptimizer):
            def produce_potential_short_preamble_ops(_self, sb):
                sb.add_potential(ResOperation(rop.GETFIELD_GC, [self.p1], self.i1))
                sb.add_potential(ResOperation(rop.GETFIELD_GC, [self.p2], self.i1))
                sb.add_potential(ResOperation(rop.INT_NEG, [self.i1], self.i2))
        sb = ShortBoxes(Optimizer(), [self.p1, self.p2])
        assert len(sb.short_boxes.values()) == 5
        int_neg = [op for op in sb.short_boxes.values()
                   if op and op.getopnum() == rop.INT_NEG]
        assert len(int_neg) == 1
        int_neg = int_neg[0]
        getfield = [op for op in sb.short_boxes.values()
                    if op and op.result == int_neg.getarg(0)]
        assert len(getfield) == 1
        assert getfield[0].getarg(0) in [self.p1, self.p2]

    def test_prioritize1bis(self):
        class Optimizer(FakeOptimizer):
            def produce_potential_short_preamble_ops(_self, sb):
                sb.add_potential(ResOperation(rop.GETFIELD_GC, [self.p1], self.i1),
                                 synthetic=True)
                sb.add_potential(ResOperation(rop.GETFIELD_GC, [self.p2], self.i1),
                                 synthetic=True)
                sb.add_potential(ResOperation(rop.INT_NEG, [self.i1], self.i2))
        sb = ShortBoxes(Optimizer(), [self.p1, self.p2])
        assert len(sb.short_boxes.values()) == 5
        int_neg = [op for op in sb.short_boxes.values()
                   if op and op.getopnum() == rop.INT_NEG]
        assert len(int_neg) == 1
        int_neg = int_neg[0]
        getfield = [op for op in sb.short_boxes.values()
                    if op and op.result == int_neg.getarg(0)]
        assert len(getfield) == 1
        assert getfield[0].getarg(0) in [self.p1, self.p2]
        
    def test_prioritize2(self):
        class Optimizer(FakeOptimizer):
            def produce_potential_short_preamble_ops(_self, sb):
                sb.add_potential(ResOperation(rop.GETFIELD_GC, [self.p1], self.i1),
                                 synthetic=True)
                sb.add_potential(ResOperation(rop.GETFIELD_GC, [self.p2], self.i1))
                sb.add_potential(ResOperation(rop.INT_NEG, [self.i1], self.i2))
        sb = ShortBoxes(Optimizer(), [self.p1, self.p2])
        assert len(sb.short_boxes.values()) == 5
        int_neg = [op for op in sb.short_boxes.values()
                   if op and op.getopnum() == rop.INT_NEG]
        assert len(int_neg) == 1
        int_neg = int_neg[0]
        getfield = [op for op in sb.short_boxes.values()
                    if op and op.result == int_neg.getarg(0)]
        assert len(getfield) == 1
        assert getfield[0].getarg(0) == self.p2
        
    def test_prioritize3(self):
        class Optimizer(FakeOptimizer):
            def produce_potential_short_preamble_ops(_self, sb):
                sb.add_potential(ResOperation(rop.GETFIELD_GC, [self.p1], self.i1))
                sb.add_potential(ResOperation(rop.GETFIELD_GC, [self.p2], self.i1),
                                 synthetic=True)
                sb.add_potential(ResOperation(rop.INT_NEG, [self.i1], self.i2))
        sb = ShortBoxes(Optimizer(), [self.p1, self.p2])
        assert len(sb.short_boxes.values()) == 5
        int_neg = [op for op in sb.short_boxes.values()
                   if op and op.getopnum() == rop.INT_NEG]
        assert len(int_neg) == 1
        int_neg = int_neg[0]
        getfield = [op for op in sb.short_boxes.values()
                    if op and op.result == int_neg.getarg(0)]
        assert len(getfield) == 1
        assert getfield[0].getarg(0) == self.p1
