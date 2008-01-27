from pypy.jit.timeshifter.test.test_portal import PortalTest, P_OOPSPEC
from pypy.jit.timeshifter.test.test_timeshift import StopAtXPolicy
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rvirtualizable import VABLERTIPTR
from pypy.rlib.jit import hint
import py

S = lltype.GcStruct('s', ('a', lltype.Signed), ('b', lltype.Signed))
PS = lltype.Ptr(S)

XY = lltype.GcForwardReference()
GETTER = lambda STRUC: lltype.Ptr(lltype.FuncType([lltype.Ptr(STRUC)],
                                                  lltype.Signed))
SETTER = lambda STRUC: lltype.Ptr(lltype.FuncType([lltype.Ptr(STRUC),
                                                  lltype.Signed],
                                                 lltype.Void))

def getset(name):
    def get(obj):
        access = obj.vable_access
        if access:
            return getattr(access, 'get_'+name)(obj)
        else:
            return getattr(obj, name)
    get.oopspec = 'vable.get_%s(obj)' % name
    def set(obj, value):
        access = obj.vable_access
        if access:
            return getattr(access, 'set_'+name)(obj, value)
        else:
            return setattr(obj, name, value)
    set.oopspec = 'vable.set_%s(obj, value)' % name
    return get, set

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
                          adtmeths = {'redirected_fields': ('x', 'y')}
                          )


XP_ACCESS = lltype.Struct('xp_access',
                          ('get_x', GETTER(XP)),
                          ('set_x', SETTER(XP)),
                          ('get_p', PGETTER(XP)),
                          ('set_p', PSETTER(XP)),
                          hints = {'immutable': True},
                          adtmeths = {'redirected_fields': ('x', 'p')}
                          )

XY.become(lltype.GcStruct('xy',
                          ('vable_base', llmemory.Address),
                          ('vable_rti', VABLERTIPTR),
                          ('vable_access', lltype.Ptr(XY_ACCESS)),
                          ('x', lltype.Signed),
                          ('y', lltype.Signed),
                          hints = {'virtualizable': True},
                          adtmeths = {'ACCESS': XY_ACCESS},
              ))

E = lltype.GcStruct('e', ('xy', lltype.Ptr(XY)),
                         ('w',  lltype.Signed))
xy_get_x, xy_set_x = getset('x')
xy_get_y, xy_set_y = getset('y')


XP.become(lltype.GcStruct('xp',
                          ('vable_base', llmemory.Address),
                          ('vable_rti', VABLERTIPTR),                     
                          ('vable_access', lltype.Ptr(XP_ACCESS)),
                          ('x', lltype.Signed),
                          ('p', PS),
                          hints = {'virtualizable': True},
                          adtmeths = {'ACCESS': XP_ACCESS},
              ))
xp_get_x, xp_set_x = getset('x')
xp_get_p, xp_set_p = getset('p')

E2 = lltype.GcStruct('e', ('xp', lltype.Ptr(XP)),
                         ('w',  lltype.Signed))

PQ = lltype.GcForwardReference()
PQ_ACCESS = lltype.Struct('pq_access',
                          ('get_p', PGETTER(PQ)),
                          ('set_p', PSETTER(PQ)),
                          ('get_q', PGETTER(PQ)),
                          ('set_q', PSETTER(PQ)),
                          hints = {'immutable': True},
                          adtmeths = {'redirected_fields': ('p', 'q')}
                          )

PQ.become(lltype.GcStruct('pq',
                          ('vable_base', llmemory.Address),
                          ('vable_rti', VABLERTIPTR),                     
                          ('vable_access', lltype.Ptr(PQ_ACCESS)),
                          ('p', PS),
                          ('q', PS),
                          hints = {'virtualizable': True},
                          adtmeths = {'ACCESS': PQ_ACCESS},
              ))
pq_get_p, pq_set_p = getset('p')
pq_get_q, pq_set_q = getset('q')

E3 = lltype.GcStruct('e', ('pq', lltype.Ptr(PQ)),
                         ('w',  lltype.Signed))



class TestVirtualizableExplicit(PortalTest):

    def test_simple(self):
   
        def f(xy):
            x = xy_get_x(xy)
            y = xy_get_y(xy)
            return x+y

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            return f(xy)

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_OOPSPEC)
        assert res == 42
        self.check_insns(getfield=0)
        if self.on_llgraph:
            residual_graph = self.get_residual_graph()
            inputargs = residual_graph.startblock.inputargs
            assert len(inputargs) == 3
            assert ([v.concretetype for v in inputargs] ==
                    [lltype.Ptr(XY), lltype.Signed, lltype.Signed])

    def test_simple_set(self):
   
        def f(xy):
            x = xy_get_x(xy)
            xy_set_y(xy, 1)
            y = xy_get_y(xy)
            return x+y

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            return f(xy)

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_OOPSPEC)
        assert res == 21
        self.check_insns(getfield=0)
        if self.on_llgraph:
            residual_graph = self.get_residual_graph()
            inputargs = residual_graph.startblock.inputargs
            assert len(inputargs) == 3
            assert ([v.concretetype for v in inputargs] ==
                    [lltype.Ptr(XY), lltype.Signed, lltype.Signed])

    def test_set_effect(self):

        def f(xy):
           x = xy_get_x(xy)
           xy_set_y(xy, 3)
           y = xy_get_y(xy)
           return x+y

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            v = f(xy)
            return v + xy.y

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_OOPSPEC)
        assert res == 26
        self.check_insns(getfield=0)
        if self.on_llgraph:
            residual_graph = self.get_residual_graph()
            inputargs = residual_graph.startblock.inputargs
            assert len(inputargs) == 3
            assert ([v.concretetype for v in inputargs] ==
                    [lltype.Ptr(XY), lltype.Signed, lltype.Signed])

    def test_simple_escape(self):
   
        def f(e, xy):
            xy_set_y(xy, 3)
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

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_OOPSPEC)
        assert res == 23
        self.check_insns(getfield=0)
        if self.on_llgraph:
            residual_graph = self.get_residual_graph()
            inputargs = residual_graph.startblock.inputargs
            assert len(inputargs) == 4
            assert ([v.concretetype for v in inputargs] ==
                [lltype.Ptr(E), lltype.Ptr(XY), lltype.Signed, lltype.Signed])

    def test_simple_return_it(self):
        def f(which, xy1, xy2):
            xy_set_y(xy1, 3)
            xy_set_y(xy2, 7)
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
                                         policy=P_OOPSPEC)
        assert res == 23
        self.check_insns(getfield=0)

    def test_simple_construct_no_escape(self):
   
        def f(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            x = xy_get_x(xy)
            y = xy_get_y(xy)
            return x+y

        def main(x, y):
            return f(x, y)

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_OOPSPEC)
        assert res == 42
        self.check_insns({'int_add': 1})

    def test_simple_construct_escape(self):
   
        def f(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            x = xy_get_x(xy)
            y = xy_get_y(xy)            
            return xy

        def main(x, y):
            xy = f(x, y)
            return xy_get_x(xy)+xy_get_y(xy)

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_OOPSPEC)
        assert res == 42
        self.check_insns(getfield=0)

    def test_simple_with_struct(self):
   
        def f(xp):
            x = xp_get_x(xp)
            p = xp_get_p(xp)
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
                                         policy=P_OOPSPEC)
        assert res == 42
        self.check_insns(getfield=2)    

    def test_simple_with_setting_struct(self):
   
        def f(xp, s):
            xp_set_p(xp, s)
            x = xp_get_x(xp)
            p = xp_get_p(xp)
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
                                         policy=P_OOPSPEC)
        assert res == 42
        self.check_insns(getfield=3)

    def test_simple_with_setting_new_struct(self):
   
        def f(xp, a, b):
            s = lltype.malloc(S)
            s.a = a
            s.b = b
            xp_set_p(xp, s)            
            p = xp_get_p(xp)
            p.b = p.b*2
            x = xp_get_x(xp)
            return x+p.a+p.b

        def main(x, a, b):
            xp = lltype.malloc(XP)
            xp.vable_access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            v = f(xp, a, b)
            return v+xp.p.b

        res = self.timeshift_from_portal(main, f, [20, 10, 3],
                                         policy=P_OOPSPEC)
        assert res == 42
        self.check_insns(getfield=0, malloc=1)


    def test_simple_constr_with_setting_new_struct(self):
   
        def f(x, a, b):
            xp = lltype.malloc(XP)
            xp.vable_access = lltype.nullptr(XP_ACCESS)
            xp.x = x
            s = lltype.malloc(S)
            s.a = a
            s.b = b            
            xp_set_p(xp, s)            
            p = xp_get_p(xp)
            p.b = p.b*2
            x = xp_get_x(xp)
            return xp

        def main(x, a, b):
            xp = f(x, a, b)
            return xp.x+xp.p.a+xp.p.b+xp.p.b

        res = self.timeshift_from_portal(main, f, [20, 10, 3],
                                         policy=P_OOPSPEC)
        assert res == 42
        self.check_insns(getfield=0, malloc=2)

    def test_simple_read(self):
   
        def f(e):
            xy = e.xy
            xy_set_y(xy, 3)
            return xy_get_x(xy)*2

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            e = lltype.malloc(E)
            e.xy = xy
            v = f(e)
            return v + e.xy.x+e.xy.y

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_OOPSPEC)
        assert res == 63
        self.check_insns(getfield=3)

    def test_simple_escape_through_vstruct(self):
   
        def f(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            e = lltype.malloc(E)
            e.xy = xy
            y = xy_get_y(xy)
            newy = 2*y
            xy_set_y(xy, newy)
            return e

        def main(x, y):
            e = f(x, y)
            return e.xy.x+e.xy.y

        res = self.timeshift_from_portal(main, f, [20, 11], policy=P_OOPSPEC)
        assert res == 42
        self.check_insns(getfield=0, malloc=2)

    def test_residual_doing_nothing(self):
        def g(xy):
            pass

        def f(xy):
            hint(None, global_merge_point=True)
            g(xy)
            return xy.x + 1
            
        def main(x, y):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            v = f(xy)
            return v

        res = self.timeshift_from_portal(main, f, [2, 20],
                                         policy=StopAtXPolicy(g))
        assert res == 3

    def test_late_residual_red_call(self):
        def g(e):
            xy = e.xy
            y = xy_get_y(xy)
            e.w = y

        def f(e, z):
            hint(None, global_merge_point=True)
            xy = e.xy
            y = xy_get_y(xy)
            newy = 2*y
            xy_set_y(xy, newy)
            if y:
                dummy = z*2
            else:
                dummy = z*3
            g(e)
            return dummy
            
        def main(x, y, z):
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            e = lltype.malloc(E)
            e.xy = xy
            f(e, z)
            return e.w

        res = self.timeshift_from_portal(main, f, [0, 21, 11],
                                         policy=StopAtXPolicy(g))
        assert res == 42

    def test_residual_red_call(self):
        def g(e):
            xy = e.xy
            y = xy_get_y(xy)
            e.w = y        

        def f(e):
            hint(None, global_merge_point=True)
            xy = e.xy
            y = xy_get_y(xy)
            newy = 2*y
            xy_set_y(xy, newy)
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

        res = self.timeshift_from_portal(main, f, [2, 20],
                                         policy=StopAtXPolicy(g))
        assert res == 42

    def test_force_in_residual_red_call(self):

        def g(e):
            xp = e.xp
            p = xp_get_p(xp)
            x = xp_get_x(xp)
                
            e.w = p.a + p.b + x

        def f(e, a, b):
            hint(None, global_merge_point=True)
            xp = e.xp
            s = lltype.malloc(S)
            s.a = a
            s.b = b

            xp_set_p(xp, s)

            x = xp_get_x(xp)
            newx = 2*x
            xp_set_x(xp, newx)
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

        res = self.timeshift_from_portal(main, f, [2, 20, 10],
                                         policy=StopAtXPolicy(g))
        assert res == 42

    def test_force_multiple_reads_residual_red_call(self):
        def g(e):
            xp = e.xp
            p1 = xp_get_p(xp)
            p2 = xp_get_p(xp)
            e.w = int(p1 == p2)

        def f(e, a, b):
            hint(None, global_merge_point=True)
            xp = e.xp
            s = lltype.malloc(S)
            s.a = a
            s.b = b            
            xp_set_p(xp, s)
            
            x = xp_get_x(xp)
            newx = 2*x
            xp_set_x(xp, newx)
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

        res = self.timeshift_from_portal(main, f, [2, 20, 10],
                                         policy=StopAtXPolicy(g))
        assert res == 1


    def test_force_unaliased_residual_red_call(self):

        def g(e):
            pq = e.pq
            p = pq_get_p(pq)
            q = pq_get_q(pq)
            e.w = int(p != q)

        def f(e, a, b):
            hint(None, global_merge_point=True)
            pq = e.pq
            s = lltype.malloc(S)
            s.a = a
            s.b = b
            pq_set_p(pq, s)
            s = lltype.malloc(S)
            s.a = a
            s.b = b            
            pq_set_q(pq, s)
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

        res = self.timeshift_from_portal(main, f, [2, 20, 10],
                                         policy=StopAtXPolicy(g))
        assert res == 1

    def test_force_aliased_residual_red_call(self):

        def g(e):
            pq = e.pq
            p = pq_get_p(pq)
            q = pq_get_q(pq)
            e.w = int(p == q)

        def f(e, a, b):
            hint(None, global_merge_point=True)            
            pq = e.pq
            s = lltype.malloc(S)
            s.a = a
            s.b = b
            pq_set_p(pq, s)
            pq_set_q(pq, s)
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

        res = self.timeshift_from_portal(main, f, [2, 20, 10],
                                         policy=StopAtXPolicy(g))
        assert res == 1

    def test_force_in_residual_red_call_with_more_use(self):
        def g(e):
            xp = e.xp
            p = xp_get_p(xp)
            x = xp_get_x(xp)
            e.w = p.a + p.b + x
            p.b, p.a = p.a, p.b

        def f(e, a, b):
            hint(None, global_merge_point=True)
            xp = e.xp
            s = lltype.malloc(S)
            s.a = a
            s.b = b
            xp_set_p(xp, s)

            x = xp_get_x(xp)
            newx = 2*x
            xp_set_x(xp, newx)
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

        res = self.timeshift_from_portal(main, f, [2, 20, 10],
                                         policy=StopAtXPolicy(g))
        assert res == 42 + 140 + 10

    def test_virtualizable_escaped_as_argument_to_red_call(self):
        def g(xy):
            x = xy_get_x(xy)
            y = xy_get_y(xy)
            return y*2 + x

        def f(x, y):
            hint(None, global_merge_point=True)
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            r = g(xy)
            x = xy_get_x(xy)
            y = xy_get_y(xy)
            return r
        
        def main(x, y):
            return f(x,y)
        
        res = self.timeshift_from_portal(main, f, [20, 11],
                                         policy=StopAtXPolicy(g))

        assert res == 42

    def test_setting_in_residual_call(self):

        def g(xy):
            x = xy_get_x(xy)
            y = xy_get_y(xy)
            xy_set_x(xy, y)
            xy_set_y(xy, x)

        def f(x):
            hint(None, global_merge_point=True)
            xy = lltype.malloc(XY)
            xy.vable_access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = 11
            g(xy)
            x = xy_get_x(xy)
            y = xy_get_y(xy)
            return x*2 + y

        
        def main(x):
            return f(x)
        
        res = self.timeshift_from_portal(main, f, [20],
                                         policy=StopAtXPolicy(g))

        assert res == 42
        
class TestVirtualizableImplicit(PortalTest):

    def test_simple(self):

        class XY(object):
            _virtualizable_ = True
            
            def __init__(self, x, y):
                self.x = x
                self.y = y
   
        def f(xy):
            return xy.x+xy.y

        def main(x, y):
            xy = XY(x, y)
            return f(xy)

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_OOPSPEC)
        assert res == 42
        self.check_insns(getfield=0)

    def test_simple__class__(self):
        class V(object):
            _virtualizable_ = True
            def __init__(self, a):
                self.a = a

        class V1(V):
            def __init__(self, b):
                V.__init__(self, 1)
                self.b = b

        class V2(V):
            def __init__(self):
                V.__init__(self, 2)

        def f(v):
            hint(None, global_merge_point=True)
            #V1(0).b
            return v.__class__

        def main(x, y):
            if x:
                v = V1(42)
            else:
                v = V2()
            if y:
                c = None
            else:
                c = f(v)
            V2()
            return c is not None

        res = self.timeshift_from_portal(main, f, [0, 1], policy=P_OOPSPEC)
        assert not res
        res = self.timeshift_from_portal(main, f, [1, 0], policy=P_OOPSPEC)
        assert res

    def test_simple_inheritance(self):

        class X(object):
            _virtualizable_ = True
            
            def __init__(self, x):
                self.x = x

        class XY(X):

            def __init__(self, x, y):
                X.__init__(self, x)
                self.y = y
   
        def f(xy):
            return xy.x+xy.y

        def main(x, y):
            X(0)
            xy = XY(x, y)
            return f(xy)

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_OOPSPEC)
        assert res == 42
        self.check_insns(getfield=0)

    def test_simple_interpreter_with_frame(self):
        class Log:
            acc = 0
        log = Log()
        class Frame(object):
            _virtualizable_ = True
            def __init__(self, code, acc, y):
                self.code = code
                self.pc = 0
                self.acc = acc
                self.y = y

            def run(self):
                self.plus_minus(self.code)
                return self.acc

            def plus_minus(self, s):
                n = len(s)
                pc = 0
                while pc < n:
                    hint(None, global_merge_point=True)
                    self.pc = pc
                    op = s[pc]
                    op = hint(op, concrete=True)
                    if op == '+':
                        self.acc += self.y
                    elif op == '-':
                        self.acc -= self.y
                    elif op == 'd':
                        self.debug()
                    pc += 1
                return 0

            def debug(self):
                log.acc = self.acc
            
        def main(x, y):
            code = '+d+-+'
            f = Frame(code, x, y)
            return f.run() * 10 + log.acc

        res = self.timeshift_from_portal(main, Frame.plus_minus.im_func,
                            [0, 2],
                            policy=StopAtXPolicy(Frame.debug.im_func))
        assert res == 42
        if self.on_llgraph:
            calls = self.count_direct_calls()
            call_count = sum([count for graph, count in calls.iteritems()
                              if not graph.name.startswith('rpyexc_')])
            assert call_count == 2


    def test_setting_pointer_in_residual_call(self):
        class S(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y
            
        class V(object):
            _virtualizable_ = True
            def __init__(self, s):
                self.s = s

        def g(v):
            assert v.s is None
            s = S(1, 7)
            v.s = s
            
        def f(v):
            hint(None, global_merge_point=True)
            g(v)
            s = v.s
            return s.x + s.y

        def main():
            S(5, 5)
            v = V(None)
            return f(v)

        res = self.timeshift_from_portal(main, f, [], policy=StopAtXPolicy(g))
        assert res == 8

        
    def test_aliased_box(self):
        class S(object):
            def __init__(self, x):
                self.x = x

        class V(object):
            _virtualizable_ = True
            def __init__(self, x):
                self.x = x

        def g(v):
            v.x = 42
        
        def f(x):
            hint(None, global_merge_point=True)
            s = S(x)
            v = V(x)
            g(v)
            return v.x + s.x
        
        def main(x):
            s = S(19)
            r = f(x)
            return r
        
        res = self.timeshift_from_portal(main, f, [0], policy=StopAtXPolicy(g))
        assert res == 42

    def test_force_then_set_in_residual_call(self):
        class S(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y
            
        class V(object):
            _virtualizable_ = True
            def __init__(self, s):
                self.s = s

        def g(v):
            s = v.s
            x = s.x
            y = s.y
            s.x = y
            s.y = x
            v.s = S(x*100, y*100)
            
        def f(v):
            hint(None, global_merge_point=True)
            s = S(1, 10)
            v.s = s
            g(v)
            s2 = v.s
            return s.x*2 + s.y + s2.x * 2 + s2.y

        def main():
            v = V(None)
            return f(v)

        res = self.timeshift_from_portal(main, f, [], policy=StopAtXPolicy(g))
        assert res == 20 + 1 + 200 + 1000


    def test_inheritance_with_residual_call(self):
        class S(object):
            def __init__(self, x, y):
                self.sx = x
                self.sy = y
            

        class X(object):
            _virtualizable_ = True
            
            def __init__(self, x):
                self.x = x

        class XY(X):

            def __init__(self, x, y, s):
                X.__init__(self, x)
                self.s = s
                self.y = y

        def g(xy):
            s = xy.s
            x = xy.x
            y = xy.y
            if x:
                xy.x = s.sx
                xy.y = s.sy
            if y:
                xy.s = S(x, y)
   
        def f(xy, sx, sy):
            hint(None, global_merge_point=True)
            xy.s = S(sx, sy)
            g(xy)
            return xy.x + xy.y * 16 + xy.s.sx * 16 ** 2 + xy.s.sy * 16 ** 3

        def main(x, y, sx, sy):
            X(0)
            xy = XY(x, y, None)
            return f(xy, sx, sy)

        res = self.timeshift_from_portal(main, f, [1, 2, 4, 8],
                                         policy=StopAtXPolicy(g))
        assert res == 4 + 8 * 16 + 1 * 16 ** 2 + 2 * 16 ** 3


    def test_force_then_set_in_residual_call_more(self):
        class S(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

        class T(object):
            def __init__(self, s1, s2):
                self.s1 = s1
                self.s2 = s2

        class V(object):
            _virtualizable_ = True
            def __init__(self, s, t):
                self.s = s
                self.t = t

        def g(v):
            s1 = v.s
            x = s1.x
            y = s1.y
            s1.x = y
            s1.y = x
            v.s = S(x*100, y*100)
            t = v.t
            s1bis = t.s1
            assert s1bis is s1
            s2 = t.s2
            x = s2.x
            y = s2.y
            s2.x = 5*y
            s2.y = 5*x
            t.s1 = s2
            
        def f(v):
            hint(None, global_merge_point=True)
            s1 = S(1, 10)
            s2 = S(3, 23)
            v.s = s1
            v.t = t0 = T(s1, s2)
            g(v)
            t = v.t
            assert t is t0
            assert t.s1 is t.s2
            assert t.s1 is s2
            assert v.s is not s1
            s3 = v.s
            return s1.x + 7*s1.y + s2.x + 11*s2.y + s3.x + 17 * s3.y 

        def main():
            v = V(None, None)
            return f(v)

        res = self.timeshift_from_portal(main, f, [], policy=StopAtXPolicy(g))
        assert res == main()



    def test_force_then_set_in_residual_call_evenmore(self):
        class S(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

        class T(object):
            def __init__(self, s1, s2):
                self.s1 = s1
                self.s2 = s2

        class V(object):
            _virtualizable_ = True
            def __init__(self, s, t):
                self.s = s
                self.t = t

        def g(v):
            s1 = v.s
            x = s1.x
            y = s1.y
            s1.x = y
            s1.y = x
            t = v.t
            s1bis = t.s1
            assert s1bis is s1
            s2 = t.s2
            x = s2.x
            y = s2.y
            s2.x = 5*y
            s2.y = 5*x
            t.s1 = s2
            v.t = T(t.s1, t.s2)
            
        def f(v):
            hint(None, global_merge_point=True)
            s1 = S(1, 10)
            s2 = S(3, 23)
            v.s = s1
            v.t = t0 = T(s1, s2)
            g(v)
            t = v.t

            assert t is not t0
            assert t.s1 is t.s2
            assert t.s1 is s2
            assert v.s is s1
            s3 = v.s
            return s1.x + 7*s1.y + s2.x + 11*s2.y + s3.x + 17 * s3.y 

        def main():
            v = V(None, None)
            return f(v)

        res = self.timeshift_from_portal(main, f, [], policy=StopAtXPolicy(g))
        assert res == main()


        
    def test_virtual_list(self):
        class V(object):
            _virtualizable_ = True
            def __init__(self, l):
                self.l = l

        def g(v):
            l = v.l
            x = l[0]
            y = l[1]
            l[0] = y
            l[1] = x
            v.l = [x*100, y*100]
            
        def f(v):
            hint(None, global_merge_point=True)
            l = [1, 10]
            v.l = l
            g(v)
            l2 = v.l
            return l[0]*2 + l[1] + l2[0] * 2 + l2[1]

        def main():
            v = V(None)
            return f(v)

        res = self.timeshift_from_portal(main, f, [], policy=StopAtXPolicy(g))
        assert res == 20 + 1 + 200 + 1000

    def test_virtual_list_and_struct(self):
        class S(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

        class V(object):
            _virtualizable_ = True
            def __init__(self, l, s):
                self.l = l
                self.s = s
        def g(v):
            l = v.l
            x = l[0]
            y = l[1]
            l[0] = y
            l[1] = x
            v.l = [x*100, y*100]
            
        def f(v):
            hint(None, global_merge_point=True)
            l = [1, 10]
            s = S(3, 7)
            v.l = l
            v.s = s
            g(v)
            l2 = v.l
            s2 = v.s
            return l[0]*2 + l[1] + l2[0] * 2 + l2[1] + s.x * 7 + s.y + s2.x * 7 + s2.y 

        def main():
            v = V(None, None)
            return f(v)

        res = self.timeshift_from_portal(main, f, [], policy=StopAtXPolicy(g))
        assert res == main()

    def test_simple_interpreter_with_frame_with_stack(self):
        class Log:
            stack = None
        log = Log()
        class Frame(object):
            _virtualizable_ = True
            def __init__(self, code, *args):
                self.code = code
                self.pc = 0
                self.stack = list(args)
                
            def run(self):
                return self.interpret(self.code)

            def interpret(self, s):
                hint(None, global_merge_point=True)
                n = len(s)
                pc = 0
                origstack = self.stack
                stacklen = len(origstack)
                stacklen = hint(stacklen, promote=True)
                curstack = [0] * stacklen
                i = 0
                while i < stacklen:
                    hint(i, concrete=True)
                    curstack[i] = origstack[i]
                    i += 1
                self.stack = curstack
                while pc < n:
                    hint(None, global_merge_point=True)
                    self.pc = pc
                    op = s[pc]
                    pc += 1
                    op = hint(op, concrete=True)
                    if op == 'P': 
                        arg = s[pc]
                        pc += 1
                        hint(arg, concrete=True)
                        self.stack.append(ord(arg) - ord('0')) 
                    elif op == 'p':
                        self.stack.pop()
                    elif op == '+':
                        arg = self.stack.pop()
                        self.stack[-1] += arg
                    elif op == '-':
                        arg = self.stack.pop()
                        self.stack[-1] -= arg
                    elif op == 'd':
                        self.debug()
                    else:
                        raise NotImplementedError
                result = self.stack.pop()
                self.stack = None
                return result

            def debug(self):
                log.stack = self.stack[:]
            
        def main(x):
            code = 'P2+P5+P3-'
            f = Frame(code, x)
            return f.run()

        res = self.timeshift_from_portal(main, Frame.interpret.im_func,
                            [38],
                            policy=StopAtXPolicy(Frame.debug.im_func))
        assert res == 42
        self.check_oops(newlist=0)


    def test_recursive(self):

        class XY(object):
            _virtualizable_ = True
            
            def __init__(self, x, back):
                self.x = x
                self.back = back
   
        def f(xy):
            return xy.x

        def main(x, y):
            xyy = XY(y, None)
            xy = XY(x, xyy)
            return f(xy)

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_OOPSPEC)
        assert res == 20
        self.check_insns(getfield=0)


    def test_recursive_load_from(self):

        class W(object):
            def __init__(self, xy):
                self.xy = xy

        class XY(object):
            _virtualizable_ = True
            
            def __init__(self, x, back):
                self.x = x
                self.back = back
   
        def f(w):
            xy = w.xy
            return xy.x

        def main(x, y):
            xyy = XY(y, None)
            xy = XY(x, xyy)
            return f(W(xy))

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_OOPSPEC)
        assert res == 20

    def test_string_in_virtualizable(self):
        class S(object):
            def __init__(self, s):
                self.s = s

        class XY(object):
            _virtualizable_ = True
            
            def __init__(self, x, s):
                self.x = x
                self.s = s
        def g(xy):
            xy.x = 19 + len(xy.s.s)
   
        def f(x, n):
            hint(None, global_merge_point=True)
            s = S('2'*n)
            xy = XY(x, s)
            g(xy)
            return xy.s

        def main(x, y):
            return int(f(x, y).s)

        res = self.timeshift_from_portal(main, f, [20, 3],
                                         policy=StopAtXPolicy(g))
        assert res == 222

    def test_type_bug(self):
        class V(object):
            _virtualizable_ = True

            def __init__(self, v):
                self.v = v

        def f(x, v):
            if x:
                v.v = 0
            else:
                pass
            return x*2, v

        def main(x,y):
            v = V(y)
            r, _ = f(x, v)
            return r

        res = self.timeshift_from_portal(main, f, [20, 3], policy=P_OOPSPEC)
        assert res == 40

    def test_indirect_residual_call(self):
        class V(object):
            _virtualizable_ = True

            def __init__(self, v):
                self.v = v

        def g(v, n):
            v.v.append(n)      # force the virtualizable arg here
        def h1(v, n):
            g(v, n)
            return n * 6
        def h2(v, n):
            return n * 8

        l = [h2, h1]

        def f(n):
            hint(None, global_merge_point=True)
            v = V([100])
            h = l[n & 1]
            n += 10
            res = h(v, n)
            return res - v.v.pop()

        P = StopAtXPolicy(g)

        assert f(-3) == 35
        res = self.timeshift_from_portal(f, f, [-3], policy=P)
        assert res == 35
        res = self.timeshift_from_portal(f, f, [4], policy=P)
        assert res == 12
