from pypy.jit.timeshifter.test.test_portal import PortalTest, P_NOVIRTUAL
from pypy.rpython.lltypesystem import lltype

import py

S = lltype.GcStruct('s', ('a', lltype.Signed), ('b', lltype.Signed))
PS = lltype.Ptr(S)

XY = lltype.GcForwardReference()
GETTER = lambda STRUC: lltype.Ptr(lltype.FuncType([lltype.Ptr(STRUC)],
                                                  lltype.Signed))
SETTER = lambda STRUC: lltype.Ptr(lltype.FuncType([lltype.Ptr(STRUC),
                                                  lltype.Signed],
                                                 lltype.Void))

XP = lltype.GcForwardReference()
PGETTER = lltype.Ptr(lltype.FuncType([lltype.Ptr(XP)], PS))
PSETTER = lltype.Ptr(lltype.FuncType([lltype.Ptr(XP), PS],
                                   lltype.Void))

XY_ACCESS = lltype.Struct('xy_access',
                          ('get_x', GETTER(XY)),
                          ('set_x', SETTER(XY)),
                          ('get_y', GETTER(XY)),
                          ('set_y', SETTER(XY)),
                          hints = {'immutable': True},
                          )


XP_ACCESS = lltype.Struct('xp_access',
                          ('get_x', GETTER(XP)),
                          ('set_x', SETTER(XP)),
                          ('get_p', PGETTER),
                          ('set_p', PSETTER),
                          hints = {'immutable': True},
                          )

XY.become(lltype.GcStruct('xy',
                          ('access', lltype.Ptr(XY_ACCESS)),
                          ('x', lltype.Signed),
                          ('y', lltype.Signed),
                          hints = {'virtualizable': True}
              ))

E = lltype.GcStruct('e', ('xy', lltype.Ptr(XY)))

XP.become(lltype.GcStruct('xp',
                          ('access', lltype.Ptr(XP_ACCESS)),
                          ('x', lltype.Signed),
                          ('p', PS),
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

    def test_simple_explicit_construct_no_escape(self):
   
        def f(x, y):
            xy = lltype.malloc(XY)
            xy.access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
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
            return f(x, y)

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns(getfield=0)

    def test_simple_explicit_construct_escape(self):
   
        def f(x, y):
            xy = lltype.malloc(XY)
            xy.access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
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
            return xy

        def main(x, y):
            xy = f(x, y)
            return xy.x+xy.y

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns(getfield=0)

    def test_simple_with_struct_explicit(self):
   
        def f(xp):
            xp_access = xp.access
            if xp_access:
                x = xp_access.get_x(xp)
            else:
                x = xp.x
            xp_access = xp.access
            if xp_access:
                p = xp_access.get_p(xp)
            else:
                p = xp.p
            return x+p.a+p.b

        def main(x, a, b):
            xp = lltype.malloc(XP)
            xp.access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            s = lltype.malloc(S)
            s.a = a
            s.b = b
            xp.p = s
            return f(xp)

        res = self.timeshift_from_portal(main, f, [20, 10, 12],
                                         policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns(getfield=2)    

    def test_simple_with_setting_struct_explicit(self):
   
        def f(xp, s):
            xp_access = xp.access
            if xp_access:
                xp_access.set_p(xp, s)
            else:
                xp.p = s
            if xp_access:
                x = xp_access.get_x(xp)
            else:
                x = xp.x
            xp_access = xp.access
            if xp_access:
                p = xp_access.get_p(xp)
            else:
                p = xp.p
            p.b = p.b*2
            return x+p.a+p.b

        def main(x, a, b):
            xp = lltype.malloc(XP)
            xp.access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            s = lltype.malloc(S)
            s.a = a
            s.b = b
            v = f(xp, s)
            return v+xp.p.b

        res = self.timeshift_from_portal(main, f, [20, 10, 3],
                                         policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns(getfield=3)

    def test_simple_with_setting_new_struct_explicit(self):
   
        def f(xp, a, b):
            s = lltype.malloc(S)
            s.a = a
            s.b = b            
            xp_access = xp.access
            if xp_access:
                xp_access.set_p(xp, s)
            else:
                xp.p = s
            xp_access = xp.access
            if xp_access:
                p = xp_access.get_p(xp)
            else:
                p = xp.p
            p.b = p.b*2
            if xp_access:
                x = xp_access.get_x(xp)
            else:
                x = xp.x
            return x+p.a+p.b

        def main(x, a, b):
            xp = lltype.malloc(XP)
            xp.access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            v = f(xp, a, b)
            return v+xp.p.b

        res = self.timeshift_from_portal(main, f, [20, 10, 3],
                                         policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns(getfield=2, malloc=1)


    def test_simple_constr_with_setting_new_struct_explicit(self):
   
        def f(x, a, b):
            xp = lltype.malloc(XP)
            xp.access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            s = lltype.malloc(S)
            s.a = a
            s.b = b            
            xp_access = xp.access
            if xp_access:
                xp_access.set_p(xp, s)
            else:
                xp.p = s
            xp_access = xp.access
            if xp_access:
                p = xp_access.get_p(xp)
            else:
                p = xp.p
            p.b = p.b*2
            if xp_access:
                x = xp_access.get_x(xp)
            else:
                x = xp.x
            return xp

        def main(x, a, b):
            xp = f(x, a, b)
            return xp.x+xp.p.a+xp.p.b+xp.p.b

        res = self.timeshift_from_portal(main, f, [20, 10, 3],
                                         policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns(getfield=0, malloc=2)

    def test_simple_explicit_read(self):
   
        def f(e):
            xy = e.xy
            xy_access = xy.access
            if xy_access:
                xy_access.set_y(xy, 3)
            else:
                xy.y = 3
            return xy.x*2

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            e = lltype.malloc(E)
            e.xy = xy
            v = f(e)
            return v + e.xy.x+e.xy.y

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_NOVIRTUAL)
        assert res == 63
        self.check_insns(getfield=3)
