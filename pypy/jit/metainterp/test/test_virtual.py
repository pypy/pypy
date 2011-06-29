import py
from pypy.rlib.jit import JitDriver, hint
from pypy.rlib.objectmodel import compute_unique_id
from pypy.jit.codewriter.policy import StopAtXPolicy
from pypy.jit.metainterp.test.support import LLJitMixin, OOJitMixin
from pypy.rpython.lltypesystem import lltype, rclass
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.ootypesystem import ootype
from pypy.jit.codewriter import heaptracker

class VirtualTests:
    def _freeze_(self):
        return True

    def test_virtualized1(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        def f(n):
            node = self._new()
            node.value = 0
            node.extra = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, node=node)
                myjitdriver.jit_merge_point(n=n, node=node)
                next = self._new()
                next.value = node.value + n
                next.extra = node.extra + 1
                node = next
                n -= 1
            return node.value * node.extra
        assert f(10) == 55 * 10
        res = self.meta_interp(f, [10])
        assert res == 55 * 10
        self.check_loop_count(1)
        self.check_loops(new=0, new_with_vtable=0,
                                getfield_gc=0, setfield_gc=0)

    def test_virtualized2(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node1', 'node2'])
        def f(n):
            node1 = self._new()
            node1.value = 0
            node2 = self._new()
            node2.value = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, node1=node1, node2=node2)
                myjitdriver.jit_merge_point(n=n, node1=node1, node2=node2)
                next1 = self._new()
                next1.value = node1.value + n + node2.value
                next2 = self._new()
                next2.value = next1.value
                node1 = next1
                node2 = next2
                n -= 1
            return node1.value * node2.value
        assert f(10) == self.meta_interp(f, [10])
        self.check_loops(new=0, new_with_vtable=0,
                         getfield_gc=0, setfield_gc=0)

    def test_virtualized_circular1(self):
        class MyNode():
            pass
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        def f(n):
            node = MyNode()
            node.value = 0
            node.extra = 0
            node.ref = node
            while n > 0:
                myjitdriver.can_enter_jit(n=n, node=node)
                myjitdriver.jit_merge_point(n=n, node=node)
                next = MyNode()
                next.value = node.ref.value + n
                next.extra = node.ref.extra + 1
                next.ref = next
                node = next
                n -= 1
            return node.value * node.extra
        assert f(10) == 55 * 10
        res = self.meta_interp(f, [10])
        assert res == 55 * 10
        self.check_loop_count(1)
        self.check_loops(new=0, new_with_vtable=0,
                                getfield_gc=0, setfield_gc=0)

    def test_virtualized_float(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        def f(n):
            node = self._new()
            node.floatval = 0.0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, node=node)
                myjitdriver.jit_merge_point(n=n, node=node)
                next = self._new()
                next.floatval = node.floatval + .5
                n -= 1
            return node.floatval
        res = self.meta_interp(f, [10])
        assert res == f(10)
        self.check_loop_count(1)
        self.check_loops(new=0, float_add=0)

    def test_virtualized_float2(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        def f(n):
            node = self._new()
            node.floatval = 0.0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, node=node)
                myjitdriver.jit_merge_point(n=n, node=node)
                next = self._new()
                next.floatval = node.floatval + .5
                node = next
                n -= 1
            return node.floatval
        res = self.meta_interp(f, [10])
        assert res == f(10)
        self.check_loop_count(1)
        self.check_loops(new=0, float_add=1)

    def test_virtualized_2(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        def f(n):
            node = self._new()
            node.value = 0
            node.extra = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, node=node)
                myjitdriver.jit_merge_point(n=n, node=node)
                next = self._new()
                next.value = node.value
                next.value += n
                next.extra = node.extra
                next.extra += 1
                next.extra += 1
                next.extra += 1
                node = next
                n -= 1
            return node.value * node.extra
        res = self.meta_interp(f, [10])
        assert res == 55 * 30
        self.check_loop_count(1)
        self.check_loops(new=0, new_with_vtable=0,
                                getfield_gc=0, setfield_gc=0)

    def test_nonvirtual_obj_delays_loop(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        node0 = self._new()
        node0.value = 10
        def f(n):
            node = node0
            while True:
                myjitdriver.can_enter_jit(n=n, node=node)
                myjitdriver.jit_merge_point(n=n, node=node)
                i = node.value
                if i >= n:
                    break
                node = self._new()
                node.value = i * 2
            return node.value
        res = self.meta_interp(f, [500])
        assert res == 640
        self.check_loop_count(1)
        self.check_loops(new=0, new_with_vtable=0,
                                getfield_gc=0, setfield_gc=0)

    def test_two_loops_with_virtual(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        def f(n):
            node = self._new()
            node.value = 0
            node.extra = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, node=node)
                myjitdriver.jit_merge_point(n=n, node=node)
                next = self._new()
                next.value = node.value + n
                next.extra = node.extra + 1
                if next.extra == 5:
                    next.value += 100
                    next.extra = 0
                node = next
                n -= 1
            return node.value
        res = self.meta_interp(f, [18])
        assert res == f(18)
        self.check_loop_count(2)
        self.check_loops(new=0, new_with_vtable=0,
                                getfield_gc=0, setfield_gc=0)
        
    def test_two_loops_with_escaping_virtual(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        def externfn(node):
            llop.debug_print(lltype.Void, compute_unique_id(node),
                             node.value, node.extra)
            return node.value * 2
        def f(n):
            node = self._new()
            node.value = 0
            node.extra = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, node=node)
                myjitdriver.jit_merge_point(n=n, node=node)
                next = self._new()
                next.value = node.value + n
                next.extra = node.extra + 1
                if next.extra == 5:
                    next.value = externfn(next)
                    next.extra = 0
                node = next
                n -= 1
            return node.value
        res = self.meta_interp(f, [20], policy=StopAtXPolicy(externfn))
        assert res == f(20)
        self.check_loop_count(3)
        self.check_loops(**{self._new_op: 1})
        self.check_loops(int_mul=0, call=1)

    def test_two_virtuals(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'prev'])
        class Foo(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

        def f(n):
            prev = Foo(n, 0)
            n -= 1
            while n >= 0:
                myjitdriver.can_enter_jit(n=n, prev=prev)
                myjitdriver.jit_merge_point(n=n, prev=prev)
                foo = Foo(n, 0)
                foo.x += prev.x
                prev = foo
                n -= 1
            return prev.x

        res = self.meta_interp(f, [12])
        assert res == 78
        self.check_loops(new_with_vtable=0, new=0)

    def test_specialied_bridge(self):
        myjitdriver = JitDriver(greens = [], reds = ['y', 'x', 'res'])
        class A:
            def __init__(self, val):
                self.val = val
            def binop(self, other):
                return A(self.val + other.val)
        def f(x, y):
            res = A(0)
            while y > 0:
                myjitdriver.can_enter_jit(y=y, x=x, res=res)
                myjitdriver.jit_merge_point(y=y, x=x, res=res)
                res = res.binop(A(y))
                if y<7:
                    res = x
                    x = A(1)
                y -= 1
            return res
        def g(x, y):
            a1 = f(A(x), y)
            a2 = f(A(x), y)
            assert a1.val == a2.val
            return a1.val
        res = self.meta_interp(g, [6, 14])
        assert res == g(6, 14)

    def test_both_virtual_and_field_variable(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        class Foo(object):
            pass
        def f(n):
            while n >= 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                foo = self._new()
                foo.value = n
                if n < 10:
                    break
                n = foo.value - 1
            return n

        res = self.meta_interp(f, [20])
        assert res == 9
        self.check_loops(new_with_vtable=0, new=0)

    def test_immutable_constant_getfield(self):
        myjitdriver = JitDriver(greens = ['stufflist'], reds = ['n', 'i'])

        class Stuff(object):
            _immutable_ = True
            def __init__(self, x):
                self.x = x

        class StuffList(object):
            _immutable_ = True
        
        def f(n, a, i):
            stufflist = StuffList()
            stufflist.lst = [Stuff(a), Stuff(3)]
            while n > 0:
                myjitdriver.can_enter_jit(n=n, i=i, stufflist=stufflist)
                myjitdriver.jit_merge_point(n=n, i=i, stufflist=stufflist)
                i = hint(i, promote=True)
                v = Stuff(i)
                n -= stufflist.lst[v.x].x
            return n

        res = self.meta_interp(f, [10, 1, 0], listops=True)
        assert res == 0
        self.check_loops(getfield_gc=0)

    def test_escapes(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'parent'])

        class Parent(object):
            def __init__(self, node):
                self.node = node

        def g(x):
            pass

        def f(n):
            node = self._new()
            node.value = 3
            parent = Parent(node)
            while n > 0:
                myjitdriver.can_enter_jit(n=n, parent=parent)
                myjitdriver.jit_merge_point(n=n, parent=parent)
                node = parent.node
                g(node)
                newnode = self._new()
                newnode.value = 3
                parent = Parent(newnode)
                n -= 1
            return parent.node.value

        res = self.meta_interp(f, [10], policy=StopAtXPolicy(g))
        assert res == 3
        self.check_loops(**{self._new_op: 1}) 

    def test_virtual_on_virtual(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'parent'])

        class Node(object):
            def __init__(self, f):
                self.f = f

        class SubNode(object):
            def __init__(self, f):
                self.f = f
        
        def f(n):
            subnode = self._new()
            subnode.value = 3
            node = Node(subnode)
            while n > 0:
                myjitdriver.can_enter_jit(n=n, parent=node)
                myjitdriver.jit_merge_point(n=n, parent=node)
                subnode = self._new()
                subnode.value = n + 1
                node = Node(subnode)
                if n == -3:
                    return 8
                n -= 1
            return node.f.value

        res = self.meta_interp(f, [10])
        assert res == 2
        self.check_loops(new=0, new_with_vtable=0) 

    def test_bridge_from_interpreter(self):
        mydriver = JitDriver(reds = ['n', 'f'], greens = [])

        def f(n):
            f = self._new()
            f.value = 0
            while n > 0:
                mydriver.can_enter_jit(n=n, f=f)
                mydriver.jit_merge_point(n=n, f=f)
                prev = f.value
                f = self._new()
                f.value = prev + n
                n -= 2
            return f

        res = self.meta_interp(f, [21], repeat=7)

        fieldname = self._field_prefix + 'value'
        assert getattr(res, fieldname, -100) == f(21).value

        self.check_tree_loop_count(2)      # the loop and the entry path
        # we get:
        #    ENTER             - compile the new loop and entry bridge
        #    ENTER             - compile the leaving path
        self.check_enter_count(2)

    def test_new_virtual_member_in_bridge(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'sa', 'node'])
        def f(n):
            node = self._new()
            node.value = 1
            node.extra = 2
            sa = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, sa=sa, node=node)
                myjitdriver.jit_merge_point(n=n, sa=sa, node=node)
                if n&30 > 0:
                    sa += node.value
                    next = self._new()
                    next.value = n
                    node = next
                    if n<10:
                        node.extra = sa
                n -= 1
            return node.extra
        assert self.meta_interp(f, [20]) == f(20)

    def test_constant_virtual1(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'sa', 'node'])
        def f(n):
            node = self._new()
            node.value = 1
            sa = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, sa=sa, node=node)
                myjitdriver.jit_merge_point(n=n, sa=sa, node=node)
                if n>20:
                    next = self._new()
                    next.value = 2
                    node = next
                elif n>10:
                    next = self._new()
                    next.value = 3
                    node = next
                sa += node.value
                n -= 1
            return sa
        assert self.meta_interp(f, [30]) == f(30)
        
    def test_constant_virtual2(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'sa', 'node'])
        def f(n):
            node = self._new()
            node.value = 1
            sa = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, sa=sa, node=node)
                myjitdriver.jit_merge_point(n=n, sa=sa, node=node)
                sa += node.value
                if n&15 > 7:
                    next = self._new()
                    next.value = 2
                    node = next
                else:
                    next = self._new()
                    next.value = 3
                    node = next
                n -= 1
            return sa
        assert self.meta_interp(f, [31]) == f(31)
        
    def test_stored_reference_with_bridge1(self):
        class RefNode(object):
            def __init__(self, ref):
                self.ref = ref
        myjitdriver = JitDriver(greens = [], reds = ['n', 'sa', 'node1', 'node2'])
        def f(n):
            node1 = self._new()
            node1.value = 1
            node2 = RefNode(node1)
            sa = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, sa=sa, node1=node1, node2=node2)
                myjitdriver.jit_merge_point(n=n, sa=sa, node1=node1, node2=node2)
                if n>10:
                    next = self._new()
                    next.value = 2
                    node1 = next
                else:
                    node2.ref.value = 3
                sa += node1.value
                n -= 1
            return sa
        def g():
            return  f(20) * 100 + f(10)
        assert f(20) == 20 * 2
        assert self.meta_interp(f, [20]) == 20 * 2
        assert f(10) == 10 * 3
        assert self.meta_interp(f, [10]) == 10 * 3
        assert g() == 4030
        assert self.meta_interp(g, []) == 4030

    def test_stored_reference_with_bridge2(self):
        class RefNode(object):
            def __init__(self, ref):
                self.ref = ref
        myjitdriver = JitDriver(greens = [], reds = ['n', 'sa', 'node1', 'node2'])
        def f(n):
            node1 = self._new()
            node1.value = 1
            node2 = RefNode(node1)
            sa = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, sa=sa, node1=node1, node2=node2)
                myjitdriver.jit_merge_point(n=n, sa=sa, node1=node1, node2=node2)
                if n>10:
                    next = self._new()
                    next.value = node1.value + 2
                    node1 = next
                else:
                    node2.ref.value += 3
                sa += node1.value
                n -= 1
            return sa
        def g():
            return  f(20) * 100 + f(10)
        assert self.meta_interp(g, []) == g()

    def test_stored_reference_with_bridge3(self):
        class RefNode(object):
            def __init__(self, ref):
                self.ref = ref
        myjitdriver = JitDriver(greens = [], reds = ['n', 'sa', 'node1', 'node2'])
        def f(n):
            node1 = self._new()
            node1.value = 1
            node2 = RefNode(node1)
            sa = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, sa=sa, node1=node1, node2=node2)
                myjitdriver.jit_merge_point(n=n, sa=sa, node1=node1, node2=node2)
                node2.ref.value += n
                sa += node1.value
                if n>10:
                    next = self._new()
                    next.value = node1.value + 1
                    node1 = next
                else:
                    node1 = node2.ref
                n -= 1
            return sa
        assert self.meta_interp(f, [20]) == f(20)

    def test_dual_counter(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 's', 'node1', 'node2'])
        def f(n, s):
            node1 = self._new()
            node1.value = 1
            node2 = self._new()
            node2.value = 2
            while n > 0:
                myjitdriver.can_enter_jit(n=n, s=s, node1=node1, node2=node2)
                myjitdriver.jit_merge_point(n=n, s=s, node1=node1, node2=node2)
                if (n>>s) & 1:
                    next = self._new()
                    next.value = node1.value + 1
                    node1 = next
                else:
                    next = self._new()
                    next.value = node2.value + 1
                    node2 = next
                n -= 1
            return node1.value + node2.value
        assert self.meta_interp(f, [40, 3]) == f(40, 3)
        self.check_loop_count(6)

    def test_single_virtual_forced_in_bridge(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 's', 'node'])
        def externfn(node):
            node.value *= 2
        def f(n, s):
            node = self._new()
            node.value = 1
            while n > 0:
                myjitdriver.can_enter_jit(n=n, s=s, node=node)
                myjitdriver.jit_merge_point(n=n, s=s, node=node)
                next = self._new()
                next.value = node.value + 1
                node = next
                if (n>>s) & 1:
                    externfn(node)
                n -= 1
            return node.value
        res = self.meta_interp(f, [48, 3], policy=StopAtXPolicy(externfn))
        assert res == f(48, 3)
        res = self.meta_interp(f, [40, 3], policy=StopAtXPolicy(externfn))
        assert res == f(40, 3)

    def test_forced_virtual_assigned_in_bridge(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 's', 'node', 'node2'])
        def externfn(node):
            node.value += 1
        def f(n, s):
            node = self._new()
            node.value = 1
            node2 = self._new()
            node2.value = 2
            while n > 0:
                myjitdriver.can_enter_jit(n=n, s=s, node=node, node2=node2)
                myjitdriver.jit_merge_point(n=n, s=s, node=node, node2=node2)
                next = self._new()
                next.value = node.value + 1
                node = next
                if (n>>s) & 1:
                    node2.value += node.value
                    node = node2
                externfn(node)
                n -= 1
            return node.value
        res = self.meta_interp(f, [48, 3], policy=StopAtXPolicy(externfn))
        assert res == f(48, 3)
        self.check_loop_count(3)
        res = self.meta_interp(f, [40, 3], policy=StopAtXPolicy(externfn))
        assert res == f(40, 3)
        self.check_loop_count(3)

    def test_forced_virtual_assigned_different_class_in_bridge(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 's', 'node', 'node2'])
        def externfn(node):
            node.value += 1
        class A(object):
            def __init__(self, value):
                self.value = value
            def op(self, val):
                return self.value + val
        class B(A):
            def op(self, val):
                return self.value - val
        def f(n, s, node2):
            node = A(1)
            while n > 0:
                myjitdriver.can_enter_jit(n=n, s=s, node=node, node2=node2)
                myjitdriver.jit_merge_point(n=n, s=s, node=node, node2=node2)
                if (n>>s) & 1:
                    node2.value += node.value
                    node = node2
                else:
                    node.value = node.op(1)
                    node = A(node.value + 7)
                    externfn(node)
                n -= 1
            return node.value
        def g1(n, s):
            return f(n, s, A(2)) + f(n, s, B(2))
        def g2(n, s):
            return f(n, s, B(2)) + f(n, s, A(2))
        res = self.meta_interp(g1, [40, 3], policy=StopAtXPolicy(externfn))
        assert res == g1(40, 3)
        res = self.meta_interp(g1, [48, 3], policy=StopAtXPolicy(externfn))
        assert res == g1(48, 3)
        res = self.meta_interp(g2, [40, 3], policy=StopAtXPolicy(externfn))
        assert res == g2(40, 3)
        res = self.meta_interp(g2, [48, 3], policy=StopAtXPolicy(externfn))
        assert res == g2(48, 3)

    def test_empty_virtual_with_bridge(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 's', 'sa', 'node'])
        def f(n, s):
            node = self._new()
            sa = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, s=s, sa=sa, node=node)
                myjitdriver.jit_merge_point(n=n, s=s, sa=sa, node=node)
                next = self._new()
                node = next
                if (n>>s) & 1:
                    sa += 1
                else:
                    sa += 2
                n -= 1
            return sa
        res = self.meta_interp(f, [48, 3])
        assert res == f(48, 3)
        res = self.meta_interp(f, [40, 3])
        assert res == f(40, 3)

    def test_virtual_array_bridge(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        def f(n):
            node = [42, 42]
            while n > 0:
                myjitdriver.can_enter_jit(n=n, node=node)
                myjitdriver.jit_merge_point(n=n, node=node)
                if (n>>3) & 1:
                    node = [node[0], node[1] + n]
                else:
                    node = [node[0] + n, node[1]]
                n -= 1
            return node[0] + node[1]
        assert self.meta_interp(f, [40]) == f(40)

    def test_virtual_array_different_bridge(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'node'])
        def f(n):
            node = [42, 42]
            while n > 0:
                myjitdriver.can_enter_jit(n=n, node=node)
                myjitdriver.jit_merge_point(n=n, node=node)
                if (n>>3) & 1:
                    node = [node[0], node[1] + n]
                else:
                    node = [node[0] + n, node[-1], node[0] + node[1]]
                n -= 1
            return node[0] + node[1]
        assert self.meta_interp(f, [40]) == f(40)

    def FIXME_why_does_this_force(self):
        mydriver = JitDriver(reds = ['i', 'j'], greens = []) 
        def f():
            i = self._new()
            i.value = 0
            j = self._new()
            while i.value < 10:
                mydriver.can_enter_jit(i=i, j=j)
                mydriver.jit_merge_point(i=i, j=j)
                nxt = self._new()
                nxt.value = i.value + 1
                i = nxt
                j = nxt
            return i.value + j.value
        assert self.meta_interp(f, []) == 20

    def FIXME_why_does_this_force2(self):
        mydriver = JitDriver(reds = ['i', 'j'], greens = []) 
        def f():
            i = self._new()
            i.value = 0
            j = self._new()
            j.value = 0
            while i.value < 10:
                mydriver.can_enter_jit(i=i, j=j)
                mydriver.jit_merge_point(i=i, j=j)
                nxt = self._new()
                nxt.value = i.value + 1
                i = nxt
                nxt = self._new()
                nxt.value = i.value + 1
                j = nxt
                i = j
            return i.value + j.value
        assert self.meta_interp(f, []) == 20
                
    def test_virtual_skipped_by_bridge(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'm', 'i', 'x'])
        def f(n, m):
            x = self._new()
            x.value = 0
            i = 0
            while i < n:
                myjitdriver.can_enter_jit(n=n, m=m, i=i, x=x)
                myjitdriver.jit_merge_point(n=n, m=m, i=i, x=x)
                if i&m != m:
                    newx = self._new()
                    newx.value = x.value + i
                    x = newx
                i = i + 1
            return x.value
        res = self.meta_interp(f, [0x1F, 0x11])
        assert res == f(0x1F, 0x11)

class VirtualMiscTests:

    def test_multiple_equal_virtuals(self):
        mydriver = JitDriver(reds = ['i'], greens = [])
        class A:
            pass
        def f():
            i = A()
            i.value = 0
            while i.value < 10:
                mydriver.can_enter_jit(i=i)
                mydriver.jit_merge_point(i=i)
                nxt = A()
                nxt.value = i.value + 1
                tmp = A()
                tmp.ref = nxt
                i = tmp.ref
            return i.value
        assert self.meta_interp(f, []) == 10

    def test_guards_around_forcing(self):
        class A(object):
            def __init__(self, x):
                self.x = x
        mydriver = JitDriver(reds = ['n'], greens = [])
        global_a = A(0)

        def g(a):
            n = a.x
            if n < 10:
                n += 1
            global_a.forced = a
            if n < 20:
                assert global_a.forced is a

        def f(n):
            while n > 0:
                mydriver.can_enter_jit(n=n)
                mydriver.jit_merge_point(n=n)
                a = A(n)
                g(a)
                n -= 1
            return 0
        self.meta_interp(f, [50])

    def test_guards_and_holes(self):
        class A(object):
            def __init__(self, x):
                self.x = x
        mydriver = JitDriver(reds = ['n', 'tot'], greens = [])

        def f(n):
            tot = 0
            while n > 0:
                mydriver.can_enter_jit(n=n, tot=tot)
                mydriver.jit_merge_point(n=n, tot=tot)
                a = A(n)
                b = A(n+1)
                if n % 9 == 0:
                    tot += (a.x + b.x) % 3
                c = A(n+1)
                if n % 10 == 0:
                    tot -= (c.x + a.x) % 3
                n -= 1
            return tot
        r = self.meta_interp(f, [70])
        expected = f(70)
        assert r == expected

    def test_arraycopy_disappears(self):
        mydriver = JitDriver(reds = ['i'], greens = []) 
        def f():
            i = 0
            while i < 10:
                mydriver.can_enter_jit(i=i)
                mydriver.jit_merge_point(i=i)                
                t = (1, 2, 3, i + 1)
                t2 = t[:]
                del t
                i = t2[3]
                del t2
            return i
        assert self.meta_interp(f, []) == 10
        self.check_loops(new_array=0)

    def test_virtual_streq_bug(self):
        mydriver = JitDriver(reds = ['i', 's', 'a'], greens = [])

        class A(object):
            def __init__(self, state):
                self.state = state
        
        def f():
            i = 0
            s = 10000
            a = A("data")
            while i < 10:
                mydriver.jit_merge_point(i=i, a=a, s=s)
                if i > 1:
                    if a.state == 'data':
                        a.state = 'escaped'
                        s += 1000
                    else:
                        s += 100
                else:
                    s += 10
                i += 1
            return s

        res = self.meta_interp(f, [], repeat=7)
        assert res == f()

    def test_getfield_gc_pure_nobug(self):
        mydriver = JitDriver(reds = ['i', 's', 'a'], greens = [])

        class A(object):
            _immutable_fields_ = ['foo']
            def __init__(self, foo):
                self.foo = foo

        prebuilt42 = A(42)
        prebuilt43 = A(43)

        def f():
            i = 0
            s = 10000
            a = prebuilt42
            while i < 10:
                mydriver.jit_merge_point(i=i, s=s, a=a)
                if i > 1:
                    s += a.foo
                    a = prebuilt43
                else:
                    s += 10
                i += 1
            return s

        res = self.meta_interp(f, [], repeat=7)
        assert res == f()

    def test_virtual_attribute_pure_function(self):
        mydriver = JitDriver(reds = ['i', 'sa', 'n', 'node'], greens = [])
        class A(object):
            def __init__(self, v1, v2):
                self.v1 = v1
                self.v2 = v2
        def f(n):
            i = sa = 0
            node = A(1, 2)
            while i < n:
                mydriver.jit_merge_point(i=i, sa=sa, n=n, node=node)
                sa += node.v1 + node.v2 + 2*node.v1
                if i < n/2:
                    node = A(n, 2*n)
                else:
                    node = A(n, 3*n)
                i += 1
            return sa

        res = self.meta_interp(f, [16])
        assert res == f(16)
        

# ____________________________________________________________
# Run 1: all the tests instantiate a real RPython class

class MyClass:
    pass

class TestLLtype_Instance(VirtualTests, LLJitMixin):
    _new_op = 'new_with_vtable'
    _field_prefix = 'inst_'
    
    @staticmethod
    def _new():
        return MyClass()

    def test_class_with_default_fields(self):
        class MyClass:
            value = 2
            value2 = 0

        class Subclass(MyClass):
            pass

        myjitdriver = JitDriver(greens = [], reds = ['n', 'res'])
        def f(n):
            res = 0
            node = MyClass()
            node.value = n  # so that the annotator doesn't think that value is constant
            node.value2 = n # ditto
            while n > 0:
                myjitdriver.can_enter_jit(n=n, res=res)
                myjitdriver.jit_merge_point(n=n, res=res)
                node = Subclass()
                res += node.value
                res += node.value2
                n -= 1
            return res
        assert f(10) == 20
        res = self.meta_interp(f, [10])
        assert res == 20
        self.check_loop_count(1)
        self.check_loops(new=0, new_with_vtable=0,
                                getfield_gc=0, setfield_gc=0)



class TestOOtype_Instance(VirtualTests, OOJitMixin):
    _new_op = 'new_with_vtable'
    _field_prefix = 'o'
    
    @staticmethod
    def _new():
        return MyClass()

    test_class_with_default_fields = TestLLtype_Instance.test_class_with_default_fields.im_func

# ____________________________________________________________
# Run 2: all the tests use lltype.malloc to make a NODE

NODE = lltype.GcStruct('NODE', ('value', lltype.Signed),
                               ('floatval', lltype.Float),
                               ('extra', lltype.Signed))

class TestLLtype_NotObject(VirtualTests, LLJitMixin):
    _new_op = 'new'
    _field_prefix = ''
    
    @staticmethod
    def _new():
        return lltype.malloc(NODE)


OONODE = ootype.Instance('NODE', ootype.ROOT, {})
OONODE._add_fields({'value': ootype.Signed,
                    'floatval' : ootype.Float,
                    'extra': ootype.Signed})

class TestOOtype_NotObject(VirtualTests, OOJitMixin):
    _new_op = 'new_with_vtable'
    _field_prefix = ''
    
    @staticmethod
    def _new():
        return ootype.new(OONODE)

# ____________________________________________________________
# Run 3: all the tests use lltype.malloc to make a NODE2
# (same as Run 2 but it is part of the OBJECT hierarchy)

NODE2 = lltype.GcStruct('NODE2', ('parent', rclass.OBJECT),
                                 ('floatval', lltype.Float),
                                 ('value', lltype.Signed),
                                 ('extra', lltype.Signed))

vtable2 = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
heaptracker.set_testing_vtable_for_gcstruct(NODE2, vtable2, 'NODE2')

class TestLLtype_Object(VirtualTests, LLJitMixin):
    _new_op = 'new_with_vtable'
    _field_prefix = ''
    
    @staticmethod
    def _new():
        p = lltype.malloc(NODE2)
        p.parent.typeptr = vtable2
        return p

# misc

class TestOOTypeMisc(VirtualMiscTests, OOJitMixin):
    pass

class TestLLTypeMisc(VirtualMiscTests, LLJitMixin):
    pass
