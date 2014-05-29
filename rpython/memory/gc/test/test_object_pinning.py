import py
from rpython.rtyper.lltypesystem import lltype, llmemory, llarena
from rpython.memory.gc.incminimark import IncrementalMiniMarkGC
from test_direct import BaseDirectGCTest

S = lltype.GcForwardReference()
S.become(lltype.GcStruct('pinning_test_struct',
                         ('someInt', lltype.Signed),
                         ('next', lltype.Ptr(S))))

class PinningGCTest(BaseDirectGCTest):

    def test_pin_can_move(self):
        # even a pinned object is considered to be movable. Only the caller
        # of pin() knows if it is currently movable or not.
        ptr = self.malloc(S)
        adr = llmemory.cast_ptr_to_adr(ptr)
        assert self.gc.can_move(adr)
        assert self.gc.pin(adr)
        assert self.gc.can_move(adr)

    def test_pin_twice(self):
        ptr = self.malloc(S)
        adr = llmemory.cast_ptr_to_adr(ptr)
        assert self.gc.pin(adr)
        assert not self.gc.pin(adr)

    def test_unpin_not_pinned(self):
        # this test checks a requirement of the unpin() interface
        ptr = self.malloc(S)
        py.test.raises(Exception,
            self.gc.unpin, llmemory.cast_ptr_to_adr(ptr))

    # XXX test with multiple mallocs, and only part of them is pinned

class TestIncminimark(PinningGCTest):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass

    def test_simple_pin(self):
        ptr = self.malloc(S)
        ptr.someInt = 100
        self.stackroots.append(ptr)

        adr = llmemory.cast_ptr_to_adr(ptr)
        assert self.gc.pin(adr)

        self.gc.collect()
        
        assert self.gc.is_in_nursery(adr)
        assert ptr.someInt == 100

    def test_simple_pin_unpin(self):
        ptr = self.malloc(S)
        ptr.someInt = 100
        self.stackroots.append(ptr)
        adr = llmemory.cast_ptr_to_adr(ptr)
        # check if pin worked
        assert self.gc.pin(adr)
        self.gc.collect()
        assert self.gc.is_in_nursery(adr)
        assert ptr.someInt == 100
        # unpin and check if object is gone from nursery
        self.gc.unpin(adr)
        self.gc.collect()
        py.test.raises(RuntimeError, 'ptr.someInt')
        ptr_old = self.stackroots[0]
        assert ptr_old.someInt == 100

    @py.test.mark.xfail(reason="Not implemented yet", run=False)
    def test_pin_referenced_from_stackroot(self):
        # XXX most likely somehow connected with `old_objects_pointing_to_young`
        # (groggi)
        root_ptr = self.malloc(S)
        next_ptr = self.malloc(S)
        self.write(root_ptr, 'next', next_ptr)
        self.stackroots.append(root_ptr)
        next_ptr.someInt = 100

        next_adr = llmemory.cast_ptr_to_adr(next_ptr)
        assert self.gc.pin(next_adr)

        self.gc.collect()

        assert self.gc.is_in_nursery(adr)
        assert next_ptr.someInt == 100
        root_ptr = self.stackroots[0]
        assert root_ptr.next == next_ptr

    def test_pin_old(self):
        ptr = self.malloc(S)
        ptr.someInt = 100
        self.stackroots.append(ptr)
        self.gc.collect()
        ptr = self.stackroots[0]
        adr = llmemory.cast_ptr_to_adr(ptr)
        assert ptr.someInt == 100
        assert not self.gc.is_in_nursery(adr)
        assert not self.gc.pin(adr)
        # ^^^ should not be possible, struct is already old and won't
        # move.

    def test_pin_malloc_pin(self):
        first_ptr = self.malloc(S)
        first_ptr.someInt = 101
        self.stackroots.append(first_ptr)
        assert self.gc.pin(llmemory.cast_ptr_to_adr(first_ptr))

        self.gc.collect()
        assert first_ptr.someInt == 101

        second_ptr = self.malloc(S)
        second_ptr.someInt = 102
        self.stackroots.append(second_ptr)
        assert self.gc.pin(llmemory.cast_ptr_to_adr(second_ptr))

        self.gc.collect()
        assert first_ptr.someInt == 101
        assert second_ptr.someInt == 102

    def test_pin_shadow_1(self):
        ptr = self.malloc(S)
        adr = llmemory.cast_ptr_to_adr(ptr)
        self.stackroots.append(ptr)
        ptr.someInt = 100
        assert self.gc.pin(adr)
        self.gc.id(ptr) # allocate shadow
        self.gc.minor_collection()
        assert self.gc.is_in_nursery(adr)
        assert ptr.someInt == 100
        self.gc.unpin(adr)
        self.gc.minor_collection() # move to shadow
        adr = llmemory.cast_ptr_to_adr(self.stackroots[0])
        assert not self.gc.is_in_nursery(adr)

    def test_pin_shadow_2(self):
        ptr = self.malloc(S)
        adr = llmemory.cast_ptr_to_adr(ptr)
        self.stackroots.append(ptr)
        ptr.someInt = 100
        assert self.gc.pin(adr)
        self.gc.identityhash(ptr) # allocate shadow
        self.gc.minor_collection()
        assert self.gc.is_in_nursery(adr)
        assert ptr.someInt == 100
        self.gc.unpin(adr)
        self.gc.minor_collection() # move to shadow
        adr = llmemory.cast_ptr_to_adr(self.stackroots[0])
        assert not self.gc.is_in_nursery(adr)

    def test_pin_shadow_3(self):
        ptr = self.malloc(S)
        adr = llmemory.cast_ptr_to_adr(ptr)
        ptr.someInt = 100 # not used, just nice to have for identification
        self.stackroots.append(ptr)
        self.gc.id(ptr) # allocate shadow

        assert self.gc.pin(adr)
        self.gc.minor_collection() # object stays in nursery
        assert self.gc.is_in_nursery(adr)

        self.gc.unpin(adr)
        # we still have a pinned object at the beginning. There is no space left
        # to malloc an object before the pinned one.
        assert self.gc.is_in_nursery(adr)
        assert self.gc.nursery_free == self.gc.nursery
        assert self.gc.nursery_top == self.gc.nursery

        self.gc.minor_collection()
        # we don't have a pinned object any more.  There is now space left at
        # the beginning of our nursery for new objects.
        adr = llmemory.cast_ptr_to_adr(self.stackroots[0])
        assert not self.gc.is_in_nursery(adr)
        assert self.gc.nursery_free == self.gc.nursery
        assert self.gc.nursery_top > self.gc.nursery

    def get_max_nursery_objects(self, TYPE):
        typeid = self.get_type_id(TYPE)
        size = self.gc.fixed_size(typeid) + self.gc.gcheaderbuilder.size_gc_header
        raw_size = llmemory.raw_malloc_usage(size)
        return self.gc.nursery_size // raw_size

    def test_full_pinned_nursery_pin_fail(self):
        object_mallocs = self.get_max_nursery_objects(S)
        for instance_nr in xrange(object_mallocs):
            ptr = self.malloc(S)
            adr = llmemory.cast_ptr_to_adr(ptr)
            ptr.someInt = 100 + instance_nr
            self.stackroots.append(ptr)
            self.gc.pin(adr)
        # nursery should be full now, at least no space for another `S`. Next malloc should fail.
        py.test.raises(Exception, self.malloc, S)


    # XXX test/define what happens if we try to pin an object that is too
    # big for the nursery and will be raw-malloc'ed.

    # XXX fill nursery with pinned objects -> + define behavior for such a
    # case
