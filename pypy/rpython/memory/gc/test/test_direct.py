""" The tests below don't use translation at all.  They run the GCs by
instantiating them and asking them to allocate memory by calling their
methods directly.  The tests need to maintain by hand what the GC should
see as the list of roots (stack and prebuilt objects).
"""

# XXX VERY INCOMPLETE, low coverage

import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory.gctypelayout import TypeLayoutBuilder
from pypy.rlib.rarithmetic import LONG_BIT

WORD = LONG_BIT // 8

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


class BaseDirectGCTest(object):
    GC_PARAMS = {}

    def setup_method(self, meth):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True).translation
        self.stackroots = []
        GC_PARAMS = self.GC_PARAMS.copy()
        if hasattr(meth, 'GC_PARAMS'):
            GC_PARAMS.update(meth.GC_PARAMS)
        GC_PARAMS['translated_to_c'] = False
        self.gc = self.GCClass(config, **GC_PARAMS)
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
            if hasattr(self.gc, 'write_barrier_from_array'):
                self.gc.write_barrier_from_array(newaddr, addr_struct, index)
            else:
                self.gc.write_barrier(newaddr, addr_struct)
        p[index] = newvalue

    def malloc(self, TYPE, n=None):
        addr = self.gc.malloc(self.get_type_id(TYPE), n, zero=True)
        return llmemory.cast_adr_to_ptr(addr, lltype.Ptr(TYPE))


class DirectGCTest(BaseDirectGCTest):

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
        # (5) p is actually moving (for the markcompact gc)
        p0 = self.malloc(S)
        self.stackroots.append(p0)
        p = self.malloc(S)
        self.stackroots.append(p)
        hash = self.gc.identityhash(p)
        self.stackroots.pop(-2)
        self.gc.collect()     # p0 goes away, p shifts left
        assert hash == self.gc.identityhash(self.stackroots[-1])
        self.gc.collect()
        assert hash == self.gc.identityhash(self.stackroots[-1])
        self.stackroots.pop()
        # (6) ask for the hash of varsized objects, larger and larger
        for i in range(10):
            self.gc.collect()
            p = self.malloc(VAR, i)
            self.stackroots.append(p)
            hash = self.gc.identityhash(p)
            self.gc.collect()
            assert hash == self.gc.identityhash(self.stackroots[-1])
            self.stackroots.pop()
        # (7) the same, but the objects are dying young
        for i in range(10):
            self.gc.collect()
            p = self.malloc(VAR, i)
            self.stackroots.append(p)
            hash1 = self.gc.identityhash(p)
            hash2 = self.gc.identityhash(p)
            assert hash1 == hash2
            self.stackroots.pop()

    def test_memory_alignment(self):
        A1 = lltype.GcArray(lltype.Char)
        for i in range(50):
            p1 = self.malloc(A1, i)
            if i:
                p1[i-1] = chr(i)
            self.stackroots.append(p1)
        self.gc.collect()
        for i in range(1, 50):
            p = self.stackroots[-50+i]
            assert p[i-1] == chr(i)

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

    GC_PARAMS = {'space_size': 48*WORD,
                 'min_nursery_size': 12*WORD,
                 'nursery_size': 12*WORD,
                 'large_object': 3*WORD,
                 'large_object_gcptrs': 3*WORD,
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

    def test_many_objects(self):
        DirectGCTest.test_many_objects(self)
    test_many_objects.GC_PARAMS = {'space_size': 3 * 1024 * WORD}

    def test_varsized_from_stack(self):
        DirectGCTest.test_varsized_from_stack(self)
    test_varsized_from_stack.GC_PARAMS = {'space_size': 2 * 1024 * WORD}

    def test_varsized_from_prebuilt_gc(self):
        DirectGCTest.test_varsized_from_prebuilt_gc(self)
    test_varsized_from_prebuilt_gc.GC_PARAMS = {'space_size': 3 * 1024 * WORD}


class TestMiniMarkGCSimple(DirectGCTest):
    from pypy.rpython.memory.gc.minimark import MiniMarkGC as GCClass
    from pypy.rpython.memory.gc.minimark import SimpleArenaCollection
    # test the GC itself, providing a simple class for ArenaCollection
    GC_PARAMS = {'ArenaCollectionClass': SimpleArenaCollection}

    def test_card_marker(self):
        for arraylength in (range(4, 17)
                            + [69]      # 3 bytes
                            + [300]):   # 10 bytes
            print 'array length:', arraylength
            nums = {}
            a = self.malloc(VAR, arraylength)
            self.stackroots.append(a)
            for i in range(50):
                p = self.malloc(S)
                p.x = -i
                a = self.stackroots[-1]
                index = (i*i) % arraylength
                self.writearray(a, index, p)
                nums[index] = p.x
                #
                for index, expected_x in nums.items():
                    assert a[index].x == expected_x
            self.stackroots.pop()
    test_card_marker.GC_PARAMS = {"card_page_indices": 4}

    def test_writebarrier_before_copy(self):
        from pypy.rpython.memory.gc import minimark
        largeobj_size =  self.gc.nonlarge_max + 1
        p_src = self.malloc(VAR, largeobj_size)
        p_dst = self.malloc(VAR, largeobj_size)
        # make them old
        self.stackroots.append(p_src)
        self.stackroots.append(p_dst)
        self.gc.collect()
        p_dst = self.stackroots.pop()
        p_src = self.stackroots.pop()
        #
        addr_src = llmemory.cast_ptr_to_adr(p_src)
        addr_dst = llmemory.cast_ptr_to_adr(p_dst)
        hdr_src = self.gc.header(addr_src)
        hdr_dst = self.gc.header(addr_dst)
        #
        assert hdr_src.tid & minimark.GCFLAG_NO_YOUNG_PTRS
        assert hdr_dst.tid & minimark.GCFLAG_NO_YOUNG_PTRS
        #
        res = self.gc.writebarrier_before_copy(addr_src, addr_dst)
        assert res
        assert hdr_dst.tid & minimark.GCFLAG_NO_YOUNG_PTRS
        #
        hdr_src.tid &= ~minimark.GCFLAG_NO_YOUNG_PTRS  # pretend we have young ptrs
        res = self.gc.writebarrier_before_copy(addr_src, addr_dst)
        assert res # we optimized it
        assert hdr_dst.tid & minimark.GCFLAG_NO_YOUNG_PTRS == 0 # and we copied the flag
        #
        # in this case, we have cards, so GCFLAG_NO_YOUNG_PTRS is set (because
        # cards takes precedence over it)
        hdr_src.tid |= minimark.GCFLAG_NO_YOUNG_PTRS
        hdr_dst.tid |= minimark.GCFLAG_NO_YOUNG_PTRS
        hdr_src.tid |= minimark.GCFLAG_CARDS_SET
        res = self.gc.writebarrier_before_copy(addr_src, addr_dst)
        assert not res # there might be young ptrs, let ll_arraycopy to find them
        assert hdr_dst.tid & minimark.GCFLAG_NO_YOUNG_PTRS

        
class TestMiniMarkGCFull(DirectGCTest):
    from pypy.rpython.memory.gc.minimark import MiniMarkGC as GCClass
