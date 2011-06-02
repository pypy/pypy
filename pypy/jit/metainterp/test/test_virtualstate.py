from pypy.jit.metainterp.optimizeopt.virtualstate import VirtualStateInfo, VStructStateInfo, \
     VArrayStateInfo, NotVirtualStateInfo
from pypy.jit.metainterp.optimizeopt.optimizer import OptValue
from pypy.jit.metainterp.history import BoxInt, BoxFloat, BoxPtr, ConstInt, ConstPtr
from pypy.rpython.lltypesystem import lltype
from pypy.jit.metainterp.test.test_optimizeutil import LLtypeMixin, BaseTest
from pypy.jit.metainterp.optimizeopt.intutils import IntBound
from pypy.jit.metainterp.test.test_optimizebasic import equaloplists

class TestBasic:
    someptr1 = LLtypeMixin.myptr
    someptr2 = LLtypeMixin.myptr2

    def test_position_generalization(self):
        def postest(info1, info2):
            info1.position = 0
            assert info1.generalization_of(info1, {}, {})
            info2.position = 0
            assert info1.generalization_of(info2, {}, {})
            info2.position = 1
            renum = {}
            assert info1.generalization_of(info2, renum, {})
            assert renum == {0:1}
            assert info1.generalization_of(info2, {0:1}, {})
            assert info1.generalization_of(info2, {1:1}, {})
            bad = {}
            assert not info1.generalization_of(info2, {0:0}, bad)
            assert info1 in bad and info2 in bad

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
            return info1.generalization_of(info2, {}, {})

        assert isgeneral(OptValue(BoxInt()), OptValue(ConstInt(7)))
        assert not isgeneral(OptValue(ConstInt(7)), OptValue(BoxInt()))

        ptr = OptValue(BoxPtr())
        nonnull = OptValue(BoxPtr())
        nonnull.make_nonnull(0)
        knownclass = OptValue(BoxPtr())
        knownclass.make_constant_class(ConstPtr(self.someptr1), 0)
        const = OptValue(BoxPtr)
        const.make_constant_class(ConstPtr(self.someptr1), 0)
        const.make_constant(ConstPtr(self.someptr1))
        inorder = [ptr, nonnull, knownclass, const]
        for i in range(len(inorder)):
            for j in range(i, len(inorder)):
                assert isgeneral(inorder[i], inorder[j])
                if i != j:
                    assert not isgeneral(inorder[j], inorder[i])

        value1 = OptValue(BoxInt())
        value2 = OptValue(BoxInt())
        value2.intbound.make_lt(IntBound(10, 10))
        assert isgeneral(value1, value2)
        assert not isgeneral(value2, value1)

    def test_field_matching_generalization(self):
        const1 = NotVirtualStateInfo(OptValue(ConstInt(1)))
        const2 = NotVirtualStateInfo(OptValue(ConstInt(2)))
        const1.position = const2.position = 1
        assert not const1.generalization_of(const2, {}, {})
        assert not const2.generalization_of(const1, {}, {})

        def fldtst(info1, info2):
            info1.position = info2.position = 0
            info1.fieldstate = [const1]
            info2.fieldstate = [const2]
            assert not info1.generalization_of(info2, {}, {})
            assert not info2.generalization_of(info1, {}, {})
            assert info1.generalization_of(info1, {}, {})
            assert info2.generalization_of(info2, {}, {})
        fldtst(VArrayStateInfo(42), VArrayStateInfo(42))
        fldtst(VStructStateInfo(42, [7]), VStructStateInfo(42, [7]))
        fldtst(VirtualStateInfo(ConstInt(42), [7]), VirtualStateInfo(ConstInt(42), [7]))

    def test_known_class_generalization(self):
        knownclass1 = OptValue(BoxPtr())
        knownclass1.make_constant_class(ConstPtr(self.someptr1), 0)
        info1 = NotVirtualStateInfo(knownclass1)
        info1.position = 0
        knownclass2 = OptValue(BoxPtr())
        knownclass2.make_constant_class(ConstPtr(self.someptr1), 0)
        info2 = NotVirtualStateInfo(knownclass2)
        info2.position = 0
        assert info1.generalization_of(info2, {}, {})
        assert info2.generalization_of(info1, {}, {})

        knownclass3 = OptValue(BoxPtr())
        knownclass3.make_constant_class(ConstPtr(self.someptr2), 0)
        info3 = NotVirtualStateInfo(knownclass3)
        info3.position = 0
        assert not info1.generalization_of(info3, {}, {})
        assert not info2.generalization_of(info3, {}, {})
        assert not info3.generalization_of(info2, {}, {})
        assert not info3.generalization_of(info1, {}, {})


    def test_circular_generalization(self):
        for info in (VArrayStateInfo(42), VStructStateInfo(42, [7]),
                     VirtualStateInfo(ConstInt(42), [7])):
            info.position = 0
            info.fieldstate = [info]
            assert info.generalization_of(info, {}, {})

class BaseTestGenerateGuards(BaseTest):            
    def test_intbounds(self):
        value1 = OptValue(BoxInt())
        value1.intbound.make_ge(IntBound(0, 10))
        value1.intbound.make_le(IntBound(20, 30))
        info1 = NotVirtualStateInfo(value1)
        info2 = NotVirtualStateInfo(OptValue(BoxInt()))
        info1.position = info2.position = 0
        guards = []
        box = BoxInt(15)
        info1.generate_guards(info2, box, None, guards, {})
        expected = """
        [i0]
        i1 = int_ge(i0, 0)
        guard_true(i1) []
        i2 = int_le(i0, 30)
        guard_true(i2) []
        """
        loop = self.parse(expected)
        assert equaloplists(guards, loop.operations, False,
                            {loop.inputargs[0]: box})
        
class TestLLtype(BaseTestGenerateGuards, LLtypeMixin):
    pass
