import py
import sys
import struct
from pypy.translator.c import gc
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory.gctransform import framework
from pypy.rpython.memory.gctransform import stacklessframework
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.memory.gc import X_CLONE, X_POOL, X_POOL_PTR
from pypy import conftest

INT_SIZE = struct.calcsize("i")   # only for estimates


def rtype(func, inputtypes, specialize=True, gcname='ref', stacklessgc=False):
    from pypy.translator.translator import TranslationContext
    t = TranslationContext()
    # XXX XXX XXX mess
    t.config.translation.gc = gcname
    t.config.translation.stacklessgc = stacklessgc
    t.buildannotator().build_types(func, inputtypes)
    if specialize:
        t.buildrtyper().specialize()
    if conftest.option.view:
        t.view()
    return t

class GCTest(object):
    gcpolicy = None
    stacklessgc = False

    def runner(self, f, nbargs=0, statistics=False):
        if nbargs == 2:
            def entrypoint(args):
                x = args[0]
                y = args[1]
                r = f(x, y)
                return r
        elif nbargs == 0:
            def entrypoint(args):
                return f()
        else:
            raise NotImplementedError("pure laziness")

        from pypy.rpython.llinterp import LLInterpreter
        from pypy.translator.c.genc import CStandaloneBuilder

        ARGS = lltype.FixedSizeArray(lltype.Signed, nbargs)
        s_args = annmodel.SomePtr(lltype.Ptr(ARGS))
        t = rtype(entrypoint, [s_args], gcname=self.gcname,
                                        stacklessgc=self.stacklessgc)
        cbuild = CStandaloneBuilder(t, entrypoint, config=t.config,
                                    gcpolicy=self.gcpolicy)
        db = cbuild.generate_graphs_for_llinterp()
        entrypointptr = cbuild.getentrypointptr()
        entrygraph = entrypointptr._obj.graph
        if conftest.option.view:
            t.viewcg()

        llinterp = LLInterpreter(t.rtyper)

        # FIIIIISH
        setupgraph = db.gctransformer.frameworkgc_setup_ptr.value._obj.graph
        llinterp.eval_graph(setupgraph, [])
        def run(args):
            ll_args = lltype.malloc(ARGS, immortal=True)
            for i in range(nbargs):
                ll_args[i] = args[i]
            res = llinterp.eval_graph(entrygraph, [ll_args])
            return res

        if statistics:
            statisticsgraph = db.gctransformer.statistics_ptr.value._obj.graph
            ll_gc = db.gctransformer.c_const_gc.value
            def statistics(index):
                return llinterp.eval_graph(statisticsgraph, [ll_gc, index])
            return run, statistics
        else:
            return run
        
class TestMarkSweepGC(GCTest):

    class gcpolicy(gc.FrameworkGcPolicy):
        class transformerclass(framework.FrameworkGCTransformer):
            GC_PARAMS = {'start_heap_size': 4096 }
            root_stack_depth = 200
    gcname = "framework"

    def heap_usage(self, statistics):
        try:
            GCClass = self.gcpolicy.transformerclass.GCClass
        except AttributeError:
            from pypy.rpython.memory.gc import MarkSweepGC as GCClass
        if hasattr(GCClass, 'STAT_HEAP_USAGE'):
            return statistics(GCClass.STAT_HEAP_USAGE)
        else:
            return -1     # xxx

    def test_llinterp_lists(self):
        def malloc_a_lot():
            i = 0
            while i < 10:
                i += 1
                a = [1] * 10
                j = 0
                while j < 30:
                    j += 1
                    a.append(j)
            return 0
        run, statistics = self.runner(malloc_a_lot, statistics=True)
        run([])
        heap_size = self.heap_usage(statistics)
        assert heap_size < 16000 * INT_SIZE / 4 # xxx

    def test_llinterp_tuples(self):
        def malloc_a_lot():
            i = 0
            while i < 10:
                i += 1
                a = (1, 2, i)
                b = [a] * 10
                j = 0
                while j < 20:
                    j += 1
                    b.append((1, j, i))
            return 0
        run, statistics = self.runner(malloc_a_lot, statistics=True)
        run([])
        heap_size = self.heap_usage(statistics)
        assert heap_size < 16000 * INT_SIZE / 4 # xxx

    def test_global_list(self):
        class Box:
            def __init__(self):
                self.lst = []
        box = Box()
        def append_to_list(i, j):
            box.lst.append([i] * 50)
            llop.gc__collect(lltype.Void)
            return box.lst[j][0]
        run = self.runner(append_to_list, nbargs=2)
        res = run([0, 0])
        assert res == 0
        for i in range(1, 5):
            res = run([i, i - 1])
            assert res == i - 1 # crashes if constants are not considered roots
            
    def test_string_concatenation(self):

        def concat(j, dummy):
            lst = []
            for i in range(j):
                lst.append(str(i))
            return len("".join(lst))
        run, statistics = self.runner(concat, nbargs=2, statistics=True)
        res = run([100, 0])
        assert res == concat(100, 0)
        heap_size = self.heap_usage(statistics)
        assert heap_size < 16000 * INT_SIZE / 4 # xxx

    def test_finalizer(self):
        class B(object):
            pass
        b = B()
        b.nextid = 0
        b.num_deleted = 0
        class A(object):
            def __init__(self):
                self.id = b.nextid
                b.nextid += 1
            def __del__(self):
                b.num_deleted += 1
        def f(x, y):
            a = A()
            i = 0
            while i < x:
                i += 1
                a = A()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            return b.num_deleted
        run = self.runner(f, nbargs=2)
        res = run([5, 42]) #XXX pure lazyness here too
        assert res == 6

    def test_finalizer_calls_malloc(self):
        class B(object):
            pass
        b = B()
        b.nextid = 0
        b.num_deleted = 0
        class A(object):
            def __init__(self):
                self.id = b.nextid
                b.nextid += 1
            def __del__(self):
                b.num_deleted += 1
                C()
        class C(A):
            def __del__(self):
                b.num_deleted += 1
        def f(x, y):
            a = A()
            i = 0
            while i < x:
                i += 1
                a = A()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            return b.num_deleted
        run = self.runner(f, nbargs=2)
        res = run([5, 42]) #XXX pure lazyness here too
        assert res == 12

    def test_finalizer_resurrects(self):
        class B(object):
            pass
        b = B()
        b.nextid = 0
        b.num_deleted = 0
        class A(object):
            def __init__(self):
                self.id = b.nextid
                b.nextid += 1
            def __del__(self):
                b.num_deleted += 1
                b.a = self
        def f(x, y):
            a = A()
            i = 0
            while i < x:
                i += 1
                a = A()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            aid = b.a.id
            b.a = None
            # check that __del__ is not called again
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            return b.num_deleted * 10 + aid + 100 * (b.a is None)
        run = self.runner(f, nbargs=2)
        res = run([5, 42]) #XXX pure lazyness here too
        assert 160 <= res <= 165

    def test_weakref(self):
        import weakref, gc
        class A(object):
            pass
        def g():
            a = A()
            return weakref.ref(a)
        def f():
            a = A()
            ref = weakref.ref(a)
            result = ref() is a
            ref = g()
            llop.gc__collect(lltype.Void)
            result = result and (ref() is None)
            # check that a further collection is fine
            llop.gc__collect(lltype.Void)
            result = result and (ref() is None)
            return result
        run = self.runner(f)
        res = run([])
        assert res

    def test_weakref_to_object_with_finalizer(self):
        import weakref, gc
        class A(object):
            count = 0
        a = A()
        class B(object):
            def __del__(self):
                a.count += 1
        def g():
            b = B()
            return weakref.ref(b)
        def f():
            ref = g()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            result = a.count == 1 and (ref() is None)
            return result
        run = self.runner(f)
        res = run([])
        assert res

    def test_collect_during_collect(self):
        class B(object):
            pass
        b = B()
        b.nextid = 1
        b.num_deleted = 0
        class A(object):
            def __init__(self):
                self.id = b.nextid
                b.nextid += 1
            def __del__(self):
                llop.gc__collect(lltype.Void)
                b.num_deleted += 1
                C()
                C()
        class C(A):
            def __del__(self):
                b.num_deleted += 1
        def f(x, y):
            persistent_a1 = A()
            persistent_a2 = A()
            i = 0
            while i < x:
                i += 1
                a = A()
            persistent_a3 = A()
            persistent_a4 = A()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            b.bla = persistent_a1.id + persistent_a2.id + persistent_a3.id + persistent_a4.id
            return b.num_deleted
        run = self.runner(f, nbargs=2)
        # runs collect recursively 4 times
        res = run([4, 42]) #XXX pure lazyness here too
        assert res == 12

    def test_cloning(self):
        B = lltype.GcStruct('B', ('x', lltype.Signed))
        A = lltype.GcStruct('A', ('b', lltype.Ptr(B)),
                                 ('unused', lltype.Ptr(B)))
        def make(n):
            b = lltype.malloc(B)
            b.x = n
            a = lltype.malloc(A)
            a.b = b
            return a
        def func():
            a1 = make(111)
            # start recording mallocs in a new pool
            oldpool = llop.gc_x_swap_pool(X_POOL_PTR, lltype.nullptr(X_POOL))
            # the following a2 goes into the new list
            a2 = make(222)
            # now put the old pool back and get the new pool
            newpool = llop.gc_x_swap_pool(X_POOL_PTR, oldpool)
            a3 = make(333)
            # clone a2
            a2ref = lltype.cast_opaque_ptr(llmemory.GCREF, a2)
            clonedata = lltype.malloc(X_CLONE)
            clonedata.gcobjectptr = a2ref
            clonedata.pool = newpool
            llop.gc_x_clone(lltype.Void, clonedata)
            a2copyref = clonedata.gcobjectptr
            a2copy = lltype.cast_opaque_ptr(lltype.Ptr(A), a2copyref)
            a2copy.b.x = 444
            return a1.b.x * 1000000 + a2.b.x * 1000 + a3.b.x

        run = self.runner(func)
        res = run([])
        assert res == 111222333

    def test_cloning_varsize(self):
        B = lltype.GcStruct('B', ('x', lltype.Signed))
        A = lltype.GcStruct('A', ('b', lltype.Ptr(B)),
                                 ('more', lltype.Array(lltype.Ptr(B))))
        def make(n):
            b = lltype.malloc(B)
            b.x = n
            a = lltype.malloc(A, 2)
            a.b = b
            a.more[0] = lltype.malloc(B)
            a.more[0].x = n*10
            a.more[1] = lltype.malloc(B)
            a.more[1].x = n*10+1
            return a
        def func():
            oldpool = llop.gc_x_swap_pool(X_POOL_PTR, lltype.nullptr(X_POOL))
            a2 = make(22)
            newpool = llop.gc_x_swap_pool(X_POOL_PTR, oldpool)
            # clone a2
            a2ref = lltype.cast_opaque_ptr(llmemory.GCREF, a2)
            clonedata = lltype.malloc(X_CLONE)
            clonedata.gcobjectptr = a2ref
            clonedata.pool = newpool
            llop.gc_x_clone(lltype.Void, clonedata)
            a2copyref = clonedata.gcobjectptr
            a2copy = lltype.cast_opaque_ptr(lltype.Ptr(A), a2copyref)
            a2copy.b.x = 44
            a2copy.more[0].x = 440
            a2copy.more[1].x = 441
            return a2.b.x * 1000000 + a2.more[0].x * 1000 + a2.more[1].x

        run = self.runner(func)
        res = run([])
        assert res == 22220221

    def test_cloning_highlevel(self):
        from pypy.rlib import rgc
        class A:
            pass
        class B(A):
            pass
        def func(n, dummy):
            if n > 5:
                x = A()
            else:
                x = B()
                x.bvalue = 123
            x.next = A()
            x.next.next = x
            y, newpool = rgc.gc_clone(x, None)
            assert y is not x
            assert y.next is not x
            assert y is not x.next
            assert y.next is not x.next
            assert y is not y.next
            assert y is y.next.next
            if isinstance(y, B):
                assert n <= 5
                assert y.bvalue == 123
            else:
                assert n > 5
            return 1

        run = self.runner(func, nbargs=2)
        res = run([3, 0])
        assert res == 1
        res = run([7, 0])
        assert res == 1

    def test_cloning_highlevel_varsize(self):
        from pypy.rlib import rgc
        class A:
            pass
        def func(n, dummy):
            lst = [A() for i in range(n)]
            for a in lst:
                a.value = 1
            lst2, newpool = rgc.gc_clone(lst, None)
            for i in range(n):
                a = A()
                a.value = i
                lst.append(a)
                lst[i].value = 4 + i
                lst2[i].value = 7 + i

            n = 0
            for a in lst:
                n = n*10 + a.value
            for a in lst2:
                n = n*10 + a.value
            return n

        run = self.runner(func, nbargs=2)
        res = run([3, 0])
        assert res == 456012789

    def test_tree_cloning(self):
        import os
        # this makes a tree of calls.  Each leaf stores its path (a linked
        # list) in 'result'.  Paths are mutated in-place but the leaves don't
        # see each other's mutations because of x_clone.
        STUFF = lltype.FixedSizeArray(lltype.Signed, 21)
        NODE = lltype.GcForwardReference()
        NODE.become(lltype.GcStruct('node', ('index', lltype.Signed),
                                            ('counter', lltype.Signed),
                                            ('next', lltype.Ptr(NODE)),
                                            ('use_some_space', STUFF)))
        PATHARRAY = lltype.GcArray(lltype.Ptr(NODE))
        clonedata = lltype.malloc(X_CLONE)

        def clone(node):
            # that's for testing if the test is correct...
            if not node:
                return node
            newnode = lltype.malloc(NODE)
            newnode.index = node.index
            newnode.counter = node.counter
            newnode.next = clone(node.next)
            return newnode

        def do_call(result, path, index, remaining_depth):
            # clone the while path
            clonedata.gcobjectptr = lltype.cast_opaque_ptr(llmemory.GCREF,
                                                           path)
            clonedata.pool = lltype.nullptr(X_POOL)
            llop.gc_x_clone(lltype.Void, clonedata)
            # install the new pool as the current one
            parentpool = llop.gc_x_swap_pool(X_POOL_PTR, clonedata.pool)
            path = lltype.cast_opaque_ptr(lltype.Ptr(NODE),
                                          clonedata.gcobjectptr)

            # The above should have the same effect as:
            #    path = clone(path)

            # bump all the path node counters by one
            p = path
            while p:
                p.counter += 1
                p = p.next

            if remaining_depth == 0:
                llop.debug_print(lltype.Void, "setting", index, "with", path)
                result[index] = path   # leaf
            else:
                node = lltype.malloc(NODE)
                node.index = index * 2
                node.counter = 0
                node.next = path
                do_call(result, node, index * 2, remaining_depth - 1)
                node.index += 1    # mutation!
                do_call(result, node, index * 2 + 1, remaining_depth - 1)

            # restore the parent pool
            llop.gc_x_swap_pool(X_POOL_PTR, parentpool)

        def check(path, index, level, depth):
            if level == depth:
                assert index == 0
                assert not path
            else:
                assert path.index == index
                assert path.counter == level + 1
                check(path.next, index >> 1, level + 1, depth)

        def func(depth, dummy):
            result = lltype.malloc(PATHARRAY, 1 << depth)
            os.write(2, 'building tree... ')
            do_call(result, lltype.nullptr(NODE), 0, depth)
            os.write(2, 'checking tree... ')
            #from pypy.rpython.lltypesystem.lloperation import llop
            #llop.debug_view(lltype.Void, result,
            #                llop.gc_x_size_header(lltype.Signed))
            for i in range(1 << depth):
                check(result[i], i, 0, depth)
            os.write(2, 'ok\n')
            return 1
        run = self.runner(func, nbargs=2)
        res = run([3, 0])
        assert res == 1

    def test_interior_ptrs(self):
        from pypy.rpython.lltypesystem.lltype import Struct, GcStruct, GcArray
        from pypy.rpython.lltypesystem.lltype import Array, Signed, malloc

        S1 = Struct("S1", ('x', Signed))
        T1 = GcStruct("T1", ('s', S1))
        def f1():
            t = malloc(T1)
            t.s.x = 1
            return t.s.x

        S2 = Struct("S2", ('x', Signed))
        T2 = GcArray(S2)
        def f2():
            t = malloc(T2, 1)
            t[0].x = 1
            return t[0].x

        S3 = Struct("S3", ('x', Signed))
        T3 = GcStruct("T3", ('items', Array(S3)))
        def f3():
            t = malloc(T3, 1)
            t.items[0].x = 1
            return t.items[0].x

        S4 = Struct("S4", ('x', Signed))
        T4 = Struct("T4", ('s', S4))
        U4 = GcArray(T4)
        def f4():
            u = malloc(U4, 1)
            u[0].s.x = 1
            return u[0].s.x

        S5 = Struct("S5", ('x', Signed))
        T5 = GcStruct("T5", ('items', Array(S5)))
        def f5():
            t = malloc(T5, 1)
            return len(t.items)

        T6 = GcStruct("T6", ('s', Array(Signed)))
        def f6():
            t = malloc(T6, 1)
            t.s[0] = 1
            return t.s[0]

        def func():
            return (f1() * 100000 +
                    f2() * 10000 +
                    f3() * 1000 +
                    f4() * 100 +
                    f5() * 10 +
                    f6())

        assert func() == 111111
        run = self.runner(func)
        res = run([])
        assert res == 111111


class TestStacklessMarkSweepGC(TestMarkSweepGC):

    stacklessgc = True
    class gcpolicy(gc.StacklessFrameworkGcPolicy):
        class transformerclass(stacklessframework.StacklessFrameworkGCTransformer):
            GC_PARAMS = {'start_heap_size': 4096 }
            root_stack_depth = 200

    def test_x_become(self):
        from pypy.rlib import objectmodel
        S = lltype.GcStruct("S", ('x', lltype.Signed))
        def f():
            x = lltype.malloc(S)
            x.x = 10
            y = lltype.malloc(S)
            y.x = 20
            z = x
            llop.gc_x_become(lltype.Void,
                             llmemory.cast_ptr_to_adr(x),
                             llmemory.cast_ptr_to_adr(y))
            # keep 'y' alive until the x_become() is finished, because in
            # theory it could go away as soon as only its address is present
            objectmodel.keepalive_until_here(y)
            return z.x
        run = self.runner(f)
        res = run([])
        assert res == 20


class TestSemiSpaceGC(TestMarkSweepGC):

    def setup_class(cls):
        py.test.skip("in-progress")

    class gcpolicy(gc.FrameworkGcPolicy):
        class transformerclass(framework.FrameworkGCTransformer):
            from pypy.rpython.memory.gc import SemiSpaceGC as GCClass
            GC_PARAMS = {'space_size': 2048}
            root_stack_depth = 200
