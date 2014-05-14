import py
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.memory.gc.incminimark import IncrementalMiniMarkGC
from test_direct import BaseDirectGCTest

S = lltype.GcForwardReference()
S.become(lltype.GcStruct('pinning_test_struct',
                         ('someInt', lltype.Signed),
                         ('next', lltype.Ptr(S))))

class PinningGCTest(BaseDirectGCTest):

    def test_simple_pin(self):
        ptr = self.malloc(S)
        ptr.someInt = 100
        self.stackroots.append(ptr)

        adr = llmemory.cast_ptr_to_adr(ptr)
        assert self.gc.pin(adr)

        self.gc.collect()
        
        assert self.gc.is_in_nursery(adr)
        assert ptr.someInt == 100

    # XXX not implemented yet
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

    # XXX test with multiple mallocs, and only part of them is pinned
    # XXX test unpin()


class TestIncminimark(PinningGCTest):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass

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

    # XXX test/define what happens if we try to pin an object that is too
    # big for the nursery and will be raw-malloc'ed.

    # XXX test/define what happens if pinned object already has a shadow
    # => shadow handling.
