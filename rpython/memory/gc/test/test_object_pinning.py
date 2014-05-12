import py
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.memory.gc.incminimark import IncrementalMiniMarkGC
from test_direct import BaseDirectGCTest

S = lltype.GcForwardReference()
S.become(lltype.GcStruct('S', ('someInt', lltype.Signed)))

class PinningGCTest(BaseDirectGCTest):

    def test_simple_pin(self):
        ptr = self.malloc(S)
        adr = llmemory.cast_ptr_to_adr(ptr)
        ptr.someInt = 100
        assert self.gc.pin(adr)
        self.gc.collect() # ptr should still live
        assert ptr.someInt == 100

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
