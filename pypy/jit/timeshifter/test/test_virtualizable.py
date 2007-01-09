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
                xy_access.set_y(xy, 1)
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

    
