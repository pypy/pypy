import py
from pypy.jit.metainterp.optimizeutil import InvalidLoop
from pypy.jit.metainterp.optimizeopt.virtualstate import VirtualStateInfo, VStructStateInfo, \
     VArrayStateInfo, NotVirtualStateInfo
from pypy.jit.metainterp.optimizeopt.optimizer import OptValue
from pypy.jit.metainterp.history import BoxInt, BoxFloat, BoxPtr, ConstInt, ConstPtr
from pypy.rpython.lltypesystem import lltype
from pypy.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin, BaseTest, equaloplists
from pypy.jit.metainterp.optimizeopt.intutils import IntBound
from pypy.jit.metainterp.history import TreeLoop, LoopToken
from pypy.jit.metainterp.optimizeopt.test.test_optimizeopt import FakeDescr, FakeMetaInterpStaticData
from pypy.jit.metainterp.optimize import RetraceLoop

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
    def guards(self, info1, info2, box, expected):
        info1.position = info2.position = 0
        guards = []
        info1.generate_guards(info2, box, self.cpu, guards, {})
        loop = self.parse(expected)
        assert equaloplists(guards, loop.operations, False,
                            {loop.inputargs[0]: box})        
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
        loop = self.parse(expected)
        assert equaloplists(guards, loop.operations, False,
                            {loop.inputargs[0]: box})        

class BaseTestBridges(BaseTest):
    enable_opts = "intbounds:rewrite:virtualize:string:heap:unroll"

    def _do_optimize_bridge(self, bridge, call_pure_results):
        from pypy.jit.metainterp.optimizeopt import optimize_bridge_1, build_opt_chain
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
        d = {}
        for name in self.enable_opts.split(":"):
            d[name] = None
        optimize_bridge_1(metainterp_sd, bridge,  d)
        
    def optimize_bridge(self, loops, bridge, expected, expected_target='Loop', **boxvalues):
        if isinstance(loops, str):
            loops = (loops, )
        loops = [self.parse(loop) for loop in loops]
        bridge = self.parse(bridge)
        for loop in loops:
            loop.preamble = TreeLoop('preamble')
            loop.preamble.inputargs = loop.inputargs
            loop.preamble.token = LoopToken()
            loop.preamble.start_resumedescr = FakeDescr()        
            self._do_optimize_loop(loop, None)
        preamble = loops[0].preamble
        for loop in loops[1:]:
            preamble.token.short_preamble.extend(loop.preamble.token.short_preamble)

        boxes = {}
        for b in bridge.inputargs + [op.result for op in bridge.operations]:
            boxes[str(b)] = b
        for b, v in boxvalues.items():
            boxes[b].value = v
        bridge.operations[-1].setdescr(preamble.token)
        try:
            self._do_optimize_bridge(bridge, None)
        except RetraceLoop:
            assert expected == 'RETRACE'
            return

        print '\n'.join([str(o) for o in bridge.operations])
        expected = self.parse(expected)
        self.assert_equal(bridge, expected)

        if expected_target == 'Preamble':
            assert bridge.operations[-1].getdescr() is preamble.token
        elif expected_target == 'Loop':
            assert len(loops) == 1
            assert bridge.operations[-1].getdescr() is loops[0].token
        elif expected_target.startswith('Loop'):
            n = int(expected_target[4:])
            assert bridge.operations[-1].getdescr() is loops[n].token
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

class TestLLtypeGuards(BaseTestGenerateGuards, LLtypeMixin):
    pass

class TestLLtypeBridges(BaseTestBridges, LLtypeMixin):
    pass

