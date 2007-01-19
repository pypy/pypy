from pypy.jit.hintannotator.annotator import HintAnnotatorPolicy
from pypy.jit.timeshifter.test.test_portal import PortalTest, P_NOVIRTUAL
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.timeshifter.rcontainer import VABLEINFOPTR
from pypy.rlib.objectmodel import hint
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
PGETTER = lambda XP: lltype.Ptr(lltype.FuncType([lltype.Ptr(XP)], PS))
PSETTER = lambda XP: lltype.Ptr(lltype.FuncType([lltype.Ptr(XP), PS],
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
                          ('get_p', PGETTER(XP)),
                          ('set_p', PSETTER(XP)),
                          hints = {'immutable': True},
                          )

XY.become(lltype.GcStruct('xy',
                          ('vable_base', llmemory.Address),
                          ('vable_info', VABLEINFOPTR),
                          ('vable_access', lltype.Ptr(XY_ACCESS)),
                          ('x', lltype.Signed),
                          ('y', lltype.Signed),
                          hints = {'virtualizable': True}
              ))

E = lltype.GcStruct('e', ('xy', lltype.Ptr(XY)),
                         ('w',  lltype.Signed))

XP.become(lltype.GcStruct('xp',
                          ('vable_base', llmemory.Address),
                          ('vable_info', VABLEINFOPTR),                     
                          ('vable_access', lltype.Ptr(XP_ACCESS)),
                          ('x', lltype.Signed),
                          ('p', PS),
                          hints = {'virtualizable': True}
              ))

E2 = lltype.GcStruct('e', ('xp', lltype.Ptr(XP)),
                         ('w',  lltype.Signed))

PQ = lltype.GcForwardReference()
PQ_ACCESS = lltype.Struct('pq_access',
                          ('get_p', PGETTER(PQ)),
                          ('set_p', PSETTER(PQ)),
                          ('get_q', PGETTER(PQ)),
                          ('set_q', PSETTER(PQ)),
                          hints = {'immutable': True},
                          )

PQ.become(lltype.GcStruct('pq',
                          ('vable_base', llmemory.Address),
                          ('vable_info', VABLEINFOPTR),                     
                          ('vable_access', lltype.Ptr(PQ_ACCESS)),
                          ('p', PS),
                          ('q', PS),
                          hints = {'virtualizable': True}
              ))

E3 = lltype.GcStruct('e', ('pq', lltype.Ptr(PQ)),
                         ('w',  lltype.Signed))

class TestVirtualizable(PortalTest):

    def test_simple_explicit(self):
   
        def f(xy):
            xy_access = xy.vable_access
            if xy_access:
                x = xy_access.get_x(xy)
            else:
                x = xy.x
            xy_access = xy.vable_access
            if xy_access:
                y = xy_access.get_y(xy)
            else:
                y = xy.y
            return x+y

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
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
            xy_access = xy.vable_access
            if xy_access:
                x = xy_access.get_x(xy)
            else:
                x = xy.x
            xy_access = xy.vable_access
            if xy_access:
                xy_access.set_y(xy, 1)
            else:
                xy.y = 1
            xy_access = xy.vable_access
            if xy_access:
                y = xy_access.get_y(xy)
            else:
                y = xy.y
            return x+y

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
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
            xy_access = xy.vable_access
            if xy_access:
                x = xy_access.get_x(xy)
            else:
                x = xy.x
            xy_access = xy.vable_access
            if xy_access:
                xy_access.set_y(xy, 3)
            else:
                xy.y = 3
            xy_access = xy.vable_access
            if xy_access:
                y = xy_access.get_y(xy)
            else:
                y = xy.y
            return x+y

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
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
            xy_access = xy.vable_access
            if xy_access:
                xy_access.set_y(xy, 3)
            else:
                xy.y = 3
            e.xy = xy
            return 0

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
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
            xy1_access = xy1.vable_access
            if xy1_access:
                xy1_access.set_y(xy1, 3)
            else:
                xy1.y = 3
            xy2_access = xy2.vable_access
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
            xy1.vable_access = lltype.nullptr(XY_ACCESS)
            xy2 = lltype.malloc(XY)
            xy2.vable_access = lltype.nullptr(XY_ACCESS)
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
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            xy_access = xy.vable_access
            if xy_access:
                x = xy_access.get_x(xy)
            else:
                x = xy.x
            xy_access = xy.vable_access
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
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            xy_access = xy.vable_access
            if xy_access:
                x = xy_access.get_x(xy)
            else:
                x = xy.x
            xy_access = xy.vable_access
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
            xp_access = xp.vable_access
            if xp_access:
                x = xp_access.get_x(xp)
            else:
                x = xp.x
            xp_access = xp.vable_access
            if xp_access:
                p = xp_access.get_p(xp)
            else:
                p = xp.p
            return x+p.a+p.b

        def main(x, a, b):
            xp = lltype.malloc(XP)
            xp.vable_access = lltype.nullptr(XP_ACCESS)
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
            xp_access = xp.vable_access
            if xp_access:
                xp_access.set_p(xp, s)
            else:
                xp.p = s
            if xp_access:
                x = xp_access.get_x(xp)
            else:
                x = xp.x
            xp_access = xp.vable_access
            if xp_access:
                p = xp_access.get_p(xp)
            else:
                p = xp.p
            p.b = p.b*2
            return x+p.a+p.b

        def main(x, a, b):
            xp = lltype.malloc(XP)
            xp.vable_access = lltype.nullptr(XP_ACCESS)
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
            xp_access = xp.vable_access
            if xp_access:
                xp_access.set_p(xp, s)
            else:
                xp.p = s
            xp_access = xp.vable_access
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
            xp.vable_access = lltype.nullptr(XP_ACCESS)
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
            xp.vable_access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            s = lltype.malloc(S)
            s.a = a
            s.b = b            
            xp_access = xp.vable_access
            if xp_access:
                xp_access.set_p(xp, s)
            else:
                xp.p = s
            xp_access = xp.vable_access
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
            xy_access = xy.vable_access
            if xy_access:
                xy_access.set_y(xy, 3)
            else:
                xy.y = 3
            return xy.x*2

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            e = lltype.malloc(E)
            e.xy = xy
            v = f(e)
            return v + e.xy.x+e.xy.y

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_NOVIRTUAL)
        assert res == 63
        self.check_insns(getfield=3)

    def test_simple_explicit_escape_through_vstruct(self):
   
        def f(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            e = lltype.malloc(E)
            e.xy = xy
            xy_access = xy.vable_access
            if xy_access:
                y = xy_access.get_y(xy)
            else:
                y = xy.y
            xy_access = xy.vable_access
            newy = 2*y
            if xy_access:
                xy_access.set_y(xy, newy)
            else:
                xy.y = newy
            return e

        def main(x, y):
            e = f(x, y)
            return e.xy.x+e.xy.y

        res = self.timeshift_from_portal(main, f, [20, 11], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns(getfield=0, malloc=2)

    def test_explicit_late_residual_red_call(self):
        def g(e):
            xy = e.xy
            xy_access = xy.vable_access
            if xy_access:
                y = xy_access.get_y(xy)
            else:
                y = xy.y
            e.w = y

        def f(e):
            hint(None, global_merge_point=True)
            xy = e.xy
            xy_access = xy.vable_access
            if xy_access:
                y = xy_access.get_y(xy)
            else:
                y = xy.y
            xy_access = xy.vable_access
            newy = 2*y
            if xy_access:
                xy_access.set_y(xy, newy)
            else:
                xy.y = newy
            g(e)
            return 0
            
        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            e = lltype.malloc(E)
            e.xy = xy
            f(e)
            return e.w


        class StopAtGPolicy(HintAnnotatorPolicy):
            def __init__(self):
                HintAnnotatorPolicy.__init__(self, novirtualcontainer=True)

            def look_inside_graph(self, graph):
                if graph.name == 'g':
                    return False
                return True

        res = self.timeshift_from_portal(main, f, [0, 21],
                                         policy=StopAtGPolicy())
        assert res == 42

    def test_explicit_residual_red_call(self):
        
        def g(e):
            xy = e.xy
            xy_access = xy.vable_access
            if xy_access:
                y = xy_access.get_y(xy)
            else:
                y = xy.y
            e.w = y

        def f(e):
            hint(None, global_merge_point=True)
            xy = e.xy
            xy_access = xy.vable_access
            if xy_access:
                y = xy_access.get_y(xy)
            else:
                y = xy.y
            xy_access = xy.vable_access
            newy = 2*y
            if xy_access:
                xy_access.set_y(xy, newy)
            else:
                xy.y = newy
            g(e)
            return xy.x
            
        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            e = lltype.malloc(E)
            e.xy = xy
            v = f(e)
            return v+e.w


        class StopAtGPolicy(HintAnnotatorPolicy):
            def __init__(self):
                HintAnnotatorPolicy.__init__(self, novirtualcontainer=True)

            def look_inside_graph(self, graph):
                if graph.name == 'g':
                    return False
                return True

        res = self.timeshift_from_portal(main, f, [2, 20],
                                         policy=StopAtGPolicy())
        assert res == 42

    def test_explicit_force_in_residual_red_call(self):

        def g(e):
            xp = e.xp
            xp_access = xp.vable_access
            if xp_access:
                p = xp_access.get_p(xp)
            else:
                p = xp.p
            xp_access = xp.vable_access
            if xp_access:
                x = xp_access.get_x(xp)
            else:
                x = xp.x
                
            e.w = p.a + p.b + x

        def f(e, a, b):
            hint(None, global_merge_point=True)
            xp = e.xp
            s = lltype.malloc(S)
            s.a = a
            s.b = b            
            xp_access = xp.vable_access
            if xp_access:
                xp_access.set_p(xp, s)
            else:
                xp.p = s
            xp_access = xp.vable_access
            
            xp_access = xp.vable_access
            if xp_access:
                x = xp_access.get_x(xp)
            else:
                x = xp.x
            xp_access = xp.vable_access
            newx = 2*x
            if xp_access:
                xp_access.set_x(xp, newx)
            else:
                xp.x = newx
            g(e)            
            return xp.x
            
        def main(a, b, x):
            xp = lltype.malloc(XP)
            xp.vable_access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            xp.p = lltype.nullptr(S)
            e = lltype.malloc(E2)
            e.xp = xp
            f(e, a, b)
            return e.w


        class StopAtGPolicy(HintAnnotatorPolicy):
            def __init__(self):
                HintAnnotatorPolicy.__init__(self, novirtualcontainer=True)

            def look_inside_graph(self, graph):
                if graph.name == 'g':
                    return False
                return True

        res = self.timeshift_from_portal(main, f, [2, 20, 10],
                                         policy=StopAtGPolicy())
        assert res == 42

    def test_explicit_force_multiple_reads_residual_red_call(self):
        def get_p(xp):
            xp_access = xp.vable_access
            if xp_access:
                p = xp_access.get_p(xp)
            else:
                p = xp.p
            return p
        def g(e):
            xp = e.xp
            p1 = get_p(xp)
            p2 = get_p(xp)
            e.w = int(p1 == p2)

        def f(e, a, b):
            hint(None, global_merge_point=True)
            xp = e.xp
            s = lltype.malloc(S)
            s.a = a
            s.b = b            
            xp_access = xp.vable_access
            if xp_access:
                xp_access.set_p(xp, s)
            else:
                xp.p = s
            xp_access = xp.vable_access
            
            xp_access = xp.vable_access
            if xp_access:
                x = xp_access.get_x(xp)
            else:
                x = xp.x
            xp_access = xp.vable_access
            newx = 2*x
            if xp_access:
                xp_access.set_x(xp, newx)
            else:
                xp.x = newx
            g(e)            
            return xp.x
            
        def main(a, b, x):
            xp = lltype.malloc(XP)
            xp.vable_access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            xp.p = lltype.nullptr(S)
            e = lltype.malloc(E2)
            e.xp = xp
            f(e, a, b)
            return e.w


        class StopAtGPolicy(HintAnnotatorPolicy):
            def __init__(self):
                HintAnnotatorPolicy.__init__(self, novirtualcontainer=True)

            def look_inside_graph(self, graph):
                if graph.name == 'g':
                    return False
                return True

        res = self.timeshift_from_portal(main, f, [2, 20, 10],
                                         policy=StopAtGPolicy())
        assert res == 1


    def test_explicit_force_unaliased_residual_red_call(self):
        def get_p(pq):
            pq_access = pq.vable_access
            if pq_access:
                p = pq_access.get_p(pq)
            else:
                p = pq.p
            return p
        def get_q(pq):
            pq_access = pq.vable_access
            if pq_access:
                q = pq_access.get_q(pq)
            else:
                q = pq.q
            return q

        def g(e):
            pq = e.pq
            p = get_p(pq)
            q = get_q(pq)
            e.w = int(p != q)

        def f(e, a, b):
            hint(None, global_merge_point=True)
            pq = e.pq
            s = lltype.malloc(S)
            s.a = a
            s.b = b            
            pq_access = pq.vable_access
            if pq_access:
                pq_access.set_p(pq, s)
            else:
                pq.p = s
            s = lltype.malloc(S)
            s.a = a
            s.b = b            
            pq_access = pq.vable_access
            if pq_access:
                pq_access.set_q(pq, s)
            else:
                pq.q = s
            
            g(e)            
            return pq.p.a
            
        
        def main(a, b, x):
            pq = lltype.malloc(PQ)
            pq.vable_access = lltype.nullptr(PQ_ACCESS)
            pq.p = lltype.nullptr(S)
            pq.q = pq.p
            e = lltype.malloc(E3)
            e.pq = pq
            f(e, a, b)
            return e.w


        class StopAtGPolicy(HintAnnotatorPolicy):
            def __init__(self):
                HintAnnotatorPolicy.__init__(self, novirtualcontainer=True)

            def look_inside_graph(self, graph):
                if graph.name == 'g':
                    return False
                return True

        res = self.timeshift_from_portal(main, f, [2, 20, 10],
                                         policy=StopAtGPolicy())
        assert res == 1

    def test_explicit_force_aliased_residual_red_call(self):
        def get_p(pq):
            pq_access = pq.vable_access
            if pq_access:
                p = pq_access.get_p(pq)
            else:
                p = pq.p
            return p
        def get_q(pq):
            pq_access = pq.vable_access
            if pq_access:
                q = pq_access.get_q(pq)
            else:
                q = pq.q
            return q

        def g(e):
            pq = e.pq
            p = get_p(pq)
            q = get_q(pq)
            e.w = int(p == q)

        def f(e, a, b):
            hint(None, global_merge_point=True)            
            pq = e.pq
            s = lltype.malloc(S)
            s.a = a
            s.b = b            
            pq_access = pq.vable_access
            if pq_access:
                pq_access.set_p(pq, s)
            else:
                pq.p = s
            pq_access = pq.vable_access
            if pq_access:
                pq_access.set_q(pq, s)
            else:
                pq.q = s
            
            g(e)            
            return pq.p.a
            
        
        def main(a, b, x):
            pq = lltype.malloc(PQ)
            pq.vable_access = lltype.nullptr(PQ_ACCESS)
            pq.p = lltype.nullptr(S)
            pq.q = pq.p
            e = lltype.malloc(E3)
            e.pq = pq
            f(e, a, b)
            return e.w


        class StopAtGPolicy(HintAnnotatorPolicy):
            def __init__(self):
                HintAnnotatorPolicy.__init__(self, novirtualcontainer=True)

            def look_inside_graph(self, graph):
                if graph.name == 'g':
                    return False
                return True

        res = self.timeshift_from_portal(main, f, [2, 20, 10],
                                         policy=StopAtGPolicy())
        assert res == 1

    def test_explicit_force_in_residual_red_call_with_more_use(self):
        def g(e):
            xp = e.xp
            xp_access = xp.vable_access
            if xp_access:
                p = xp_access.get_p(xp)
            else:
                p = xp.p
            xp_access = xp.vable_access
            if xp_access:
                x = xp_access.get_x(xp)
            else:
                x = xp.x                
            e.w = p.a + p.b + x
            p.b, p.a = p.a, p.b

        def f(e, a, b):
            hint(None, global_merge_point=True)
            xp = e.xp
            s = lltype.malloc(S)
            s.a = a
            s.b = b            
            xp_access = xp.vable_access
            if xp_access:
                xp_access.set_p(xp, s)
            else:
                xp.p = s
            xp_access = xp.vable_access
            
            xp_access = xp.vable_access
            if xp_access:
                x = xp_access.get_x(xp)
            else:
                x = xp.x
            xp_access = xp.vable_access
            newx = 2*x
            if xp_access:
                xp_access.set_x(xp, newx)
            else:
                xp.x = newx
            g(e)
            s.a = s.a*7
            s.b = s.b*5
            return xp.x
            
        def main(a, b, x):
            xp = lltype.malloc(XP)
            xp.vable_access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            xp.p = lltype.nullptr(S)
            e = lltype.malloc(E2)
            e.xp = xp
            f(e, a, b)
            return e.w + xp.p.a + xp.p.b


        class StopAtGPolicy(HintAnnotatorPolicy):
            def __init__(self):
                HintAnnotatorPolicy.__init__(self, novirtualcontainer=True)

            def look_inside_graph(self, graph):
                if graph.name == 'g':
                    return False
                return True

        res = self.timeshift_from_portal(main, f, [2, 20, 10],
                                         policy=StopAtGPolicy())
        assert res == 42 + 140 + 10
