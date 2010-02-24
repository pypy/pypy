""" The tests below don't use translation at all.  They run the GCs by
instantiating them and asking them to allocate memory by calling their
methods directly.  The tests need to maintain by hand what the GC should
see as the list of roots (stack and prebuilt objects).
"""

# XXX VERY INCOMPLETE, low coverage

import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory.gctypelayout import TypeLayoutBuilder

ADDR_ARRAY = lltype.Array(llmemory.Address)
S = lltype.GcForwardReference()
S.become(lltype.GcStruct('S',
                         ('x', lltype.Signed),
                         ('prev', lltype.Ptr(S)),
                         ('next', lltype.Ptr(S))))
RAW = lltype.Struct('RAW', ('p', lltype.Ptr(S)), ('q', lltype.Ptr(S)))
VAR = lltype.GcArray(lltype.Ptr(S))
VARNODE = lltype.GcStruct('VARNODE', ('a', lltype.Ptr(VAR)))


class DirectRootWalker(object):

    def __init__(self, tester):
        self.tester = tester

    def walk_roots(self, collect_stack_root,
                   collect_static_in_prebuilt_nongc,
                   collect_static_in_prebuilt_gc):
        gc = self.tester.gc
        layoutbuilder = self.tester.layoutbuilder
        if collect_static_in_prebuilt_gc:
            for addrofaddr in layoutbuilder.addresses_of_static_ptrs:
                if addrofaddr.address[0]:
                    collect_static_in_prebuilt_gc(gc, addrofaddr)
        if collect_static_in_prebuilt_nongc:
            for addrofaddr in layoutbuilder.addresses_of_static_ptrs_in_nongc:
                if addrofaddr.address[0]:
                    collect_static_in_prebuilt_nongc(gc, addrofaddr)
        if collect_stack_root:
            stackroots = self.tester.stackroots
            a = lltype.malloc(ADDR_ARRAY, len(stackroots), flavor='raw')
            for i in range(len(a)):
                a[i] = llmemory.cast_ptr_to_adr(stackroots[i])
            a_base = lltype.direct_arrayitems(a)
            for i in range(len(a)):
                ai = lltype.direct_ptradd(a_base, i)
                collect_stack_root(gc, llmemory.cast_ptr_to_adr(ai))
            for i in range(len(a)):
                PTRTYPE = lltype.typeOf(stackroots[i])
                stackroots[i] = llmemory.cast_adr_to_ptr(a[i], PTRTYPE)
            lltype.free(a, flavor='raw')

    def _walk_prebuilt_gc(self, callback):
        pass


class DirectGCTest(object):
    GC_PARAMS = {}

    def setup_method(self, meth):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True).translation
        self.stackroots = []
        self.gc = self.GCClass(config, **self.GC_PARAMS)
        self.gc.DEBUG = True
        self.rootwalker = DirectRootWalker(self)
        self.gc.set_root_walker(self.rootwalker)
        self.layoutbuilder = TypeLayoutBuilder(self.GCClass)
        self.get_type_id = self.layoutbuilder.get_type_id
        self.layoutbuilder.initialize_gc_query_function(self.gc)
        self.gc.setup()

    def consider_constant(self, p):
        obj = p._obj
        TYPE = lltype.typeOf(obj)
        self.layoutbuilder.consider_constant(TYPE, obj, self.gc)

    def write(self, p, fieldname, newvalue):
        if self.gc.needs_write_barrier:
            newaddr = llmemory.cast_ptr_to_adr(newvalue)
            addr_struct = llmemory.cast_ptr_to_adr(p)
            self.gc.write_barrier(newaddr, addr_struct)
        setattr(p, fieldname, newvalue)

    def writearray(self, p, index, newvalue):
        if self.gc.needs_write_barrier:
            newaddr = llmemory.cast_ptr_to_adr(newvalue)
            addr_struct = llmemory.cast_ptr_to_adr(p)
            self.gc.write_barrier(newaddr, addr_struct)
        p[index] = newvalue

    def malloc(self, TYPE, n=None):
        addr = self.gc.malloc(self.get_type_id(TYPE), n)
        return llmemory.cast_adr_to_ptr(addr, lltype.Ptr(TYPE))

    def test_simple(self):
        p = self.malloc(S)
        p.x = 5
        self.stackroots.append(p)
        self.gc.collect()
        p = self.stackroots[0]
        assert p.x == 5

    def test_missing_stack_root(self):
        p = self.malloc(S)
        p.x = 5
        self.gc.collect()    # 'p' should go away
        py.test.raises(RuntimeError, 'p.x')

    def test_prebuilt_gc(self):
        k = lltype.malloc(S, immortal=True)
        k.x = 42
        self.consider_constant(k)
        self.write(k, 'next', self.malloc(S))
        k.next.x = 43
        self.write(k.next, 'next', self.malloc(S))
        k.next.next.x = 44
        self.gc.collect()
        assert k.x == 42
        assert k.next.x == 43
        assert k.next.next.x == 44

    def test_prebuilt_nongc(self):
        raw = lltype.malloc(RAW, immortal=True)
        self.consider_constant(raw)
        raw.p = self.malloc(S)
        raw.p.x = 43
        raw.q = self.malloc(S)
        raw.q.x = 44
        self.gc.collect()
        assert raw.p.x == 43
        assert raw.q.x == 44

    def test_many_objects(self):

        def alloc2(i):
            a1 = self.malloc(S)
            a1.x = i
            self.stackroots.append(a1)
            a2 = self.malloc(S)
            a1 = self.stackroots.pop()
            a2.x = i + 1000
            return a1, a2

        def growloop(loop, a1, a2):
            self.write(a1, 'prev', loop.prev)
            self.write(a1.prev, 'next', a1)
            self.write(a1, 'next', loop)
            self.write(loop, 'prev', a1)
            self.write(a2, 'prev', loop)
            self.write(a2, 'next', loop.next)
            self.write(a2.next, 'prev', a2)
            self.write(loop, 'next', a2)

        def newloop():
            p = self.malloc(S)
            p.next = p          # initializing stores, no write barrier
            p.prev = p
            return p

        # a loop attached to a stack root
        self.stackroots.append(newloop())

        # another loop attached to a prebuilt gc node
        k = lltype.malloc(S, immortal=True)
        k.next = k
        k.prev = k
        self.consider_constant(k)

        # a third loop attached to a prebuilt nongc
        raw = lltype.malloc(RAW, immortal=True)
        self.consider_constant(raw)
        raw.p = newloop()

        # run!
        for i in range(100):
            a1, a2 = alloc2(i)
            growloop(self.stackroots[0], a1, a2)
            a1, a2 = alloc2(i)
            growloop(k, a1, a2)
            a1, a2 = alloc2(i)
            growloop(raw.p, a1, a2)

    def test_varsized_from_stack(self):
        expected = {}
        def verify():
            for (index, index2), value in expected.items():
                assert self.stackroots[index][index2].x == value
        x = 0
        for i in range(40):
            self.stackroots.append(self.malloc(VAR, i))
            for j in range(5):
                p = self.malloc(S)
                p.x = x
                index = x % len(self.stackroots)
                if index > 0:
                    index2 = (x / len(self.stackroots)) % index
                    a = self.stackroots[index]
                    assert len(a) == index
                    self.writearray(a, index2, p)
                    expected[index, index2] = x
                x += 1291
        verify()
        self.gc.collect()
        verify()
        self.gc.collect()
        verify()

    def test_varsized_from_prebuilt_gc(self):
        expected = {}
        def verify():
            for (index, index2), value in expected.items():
                assert prebuilt[index].a[index2].x == value
        x = 0
        prebuilt = [lltype.malloc(VARNODE, immortal=True, zero=True)
                    for i in range(40)]
        for node in prebuilt:
            self.consider_constant(node)
        for i in range(len(prebuilt)):
            self.write(prebuilt[i], 'a', self.malloc(VAR, i))
            for j in range(20):
                p = self.malloc(S)
                p.x = x
                index = x % (i+1)
                if index > 0:
                    index2 = (x / (i+1)) % index
                    a = prebuilt[index].a
                    assert len(a) == index
                    self.writearray(a, index2, p)
                    expected[index, index2] = x
                x += 1291
        verify()
        self.gc.collect()
        verify()
        self.gc.collect()
        verify()

    def test_id(self):
        ids = {}
        def allocate_bunch(count=50):
            base = len(self.stackroots)
            for i in range(count):
                p = self.malloc(S)
                self.stackroots.append(p)
            for i in range(count):
                j = base + (i*1291) % count
                pid = self.gc.id(self.stackroots[j])
                assert isinstance(pid, int)
                ids[j] = pid
        def verify():
            for j, expected in ids.items():
                assert self.gc.id(self.stackroots[j]) == expected
        allocate_bunch(5)
        verify()
        allocate_bunch(75)
        verify()
        allocate_bunch(5)
        verify()
        self.gc.collect()
        verify()
        self.gc.collect()
        verify()

    def test_identityhash(self):
        # a "does not crash" kind of test
        p_const = lltype.malloc(S, immortal=True)
        self.consider_constant(p_const)
        # (1) p is in the nursery
        self.gc.collect()
        p = self.malloc(S)
        hash = self.gc.identityhash(p)
        print hash
        assert isinstance(hash, (int, long))
        assert hash == self.gc.identityhash(p)
        self.stackroots.append(p)
        for i in range(6):
            self.gc.collect()
            assert hash == self.gc.identityhash(self.stackroots[-1])
        self.stackroots.pop()
        # (2) p is an older object
        p = self.malloc(S)
        self.stackroots.append(p)
        self.gc.collect()
        hash = self.gc.identityhash(self.stackroots[-1])
        print hash
        assert isinstance(hash, (int, long))
        for i in range(6):
            self.gc.collect()
            assert hash == self.gc.identityhash(self.stackroots[-1])
        self.stackroots.pop()
        # (3) p is a gen3 object (for hybrid)
        p = self.malloc(S)
        self.stackroots.append(p)
        for i in range(6):
            self.gc.collect()
        hash = self.gc.identityhash(self.stackroots[-1])
        print hash
        assert isinstance(hash, (int, long))
        for i in range(2):
            self.gc.collect()
            assert hash == self.gc.identityhash(self.stackroots[-1])
        self.stackroots.pop()
        # (4) p is a prebuilt object
        hash = self.gc.identityhash(p_const)
        print hash
        assert isinstance(hash, (int, long))
        assert hash == self.gc.identityhash(p_const)


class TestSemiSpaceGC(DirectGCTest):
    from pypy.rpython.memory.gc.semispace import SemiSpaceGC as GCClass

    def test_shrink_array(self):
        S1 = lltype.GcStruct('S1', ('h', lltype.Char),
                                   ('v', lltype.Array(lltype.Char)))
        p1 = self.malloc(S1, 2)
        p1.h = '?'
        for i in range(2):
            p1.v[i] = chr(50 + i)
        addr = llmemory.cast_ptr_to_adr(p1)
        ok = self.gc.shrink_array(addr, 1)
        assert ok
        assert p1.h == '?'
        assert len(p1.v) == 1
        for i in range(1):
            assert p1.v[i] == chr(50 + i)


class TestGenerationGC(TestSemiSpaceGC):
    from pypy.rpython.memory.gc.generation import GenerationGC as GCClass

    def test_collect_gen(self):
        gc = self.gc
        old_semispace_collect = gc.semispace_collect
        old_collect_nursery = gc.collect_nursery
        calls = []
        def semispace_collect():
            calls.append('semispace_collect')
            return old_semispace_collect()
        def collect_nursery():
            calls.append('collect_nursery')
            return old_collect_nursery()
        gc.collect_nursery = collect_nursery
        gc.semispace_collect = semispace_collect

        gc.collect()
        assert calls == ['semispace_collect']
        calls = []

        gc.collect(0)
        assert calls == ['collect_nursery']
        calls = []

        gc.collect(1)
        assert calls == ['semispace_collect']
        calls = []

        gc.collect(9)
        assert calls == ['semispace_collect']
        calls = []

    def test_assume_young_pointers(self):
        s0 = lltype.malloc(S, immortal=True)
        self.consider_constant(s0)
        s = self.malloc(S)
        s.x = 1
        s0.next = s
        self.gc.assume_young_pointers(llmemory.cast_ptr_to_adr(s0))

        self.gc.collect(0)

        assert s0.next.x == 1


class TestHybridGC(TestGenerationGC):
    from pypy.rpython.memory.gc.hybrid import HybridGC as GCClass

    GC_PARAMS = {'space_size': 192,
                 'min_nursery_size': 48,
                 'nursery_size': 48,
                 'large_object': 12,
                 'large_object_gcptrs': 12,
                 'generation3_collect_threshold': 5,
                 }

    def test_collect_gen(self):
        gc = self.gc
        old_semispace_collect = gc.semispace_collect
        old_collect_nursery = gc.collect_nursery
        calls = []
        def semispace_collect():
            gen3 = gc.is_collecting_gen3()
            calls.append(('semispace_collect', gen3))
            return old_semispace_collect()
        def collect_nursery():
            calls.append('collect_nursery')
            return old_collect_nursery()
        gc.collect_nursery = collect_nursery
        gc.semispace_collect = semispace_collect

        gc.collect()
        assert calls == [('semispace_collect', True)]
        calls = []

        gc.collect(0)
        assert calls == ['collect_nursery']
        calls = []

        gc.collect(1)
        assert calls == [('semispace_collect', False)]
        calls = []

        gc.collect(2)
        assert calls == [('semispace_collect', True)]
        calls = []

        gc.collect(9)
        assert calls == [('semispace_collect', True)]
        calls = []

    def test_identityhash(self):
        py.test.skip("does not support raw_mallocs(sizeof(S)+sizeof(hash))")


class TestMarkCompactGC(DirectGCTest):
    from pypy.rpython.memory.gc.markcompact import MarkCompactGC as GCClass

