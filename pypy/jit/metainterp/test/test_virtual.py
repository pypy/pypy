import py
from pypy.rlib.jit import JitDriver, hint
from pypy.rlib.objectmodel import compute_unique_id
from pypy.jit.metainterp.policy import StopAtXPolicy
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.rpython.lltypesystem import lltype, rclass
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp import heaptracker

class VirtualTests:
    def _freeze_(self):
        return True

    def test_virtualized(self):
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
                if next.extra == 4:
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
                if next.extra == 4:
                    next.value = externfn(next)
                    next.extra = 0
                node = next
                n -= 1
            return node.value
        res = self.meta_interp(f, [11], policy=StopAtXPolicy(externfn))
        assert res == f(11)
        self.check_loop_count(2)
        self.check_loops(**{self._new_op: 2})     # XXX was 1
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
        #    ENTER             - compile the new loop
        #    ENTER (BlackHole) - leave
        #    ENTER             - compile the entry bridge
        #    ENTER             - compile the leaving path
        self.check_enter_count(4)

class VirtualMiscTests:

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
