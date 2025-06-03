""" The tests below don't use translation at all.  They run the GCs by
instantiating them and asking them to allocate memory by calling their
methods directly.  The tests need to maintain by hand what the GC should
see as the list of roots (stack and prebuilt objects).
"""

# XXX VERY INCOMPLETE, low coverage

import py

from hypothesis import strategies, given, assume, example

from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.memory.gctypelayout import TypeLayoutBuilder, FIN_HANDLER_ARRAY
from rpython.memory.gctypelayout import WEAKREF, WEAKREFPTR
from rpython.rlib.rarithmetic import LONG_BIT, is_valid_int
from rpython.memory.gc import minimark, incminimark
from rpython.memory.gctypelayout import zero_gc_pointers_inside, zero_gc_pointers
from rpython.rlib.debug import debug_print
from rpython.rlib.test.test_debug import debuglog
from rpython.rlib import rgc
import pdb
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

STR = lltype.GcStruct('rpy_string',
                      ('hash',  lltype.Signed),
                      ('chars', lltype.Array(lltype.Char, hints={'immutable': True, 'extra_item_after_alloc': 1})))

class DirectRootWalker(object):

    def __init__(self, tester):
        self.tester = tester

    def walk_roots(self, collect_stack_root,
                   collect_static_in_prebuilt_nongc,
                   collect_static_in_prebuilt_gc,
                   is_minor=False):
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

    def finished_minor_collection(self):
        pass


class BaseDirectGCTest(object):
    GC_PARAMS = {}

    def get_extra_gc_params(self):
        return {}

    def setup_method(self, meth):
        from rpython.config.translationoption import get_combined_translation_config
        config = get_combined_translation_config(translating=True).translation
        self.stackroots = []
        GC_PARAMS = self.GC_PARAMS.copy()
        if hasattr(meth, 'GC_PARAMS'):
            GC_PARAMS.update(meth.GC_PARAMS)
        GC_PARAMS['translated_to_c'] = False
        GC_PARAMS.update(self.get_extra_gc_params())
        self.gc = self.GCClass(config, **GC_PARAMS)
        self.gc.DEBUG = True
        self.rootwalker = DirectRootWalker(self)
        self.gc.set_root_walker(self.rootwalker)
        self.layoutbuilder = TypeLayoutBuilder(self.GCClass)
        self.get_type_id = self.layoutbuilder.get_type_id
        gcdata = self.layoutbuilder.initialize_gc_query_function(self.gc)
        ll_handlers = lltype.malloc(FIN_HANDLER_ARRAY, 0, immortal=True)
        gcdata.finalizer_handlers = llmemory.cast_ptr_to_adr(ll_handlers)
        self.gc.setup()

    def consider_constant(self, p):
        obj = p._obj
        TYPE = lltype.typeOf(obj)
        self.layoutbuilder.consider_constant(TYPE, obj, self.gc)

    def write(self, p, fieldname, newvalue):
        if self.gc.needs_write_barrier:
            addr_struct = llmemory.cast_ptr_to_adr(p)
            self.gc.write_barrier(addr_struct)
        setattr(p, fieldname, newvalue)

    def writearray(self, p, index, newvalue):
        if self.gc.needs_write_barrier:
            addr_struct = llmemory.cast_ptr_to_adr(p)
            if hasattr(self.gc, 'write_barrier_from_array'):
                self.gc.write_barrier_from_array(addr_struct, index)
            else:
                self.gc.write_barrier(addr_struct)
        p[index] = newvalue

    def malloc(self, TYPE, n=None):
        addr = self.gc.malloc(self.get_type_id(TYPE), n)
        obj_ptr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(TYPE))
        if not self.gc.malloc_zero_filled:
            zero_gc_pointers_inside(obj_ptr, TYPE)
        return obj_ptr


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
            assert 'DEAD' not in repr(self.stackroots)
            a = self.malloc(VAR, i)
            assert 'DEAD' not in repr(a)
            self.stackroots.append(a)
            print 'ADDED TO STACKROOTS:', llmemory.cast_adr_to_int(
                llmemory.cast_ptr_to_adr(a))
            assert 'DEAD' not in repr(self.stackroots)
            for j in range(5):
                assert 'DEAD' not in repr(self.stackroots)
                p = self.malloc(S)
                assert 'DEAD' not in repr(self.stackroots)
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
        assert is_valid_int(hash)
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
        assert is_valid_int(hash)
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
        assert is_valid_int(hash)
        for i in range(2):
            self.gc.collect()
            assert hash == self.gc.identityhash(self.stackroots[-1])
        self.stackroots.pop()
        # (4) p is a prebuilt object
        hash = self.gc.identityhash(p_const)
        print hash
        assert is_valid_int(hash)
        assert hash == self.gc.identityhash(p_const)
        # (5) p is actually moving (for the markcompact gc only?)
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
    from rpython.memory.gc.semispace import SemiSpaceGC as GCClass

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
    from rpython.memory.gc.generation import GenerationGC as GCClass

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

    def test_write_barrier_direct(self):
        s0 = lltype.malloc(S, immortal=True)
        self.consider_constant(s0)
        s = self.malloc(S)
        s.x = 1
        s0.next = s
        self.gc.write_barrier(llmemory.cast_ptr_to_adr(s0))

        self.gc.collect(0)

        assert s0.next.x == 1


class TestHybridGC(TestGenerationGC):
    from rpython.memory.gc.hybrid import HybridGC as GCClass

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


class TestMiniMarkGCSimple(DirectGCTest):
    from rpython.memory.gc.minimark import MiniMarkGC as GCClass
    from rpython.memory.gc.minimarktest import SimpleArenaCollection
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
        largeobj_size =  self.gc.nonlarge_max + 1
        self.gc.next_major_collection_threshold = 99999.0
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
        assert hdr_src.tid & minimark.GCFLAG_TRACK_YOUNG_PTRS
        assert hdr_dst.tid & minimark.GCFLAG_TRACK_YOUNG_PTRS
        #
        res = self.gc.writebarrier_before_copy(addr_src, addr_dst, 0, 0, 10)
        assert res
        assert hdr_dst.tid & minimark.GCFLAG_TRACK_YOUNG_PTRS
        #
        hdr_src.tid &= ~minimark.GCFLAG_TRACK_YOUNG_PTRS  # pretend we have young ptrs
        res = self.gc.writebarrier_before_copy(addr_src, addr_dst, 0, 0, 10)
        assert res # we optimized it
        assert hdr_dst.tid & minimark.GCFLAG_TRACK_YOUNG_PTRS == 0 # and we copied the flag
        #
        self.gc.card_page_indices = 128     # force > 0
        hdr_src.tid |= minimark.GCFLAG_TRACK_YOUNG_PTRS
        hdr_dst.tid |= minimark.GCFLAG_TRACK_YOUNG_PTRS
        hdr_src.tid |= minimark.GCFLAG_HAS_CARDS
        hdr_src.tid |= minimark.GCFLAG_CARDS_SET
        # hdr_dst.tid does not have minimark.GCFLAG_HAS_CARDS
        res = self.gc.writebarrier_before_copy(addr_src, addr_dst, 0, 0, 10)
        assert not res # there might be young ptrs, let ll_arraycopy to find them

    def test_writebarrier_before_copy_preserving_cards(self):
        from rpython.rtyper.lltypesystem import llarena
        tid = self.get_type_id(VAR)
        largeobj_size =  self.gc.nonlarge_max + 1
        self.gc.next_major_collection_threshold = 99999.0
        addr_src = self.gc.external_malloc(tid, largeobj_size, alloc_young=True)
        addr_dst = self.gc.external_malloc(tid, largeobj_size, alloc_young=True)
        hdr_src = self.gc.header(addr_src)
        hdr_dst = self.gc.header(addr_dst)
        #
        assert hdr_src.tid & minimark.GCFLAG_HAS_CARDS
        assert hdr_dst.tid & minimark.GCFLAG_HAS_CARDS
        #
        self.gc.write_barrier_from_array(addr_src, 0)
        index_in_third_page = int(2.5 * self.gc.card_page_indices)
        assert index_in_third_page < largeobj_size
        self.gc.write_barrier_from_array(addr_src, index_in_third_page)
        #
        assert hdr_src.tid & minimark.GCFLAG_CARDS_SET
        addr_byte = self.gc.get_card(addr_src, 0)
        assert ord(addr_byte.char[0]) == 0x01 | 0x04  # bits 0 and 2
        #
        res = self.gc.writebarrier_before_copy(addr_src, addr_dst,
                                             0, 0, 2*self.gc.card_page_indices)
        assert res
        #
        assert hdr_dst.tid & minimark.GCFLAG_CARDS_SET
        addr_byte = self.gc.get_card(addr_dst, 0)
        assert ord(addr_byte.char[0]) == 0x01 | 0x04  # bits 0 and 2

    test_writebarrier_before_copy_preserving_cards.GC_PARAMS = {
        "card_page_indices": 4}


class TestMiniMarkGCFull(DirectGCTest):
    from rpython.memory.gc.minimark import MiniMarkGC as GCClass

class TestIncrementalMiniMarkGCSimple(TestMiniMarkGCSimple):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass

    def test_write_barrier_marking_simple(self):
        for i in range(2):
            curobj = self.malloc(S)
            curobj.x = i
            self.stackroots.append(curobj)


        oldobj = self.stackroots[-1]
        oldhdr = self.gc.header(llmemory.cast_ptr_to_adr(oldobj))

        assert oldhdr.tid & incminimark.GCFLAG_VISITED == 0
        self.gc.debug_gc_step_until(incminimark.STATE_MARKING)
        oldobj = self.stackroots[-1]
        # object shifted by minor collect
        oldhdr = self.gc.header(llmemory.cast_ptr_to_adr(oldobj))
        assert oldhdr.tid & incminimark.GCFLAG_VISITED == 0

        self.gc._minor_collection()
        self.gc.visit_all_objects_step(1)

        assert oldhdr.tid & incminimark.GCFLAG_VISITED

        #at this point the first object should have been processed
        newobj = self.malloc(S)
        self.write(oldobj,'next',newobj)

        assert self.gc.header(self.gc.old_objects_pointing_to_young.tolist()[0]) == oldhdr

        self.gc._minor_collection()
        self.gc.debug_check_consistency()

    def test_sweeping_simple(self):
        assert self.gc.gc_state == incminimark.STATE_SCANNING

        for i in range(2):
            curobj = self.malloc(S)
            curobj.x = i
            self.stackroots.append(curobj)

        self.gc.debug_gc_step_until(incminimark.STATE_SWEEPING)
        oldobj = self.stackroots[-1]
        oldhdr = self.gc.header(llmemory.cast_ptr_to_adr(oldobj))
        assert oldhdr.tid & incminimark.GCFLAG_VISITED

        newobj1 = self.malloc(S)
        newobj2 = self.malloc(S)
        newobj1.x = 1337
        newobj2.x = 1338
        self.write(oldobj,'next',newobj1)
        self.gc.debug_gc_step_until(incminimark.STATE_SCANNING)
        #should not be cleared even though it was allocated while sweeping
        newobj1 = oldobj.next
        assert newobj1.x == 1337

    def test_obj_on_escapes_on_stack(self):
        obj0 = self.malloc(S)

        self.stackroots.append(obj0)
        obj0.next = self.malloc(S)
        self.gc.debug_gc_step_until(incminimark.STATE_MARKING)
        obj0 = self.stackroots[-1]
        obj1 = obj0.next
        obj1.x = 13
        obj0.next = lltype.nullptr(S)
        self.stackroots.append(obj1)
        self.gc.debug_gc_step_until(incminimark.STATE_SCANNING)
        assert self.stackroots[1].x == 13

    def test_move_out_of_nursery(self):
        obj0 = self.malloc(S)
        obj0.x = 123
        adr1 = self.gc.move_out_of_nursery(llmemory.cast_ptr_to_adr(obj0))
        obj1 = llmemory.cast_adr_to_ptr(adr1, lltype.Ptr(S))
        assert obj1.x == 123
        #
        import pytest
        obj2 = self.malloc(S)
        obj2.x = 456
        adr3 = self.gc._find_shadow(llmemory.cast_ptr_to_adr(obj2))
        obj3 = llmemory.cast_adr_to_ptr(adr3, lltype.Ptr(S))
        with pytest.raises(lltype.UninitializedMemoryAccess):
            obj3.x     # the shadow is not populated yet
        adr4 = self.gc.move_out_of_nursery(llmemory.cast_ptr_to_adr(obj2))
        assert adr4 == adr3
        assert obj3.x == 456     # it is populated now


class TestIncrementalMiniMarkGCFull(DirectGCTest):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass

    def flags(self, obj):
        return self.gc.header(llmemory.cast_ptr_to_adr(obj)).tid.rest

    def test_malloc_fixedsize_no_cleanup(self):
        p = self.malloc(S)
        import pytest
        #ensure the memory is uninitialized
        with pytest.raises(lltype.UninitializedMemoryAccess):
            x1 = p.x
        #ensure all the ptr fields are zeroed
        assert p.prev == lltype.nullptr(S)
        assert p.next == lltype.nullptr(S)
    
    def test_malloc_varsize_no_cleanup(self):
        x = lltype.Signed
        VAR1 = lltype.GcArray(x)
        p = self.malloc(VAR1,5)
        import pytest
        with pytest.raises(lltype.UninitializedMemoryAccess):
            assert isinstance(p[0], lltype._uninitialized)
            x1 = p[0]

    def test_malloc_varsize_no_cleanup2(self):
        #as VAR is GcArray so the ptr will don't need to be zeroed
        p = self.malloc(VAR, 100)
        for i in range(100):
            assert p[i] == lltype.nullptr(S)

    def test_malloc_varsize_no_cleanup3(self):
        VAR1 = lltype.Array(lltype.Ptr(S))
        p1 = lltype.malloc(VAR1, 10, flavor='raw', track_allocation=False)
        import pytest
        with pytest.raises(lltype.UninitializedMemoryAccess):
            for i in range(10):
                assert p1[i] == lltype.nullptr(S)
                p1[i]._free()
            p1._free()

    def test_malloc_struct_of_ptr_struct(self):
        S3 = lltype.GcForwardReference()
        S3.become(lltype.GcStruct('S3',
                         ('gcptr_struct', S),
                         ('prev', lltype.Ptr(S)),
                         ('next', lltype.Ptr(S))))
        s3 = self.malloc(S3)
        assert s3.gcptr_struct.prev == lltype.nullptr(S)
        assert s3.gcptr_struct.next == lltype.nullptr(S)

    def test_malloc_array_of_ptr_struct(self):
        ARR_OF_PTR_STRUCT = lltype.GcArray(lltype.Ptr(S))
        arr_of_ptr_struct = self.malloc(ARR_OF_PTR_STRUCT,5)
        for i in range(5):
            assert arr_of_ptr_struct[i] == lltype.nullptr(S)
            assert arr_of_ptr_struct[i] == lltype.nullptr(S)
            arr_of_ptr_struct[i] = self.malloc(S)
            assert arr_of_ptr_struct[i].prev == lltype.nullptr(S)
            assert arr_of_ptr_struct[i].next == lltype.nullptr(S)

    #fail for now
    def xxx_test_malloc_array_of_ptr_arr(self):
        ARR_OF_PTR_ARR = lltype.GcArray(lltype.Ptr(lltype.GcArray(lltype.Ptr(S))))
        arr_of_ptr_arr = self.malloc(ARR_OF_PTR_ARR, 10)
        self.stackroots.append(arr_of_ptr_arr)
        for i in range(10):
            assert arr_of_ptr_arr[i] == lltype.nullptr(lltype.GcArray(lltype.Ptr(S)))
        for i in range(10):
            self.writearray(arr_of_ptr_arr, i,
                            self.malloc(lltype.GcArray(lltype.Ptr(S)), i))
            #self.stackroots.append(arr_of_ptr_arr[i])
            #debug_print(arr_of_ptr_arr[i])
            for elem in arr_of_ptr_arr[i]:
                #self.stackroots.append(elem)
                assert elem == lltype.nullptr(S)
                elem = self.malloc(S)
                assert elem.prev == lltype.nullptr(S)
                assert elem.next == lltype.nullptr(S)

    def test_collect_0(self, debuglog):
        self.gc.collect(1) # start a major
        debuglog.reset()
        self.gc.collect(-1) # do ONLY a minor
        assert debuglog.summary() == {'gc-minor': 1}

    def test_enable_disable(self, debuglog):
        def large_malloc():
            # malloc an object which is large enough to trigger a major collection
            threshold = self.gc.next_major_collection_threshold
            self.malloc(VAR, int(threshold/4))
            summary = debuglog.summary()
            debuglog.reset()
            return summary
        #
        summary = large_malloc()
        assert sorted(summary.keys()) == ['gc-collect-step', 'gc-minor']
        #
        self.gc.disable()
        summary = large_malloc()
        assert sorted(summary.keys()) == ['gc-minor']
        #
        self.gc.enable()
        summary = large_malloc()
        assert sorted(summary.keys()) == ['gc-collect-step', 'gc-minor']

    def test_call_collect_when_disabled(self, debuglog):
        # malloc an object and put it the old generation
        s = self.malloc(S)
        s.x = 42
        self.stackroots.append(s)
        self.gc.collect()
        s = self.stackroots.pop()
        #
        self.gc.disable()
        self.gc.collect(1) # start a major collect
        assert sorted(debuglog.summary()) == ['gc-collect-step', 'gc-minor']
        assert s.x == 42 # s is not freed yet
        #
        debuglog.reset()
        self.gc.collect(1) # run one more step
        assert sorted(debuglog.summary()) == ['gc-collect-step', 'gc-minor']
        assert s.x == 42 # s is not freed yet
        #
        debuglog.reset()
        self.gc.collect() # finish the major collection
        summary = debuglog.summary()
        assert sorted(debuglog.summary()) == ['gc-collect-step', 'gc-minor']
        # s is freed
        py.test.raises(RuntimeError, 's.x')

    def test_collect_step(self, debuglog):
        n = 0
        states = []
        while True:
            debuglog.reset()
            val = self.gc.collect_step()
            states.append((rgc.old_state(val), rgc.new_state(val)))
            summary = debuglog.summary()
            assert summary == {'gc-minor': 1, 'gc-collect-step': 1}
            if rgc.is_done(val):
                break
            n += 1
            if n == 100:
                assert False, 'this looks like an endless loop'
        #
        assert states == [
            (incminimark.STATE_SCANNING, incminimark.STATE_MARKING),
            (incminimark.STATE_MARKING, incminimark.STATE_SWEEPING),
            (incminimark.STATE_SWEEPING, incminimark.STATE_FINALIZING),
            (incminimark.STATE_FINALIZING, incminimark.STATE_SCANNING)
            ]

    def test_gc_debug_crash_with_prebuilt_objects(self):
        from rpython.rlib import rgc
        flags = self.flags

        prebuilt = lltype.malloc(S, immortal=True)
        prebuilt.x = 42
        self.consider_constant(prebuilt)

        self.gc.DEBUG = 2

        old2 = self.malloc(S)
        old2.x = 45
        self.stackroots.append(old2)
        old = self.malloc(S)
        old.x = 43
        self.write(old, 'next', prebuilt)
        self.stackroots.append(old)
        val = self.gc.collect_step()
        assert rgc.old_state(val) == incminimark.STATE_SCANNING
        assert rgc.new_state(val) == incminimark.STATE_MARKING
        old2 = self.stackroots[0] # reload
        old = self.stackroots[1]

        # now a major next collection starts
        # run things with TEST_VISIT_SINGLE_STEP = True so we can control
        # the timing correctly
        self.gc.TEST_VISIT_SINGLE_STEP = True
        # run two marking steps, the first one marks obj, the second one
        # prebuilt (which does nothing), but obj2 is left so we aren't done
        # with marking
        val = self.gc.collect_step()
        val = self.gc.collect_step()
        assert rgc.old_state(val) == incminimark.STATE_MARKING
        assert rgc.new_state(val) == incminimark.STATE_MARKING
        assert flags(old) & incminimark.GCFLAG_VISITED
        assert (flags(old2) & incminimark.GCFLAG_VISITED) == 0
        # prebuilt counts as grey but for prebuilt reasons
        assert (flags(prebuilt) & incminimark.GCFLAG_VISITED) == 0
        assert flags(prebuilt) & incminimark.GCFLAG_NO_HEAP_PTRS
        # its write barrier is active
        assert flags(prebuilt) & incminimark.GCFLAG_TRACK_YOUNG_PTRS

        # now lets write a newly allocated object into prebuilt
        new = self.malloc(S)
        new.x = -10
        # write barrier of prebuilt triggers
        self.write(prebuilt, 'next', new)
        # prebuilt got added both to old_objects_pointing_to_young and
        # prebuilt_root_objects, so those flags get cleared
        assert (flags(prebuilt) & incminimark.GCFLAG_NO_HEAP_PTRS) == 0
        assert (flags(prebuilt) & incminimark.GCFLAG_TRACK_YOUNG_PTRS) == 0
        # thus the prebuilt object now counts as white!
        assert (flags(prebuilt) & incminimark.GCFLAG_VISITED) == 0

        # this triggers the assertion black -> white pointer
        # for the reference obj -> prebuilt
        self.gc.collect_step()

    def test_incrementality_bug_arraycopy(self, size1=8, size2=8):
        from rpython.rlib import rgc
        flags = self.flags
        self.gc.DEBUG = 0

        source = self.malloc(VAR, size1)
        self.stackroots.append(source)
        target = self.malloc(VAR, size2)
        self.stackroots.append(target)
        node = self.malloc(S)
        node.x = 5
        self.writearray(source, 0, node)
        val = self.gc.collect_step()
        assert rgc.old_state(val) == incminimark.STATE_SCANNING
        assert rgc.new_state(val) == incminimark.STATE_MARKING
        source = self.stackroots[0] # reload
        target = self.stackroots[1]
        assert (flags(source) & incminimark.GCFLAG_VISITED) == 0
        assert flags(source) & incminimark.GCFLAG_TRACK_YOUNG_PTRS
        assert (flags(target) & incminimark.GCFLAG_VISITED) == 0
        assert flags(target) & incminimark.GCFLAG_TRACK_YOUNG_PTRS
        self.gc.TEST_VISIT_SINGLE_STEP = True
        # this traces target
        val = self.gc.collect_step()
        assert (flags(source) & incminimark.GCFLAG_VISITED) == 0
        assert flags(source) & incminimark.GCFLAG_TRACK_YOUNG_PTRS
        assert flags(target) & incminimark.GCFLAG_VISITED
        assert flags(target) & incminimark.GCFLAG_TRACK_YOUNG_PTRS

        addr_src = llmemory.cast_ptr_to_adr(source)
        addr_dst = llmemory.cast_ptr_to_adr(target)
        res = self.gc.writebarrier_before_copy(addr_src, addr_dst, 0, 0, 2)
        if res:
            # manually do the copy
            target[0] = source[0]
            target[1] = source[1]
        else:
            self.writearray(target, 0, source[0])
            self.writearray(target, 1, source[1])
        self.writearray(source, 0, lltype.nullptr(S))
        # this traces source
        self.gc.collect_step()
        # going through more_objects_to_trace (only the arrays are there)
        self.gc.collect_step()
        # sweeping 1
        self.gc.collect_step()
        # sweeping 2
        self.gc.collect_step()
        # used to crash, node got collected
        assert target[0].x == 5

    def test_incrementality_bug_arraycopy2(self):
        # same test as before, but with card marking *on* for the arrays
        # in the previous one they are too small for card marking
        self.test_incrementality_bug_arraycopy()
    test_incrementality_bug_arraycopy2.GC_PARAMS = {
        "card_page_indices": 4}

    def test_incrementality_bug_arraycopy3(self):
        # same test as before, but with card marking *on* for the arrays
        # in the previous one they are too small for card marking
        self.test_incrementality_bug_arraycopy(size2=2)
    test_incrementality_bug_arraycopy3.GC_PARAMS = {
        "card_page_indices": 4}

    def test_pin_id_bug(self):
        from rpython.rlib import rgc

        flags = self.flags

        self.gc.DEBUG = 2
        self.gc.TEST_VISIT_SINGLE_STEP = True
        self.gc.gc_step_until(incminimark.STATE_MARKING)

        s = self.malloc(STR, 1)
        self.stackroots.append(s)
        assert self.gc.gc_state == incminimark.STATE_MARKING
        sid = self.gc.id(s)
        assert self.gc.gc_state == incminimark.STATE_MARKING
        pinned = self.gc.pin(llmemory.cast_ptr_to_adr(s))
        assert pinned
        self.gc.collect_step()
        assert self.gc.gc_state == incminimark.STATE_SWEEPING
        self.gc.unpin(llmemory.cast_ptr_to_adr(s))
        self.gc.collect()

    def test_pin_id_bug2(self):
        flags = self.flags
        self.gc.DEBUG = 2
        self.gc.TEST_VISIT_SINGLE_STEP = True

        s = self.malloc(STR, 1)
        self.stackroots.append(s)
        sid = self.gc.id(s)
        pinned = self.gc.pin(llmemory.cast_ptr_to_adr(s))
        assert pinned
        self.gc.gc_step_until(incminimark.STATE_FINALIZING)
        assert self.gc.gc_state == incminimark.STATE_FINALIZING
        self.gc.collect_step()
        self.gc.unpin(llmemory.cast_ptr_to_adr(s))
        assert self.gc.gc_state == incminimark.STATE_SCANNING
        # this used to crash, with unexpected GCFLAG_VISITED in
        # _debug_check_object_scanning, called on the shadow
        self.gc.collect()


class Node(object):
    def __init__(self, x, prev, next):
        self.x = x
        self.prev = prev # an identity
        self.next = next # an identity

    def __repr__(self):
        return "Node(%s, %s, %s)" % (self.x, self.prev, self.next)

class Weakref(object):
    def __init__(self, identity):
        self.identity = identity

    def __repr__(self):
        return "Weakref(%s)" % self.identity

@strategies.composite
def random_action_sequences(draw):
    import itertools

    result = {}
    # make sure that drawing "False" leads to the "simpler" choice
    result['use_card_marking'] = draw(strategies.booleans())
    result['use_simple_arena'] = not draw(strategies.booleans())
    result['visit_single_step'] = not draw(strategies.booleans())
    result['debug_level'] = draw(strategies.integers(0, 2))

    # identity: object
    model = {}
    stackroots = []
    prebuilts = []
    pinned_indexes = []
    ids_taken = {} # identity -> index in ids list

    current_identity = itertools.count(1)
    def next_identity():
        return next(current_identity)

    def filter_objects(typ):
        indexes = []
        for index, identity in enumerate(prebuilts):
            if isinstance(model[identity], typ):
                indexes.append(~index)
        for index, identity in enumerate(stackroots):
            if isinstance(model[identity], typ):
                indexes.append(index)
        return indexes

    def random_object_index():
        indexes = filter_objects(object)
        return draw(strategies.sampled_from(indexes))

    def random_node_index():
        indexes = filter_objects(Node)
        return draw(strategies.sampled_from(indexes))

    def random_array_index():
        indexes = filter_objects(list)
        return draw(strategies.sampled_from(indexes))

    def get_obj_identity(index):
        if index < 0:
            return prebuilts[~index]
        return stackroots[index]

    def create_array():
        length = draw(strategies.integers(1, 20))
        identity = next_identity()
        indexes = [random_node_index() for _ in range(length)]
        model[identity] = [get_obj_identity(index) for index in indexes]
        return identity, indexes

    def create_string():
        identity = next_identity()
        data = draw(strategies.binary(1, 20))
        model[identity] = data
        return identity, data

    # make some prebuilt nodes
    prebuilts_result = []
    num_prebuilts = draw(strategies.integers(1, 10))
    for prebuilt in range(num_prebuilts):
        identity = next_identity()
        prebuilts.append(identity)
        model[identity] = Node(None, None, None)
        previndex = random_node_index()
        nextindex = random_node_index()
        model[identity] = Node(identity, get_obj_identity(previndex), get_obj_identity(nextindex))
        prebuilts_result.append((identity, previndex, nextindex))
    result['prebuilts'] = prebuilts_result
    prebuilts = [el[0] for el in prebuilts_result]

    # prebuilt arrays
    prebuilt_arrays_result = []
    for i in range(draw(strategies.integers(1, 10))):
        identity, indexes = create_array()
        prebuilt_arrays_result.append(indexes)
        prebuilts.append(identity)
    result['prebuilt_arrays'] = prebuilt_arrays_result

    # now create actions
    actions = []
    result['actions'] = actions
    def add_action(*args):
        # compute a heap checking action
        checking_actions = []
        reachable_model = {}
        seen = {} # identity: path
        todo = [(identity, ("prebuilt", i)) for i, identity in enumerate(prebuilts)]
        todo += [(identity, ("stackroots", i)) for i, identity in enumerate(stackroots)]
        while todo:
            identity, path = todo.pop()
            if identity in seen:
                checking_actions.append(("seen", path))
                continue
            seen[identity] = path
            obj = model[identity]
            if isinstance(obj, Node):
                checking_actions.append(("node", obj.x, path))

                for field in ['prev', 'next']:
                    res = getattr(obj, field)
                    todo.append((res, path + (field, )))
            elif isinstance(obj, list):
                checking_actions.append(("array", len(obj), path))
                for index, res in enumerate(model[identity]):
                    todo.append((res, path + (index, )))
            elif isinstance(obj, Weakref):
                if obj.identity in seen:
                    checking_actions.append(("weakref", "seen", seen[obj.identity], path))
                else:
                    checking_actions.append((obj, path))
            else:
                assert isinstance(obj, str)
                checking_actions.append(("str", obj, path))
        # deal with the weakrefs
        for index, tup in enumerate(checking_actions):
            obj = tup[0]
            if not isinstance(obj, Weakref):
                continue
            if obj.identity in seen:
                checking_actions[index] = ("weakref", "alive", seen[obj.identity], tup[1])
            else:
                checking_actions[index] = ("weakref", "dead", None, tup[1])
        args += (checking_actions, )
        assert "weakref" not in checking_actions
        actions.append(args)

    all_actions = []
    def gen_action(name, precond=None):
        def wrap(func):
            if precond is None:
                precond1 = lambda: True
            elif isinstance(precond, type):
                # passing a type means "do we have an object of that type
                # available currently"
                typ = precond
                precond1 = lambda: len(filter_objects(typ)) != 0
            else:
                precond1 = precond
            all_actions.append((func, precond1))
            return func
        return wrap

    @gen_action("drop", lambda: len(stackroots) != 0)
    def drop():
        index = draw(strategies.integers(0, len(stackroots)-1))
        if index in pinned_indexes:
            indexindex = pinned_indexes.index(index)
            add_action("unpin", indexindex)
            del pinned_indexes[indexindex]
        del stackroots[index]
        # ugh, annoying
        pinned_indexes[:] = [(pinned_index if pinned_index < index else pinned_index - 1)
                             for pinned_index in pinned_indexes]
        add_action("drop", index)

    @gen_action("malloc", object)
    def malloc():
        nextindex = random_object_index()
        previndex = random_object_index()
        identity = next_identity()
        model[identity] = Node(identity, get_obj_identity(previndex), get_obj_identity(nextindex))
        stackroots.append(identity)
        add_action('malloc', identity, previndex, nextindex)

    @gen_action("read", Node)
    def read():
        index = random_node_index()
        identity = get_obj_identity(index)
        if draw(strategies.booleans()):
            field = 'prev'
        else:
            field = 'next'
        res = getattr(model[identity], field)
        stackroots.append(res)
        add_action("read", index, field)

    @gen_action("write", Node)
    def write():
        index1 = random_node_index()
        index2 = random_object_index()
        if draw(strategies.booleans()):
            field = 'prev'
        else:
            field = 'next'
        identity1 = get_obj_identity(index1)
        identity2 = get_obj_identity(index2)
        setattr(model[identity1], field, identity2)
        add_action('write', index1, field, index2)

    @gen_action("collect")
    def collect():
        add_action('collect')

    @gen_action("readarray", list)
    def readarray():
        arrayindex = random_array_index()
        identity = get_obj_identity(arrayindex)
        l = model[identity]
        index = draw(strategies.integers(0, len(l) - 1))
        res = model[identity][index]
        stackroots.append(res)
        add_action('readarray', arrayindex, index)

    @gen_action("writearray", list)
    def writearray():
        arrayindex = random_array_index()
        objindex = random_object_index()
        identity = get_obj_identity(arrayindex)
        l = model[identity]
        length = len(l)
        index = draw(strategies.integers(0, length - 1))
        l[index] = get_obj_identity(objindex)
        add_action('writearray', arrayindex, index, objindex)

    @gen_action("copy_array", list)
    def copy_array():
        array1index = random_array_index()
        array2index = random_array_index()
        array1identity = get_obj_identity(array1index)
        array2identity = get_obj_identity(array2index)
        assume(array1identity != array2identity)
        array1 = model[array1identity]
        array2 = model[array2identity]
        array1length = len(array1)
        array2length = len(array2)
        if not draw(strategies.booleans()):
            source_start = dest_start = 0
            length = draw(strategies.integers(1, min(array1length, array2length)))
        else:
            source_start = draw(strategies.integers(0, array1length-1))
            dest_start = draw(strategies.integers(0, array2length-1))
            length = draw(strategies.integers(1, min(array1length - source_start, array2length - dest_start)))
        for i in range(length):
            array2[dest_start + i] = array1[source_start + i]
        add_action('copy_array', array1index, array2index, source_start, dest_start, length)

    @gen_action("malloc_array")
    def malloc_array():
        identity, indexes = create_array()
        stackroots.append(identity)
        add_action('malloc_array', indexes)

    @gen_action("malloc_string")
    def malloc_string():
        identity, value = create_string()
        stackroots.append(identity)
        add_action('malloc_string', value)

    @gen_action("pin", str)
    def pin():
        indexes = [index for index, identity in enumerate(stackroots) if isinstance(model[identity], str) and index not in pinned_indexes]
        index = draw(strategies.sampled_from(indexes))
        pinned_indexes.append(index)
        add_action('pin', index)

    @gen_action("unpin", lambda: len(pinned_indexes) != 0)
    def unpin():
        index = draw(strategies.integers(0, len(pinned_indexes) - 1))
        del pinned_indexes[index]
        add_action('unpin', index)

    @gen_action("take_id", object)
    def take_id():
        index = random_object_index()
        identity = get_obj_identity(index)
        if identity in ids_taken:
            add_action('take_id', index, ids_taken[identity])
        else:
            ids_taken[identity] = len(ids_taken)
            add_action('take_id', index, -1)

    @gen_action("create_weakref", lambda: len(filter_objects((Node, list))) != 0)
    def create_weakref():
        indexes = filter_objects((Node, list))
        index = draw(strategies.sampled_from(indexes))
        identity = get_obj_identity(index)
        new_identity = next_identity()
        ref = Weakref(identity)
        model[new_identity] = ref
        stackroots.append(new_identity)
        add_action("create_weakref", index)

    for i in range(draw(strategies.integers(2, 100))):
        # generate steps

        # sample from the actions where preconditions are met:
        active_actions = [action for action, precond in all_actions if precond()]
        action = draw(strategies.sampled_from(active_actions))
        action()
    return result

class TestIncrementalMiniMarkGCFullRandom(DirectGCTest):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass

    NODE = lltype.GcStruct('NODE',
                           ('x', lltype.Signed),
                           ('prev', llmemory.GCREF),
                           ('next', llmemory.GCREF))

    VAR = lltype.GcArray(llmemory.GCREF)

    def state_setup(self, random_data):
        from rpython.memory.gc.minimarktest import SimpleArenaCollection
        if random_data['use_card_marking']:
            # enable card marking
            GC_PARAMS = {"card_page_indices": 4}
        else:
            GC_PARAMS = {}
        if random_data['use_simple_arena']:
            GC_PARAMS['ArenaCollectionClass'] = SimpleArenaCollection
        self.test_random.im_func.GC_PARAMS = GC_PARAMS
        self.setup_method(self.test_random.im_func)
        self.gc.TEST_VISIT_SINGLE_STEP = random_data['visit_single_step']
        self.gc.DEBUG = random_data['debug_level']
        self.make_prebuilts(random_data)
        self.pinned_strings = []
        self.computed_ids = []

    def erase(self, obj):
        return lltype.cast_opaque_ptr(llmemory.GCREF, obj)

    def unerase_array(self, gcref):
        return lltype.cast_opaque_ptr(lltype.Ptr(self.VAR), gcref)

    def unerase_node(self, gcref):
        return lltype.cast_opaque_ptr(lltype.Ptr(self.NODE), gcref)

    def unerase_str(self, gcref):
        return lltype.cast_opaque_ptr(lltype.Ptr(STR), gcref)

    def unerase_weakref(self, gcref):
        return lltype.cast_opaque_ptr(WEAKREFPTR, gcref)

    def make_prebuilts(self, random_data):
        prebuilts = self.prebuilts = []
        # construct the prebuilt nodes
        for identity, _, _ in random_data['prebuilts']:
            prebuilt = lltype.malloc(self.NODE, immortal=True)
            prebuilt.x = identity
            prebuilts.append(prebuilt)
        # initialize next and prev fields
        for node, (_, previd, nextid) in zip(prebuilts, random_data['prebuilts']):
            self.consider_constant(node)
            node.prev = self.erase(self.get_node(previd))
            node.next = self.erase(self.get_node(nextid))

        # prebuilt arrays
        for content in random_data['prebuilt_arrays']:
            array = self.create_array(content, immortal=True)
            self.prebuilts.append(array)
            self.consider_constant(array)

    def get_obj(self, index):
        if index < 0:
            return self.prebuilts[~index]
        else:
            return self.stackroots[index]

    def get_node(self, index):
        res = self.get_obj(index)
        return self.unerase_node(res)

    def get_array(self, index):
        res = self.get_obj(index)
        return self.unerase_array(res)

    def create_array(self, content, immortal=False):
        if immortal:
            array = lltype.malloc(self.VAR, len(content), immortal=True)
        else:
            array = self.malloc(self.VAR, len(content))
        for index, objindex in enumerate(content):
            obj = self.erase(self.get_node(objindex))
            if immortal:
                array[index] = obj
            else:
                self.writearray(array, index, obj)
        return array

    def create_string(self, content):
        string = self.malloc(STR, len(content))
        for index, c in enumerate(content):
            string.chars[index] = c
        return string

    def check(self, checking_actions, must_be_dead=False):
        # check that all the successfully pinned strings can be accessed
        # without going via stackroots
        for s in self.pinned_strings:
            if s is not None:
                len(self.unerase_str(s).chars) # would crash
        todo = self.prebuilts + self.stackroots
        # walk the reachable heap and compare against model
        iterator = iter(checking_actions)
        while todo:
            obj = todo.pop()
            action = next(iterator)
            path = action[-1]
            actiondata = action[:-1]
            if actiondata[0] == "seen":
                continue
            elif actiondata[0] == "array":
                obj = self.unerase_array(obj)
                assert actiondata == ("array", len(obj))
                for i in range(len(obj)):
                    todo.append(obj[i])
            elif actiondata[0] == "node":
                obj = self.unerase_node(obj)
                assert actiondata == ("node", obj.x)
                todo.append(obj.prev)
                todo.append(obj.next)
            elif actiondata[0] == "weakref":
                obj = self.unerase_weakref(obj)
                ptr = llmemory.cast_adr_to_ptr(obj.weakptr, llmemory.GCREF)
                _, status, objpath = actiondata
                if status == "seen" or status == "alive":
                    # treat seen and alive the same for now
                    # just check that it's a valid object, in a somewhat
                    # annoying way
                    assert ptr
                    assert "DEAD" not in str(ptr._obj.container)
                else:
                    assert status == "dead"
                    if must_be_dead:
                        assert not ptr
                    else:
                        if ptr:
                            # it can point to an object, but that must be a
                            # still alive one
                            assert "DEAD" not in str(ptr._obj.container)
            else:
                assert actiondata[0] == "str"
                obj = self.unerase_str(obj)
                assert "".join(obj.chars) == actiondata[1]

    @given(random_action_sequences())
    def test_random(self, random_data):
        from rpython.rlib import rgc
        self.state_setup(random_data)
        for action in random_data['actions']:
            kind = action[0]
            actiondata = action[1:-1]
            print kind, actiondata
            if kind == "drop": # drop
                index, = actiondata
                del self.stackroots[index]
            elif kind == "malloc": # alloc
                identity, previd, nextid = actiondata
                p = self.malloc(self.NODE)
                p.x = identity
                self.write(p, 'prev', self.erase(self.get_obj(previd)))
                self.write(p, 'next', self.erase(self.get_obj(nextid)))
                self.stackroots.append(p)
            elif kind == "read": # read field
                objindex, field = actiondata
                obj = self.get_node(objindex)
                res = getattr(obj, field)
                self.stackroots.append(res)
            elif kind == "write":
                obj1index, field, obj2index = actiondata
                obj1 = self.get_node(obj1index)
                obj2 = self.get_obj(obj2index)
                self.write(obj1, field, self.erase(obj2))
            elif kind == "collect":
                assert actiondata == ()
                self.gc.collect_step()
            elif kind == "readarray":
                arrayindex, index = actiondata
                array = self.get_array(arrayindex)
                self.stackroots.append(array[index])
            elif kind == "writearray":
                arrayindex, index, objindex = actiondata
                array = self.get_array(arrayindex)
                node = self.get_obj(objindex)
                self.writearray(array, index, self.erase(node))
            elif kind == "copy_array":
                array1index, array2index, source_start, dest_start, length = actiondata
                array1 = self.get_array(array1index)
                array2 = self.get_array(array2index)
                slowpath = not self.gc.writebarrier_before_copy(llmemory.cast_ptr_to_adr(array1), llmemory.cast_ptr_to_adr(array2),
                                                                source_start, dest_start,
                                                                length)
                for i in range(length):
                    if slowpath:
                        self.writearray(array2, dest_start, array1[source_start])
                    else:
                        # don't call the write barrier
                        array2[dest_start] = array1[source_start]
                    dest_start += 1
                    source_start += 1
            elif kind == "malloc_array":
                content, = actiondata
                array = self.create_array(content)
                self.stackroots.append(array)
            elif kind == "malloc_string":
                content, = actiondata
                array = self.create_string(content)
                self.stackroots.append(array)
            elif kind == "pin":
                index, = actiondata
                ptr = self.stackroots[index]
                flag = self.gc.pin(llmemory.cast_ptr_to_adr(ptr))
                if flag:
                    self.pinned_strings.append(ptr)
                else:
                    self.pinned_strings.append(None)
            elif kind == "unpin":
                index, = actiondata
                ptr = self.pinned_strings[index]
                if ptr is None:
                    # pinning had failed, do nothing
                    pass
                else:
                    self.gc.unpin(llmemory.cast_ptr_to_adr(ptr))
                del self.pinned_strings[index]
            elif kind == "take_id":
                index, compare_with = actiondata
                node = self.get_obj(index)
                int_id = self.gc.id(node)
                if compare_with == -1:
                    self.computed_ids.append(int_id)
                else:
                    assert self.computed_ids[compare_with] == int_id
            elif kind == "create_weakref":
                index, = actiondata
                ref = self.malloc(WEAKREF)
                # must read node *after* malloc, in case malloc collects and moves
                node = self.get_obj(index)
                ref.weakptr = llmemory.cast_ptr_to_adr(node)
                self.stackroots.append(ref)
            else:
                assert 0, "unreachable"
            checking_actions = action[-1]
            self.check(checking_actions)
        self.gc.TEST_VISIT_SINGLE_STEP = False # otherwise the collection might not finish
        self.gc.collect()
        self.check(checking_actions, must_be_dead=True)
