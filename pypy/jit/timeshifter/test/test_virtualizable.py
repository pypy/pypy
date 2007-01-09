from pypy.jit.timeshifter.test.test_portal import PortalTest, P_NOVIRTUAL
from pypy.rpython.lltypesystem import lltype

import py

XY = lltype.GcForwardReference()
GETTER = lltype.Ptr(lltype.FuncType([lltype.Ptr(XY)], lltype.Signed))
SETTER = lltype.Ptr(lltype.FuncType([lltype.Ptr(XY), lltype.Signed],
                                    lltype.Void))
XY_ACCESS = lltype.Struct('xy',
                          ('get_x', GETTER),
                          ('set_x', SETTER),
                          ('get_y', GETTER),
                          ('set_y', SETTER),
                          hints = {'immutable': True},
                          )

XY.become(lltype.GcStruct('xy',
                          ('access', lltype.Ptr(XY_ACCESS)),
                          ('x', lltype.Signed),
                          ('y', lltype.Signed),
                          hints = {'virtualizable': True}
              ))
     
class TestVirtualizable(PortalTest):

    def test_simple_explicit(self):
   
        def f(xy):
            xy_access = xy.access
            if xy_access:
                x = xy_access.get_x(xy)
            else:
                x = xy.x
            xy_access = xy.access
            if xy_access:
                y = xy_access.get_y(xy)
            else:
                y = xy.y
            return x+y

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            return f(xy)

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns(getfield=0)
        residual_graph = self.get_residual_graph()
        assert len(residual_graph.startblock.inputargs) == 3
        assert ([v.concretetype for v in residual_graph.startblock.inputargs] ==
                [lltype.Ptr(XY), lltype.Signed, lltype.Signed])

    def test_simple_explicit_set(self):
   
        def f(xy):
            xy_access = xy.access
            if xy_access:
                x = xy_access.get_x(xy)
            else:
                x = xy.x
            xy_access = xy.access
            if xy_access:
                xy_access.set_y(xy, 1)
            else:
                xy.y = 1
            xy_access = xy.access
            if xy_access:
                y = xy_access.get_y(xy)
            else:
                y = xy.y
            return x+y

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            return f(xy)

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_NOVIRTUAL)
        assert res == 21
        self.check_insns(getfield=0)
        residual_graph = self.get_residual_graph()
        assert len(residual_graph.startblock.inputargs) == 3
        assert ([v.concretetype for v in residual_graph.startblock.inputargs] ==
                [lltype.Ptr(XY), lltype.Signed, lltype.Signed])

    def test_explicit_set_effect(self):
   
        def f(xy):
            xy_access = xy.access
            if xy_access:
                x = xy_access.get_x(xy)
            else:
                x = xy.x
            xy_access = xy.access
            if xy_access:
                xy_access.set_y(xy, 3)
            else:
                xy.y = 3
            xy_access = xy.access
            if xy_access:
                y = xy_access.get_y(xy)
            else:
                y = xy.y
            return x+y

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            v = f(xy)
            return v + xy.y

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_NOVIRTUAL)
        assert res == 26
        self.check_insns(getfield=0)
        residual_graph = self.get_residual_graph()
        assert len(residual_graph.startblock.inputargs) == 3
        assert ([v.concretetype for v in residual_graph.startblock.inputargs] ==
                [lltype.Ptr(XY), lltype.Signed, lltype.Signed])

    def test_simple_explicit_escape(self):
        E = lltype.GcStruct('e', ('xy', lltype.Ptr(XY)))
   
        def f(e, xy):
            xy_access = xy.access
            if xy_access:
                xy_access.set_y(xy, 3)
            else:
                xy.y = 3
            e.xy = xy
            return 0

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            e = lltype.malloc(E)
            f(e, xy)
            return e.xy.x+e.xy.y

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_NOVIRTUAL)
        assert res == 23
        self.check_insns(getfield=0)
        residual_graph = self.get_residual_graph()
        assert len(residual_graph.startblock.inputargs) == 4
        assert ([v.concretetype for v in residual_graph.startblock.inputargs] ==
                [lltype.Ptr(E), lltype.Ptr(XY), lltype.Signed, lltype.Signed])

    def test_simple_explicit_return_it(self):
        def f(which, xy1, xy2):
            xy1_access = xy1.access
            if xy1_access:
                xy1_access.set_y(xy1, 3)
            else:
                xy1.y = 3
            xy2_access = xy2.access
            if xy2_access:
                xy2_access.set_y(xy2, 7)
            else:
                xy2.y = 7
            if which == 1:
                return xy1
            else:
                return xy2

        def main(which, x, y):
            xy1 = lltype.malloc(XY)
            xy1.access = lltype.nullptr(XY_ACCESS)
            xy2 = lltype.malloc(XY)
            xy2.access = lltype.nullptr(XY_ACCESS)
            xy1.x = x
            xy1.y = y
            xy2.x = y
            xy2.y = x
            xy = f(which, xy1, xy2)
            assert xy is xy1 or xy is xy2
            return xy.x+xy.y

        res = self.timeshift_from_portal(main, f, [1, 20, 22],
                                         policy=P_NOVIRTUAL)
        assert res == 23
        self.check_insns(getfield=0)

