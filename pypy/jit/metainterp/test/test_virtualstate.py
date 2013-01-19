from __future__ import with_statement
import py
from pypy.jit.metainterp.optimize import InvalidLoop
from pypy.jit.metainterp.optimizeopt.virtualstate import VirtualStateInfo, VStructStateInfo, \
     VArrayStateInfo, NotVirtualStateInfo, VirtualState, ShortBoxes, VirtualStateAdder
from pypy.jit.metainterp.optimizeopt.virtualize import VirtualValue, VArrayValue
from pypy.jit.metainterp.optimizeopt.optimizer import OptValue
from pypy.jit.metainterp.history import BoxInt, BoxFloat, BoxPtr, ConstInt, ConstPtr, AbstractValue
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin, BaseTest, \
                                                           equaloplists, FakeDescrWithSnapshot
from pypy.jit.metainterp.optimizeopt.intutils import IntBound
from pypy.jit.metainterp.history import TreeLoop, JitCellToken
from pypy.jit.metainterp.optimizeopt.test.test_optimizeopt import FakeMetaInterpStaticData
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.optimizeopt.optimizer import LEVEL_UNKNOWN, LEVEL_CONSTANT, Optimizer, CVAL_ZERO
import itertools

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

        assert isgeneral(OptValue(ConstInt(7)), OptValue(ConstInt(7)))
        S = lltype.GcStruct('S')
        foo = lltype.malloc(S)
        fooref = lltype.cast_opaque_ptr(llmemory.GCREF, foo)
        assert isgeneral(OptValue(ConstPtr(fooref)),
                         OptValue(ConstPtr(fooref)))

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
    def guards(self, info1, info2, box, expected):
        info1.position = info2.position = 0
        guards = []
        info1.generate_guards(info2, box, self.cpu, guards, {})
        self.compare(guards, expected, [box])

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
    def test_intbounds(self):
        value1 = OptValue(BoxInt())
        value1.intbound.make_ge(IntBound(0, 10))
        value1.intbound.make_le(IntBound(20, 30))
        info1 = NotVirtualStateInfo(value1)
        info2 = NotVirtualStateInfo(OptValue(BoxInt()))
        expected = """
        [i0]
        i1 = int_ge(i0, 0)
        guard_true(i1) []
        i2 = int_le(i0, 30)
        guard_true(i2) []
        """
        self.guards(info1, info2, BoxInt(15), expected)
        py.test.raises(InvalidLoop, self.guards,
                       info1, info2, BoxInt(50), expected)


    def test_known_class(self):
        value1 = OptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value1.make_constant_class(classbox, -1)
        info1 = NotVirtualStateInfo(value1)
        info2 = NotVirtualStateInfo(OptValue(self.nodebox))
        expected = """
        [p0]
        guard_nonnull(p0) []        
        guard_class(p0, ConstClass(node_vtable)) []
        """
        self.guards(info1, info2, self.nodebox, expected)
        py.test.raises(InvalidLoop, self.guards,
                       info1, info2, BoxPtr(), expected)

    def test_known_class_value(self):
        value1 = OptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value1.make_constant_class(classbox, -1)
        box = self.nodebox
        guards = value1.make_guards(box)
        expected = """
        [p0]
        guard_nonnull(p0) []        
        guard_class(p0, ConstClass(node_vtable)) []
        """
        self.compare(guards, expected, [box])

    def test_equal_inputargs(self):
        value = OptValue(self.nodebox)        
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        vstate1 = VirtualState([knownclass_info, knownclass_info])
        assert vstate1.generalization_of(vstate1)

        unknown_info1 = NotVirtualStateInfo(OptValue(self.nodebox))
        vstate2 = VirtualState([unknown_info1, unknown_info1])
        assert vstate2.generalization_of(vstate2)
        assert not vstate1.generalization_of(vstate2)
        assert vstate2.generalization_of(vstate1)

        unknown_info1 = NotVirtualStateInfo(OptValue(self.nodebox))
        unknown_info2 = NotVirtualStateInfo(OptValue(self.nodebox))
        vstate3 = VirtualState([unknown_info1, unknown_info2])
        assert vstate3.generalization_of(vstate2)
        assert vstate3.generalization_of(vstate1)
        assert not vstate2.generalization_of(vstate3)
        assert not vstate1.generalization_of(vstate3)

        expected = """
        [p0]
        guard_nonnull(p0) []        
        guard_class(p0, ConstClass(node_vtable)) []
        """
        guards = []
        vstate1.generate_guards(vstate2, [self.nodebox, self.nodebox], self.cpu, guards)
        self.compare(guards, expected, [self.nodebox])

        with py.test.raises(InvalidLoop):
            guards = []
            vstate1.generate_guards(vstate3, [self.nodebox, self.nodebox],
                                    self.cpu, guards)
        with py.test.raises(InvalidLoop):
            guards = []
            vstate2.generate_guards(vstate3, [self.nodebox, self.nodebox],
                                    self.cpu, guards)
        
    def test_virtuals_with_equal_fields(self):
        info1 = VirtualStateInfo(ConstInt(42), [1, 2])
        value = OptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(classbox, -1)
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
        value = OptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = VirtualStateInfo(ConstInt(42), [1, 2])
        value = OptValue(self.nodebox2)
        classbox = self.cpu.ts.cls_of_box(self.nodebox2)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        info2.fieldstate = [knownclass_info, knownclass_info]
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)

    def test_virtuals_with_nonmatching_descrs(self):
        info1 = VirtualStateInfo(ConstInt(42), [10, 20])
        value = OptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = VirtualStateInfo(ConstInt(42), [1, 2])
        value = OptValue(self.nodebox2)
        classbox = self.cpu.ts.cls_of_box(self.nodebox2)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        info2.fieldstate = [knownclass_info, knownclass_info]
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)
        
    def test_virtuals_with_nonmatching_classes(self):
        info1 = VirtualStateInfo(ConstInt(42), [1, 2])
        value = OptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = VirtualStateInfo(ConstInt(7), [1, 2])
        value = OptValue(self.nodebox2)
        classbox = self.cpu.ts.cls_of_box(self.nodebox2)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        info2.fieldstate = [knownclass_info, knownclass_info]
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)
        
    def test_nonvirtual_is_not_virtual(self):
        info1 = VirtualStateInfo(ConstInt(42), [1, 2])
        value = OptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(classbox, -1)
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
        value = OptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = VArrayStateInfo(42)
        value = OptValue(self.nodebox2)
        classbox = self.cpu.ts.cls_of_box(self.nodebox2)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        info2.fieldstate = [knownclass_info, knownclass_info]
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)

    def test_arrays_of_different_sizes(self):
        info1 = VArrayStateInfo(42)
        value = OptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = VArrayStateInfo(42)
        value = OptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        info2.fieldstate = [knownclass_info]
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)

    def test_arrays_with_nonmatching_types(self):
        info1 = VArrayStateInfo(42)
        value = OptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = VArrayStateInfo(7)
        value = OptValue(self.nodebox2)
        classbox = self.cpu.ts.cls_of_box(self.nodebox2)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        info2.fieldstate = [knownclass_info, knownclass_info]
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)
        
    def test_nonvirtual_is_not_array(self):
        info1 = VArrayStateInfo(42)
        value = OptValue(self.nodebox)
        classbox = self.cpu.ts.cls_of_box(self.nodebox)
        value.make_constant_class(classbox, -1)
        knownclass_info = NotVirtualStateInfo(value)
        info1.fieldstate = [knownclass_info, knownclass_info]
        vstate1 = VirtualState([info1])
        assert vstate1.generalization_of(vstate1)

        info2 = NotVirtualStateInfo(value)
        vstate2 = VirtualState([info2])
        assert vstate2.generalization_of(vstate2)

        assert not vstate2.generalization_of(vstate1)
        assert not vstate1.generalization_of(vstate2)
        

class BaseTestBridges(BaseTest):
    enable_opts = "intbounds:rewrite:virtualize:string:pure:heap:unroll"

    def _do_optimize_bridge(self, bridge, call_pure_results):
        from pypy.jit.metainterp.optimizeopt import optimize_trace
        from pypy.jit.metainterp.optimizeopt.util import args_dict

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
        bridge.resume_at_jump_descr = FakeDescrWithSnapshot()
        optimize_trace(metainterp_sd, bridge, self.enable_opts)

        
    def optimize_bridge(self, loops, bridge, expected, expected_target='Loop', **boxvalues):
        if isinstance(loops, str):
            loops = (loops, )
        loops = [self.parse(loop) for loop in loops]
        bridge = self.parse(bridge)
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
        [p0]
        p1 = same_as(ConstPtr(myptr))
        jump(p1)
        """, """
        [p0]
        p1 = same_as(ConstPtr(myptr2))
        jump(p1)
        """, """
        [p0]
        jump(p0)
        """
        expected = """
        [p0]
        jump()
        """
        self.optimize_bridge(loops, loops[0], expected, 'Loop0')
        self.optimize_bridge(loops, loops[1], expected, 'Loop1')
        expected = """
        [p0]
        jump(p0)
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

    def test_virtual(self):
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

class FakeCPU(object):
    pass
class FakeDescr(object):
    def sort_key(self):
        return id(self)

class FakeGuardedGenerlaizationOptimizer(object):
    unknown_ptr1, unknown_ptr2 = BoxPtr(), BoxPtr()
    unknown_int1, unknown_int2, unknown_int3 = BoxInt(1), BoxInt(2), BoxInt(3)
    const_int0, const_int1, const_int2 = ConstInt(0), ConstInt(1), ConstInt(2)
    node_class = ConstInt(42)
    node1, node2 = BoxPtr(), BoxPtr()
    descr1, descr2, descr3 = FakeDescr(), FakeDescr(), FakeDescr()
    subnode_class = ConstInt(7)
    subnode1 = BoxPtr()
    array1, array2 = BoxPtr(), BoxPtr()
    array_descr = FakeDescr()

    def __init__(self):
        self.values = {}
        self.values[self.node1] = VirtualValue(self.cpu, self.node_class, self.node1)
        self.values[self.node2] = VirtualValue(self.cpu, self.node_class, self.node2)
        self.values[self.subnode1] = VirtualValue(self.cpu, self.subnode_class, self.subnode1)
        self.values[self.array1] = VArrayValue(self.array_descr, OptValue(self.const_int1), 7, self.array_descr)
        self.values[self.array2] = VArrayValue(self.array_descr, OptValue(self.const_int2), 7, self.array_descr)
        for n in dir(self):
            box = getattr(self, n)
            if isinstance(box, AbstractValue) and box not in self.values:
                self.values[box] = OptValue(box)

    def getvalue(self, box):
        return self.values[box]

    def force_at_end_of_preamble(self):
        pass

    def make_equal_to(self, box, value, replace=False):
        self.values[box] = value

    def new_const(self, descr):
        assert isinstance(descr, FakeDescr)
        return CVAL_ZERO
    
    optearlyforce = None
    opaque_pointers = {}
    cpu = FakeCPU()

class CompareUnknown(object):
    def __eq__(self, other):
        return isinstance(other, NotVirtualStateInfo) and other.level == LEVEL_UNKNOWN
Unknown = CompareUnknown()

class Const(object):
    def __init__(self, value):
        assert isinstance(value, int)
        self.value = ConstInt(value)

    def __eq__(self, other):
        return isinstance(other, NotVirtualStateInfo) and other.level == LEVEL_CONSTANT and \
                other.constbox.same_constant(self.value)

class Virtual(object):
    def __init__(self, known_class, fields):
        self.known_class = known_class
        self.fields = fields

    def __eq__(self, other):
        return isinstance(other, VirtualStateInfo) and \
               other.known_class.same_constant(self.known_class) and \
               {k:v for k,v in zip(other.fielddescrs, other.fieldstate)} == self.fields

class TestGuardedGenerlaization:
    def setup_method(self, m):
        self.optimizer = FakeGuardedGenerlaizationOptimizer()

    def teardown_method(self, m):
        del self.optimizer

    def combine(self, inputargs, jumpargs, expected):
        modifier = VirtualStateAdder(self.optimizer)
        vstate1 = modifier.get_virtual_state(inputargs)
        vstate2 = modifier.get_virtual_state(jumpargs)
        if isinstance(expected, type) and issubclass(expected, Exception):
            with raises(expected):
                vstate = vstate1.make_guardable_generalization_of(vstate2, jumpargs, self.optimizer) 
        else:
            vstate = vstate1.make_guardable_generalization_of(vstate2, jumpargs, self.optimizer) 
            assert vstate.state == expected

    def setfield(self, node, descr, box):
        self.optimizer.getvalue(node).setfield(descr, self.optimizer.getvalue(box))
        
    def test_unknown(self):
        o = self.optimizer
        self.combine([o.unknown_ptr1, o.unknown_int1],
                     [o.unknown_ptr2, o.unknown_int2],
                     [Unknown, Unknown])

    def test_matching_consts(self):
        o = self.optimizer
        self.combine([o.unknown_ptr1, o.const_int1],
                     [o.unknown_ptr2, o.const_int1],
                     [Unknown, Const(1)])

    def test_not_matching_consts(self):
        o = self.optimizer
        self.combine([o.unknown_ptr1, o.const_int0],
                     [o.unknown_ptr2, o.const_int1],
                     [Unknown, Unknown])

    def test_virtual_simple1(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr2, o.const_int1)
        self.setfield(o.node2, o.descr2, o.const_int2)
        self.combine([o.node1, o.node2],
                     [o.node1, o.node2],
                     [Virtual(o.node_class, {o.descr2: Const(1)}), 
                      Virtual(o.node_class, {o.descr2: Const(2)})])

    def test_virtual_simple2(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr2, o.const_int1)
        self.setfield(o.node2, o.descr2, o.const_int2)
        self.combine([o.node1], [o.node2], [Virtual(o.node_class, {o.descr2: Unknown})])

    def test_virtual_class_missmatch(self):
        o = self.optimizer
        self.combine([o.node1], [o.subnode1], InvalidLoop)

    def test_boxed_int_zero1(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr1, o.const_int1)
        self.setfield(o.node2, o.descr1, o.const_int0)
        self.combine([o.node1], [o.node1], [Virtual(o.node_class, {o.descr1: Const(1)})])

    def test_boxed_int_zero2(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr1, o.const_int1)
        self.setfield(o.node2, o.descr1, o.const_int0)
        self.combine([o.node2], [o.node2], [Virtual(o.node_class, {})])

    def test_boxed_int_zero3(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr1, o.const_int1)
        self.setfield(o.node2, o.descr1, o.const_int0)
        self.combine([o.node1], [o.node2], [Virtual(o.node_class, {o.descr1: Unknown})])

    def test_boxed_int_zero4(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr1, o.const_int1)
        self.setfield(o.node2, o.descr1, o.const_int0)
        self.combine([o.node2], [o.node1], [Virtual(o.node_class, {o.descr1: Unknown})])

    def test_boxed_int_unassigned_zero1(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr1, o.const_int1)
        self.combine([o.node1], [o.node1], [Virtual(o.node_class, {o.descr1: Const(1)})])

    def test_boxed_int_unassigned_zero2(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr1, o.const_int1)
        self.combine([o.node2], [o.node2], [Virtual(o.node_class, {})])

    def test_boxed_int_unassigned_zero3(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr1, o.const_int1)
        self.combine([o.node1], [o.node2], [Virtual(o.node_class, {o.descr1: Unknown})])

    def test_boxed_int_unassigned_zero4(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr1, o.const_int1)
        self.combine([o.node2], [o.node1], [Virtual(o.node_class, {o.descr1: Unknown})])

    def test_three_boxed_int_zero(self):
        o = self.optimizer
        for consts1 in itertools.permutations([o.const_int0, o.const_int1, o.const_int2]):
            for consts2 in itertools.permutations([o.const_int0, o.const_int1, o.const_int2]):
                self.setfield(o.node1, o.descr1, consts1[0])
                self.setfield(o.node1, o.descr2, consts1[1])
                self.setfield(o.node1, o.descr3, consts1[2])
                self.setfield(o.node2, o.descr1, consts2[0])
                self.setfield(o.node2, o.descr2, consts2[1])
                self.setfield(o.node2, o.descr3, consts2[2])
                flds = {d: Const(c1.value) if c1 is c2 else Unknown 
                        for d, c1, c2 in zip([o.descr1, o.descr2, o.descr3], consts1, consts2)}
                for d in flds.keys():
                    try:
                        if flds[d].value.value == 0:
                            del flds[d]
                    except AttributeError:
                        pass
                self.combine([o.node1], [o.node2], [Virtual(o.node_class, flds)])

    def test_currently_unsupported_case(self):
        o = self.optimizer
        self.combine([o.array1], [o.array2], InvalidLoop)


class TestGenerlaization:
    def setup_method(self, m):
        self.optimizer = FakeGuardedGenerlaizationOptimizer()

    def teardown_method(self, m):
        del self.optimizer

    def is_more_general(self, args1, args2):
        modifier = VirtualStateAdder(self.optimizer)
        vstate1 = modifier.get_virtual_state(args1)
        vstate2 = modifier.get_virtual_state(args2)
        return vstate1.generalization_of(vstate2)
    
    def setfield(self, node, descr, box):
        self.optimizer.getvalue(node).setfield(descr, self.optimizer.getvalue(box))

    def test_int(self):
        o = self.optimizer
        assert self.is_more_general([o.unknown_int1], [o.const_int1])
        assert not self.is_more_general([o.const_int1], [o.unknown_int1])
        assert self.is_more_general([o.unknown_int1], [o.unknown_int2])

    def test_boxed_int_one(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr1, o.unknown_int1)
        self.setfield(o.node2, o.descr1, o.const_int1)
        assert self.is_more_general([o.node1], [o.node2])
        assert not self.is_more_general([o.node2], [o.node1])
        assert self.is_more_general([o.node1], [o.node1])

    def test_boxed_int_zero(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr1, o.unknown_int1)
        self.setfield(o.node2, o.descr1, o.const_int0)
        assert self.is_more_general([o.node1], [o.node2])
        assert not self.is_more_general([o.node2], [o.node1])
        assert self.is_more_general([o.node1], [o.node1])

    def test_two_boxed_int_one(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr1, o.unknown_int1)
        self.setfield(o.node2, o.descr1, o.const_int1)
        self.setfield(o.node1, o.descr2, o.const_int2)
        self.setfield(o.node2, o.descr2, o.const_int2)
        assert self.is_more_general([o.node1], [o.node2])
        assert not self.is_more_general([o.node2], [o.node1])
        assert self.is_more_general([o.node1], [o.node1])

    def test_three_boxed_int_zero(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr1, o.unknown_int1)
        self.setfield(o.node1, o.descr2, o.unknown_int2)
        self.setfield(o.node1, o.descr3, o.unknown_int3)
        
        for consts in itertools.permutations([o.const_int0, o.const_int1, o.const_int2]):
            self.setfield(o.node2, o.descr1, consts[0])
            self.setfield(o.node2, o.descr2, consts[1])
            self.setfield(o.node2, o.descr3, consts[2])
            assert self.is_more_general([o.node1], [o.node2])
            assert not self.is_more_general([o.node2], [o.node1])
            assert self.is_more_general([o.node1], [o.node1])

    def test_three_boxed_int_zero_missmatch(self):
        o = self.optimizer
        self.setfield(o.node1, o.descr1, o.unknown_int1)
        self.setfield(o.node1, o.descr2, o.unknown_int2)
        self.setfield(o.node1, o.descr3, o.unknown_int3)
        
        constmap = {o.const_int0: o.const_int1, 
                    o.const_int1: o.const_int1, 
                    o.const_int2: o.const_int2}
        for consts in itertools.permutations([o.const_int0, o.const_int1, o.const_int2]):
            self.setfield(o.node1, o.descr1, constmap[consts[0]])
            self.setfield(o.node1, o.descr2, constmap[consts[1]])
            self.setfield(o.node1, o.descr3, constmap[consts[2]])
            self.setfield(o.node2, o.descr1, consts[0])
            self.setfield(o.node2, o.descr2, consts[1])
            self.setfield(o.node2, o.descr3, consts[2])
            assert not self.is_more_general([o.node1], [o.node2])
            assert not self.is_more_general([o.node2], [o.node1])
