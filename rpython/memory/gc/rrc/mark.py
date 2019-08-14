from rpython.memory.gc.rrc.base import RawRefCountBaseGC
from rpython.rlib.debug import ll_assert, debug_print, debug_start, debug_stop

class RawRefCountMarkGC(RawRefCountBaseGC):

    def major_collection_trace_step(self):
        if not self.cycle_enabled:
            self._debug_check_consistency(print_label="begin-mark")

        if self.state == self.STATE_DEFAULT:
            self.state = self.STATE_MARKING

        # First, untrack all tuples with only non-gc rrc objects and promote
        # all other tuples to the pyobj_list
        self._untrack_tuples()

        # Only trace and mark rawrefcounted object if we are not doing
        # something special, like building gc.garbage.
        if (self.state == self.STATE_MARKING and self.cycle_enabled):
            merged_old_list = False
            # check objects with finalizers from last collection cycle
            if not self._gc_list_is_empty(self.pyobj_old_list):
                merged_old_list = self._check_finalizer()
            # collect all rawrefcounted roots
            self._collect_roots(self.pyobj_list)
            if merged_old_list:
                # set all refcounts to zero for objects in dead list
                # (might have been incremented) by fix_refcnt
                gchdr = self.pyobj_dead_list.c_gc_next
                while gchdr <> self.pyobj_dead_list:
                    gchdr.c_gc_refs = 0
                    gchdr = gchdr.c_gc_next
            self._debug_check_consistency(print_label="roots-marked")
            # mark all objects reachable from rawrefcounted roots
            self._mark_rawrefcount()
            self._debug_check_consistency(print_label="before-fin")
            self.state = self.STATE_GARBAGE_MARKING
            if self._find_garbage(): # handle legacy finalizers
                self._mark_garbage()
                self._debug_check_consistency(print_label="end-legacy-fin")
            self.state = self.STATE_MARKING
            found_finalizer = self._find_finalizer()
            if found_finalizer:
                self._gc_list_move(self.pyobj_old_list,
                                   self.pyobj_isolate_list)
            use_cylicrc = not found_finalizer
            self._debug_check_consistency(print_label="end-mark-cyclic")
        else:
            use_cylicrc = False # don't sweep any objects in cyclic isolates

        # now mark all pypy objects at the border, depending on the results
        debug_print("use_cylicrc", use_cylicrc)
        self.p_list_old.foreach(self._major_trace, (use_cylicrc, True))
        self._debug_check_consistency(print_label="end-mark")

        # fix refcnt back
        self.refcnt_dict.foreach(self._fix_refcnt_back, None)
        self.refcnt_dict.delete()
        self.refcnt_dict = self.gc.AddressDict()

        self.state = self.STATE_DEFAULT
        return True
