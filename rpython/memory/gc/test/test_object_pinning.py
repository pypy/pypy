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
        self.gc.collect()
        assert ptr.someInt == 100

    def test_pin_shadow_2(self):
        ptr = self.malloc(S)
        adr = llmemory.cast_ptr_to_adr(ptr)
        self.stackroots.append(ptr)
        ptr.someInt = 100
        assert self.gc.pin(adr)
        self.gc.identityhash(ptr) # allocate shadow
        self.gc.collect()
        assert ptr.someInt == 100

    def test_pin_shadow_3(self):
        s = self.malloc(S)
        self.stackroots.append(s)
        self.gc.id(s) # allocate shadow
        self.gc.pin(llmemory.cast_ptr_to_adr(s))
        
        print("free: %s" % self.gc.nursery_free)
        print("top: %s" % self.gc.nursery_top)
        self.gc.minor_collection()
        # XXX it seems like we adjust nursery_free wrong after the minor
        # collection or there is some other bug. (groggi)
        print("free: %s" % self.gc.nursery_free)
        print("top: %s" % self.gc.nursery_top)

        self.gc.unpin(llmemory.cast_ptr_to_adr(s))
        assert self.gc.nursery_free != self.gc.nursery
        # we still have a pinned object
        self.gc.minor_collection()
        assert self.gc.nursery_free == self.gc.nursery
        # we don't have a pinned object any more

    # XXX test/define what happens if we try to pin an object that is too
    # big for the nursery and will be raw-malloc'ed.

    # XXX test/define what happens if pinned object already has a shadow
    # => shadow handling.

    # XXX fill nursery with pinned objects -> + define behavior for such a
    # case
