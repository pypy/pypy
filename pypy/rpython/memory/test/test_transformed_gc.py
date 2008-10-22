import py
import sys
import struct
from pypy.translator.c import gc
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory.gctransform import framework
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.memory.gc.marksweep import X_CLONE, X_POOL, X_POOL_PTR
from pypy.rlib.objectmodel import compute_unique_id
from pypy.rlib.debug import ll_assert
from pypy import conftest
from pypy.rlib.rstring import StringBuilder

INT_SIZE = struct.calcsize("i")   # only for estimates


def rtype(func, inputtypes, specialize=True, gcname='ref', stacklessgc=False,
          backendopt=False, **extraconfigopts):
    from pypy.translator.translator import TranslationContext
    t = TranslationContext()
    # XXX XXX XXX mess
    t.config.translation.gc = gcname
    if stacklessgc:
        t.config.translation.gcrootfinder = "stackless"
    t.config.set(**extraconfigopts)
    t.buildannotator().build_types(func, inputtypes)
    if specialize:
        t.buildrtyper().specialize()
    if backendopt:
        from pypy.translator.backendopt.all import backend_optimizations
        backend_optimizations(t)
    if conftest.option.view:
        t.viewcg()
    return t

class GCTest(object):
    gcpolicy = None
    stacklessgc = False
    GC_CAN_MOVE = False
    GC_CANNOT_MALLOC_NONMOVABLE = False

    def runner(self, f, nbargs=0, statistics=False, transformer=False,
               **extraconfigopts):
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
                                        stacklessgc=self.stacklessgc,
                                        **extraconfigopts)
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
        elif transformer:
            return run, db.gctransformer
        else:
            return run
        
class GenericGCTests(GCTest):

    def heap_usage(self, statistics):
        try:
            GCClass = self.gcpolicy.transformerclass.GCClass
        except AttributeError:
            from pypy.rpython.memory.gc.marksweep import MarkSweepGC as GCClass
        if hasattr(GCClass, 'STAT_HEAP_USAGE'):
            return statistics(GCClass.STAT_HEAP_USAGE)
        else:
            return -1     # xxx

    def test_instances(self):
        class A(object):
            pass
        class B(A):
            def __init__(self, something):
                self.something = something
        def malloc_a_lot():
            i = 0
            first = None
            while i < 10:
                i += 1
                a = somea = A()
                a.last = first
                first = a
                j = 0
                while j < 30:
                    b = B(somea)
                    b.last = first
                    j += 1
            return 0
        run, statistics = self.runner(malloc_a_lot, statistics=True)
        run([])
        heap_size = self.heap_usage(statistics)


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

    def test_nongc_static_root(self):
        from pypy.rpython.lltypesystem import lltype
        T1 = lltype.GcStruct("C", ('x', lltype.Signed))
        T2 = lltype.Struct("C", ('p', lltype.Ptr(T1)))
        static = lltype.malloc(T2, immortal=True)
        def f():
            t1 = lltype.malloc(T1)
            t1.x = 42
            static.p = t1
            llop.gc__collect(lltype.Void)
            return static.p.x
        run = self.runner(f, nbargs=0)
        res = run([])
        assert res == 42

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
        b.num_deleted_c = 0
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
                b.num_deleted_c += 1
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
            print b.num_deleted_c
            return b.num_deleted
        run = self.runner(f, nbargs=2)
        # runs collect recursively 4 times
        res = run([4, 42]) #XXX pure lazyness here too
        assert res == 12

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

    def test_id(self):
        class A(object):
            pass
        a1 = A()
        def func():
            a2 = A()
            a3 = A()
            id1 = compute_unique_id(a1)
            id2 = compute_unique_id(a2)
            id3 = compute_unique_id(a3)
            llop.gc__collect(lltype.Void)
            error = 0
            if id1 != compute_unique_id(a1): error += 1
            if id2 != compute_unique_id(a2): error += 2
            if id3 != compute_unique_id(a3): error += 4
            return error
        run = self.runner(func)
        res = run([])
        assert res == 0

    def test_can_move(self):
        TP = lltype.GcArray(lltype.Float)
        def func():
            from pypy.rlib import rgc
            return rgc.can_move(lltype.malloc(TP, 1))
        run = self.runner(func)
        res = run([])
        assert res == self.GC_CAN_MOVE

    def test_malloc_nonmovable(self):
        TP = lltype.GcArray(lltype.Char)
        def func():
            #try:
            from pypy.rlib import rgc
            a = rgc.malloc_nonmovable(TP, 3)
            rgc.collect()
            if a:
                assert not rgc.can_move(a)
                return 0
            return 1
            #except Exception, e:
            #    return 2

        run = self.runner(func)
        assert int(self.GC_CANNOT_MALLOC_NONMOVABLE) == run([])

    def test_malloc_nonmovable_fixsize(self):
        S = lltype.GcStruct('S', ('x', lltype.Float))
        TP = lltype.GcStruct('T', ('s', lltype.Ptr(S)))
        def func():
            try:
                from pypy.rlib import rgc
                a = rgc.malloc_nonmovable(TP)
                rgc.collect()
                if a:
                    assert not rgc.can_move(a)
                    return 0
                return 1
            except Exception, e:
                return 2

        run = self.runner(func)
        assert run([]) == int(self.GC_CANNOT_MALLOC_NONMOVABLE)

    def test_resizable_buffer(self):
        from pypy.rpython.lltypesystem.rstr import STR
        from pypy.rpython.annlowlevel import hlstr
        from pypy.rlib import rgc

        def f():
            ptr = rgc.resizable_buffer_of_shape(STR, 2)
            ptr.chars[0] = 'a'
            ptr = rgc.resize_buffer(ptr, 1, 200)
            ptr.chars[1] = 'b'
            return hlstr(rgc.finish_building_buffer(ptr, 2)) == "ab"

        run = self.runner(f)
        assert run([]) == 1

    def test_string_builder_over_allocation(self):
        import gc
        def fn():
            s = StringBuilder(4)
            s.append("abcd")
            s.append("defg")
            s.append("rty")
            s.append_multiple_char('y', 1000)
            gc.collect()
            s.append_multiple_char('y', 1000)
            res = s.build()[1000]
            gc.collect()
            return res
        fn = self.runner(fn)
        res = fn([])
        assert res == 'y'

class GenericMovingGCTests(GenericGCTests):
    GC_CAN_MOVE = True
    GC_CANNOT_MALLOC_NONMOVABLE = True

    def test_many_ids(self):
        py.test.skip("fails for bad reasons in lltype.py :-(")
        class A(object):
            pass
        def f():
            from pypy.rpython.lltypesystem import lltype, rffi
            alist = [A() for i in range(50)]
            idarray = lltype.malloc(rffi.INTP.TO, len(alist), flavor='raw')
            # Compute the id of all the elements of the list.  The goal is
            # to not allocate memory, so that if the GC needs memory to
            # remember the ids, it will trigger some collections itself
            i = 0
            while i < len(alist):
                idarray[i] = compute_unique_id(alist[i])
                i += 1
            j = 0
            while j < 2:
                if j == 1:     # allocate some stuff between the two iterations
                    [A() for i in range(20)]
                i = 0
                while i < len(alist):
                    assert idarray[i] == compute_unique_id(alist[i])
                    i += 1
                j += 1
            lltype.free(idarray, flavor='raw')
        run = self.runner(f)
        run([])

class TestMarkSweepGC(GenericGCTests):
    gcname = "marksweep"
    class gcpolicy(gc.FrameworkGcPolicy):
        class transformerclass(framework.FrameworkGCTransformer):
            GC_PARAMS = {'start_heap_size': 4096 }
            root_stack_depth = 200


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


class TestPrintingGC(GenericGCTests):
    gcname = "statistics"

    class gcpolicy(gc.FrameworkGcPolicy):
        class transformerclass(framework.FrameworkGCTransformer):
            from pypy.rpython.memory.gc.marksweep import PrintingMarkSweepGC as GCClass
            GC_PARAMS = {'start_heap_size': 4096 }
            root_stack_depth = 200

class TestSemiSpaceGC(GenericMovingGCTests):
    gcname = "semispace"

    class gcpolicy(gc.FrameworkGcPolicy):
        class transformerclass(framework.FrameworkGCTransformer):
            from pypy.rpython.memory.gc.semispace import SemiSpaceGC as GCClass
            GC_PARAMS = {'space_size': 2048}
            root_stack_depth = 200

class TestMarkCompactGC(GenericMovingGCTests):
    gcname = 'markcompact'

    class gcpolicy(gc.FrameworkGcPolicy):
        class transformerclass(framework.FrameworkGCTransformer):
            from pypy.rpython.memory.gc.markcompact import MarkCompactGC as GCClass
            GC_PARAMS = {'space_size': 2048}
            root_stack_depth = 200

class TestGenerationGC(GenericMovingGCTests):
    gcname = "generation"

    class gcpolicy(gc.FrameworkGcPolicy):
        class transformerclass(framework.FrameworkGCTransformer):
            from pypy.rpython.memory.gc.generation import GenerationGC as \
                                                          GCClass
            GC_PARAMS = {'space_size': 2048,
                         'nursery_size': 128}
            root_stack_depth = 200

    def test_weakref_across_minor_collection(self):
        import weakref
        class A:
            pass
        def f():
            x = 20    # for GenerationGC, enough for a minor collection
            a = A()
            a.foo = x
            ref = weakref.ref(a)
            all = [None] * x
            i = 0
            while i < x:
                all[i] = [i] * i
                i += 1
            assert ref() is a
            llop.gc__collect(lltype.Void)
            assert ref() is a
            return a.foo + len(all)
        run = self.runner(f)
        res = run([])
        assert res == 20 + 20

    def test_nongc_static_root_minor_collect(self):
        from pypy.rpython.lltypesystem import lltype
        T1 = lltype.GcStruct("C", ('x', lltype.Signed))
        T2 = lltype.Struct("C", ('p', lltype.Ptr(T1)))
        static = lltype.malloc(T2, immortal=True)
        def f():
            t1 = lltype.malloc(T1)
            t1.x = 42
            static.p = t1
            x = 20
            all = [None] * x
            i = 0
            while i < x: # enough to cause a minor collect
                all[i] = [i] * i
                i += 1
            i = static.p.x
            llop.gc__collect(lltype.Void)
            return static.p.x + i
        run = self.runner(f, nbargs=0)
        res = run([])
        assert res == 84


    def test_static_root_minor_collect(self):
        from pypy.rpython.lltypesystem import lltype
        class A:
            pass
        class B:
            pass
        static = A()
        static.p = None
        def f():
            t1 = B()
            t1.x = 42
            static.p = t1
            x = 20
            all = [None] * x
            i = 0
            while i < x: # enough to cause a minor collect
                all[i] = [i] * i
                i += 1
            i = static.p.x
            llop.gc__collect(lltype.Void)
            return static.p.x + i
        run = self.runner(f, nbargs=0)
        res = run([])
        assert res == 84


    def test_many_weakrefs(self):
        # test for the case where allocating the weakref itself triggers
        # a collection
        import weakref
        class A:
            pass
        def f():
            a = A()
            i = 0
            while i < 17:
                ref = weakref.ref(a)
                assert ref() is a
                i += 1
        run = self.runner(f, nbargs=0)
        run([])

    def test_immutable_to_old_promotion(self):
        T_CHILD = lltype.Ptr(lltype.GcStruct('Child', ('field', lltype.Signed)))
        T_PARENT = lltype.Ptr(lltype.GcStruct('Parent', ('sub', T_CHILD)))
        child = lltype.malloc(T_CHILD.TO)
        child2 = lltype.malloc(T_CHILD.TO)
        parent = lltype.malloc(T_PARENT.TO)
        parent2 = lltype.malloc(T_PARENT.TO)
        parent.sub = child
        child.field = 3
        parent2.sub = child2
        child2.field = 8

        T_ALL = lltype.Ptr(lltype.GcArray(T_PARENT))
        all = lltype.malloc(T_ALL.TO, 2)
        all[0] = parent
        all[1] = parent2

        def f(x, y):
            res = all[x]
            #all[x] = lltype.nullptr(T_PARENT.TO)
            return res.sub.field

        run, transformer = self.runner(f, nbargs=2, transformer=True)
        run([1, 4])
        if not transformer.GCClass.prebuilt_gc_objects_are_static_roots:
            assert len(transformer.layoutbuilder.addresses_of_static_ptrs) == 0
        else:
            assert len(transformer.layoutbuilder.addresses_of_static_ptrs) >= 4
        # NB. Remember that the number above does not count
        # the number of prebuilt GC objects, but the number of locations
        # within prebuilt GC objects that are of type Ptr(Gc).
        # At the moment we get additional_roots_sources == 6:
        #  * all[0]
        #  * all[1]
        #  * parent.sub
        #  * parent2.sub
        #  * the GcArray pointer from gc.wr_to_objects_with_id
        #  * the GcArray pointer from gc.object_id_dict.

class TestGenerationalNoFullCollectGC(GCTest):
    # test that nursery is doing its job and that no full collection
    # is needed when most allocated objects die quickly

    gcname = "generation"

    class gcpolicy(gc.FrameworkGcPolicy):
        class transformerclass(framework.FrameworkGCTransformer):
            from pypy.rpython.memory.gc.generation import GenerationGC
            class GCClass(GenerationGC):
                __ready = False
                def setup(self):
                    from pypy.rpython.memory.gc.generation import GenerationGC
                    GenerationGC.setup(self)
                    self.__ready = True
                def semispace_collect(self, size_changing=False):
                    ll_assert(not self.__ready,
                              "no full collect should occur in this test")
            GC_PARAMS = {'space_size': 2048,
                         'nursery_size': 512}
            root_stack_depth = 200

    def test_working_nursery(self):
        def f():
            total = 0
            i = 0
            while i < 40:
                lst = []
                j = 0
                while j < 5:
                    lst.append(i*j)
                    j += 1
                total += len(lst)
                i += 1
            return total
        run = self.runner(f, nbargs=0)
        res = run([])
        assert res == 40 * 5

class TestHybridGC(TestGenerationGC):
    gcname = "hybrid"
    GC_CANNOT_MALLOC_NONMOVABLE = False

    class gcpolicy(gc.FrameworkGcPolicy):
        class transformerclass(framework.FrameworkGCTransformer):
            from pypy.rpython.memory.gc.hybrid import HybridGC as GCClass
            GC_PARAMS = {'space_size': 2048,
                         'nursery_size': 128,
                         'large_object': 32}
            root_stack_depth = 200

    def test_ref_from_rawmalloced_to_regular(self):
        import gc
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        A = lltype.GcStruct('A', ('p', lltype.Ptr(S)),
                                 ('a', lltype.Array(lltype.Char)))
        def setup(j):
            p = lltype.malloc(S)
            p.x = j*2
            lst = lltype.malloc(A, j)
            # the following line generates a write_barrier call at the moment,
            # which is important because the 'lst' can be allocated directly
            # in generation 2.  This can only occur with varsized mallocs.
            lst.p = p
            return lst
        def f(i, j):
            lst = setup(j)
            gc.collect()
            return lst.p.x
        run = self.runner(f, nbargs=2)
        res = run([100, 100])
        assert res == 200

    def test_malloc_nonmovable_fixsize(self):
        py.test.skip("not supported")
