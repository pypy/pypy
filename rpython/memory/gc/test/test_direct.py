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
from rpython.rlib.rarithmetic import LONG_BIT, is_valid_int
from rpython.memory.gc import minimark, incminimark
from rpython.memory.gctypelayout import zero_gc_pointers_inside, zero_gc_pointers
from rpython.rlib.debug import debug_print
from rpython.rlib.test.test_debug import debuglog
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
        from rpython.rlib import rgc
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
        def flags(obj):
            return self.gc.header(llmemory.cast_ptr_to_adr(obj)).tid.rest

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
        def flags(obj):
            return self.gc.header(llmemory.cast_ptr_to_adr(obj)).tid.rest
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

@strategies.composite
def random_action_sequences(draw):
    import itertools

    result = {}
    # make sure that drawing "False" leads to the "simpler" choice
    result['use_card_marking'] = draw(strategies.booleans())
    result['use_simple_arena'] = not draw(strategies.booleans())
    result['visit_single_step'] = not draw(strategies.booleans())
    result['debug_level'] = draw(strategies.integers(0, 2))

    model = {}
    arraymodel = {}
    stackroots = []

    def random_obj():
        objects = [obj for typ, obj in stackroots if typ == "node"]
        return draw(strategies.sampled_from(prebuilts + objects))

    def random_array():
        arrays = [obj for typ, obj in stackroots if typ == "array"]
        return draw(strategies.sampled_from(prebuilt_arrays + arrays))

    def create_array():
        length = next(current_array_length)
        content = []
        for i in range(length):
            obj = random_obj()
            arraymodel[length, i] = obj
            content.append(obj)
        return length, content

    # make some prebuilt nodes
    prebuilts_result = []
    num_prebuilts = draw(strategies.integers(1, 10))
    for prebuilt in range(num_prebuilts):
        previndex = ~draw(strategies.integers(0, num_prebuilts-1))
        nextindex = ~draw(strategies.integers(0, num_prebuilts-1))
        model[~prebuilt, 'prev'] = previndex
        model[~prebuilt, 'next'] = nextindex
        prebuilts_result.append((~prebuilt, previndex, nextindex))
    result['prebuilts'] = prebuilts_result
    prebuilts = [el[0] for el in prebuilts_result]
    for identity in prebuilts:
        assert identity < 0

    # prebuilt arrays
    # hack, arrays are uniquely identified by their lengths :-)
    current_array_length = itertools.count(1)
    prebuilt_arrays_result = []
    for i in range(draw(strategies.integers(1, 10))):
        prebuilt_arrays_result.append(create_array())
    result['prebuilt_arrays'] = prebuilt_arrays_result
    prebuilt_arrays = [el[0] for el in prebuilt_arrays_result]

    # now create actions
    actions = []
    result['actions'] = actions
    def add_action(*args):
        # compute the reachable part of the heap, starting from prebuilt and
        # stackroots
        reachable_model = {}
        reachable_arraymodel = {}
        seen = set()
        seen_arrays = set()
        todo = ([("node", i) for i in prebuilts] +
                [("array", i) for i in prebuilt_arrays] +
                stackroots)
        while todo:
            typ, identity = todo.pop()
            if typ == "node":
                if identity in seen:
                    continue
                seen.add(identity)
                for field in ['prev', 'next']:
                    res = model[identity, field]
                    todo.append(('node', res))
                    reachable_model[identity, field] = res
            else:
                assert typ == "array"
                if identity in seen_arrays:
                    continue
                seen_arrays.add(identity)
                for i in range(identity):
                    res = arraymodel[identity, i]
                    todo.append(("node", res))
                    reachable_arraymodel[identity, i] = res
        args += (reachable_model, reachable_arraymodel, stackroots[:])
        actions.append(args)
    for i in range(draw(strategies.integers(2, 100))):
        # perform steps
        have_stackroot = bool(stackroots)
        action = draw(strategies.integers(0 if have_stackroot else 1, 8))
        if action == 0: # drop
            index = draw(strategies.integers(0, len(stackroots)-1))
            del stackroots[index]
            add_action("drop", index)
        elif action == 1: # alloc
            nextindex = random_obj()
            previndex = random_obj()
            if nextindex >= 0:
                assert nextindex in {obj for typ, obj in stackroots if typ == "node"}
            if previndex >= 0:
                assert previndex in {obj for typ, obj in stackroots if typ == "node"}
            model[i, 'next'] = nextindex
            model[i, 'prev'] = previndex
            stackroots.append(('node', i))
            add_action('malloc', i, previndex, nextindex)
        elif action == 2: # read field
            obj = random_obj()
            if draw(strategies.booleans()):
                field = 'prev'
            else:
                field = 'next'
            res = model[obj, field]
            stackroots.append(('node', res))
            add_action("read", obj, field, res)
        elif action == 3:
            obj1 = random_obj()
            obj2 = random_obj()
            if draw(strategies.booleans()):
                field = 'prev'
            else:
                field = 'next'
            model[obj1, field] = obj2
            add_action('write', obj1, field, obj2)
        elif action == 4:
            add_action('collect')
        elif action == 5:
            array = random_array()
            index = draw(strategies.integers(0, array - 1))
            res = arraymodel[array, index]
            stackroots.append(('node', res))
            add_action('readarray', array, index, res)
        elif action == 6:
            array = random_array()
            index = draw(strategies.integers(0, array - 1))
            obj = random_obj()
            arraymodel[array, index] = obj
            add_action('writearray', array, index, obj)
        elif action == 7:
            array1 = random_array()
            array2 = random_array()
            assume(array1 != array2)
            if not draw(strategies.booleans()):
                source_start = dest_start = 0
                length = draw(strategies.integers(1, min(array1, array2)))
            else:
                source_start = draw(strategies.integers(0, array1-1))
                dest_start = draw(strategies.integers(0, array2-1))
                length = draw(strategies.integers(1, min(array1 - source_start, array2 - dest_start)))
            for i in range(length):
                arraymodel[array2, dest_start + i] = arraymodel[array1, source_start + i]
            add_action('copy_array', array1, array2, source_start, dest_start, length)
        elif action == 8:
            array = create_array()
            stackroots.append(('array', array[0]))
            add_action('malloc_array', *array)
        else:
            assert "unreachable"

    return result

class TestIncrementalMiniMarkGCFullRandom(DirectGCTest):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass

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

    def make_prebuilts(self, random_data):
        prebuilts = self.prebuilts = []
        # construct the prebuilt nodes
        for identity, _, _ in random_data['prebuilts']:
            prebuilt = lltype.malloc(S, immortal=True)
            prebuilt.x = identity
            prebuilts.append(prebuilt)
        # initialize next and prev fields
        for identity, previd, nextid in random_data['prebuilts']:
            prebuilt = self.get_node(identity)
            self.consider_constant(prebuilt)
            prebuilt.prev = self.get_node(previd)
            prebuilt.next = self.get_node(nextid)

        # prebuilt arrays
        prebuilt_arrays = self.prebuilt_arrays = []
        for length, content in random_data['prebuilt_arrays']:
            array = self.create_array(length, content, immortal=True)
            self.prebuilt_arrays.append(array)
            self.consider_constant(array)

    def get_node(self, identity):
        if identity < 0:
            return self.prebuilts[~identity]
        for obj in self.stackroots:
            if lltype.typeOf(obj) == lltype.Ptr(S) and obj.x == identity:
                return obj
        assert 0, "should be unreachable"

    def get_array(self, index):
        assert index > 0
        if index <= len(self.prebuilt_arrays):
            return self.prebuilt_arrays[index - 1]
        for obj in self.stackroots:
            if lltype.typeOf(obj) == lltype.Ptr(VAR) and len(obj) == index:
                return obj
        assert 0, "should be unreachable"

    def create_array(self, length, content, immortal=False):
        if immortal:
            array = lltype.malloc(VAR, length, immortal=True)
        else:
            array = self.malloc(VAR, length)
        for index, objid in enumerate(content):
            obj = self.get_node(objid)
            if immortal:
                array[index] = obj
            else:
                self.writearray(array, index, obj)
        return array

    def check(self, model, arraymodel, stackroots):
        # first check stackroots
        for index, (typ, identity) in enumerate(stackroots):
            obj = self.stackroots[index]
            if typ == "node":
                assert lltype.typeOf(obj) == lltype.Ptr(S)
                assert identity == obj.x
            else:
                assert typ == "array"
                assert lltype.typeOf(obj) == lltype.Ptr(VAR)
                assert identity == len(obj)
        # walk the reachable heap and compare against model
        seen = set()
        seen_arrays = set()
        todo = self.prebuilts + self.prebuilt_arrays + self.stackroots
        while todo:
            obj = todo.pop()
            if lltype.typeOf(obj) == lltype.Ptr(VAR):
                if len(obj) in seen_arrays:
                    continue
                seen_arrays.add(len(obj))
                for i in range(len(obj)):
                    todo.append(obj[i])
                    assert arraymodel[len(obj), i] == obj[i].x
            else:
                if obj.x in seen:
                    continue
                seen.add(obj.x)
                todo.append(obj.next)
                todo.append(obj.prev)
                assert model[obj.x, 'prev'] == obj.prev.x
                assert model[obj.x, 'next'] == obj.next.x

    @given(random_action_sequences())
    def test_random(self, random_data):
        from rpython.rlib import rgc
        self.state_setup(random_data)
        for action in random_data['actions']:
            kind = action[0]
            actiondata = action[1:-3]
            print kind, actiondata
            if kind == "drop": # drop
                index, = actiondata
                del self.stackroots[index]
            elif kind == "malloc": # alloc
                identity, previd, nextid = actiondata
                p = self.malloc(S)
                p.x = identity
                self.write(p, 'next', self.get_node(nextid))
                self.write(p, 'prev', self.get_node(previd))
                self.stackroots.append(p)
            elif kind == "read": # read field
                objid, field, resid = actiondata
                obj = self.get_node(objid)
                res = getattr(obj, field)
                assert res.x == resid
                self.stackroots.append(res)
            elif kind == "write":
                obj1id, field, obj2id = actiondata
                obj1 = self.get_node(obj1id)
                obj2 = self.get_node(obj2id)
                self.write(obj1, field, obj2)
            elif kind == "collect":
                assert actiondata == ()
                self.gc.collect_step()
            elif kind == "readarray":
                arrayindex, index, resultindex = actiondata
                array = self.get_array(arrayindex)
                assert array[index].x == resultindex
                self.stackroots.append(array[index])
            elif kind == "writearray":
                arrayindex, index, objindex = actiondata
                array = self.get_array(arrayindex)
                node = self.get_node(objindex)
                self.writearray(array, index, node)
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
                length, content = actiondata
                array = self.create_array(length, content)
                self.stackroots.append(array)
            else:
                assert "unreachable"
            model, arraymodel, stackroots = action[-3:]
            self.check(model, arraymodel, stackroots)
        self.gc.collect()
        self.check(model, arraymodel, stackroots)

