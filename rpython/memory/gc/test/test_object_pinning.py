import py
from rpython.rtyper.lltypesystem import lltype, llmemory, llarena
from rpython.memory.gc.incminimark import IncrementalMiniMarkGC, WORD
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

    def test__is_pinned(self):
        ptr = self.malloc(S)
        adr = llmemory.cast_ptr_to_adr(ptr)
        assert not self.gc._is_pinned(adr)
        assert self.gc.pin(adr)
        assert self.gc._is_pinned(adr)
        self.gc.unpin(adr)
        assert not self.gc._is_pinned(adr)

    # XXX test with multiple mallocs, and only part of them is pinned


class TestIncminimark(PinningGCTest):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass

    def simple_pin_stack(self, collect_func):
        # create object, pin it and point from stackroots to it
        ptr = self.malloc(S)
        ptr.someInt = 100
        self.stackroots.append(ptr)

        adr = llmemory.cast_ptr_to_adr(ptr)
        assert self.gc.pin(adr)

        collect_func()
        
        assert self.gc.is_in_nursery(adr)
        assert ptr.someInt == 100

    def test_simple_pin_stack_full_collect(self):
        self.simple_pin_stack(self.gc.collect)

    def test_simple_pin_stack_minor_collect(self):
        self.simple_pin_stack(self.gc.minor_collection)

    def simple_pin_unpin_stack(self, collect_func):
        ptr = self.malloc(S)
        ptr.someInt = 100
        
        self.stackroots.append(ptr)
        
        adr = llmemory.cast_ptr_to_adr(ptr)
        assert self.gc.pin(adr)
        
        collect_func()

        assert self.gc.is_in_nursery(adr)
        assert ptr.someInt == 100
        
        # unpin and check if object is gone from nursery
        self.gc.unpin(adr)
        collect_func()
        try:
            assert ptr.someInt == 100
            assert False
        except RuntimeError as ex:
            assert "freed" in str(ex)
        
        # check if we object is still accessible
        ptr_old = self.stackroots[0]
        assert not self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(ptr_old))
        assert ptr_old.someInt == 100

    def test_simple_pin_unpin_stack_full_collect(self):
        self.simple_pin_unpin_stack(self.gc.collect)

    def test_simple_pin_unpin_stack_minor_collect(self):
        self.simple_pin_unpin_stack(self.gc.minor_collection)

    def test_pinned_obj_collected_after_old_object_collected(self):
        root_ptr = self.malloc(S)
        root_ptr.someInt = 999
        self.stackroots.append(root_ptr)
        self.gc.collect()

        root_ptr = self.stackroots[0]
        next_ptr = self.malloc(S)
        next_ptr.someInt = 111
        assert self.gc.pin(llmemory.cast_ptr_to_adr(next_ptr))
        self.write(root_ptr, 'next', next_ptr)
        self.gc.collect()
        # check still alive
        assert self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(root_ptr.next))
        self.stackroots.remove(root_ptr)
        self.gc.collect()
        # root_ptr was collected and therefore also the pinned object should
        # be gone
        try:
            next_ptr.someInt = 101
            assert False
        except RuntimeError as ex:
            assert "freed" in str(ex)

    # XXX more tests like the one above. Make list of all possible cases and
    # write tests for each one. Also: minor/full major collection tests maybe
    # needed

    def test_pin_referenced_from_stackroot_young(self):
        #
        # create two objects and reference the pinned one
        # from the one that will be moved out of the
        # nursery.
        root_ptr = self.malloc(S)
        next_ptr = self.malloc(S)
        self.write(root_ptr, 'next', next_ptr)
        self.stackroots.append(root_ptr)
        #
        next_ptr.someInt = 100
        root_ptr.someInt = 999
        #
        next_adr = llmemory.cast_ptr_to_adr(next_ptr)
        assert self.gc.pin(next_adr)
        #
        # in this step the 'root_ptr' object will be
        # outside the nursery, pointing to the still
        # young (because it's pinned) 'next_ptr'.
        self.gc.collect()
        #
        root_ptr = self.stackroots[0]
        assert not self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(root_ptr))
        assert self.gc.is_in_nursery(next_adr)
        assert next_ptr.someInt == 100
        assert root_ptr.next == next_ptr
        #
        # now we remove the reference to the pinned object and do a collect
        # to check if the pinned object was removed from nursery.
        self.write(root_ptr, 'next', lltype.nullptr(S))
        self.gc.collect()
        try:
            # should fail as this was the pinned object that is now collected
            next_ptr.someInt = 0
            assert False
        except RuntimeError as ex:
            assert "freed" in str(ex)

    def test_old_points_to_pinned(self):
        # Test if we handle the case that an already old object can point
        # to a pinned object and keeps the pinned object alive by
        # that.
        #
        # create the old object that will point to a pinned object
        old_ptr = self.malloc(S)
        old_ptr.someInt = 999
        self.stackroots.append(old_ptr)
        self.gc.collect()
        assert not self.gc.is_in_nursery(
                llmemory.cast_ptr_to_adr(self.stackroots[0]))
        #
        # create the young pinned object and attach it to the old object
        pinned_ptr = self.malloc(S)
        pinned_ptr.someInt = 6
        assert self.gc.pin(llmemory.cast_ptr_to_adr(pinned_ptr))
        self.write(self.stackroots[0], 'next', pinned_ptr)
        #
        # let's check if everything stays in place before/after a collection
        assert self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(pinned_ptr))
        self.gc.collect()
        assert self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(pinned_ptr))
        #
        self.stackroots[0].next.someInt = 100
        self.gc.collect()
        assert self.stackroots[0].next.someInt == 100

    def not_pinned_and_stackroots_point_to_pinned(self, make_old):
        # In this test case we point to a pinned object from an (old) object
        # *and* from the stackroots
        obj_ptr = self.malloc(S)
        obj_ptr.someInt = 999
        self.stackroots.append(obj_ptr)
        if make_old:
            self.gc.collect()
            obj_ptr = self.stackroots[0]
            assert not self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(obj_ptr))
        else:
            assert self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(obj_ptr))

        pinned_ptr = self.malloc(S)
        pinned_ptr.someInt = 111
        assert self.gc.pin(llmemory.cast_ptr_to_adr(pinned_ptr))

        self.stackroots.append(pinned_ptr)
        self.write(obj_ptr, 'next', pinned_ptr)
        
        self.gc.collect()
        # done with preparation. do some basic checks
        assert self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(pinned_ptr))
        assert pinned_ptr.someInt == 111
        assert self.stackroots[0].next == pinned_ptr

    def test_old_and_stackroots_point_to_pinned(self):
        self.not_pinned_and_stackroots_point_to_pinned(make_old=True)

    def test_young_and_stackroots_point_to_pinned(self):
        self.not_pinned_and_stackroots_point_to_pinned(make_old=False)

    def test_old_points_to_old_points_to_pinned_1(self):
        #
        # Scenario:
        # stackroots points to 'root_ptr'. 'root_ptr' points to 'next_ptr'.
        # 'next_ptr' points to the young and pinned 'pinned_ptr'. Here we
        # remove the reference to 'next_ptr' from 'root_ptr' and check if it
        # behaves as expected.
        #
        root_ptr = self.malloc(S)
        root_ptr.someInt = 100
        self.stackroots.append(root_ptr)
        self.gc.collect()
        root_ptr = self.stackroots[0]
        #
        next_ptr = self.malloc(S)
        next_ptr.someInt = 200
        self.write(root_ptr, 'next', next_ptr)
        self.gc.collect()
        next_ptr = root_ptr.next
        #
        # check if everything is as expected
        assert not self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(root_ptr))
        assert not self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(next_ptr))
        assert root_ptr.someInt == 100
        assert next_ptr.someInt == 200
        #
        pinned_ptr = self.malloc(S)
        pinned_ptr.someInt = 300
        assert self.gc.pin(llmemory.cast_ptr_to_adr(pinned_ptr))
        self.write(next_ptr, 'next', pinned_ptr)
        self.gc.collect()
        #
        # validate everything is as expected with 3 rounds of GC collecting
        for _ in range(3):
            self.gc.collect()
            assert next_ptr.next == pinned_ptr
            assert self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(pinned_ptr))
            assert pinned_ptr.someInt == 300
            assert root_ptr.someInt == 100
            assert next_ptr.someInt == 200
        #
        # remove the reference to the pinned object
        self.write(next_ptr, 'next', root_ptr)
        self.gc.minor_collection()
        # the minor collection visits all old objects pointing to pinned ones.
        # therefore the pinned object should be gone
        try:
            pinned_ptr.someInt == 300
            assert False
        except RuntimeError as ex:
            assert "freed" in str(ex)

    def test_old_points_to_old_points_to_pinned_2(self):
        #
        # Scenario:
        # stackroots points to 'root_ptr'. 'root_ptr' points to 'next_ptr'.
        # 'next_ptr' points to the young and pinned 'pinned_ptr'. Here we
        # remove 'root_ptr' from the stackroots and check if it behaves as
        # expected.
        #
        root_ptr = self.malloc(S)
        root_ptr.someInt = 100
        self.stackroots.append(root_ptr)
        self.gc.collect()
        root_ptr = self.stackroots[0]
        #
        next_ptr = self.malloc(S)
        next_ptr.someInt = 200
        self.write(root_ptr, 'next', next_ptr)
        self.gc.collect()
        next_ptr = root_ptr.next
        #
        # check if everything is as expected
        assert not self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(root_ptr))
        assert not self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(next_ptr))
        assert root_ptr.someInt == 100
        assert next_ptr.someInt == 200
        #
        pinned_ptr = self.malloc(S)
        pinned_ptr.someInt = 300
        assert self.gc.pin(llmemory.cast_ptr_to_adr(pinned_ptr))
        self.write(next_ptr, 'next', pinned_ptr)
        self.gc.collect()
        #
        # validate everything is as expected with 3 rounds of GC collecting
        for _ in range(3):
            self.gc.collect()
            assert next_ptr.next == pinned_ptr
            assert self.gc.is_in_nursery(llmemory.cast_ptr_to_adr(pinned_ptr))
            assert pinned_ptr.someInt == 300
            assert root_ptr.someInt == 100
            assert next_ptr.someInt == 200
        #
        # remove the root from stackroots
        self.stackroots.remove(root_ptr)
        self.gc.minor_collection()
        #
        # the minor collection will still visit 'next_ptr', although
        # 'root_ptr' is not part of the stackroots anymore. This makes
        # sense as 'next_ptr' is removed only in the next major collection
        assert next_ptr.next.someInt == 300
        #
        # now we do a major collection and everything should be gone
        self.gc.collect()
        try:
            pinned_ptr.someInt == 300
            assert False
        except RuntimeError as ex:
            assert "freed" in str(ex)


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

    def pin_shadow_1(self, collect_func):
        ptr = self.malloc(S)
        adr = llmemory.cast_ptr_to_adr(ptr)
        self.stackroots.append(ptr)
        ptr.someInt = 100
        assert self.gc.pin(adr)
        self.gc.id(ptr) # allocate shadow
        collect_func()
        assert self.gc.is_in_nursery(adr)
        assert ptr.someInt == 100
        self.gc.unpin(adr)
        collect_func() # move to shadow
        adr = llmemory.cast_ptr_to_adr(self.stackroots[0])
        assert not self.gc.is_in_nursery(adr)

    def test_pin_shadow_1_minor(self):
        self.pin_shadow_1(self.gc.minor_collection)

    def test_pin_shadow_1_full(self):
        self.pin_shadow_1(self.gc.collect)

    def pin_shadow_2(self, collect_func):
        ptr = self.malloc(S)
        adr = llmemory.cast_ptr_to_adr(ptr)
        self.stackroots.append(ptr)
        ptr.someInt = 100
        assert self.gc.pin(adr)
        self.gc.identityhash(ptr) # allocate shadow
        collect_func()
        assert self.gc.is_in_nursery(adr)
        assert ptr.someInt == 100
        self.gc.unpin(adr)
        collect_func() # move to shadow
        adr = llmemory.cast_ptr_to_adr(self.stackroots[0])
        assert not self.gc.is_in_nursery(adr)

    def test_pin_shadow_2_minor(self):
        self.pin_shadow_2(self.gc.minor_collection)

    def test_pin_shadow_2_full(self):
        self.pin_shadow_2(self.gc.collect)

    def test_pin_nursery_top_scenario1(self):
        ptr1 = self.malloc(S)
        adr1 = llmemory.cast_ptr_to_adr(ptr1)
        ptr1.someInt = 101
        self.stackroots.append(ptr1)
        assert self.gc.pin(adr1)
        
        ptr2 = self.malloc(S)
        adr2 = llmemory.cast_ptr_to_adr(ptr2)
        ptr2.someInt = 102
        self.stackroots.append(ptr2)
        assert self.gc.pin(adr2)

        ptr3 = self.malloc(S)
        adr3 = llmemory.cast_ptr_to_adr(ptr3)
        ptr3.someInt = 103
        self.stackroots.append(ptr3)
        assert self.gc.pin(adr3)

        # scenario: no minor collection happened, only three mallocs
        # and pins
        #
        # +- nursery                           nursery_real_top -+
        # |                                                      |
        # v                                                      v
        # +--------+--------+--------+---------------------...---+
        # | pinned | pinned | pinned | empty                     |
        # +--------+--------+--------+---------------------...---+
        #                            ^                           ^
        #                            |                           |
        #              nursery_free -+                           |
        #                                           nursery_top -+
        #
        assert adr3 < self.gc.nursery_free
        assert self.gc.nursery_free < self.gc.nursery_top
        assert self.gc.nursery_top == self.gc.nursery_real_top

    def test_pin_nursery_top_scenario2(self):
        ptr1 = self.malloc(S)
        adr1 = llmemory.cast_ptr_to_adr(ptr1)
        ptr1.someInt = 101
        self.stackroots.append(ptr1)
        assert self.gc.pin(adr1)
        
        ptr2 = self.malloc(S)
        adr2 = llmemory.cast_ptr_to_adr(ptr2)
        ptr2.someInt = 102
        self.stackroots.append(ptr2)
        assert self.gc.pin(adr2)

        ptr3 = self.malloc(S)
        adr3 = llmemory.cast_ptr_to_adr(ptr3)
        ptr3.someInt = 103
        self.stackroots.append(ptr3)
        assert self.gc.pin(adr3)

        # scenario: after first GC minor collection
        #
        # +- nursery                           nursery_real_top -+
        # |                                                      |
        # v                                                      v
        # +--------+--------+--------+---------------------...---+
        # | pinned | pinned | pinned | empty                     |
        # +--------+--------+--------+---------------------...---+
        # ^
        # |
        # +- nursery_free
        # +- nursery_top
        #
        self.gc.collect()

        assert self.gc.nursery_free == self.gc.nursery_top
        assert self.gc.nursery_top == self.gc.nursery
        assert self.gc.nursery_top < adr3
        assert adr3 < self.gc.nursery_real_top

    def test_pin_nursery_top_scenario3(self):
        ptr1 = self.malloc(S)
        adr1 = llmemory.cast_ptr_to_adr(ptr1)
        ptr1.someInt = 101
        self.stackroots.append(ptr1)
        assert self.gc.pin(adr1)
        
        ptr2 = self.malloc(S)
        adr2 = llmemory.cast_ptr_to_adr(ptr2)
        ptr2.someInt = 102
        self.stackroots.append(ptr2)
        assert self.gc.pin(adr2)

        ptr3 = self.malloc(S)
        adr3 = llmemory.cast_ptr_to_adr(ptr3)
        ptr3.someInt = 103
        self.stackroots.append(ptr3)
        assert self.gc.pin(adr3)

        # scenario: after unpinning first object and a minor
        # collection
        #
        # +- nursery                           nursery_real_top -+
        # |                                                      |
        # v                                                      v
        # +--------+--------+--------+---------------------...---+
        # | empty  | pinned | pinned | empty                     |
        # +--------+--------+--------+---------------------...---+
        # ^        ^
        # |        |
        # |        +- nursery_top
        # +- nursery_free
        #
        self.gc.unpin(adr1)
        self.gc.collect()

        assert self.gc.nursery_free == self.gc.nursery
        assert self.gc.nursery_top > self.gc.nursery_free
        assert self.gc.nursery_top < adr2
        assert adr3 < self.gc.nursery_real_top

    def test_pin_nursery_top_scenario4(self):
        ptr1 = self.malloc(S)
        adr1 = llmemory.cast_ptr_to_adr(ptr1)
        ptr1.someInt = 101
        self.stackroots.append(ptr1)
        assert self.gc.pin(adr1)
        
        ptr2 = self.malloc(S)
        adr2 = llmemory.cast_ptr_to_adr(ptr2)
        ptr2.someInt = 102
        self.stackroots.append(ptr2)
        assert self.gc.pin(adr2)

        ptr3 = self.malloc(S)
        adr3 = llmemory.cast_ptr_to_adr(ptr3)
        ptr3.someInt = 103
        self.stackroots.append(ptr3)
        assert self.gc.pin(adr3)

        # scenario: after unpinning first & second object and a minor
        # collection
        #
        # +- nursery                           nursery_real_top -+
        # |                                                      |
        # v                                                      v
        # +-----------------+--------+---------------------...---+
        # | empty           | pinned | empty                     |
        # +-----------------+--------+---------------------...---+
        # ^                 ^
        # |                 |
        # |                 +- nursery_top
        # +- nursery_free
        #
        self.gc.unpin(adr1)
        self.gc.unpin(adr2)
        self.gc.collect()

        assert self.gc.nursery_free == self.gc.nursery
        assert self.gc.nursery_free < self.gc.nursery_top
        assert self.gc.nursery_top < adr3
        assert adr3 < self.gc.nursery_real_top
        
    def test_pin_nursery_top_scenario5(self):
        ptr1 = self.malloc(S)
        adr1 = llmemory.cast_ptr_to_adr(ptr1)
        ptr1.someInt = 101
        self.stackroots.append(ptr1)
        assert self.gc.pin(adr1)
        
        ptr2 = self.malloc(S)
        adr2 = llmemory.cast_ptr_to_adr(ptr2)
        ptr2.someInt = 102
        self.stackroots.append(ptr2)
        assert self.gc.pin(adr2)

        ptr3 = self.malloc(S)
        adr3 = llmemory.cast_ptr_to_adr(ptr3)
        ptr3.someInt = 103
        self.stackroots.append(ptr3)
        assert self.gc.pin(adr3)

        # scenario: no minor collection happened, only three mallocs
        # and pins
        #
        # +- nursery                           nursery_real_top -+
        # |                                                      |
        # v                                                      v
        # +--------+--------+--------+---------------------...---+
        # | pinned | pinned | pinned | empty                     |
        # +--------+--------+--------+---------------------...---+
        #                            ^                           ^
        #                            |                           |
        #              nursery_free -+                           |
        #                                           nursery_top -+
        #
        assert adr3 < self.gc.nursery_free
        assert self.gc.nursery_free < self.gc.nursery_top
        assert self.gc.nursery_top == self.gc.nursery_real_top

        # scenario: unpin everything and minor collection
        #
        # +- nursery                           nursery_real_top -+
        # |                                                      |
        # v                                                      v
        # +----------------------------------+-------------...---+
        # | reset arena                      | empty (not reset) |
        # +----------------------------------+-------------...---+
        # ^                                  ^
        # |                                  |
        # +- nursery_free                    |
        #                       nursery_top -+
        #
        self.gc.unpin(adr1)
        self.gc.unpin(adr2)
        self.gc.unpin(adr3)
        self.gc.collect()

        assert self.gc.nursery_free == self.gc.nursery
        # the following assert is important: make sure that
        # we did not reset the whole nursery
        assert self.gc.nursery_top < self.gc.nursery_real_top

    def test_collect_dead_pinned_objects(self):
        # prepare three object, where two are stackroots
        ptr_stackroot_1 = self.malloc(S)
        ptr_stackroot_1.someInt = 100
        self.stackroots.append(ptr_stackroot_1)

        ptr_not_stackroot = self.malloc(S)

        ptr_stackroot_2 = self.malloc(S)
        ptr_stackroot_2.someInt = 100
        self.stackroots.append(ptr_stackroot_2)

        # pin all three objects
        assert self.gc.pin(llmemory.cast_ptr_to_adr(ptr_stackroot_1))
        assert self.gc.pin(llmemory.cast_ptr_to_adr(ptr_not_stackroot))
        assert self.gc.pin(llmemory.cast_ptr_to_adr(ptr_stackroot_2))
        assert self.gc.pinned_objects_in_nursery == 3

        self.gc.collect()
        # now the one not on the stack should be gone.
        assert self.gc.pinned_objects_in_nursery == 2
        assert ptr_stackroot_1.someInt == 100
        assert ptr_stackroot_2.someInt == 100
        try:
            ptr_not_stackroot.someInt = 100
            assert False
        except RuntimeError as ex:
            assert "freed" in str(ex)

    def fill_nursery_with_pinned_objects(self):
        typeid = self.get_type_id(S)
        size = self.gc.fixed_size(typeid) + self.gc.gcheaderbuilder.size_gc_header
        raw_size = llmemory.raw_malloc_usage(size)
        object_mallocs = self.gc.nursery_size // raw_size
        for instance_nr in xrange(object_mallocs):
            ptr = self.malloc(S)
            adr = llmemory.cast_ptr_to_adr(ptr)
            ptr.someInt = 100 + instance_nr
            self.stackroots.append(ptr)
            self.gc.pin(adr)

    def test_full_pinned_nursery_pin_fail(self):
        self.fill_nursery_with_pinned_objects()
        # nursery should be full now, at least no space for another `S`. Next malloc should fail.
        py.test.raises(Exception, self.malloc, S)

    def test_full_pinned_nursery_arena_reset(self):
        # there were some bugs regarding the 'arena_reset()' calls at
        # the end of the minor collection.  This test brought them to light.
        self.fill_nursery_with_pinned_objects()
        self.gc.collect()

    def test_pinning_limit(self):
        for instance_nr in xrange(self.gc.max_number_of_pinned_objects):
            ptr = self.malloc(S)
            adr = llmemory.cast_ptr_to_adr(ptr)
            ptr.someInt = 100 + instance_nr
            self.stackroots.append(ptr)
            self.gc.pin(adr)
        #
        # now we reached the maximum amount of pinned objects
        ptr = self.malloc(S)
        adr = llmemory.cast_ptr_to_adr(ptr)
        self.stackroots.append(ptr)
        assert not self.gc.pin(adr)
    test_pinning_limit.GC_PARAMS = {'max_number_of_pinned_objects': 5}

    def test_full_pinned_nursery_pin_fail(self):
        typeid = self.get_type_id(S)
        size = self.gc.fixed_size(typeid) + self.gc.gcheaderbuilder.size_gc_header
        raw_size = llmemory.raw_malloc_usage(size)
        object_mallocs = self.gc.nursery_size // raw_size
        # just to be sure we do not run into the limit as we test not the limiter
        # but rather the case of a nursery full with pinned objects.
        assert object_mallocs < self.gc.max_number_of_pinned_objects
        for instance_nr in xrange(object_mallocs):
            ptr = self.malloc(S)
            adr = llmemory.cast_ptr_to_adr(ptr)
            ptr.someInt = 100 + instance_nr
            self.stackroots.append(ptr)
            self.gc.pin(adr)
        #
        # nursery should be full now, at least no space for another `S`. Next malloc should fail.
        py.test.raises(Exception, self.malloc, S)
    test_full_pinned_nursery_pin_fail.GC_PARAMS = {'max_number_of_pinned_objects': 50}
