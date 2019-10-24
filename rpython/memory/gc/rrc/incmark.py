from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem import rffi
from rpython.memory.gc.rrc.base import RawRefCountBaseGC
from rpython.rlib.debug import ll_assert, debug_print, debug_start, debug_stop
import time

class RawRefCountIncMarkGC(RawRefCountBaseGC):

    def major_collection_trace_step(self):
        if (not self.cycle_enabled or self.state == self.STATE_GARBAGE or
                not self._gc_list_is_empty(self.pyobj_isolate_list)):
            self._debug_check_consistency(print_label="begin-mark")
            self.p_list_old.foreach(self._major_trace, (False, False))
            self._debug_check_consistency(print_label="end-mark")
            return True

        if self.state == self.STATE_DEFAULT:
            # untrack all tuples with only non-gc rrc objects and
            # promote all other tuples to the pyobj_list
            self._untrack_tuples() # execute incrementally?

            # now take a snapshot
            self._take_snapshot()
            self._debug_print_snap(print_label="after-snapshot")

            self.state = self.STATE_MARKING
            self.marking_state = 0
            return False

        if self.state == self.STATE_MARKING:
            if self.marking_state == 0:
                # collect all rawrefcounted roots
                self._collect_roots() # execute incrementally (save index)?
                self._debug_print_snap(print_label="roots-marked")
                self._debug_check_consistency(print_label="roots-marked")
                self._gc_list_init(self.pyobj_old_list)
                self.marking_state = 1
                return False
            elif self.marking_state == 1:
                # initialize working set from roots, then pause
                self.pyobj_to_trace = self.gc.AddressStack()
                for i in range(0, self.total_objs):
                    obj = self.snapshot_objs[i]
                    self._mark_rawrefcount_obj(obj)
                self.p_list_old.foreach(self._mark_rawrefcount_linked, None)
                self.o_list_old.foreach(self._mark_rawrefcount_linked, None)
                self.marking_state = 2
                return False
            else:
                # mark all objects reachable from rawrefcounted roots
                all_rrc_marked = self._mark_rawrefcount()
                if (all_rrc_marked and not self.gc.objects_to_trace.non_empty() and
                        not self.gc.more_objects_to_trace.non_empty()):
                    # all objects have been marked, dead objects will stay dead
                    self._debug_print_snap(print_label="before-fin")
                    self._debug_check_consistency(print_label="before-fin")
                    self.state = self.STATE_GARBAGE_MARKING
                else:
                    return False

        # we are finished with marking, now finish things up
        ll_assert(self.state == self.STATE_GARBAGE_MARKING, "invalid state")

        start = time.time()

        # sync snapshot
        self._sync_snapshot()
        self._debug_check_consistency(print_label="before-snap-discard")

        debug_print("time snapshot sync", time.time() - start)
        start = time.time()

        # now the snapshot is not needed any more, discard it
        self._discard_snapshot()

        debug_print("time discard snapshot", time.time() - start)
        start = time.time()

        # handle legacy finalizers (assumption: not a lot of legacy finalizers,
        # so no need to do it incrementally)
        if self._find_garbage(False):
            self._mark_garbage(False)
            self._debug_check_consistency(print_label="end-legacy-fin")
        self.state = self.STATE_DEFAULT

        debug_print("time legacy finalizer", time.time() - start)
        start = time.time()

        # handle modern finalizers
        found_finalizer = self._find_finalizer()
        if found_finalizer:
            self._gc_list_move(self.pyobj_old_list, self.pyobj_isolate_list)
        use_cylicrc = not found_finalizer

        debug_print("time modern finalizer", time.time() - start)
        start = time.time()

        # now mark all pypy objects at the border, depending on the results
        self._debug_check_consistency(print_label="end-mark-cyclic")
        debug_print("use_cylicrc", use_cylicrc)
        self.p_list_old.foreach(self._major_trace, (use_cylicrc, False))
        self._debug_check_consistency(print_label="end-mark")

        debug_print("time mark p_list_old", time.time() - start)
        return True

    def _sync_snapshot(self):
        # sync snapshot with pyob_list:
        #  * check the consistency of "dead" objects and keep all of them
        #    alive, in case an inconsistency is found (the graph changed
        #    between two pauses, so some of those objects might be alive)
        #  * move all dead objects still in pyob_list to pyobj_old_list
        #  * for all other objects (in snapshot and new),
        #    set their cyclic refcount to > 0 to mark them as live
        consistent = True
        self.snapshot_consistent = True

        start = time.time()

        # sync p_list_old (except gc-objects)
        # simply iterate the snapshot for objects in p_list, as linked objects
        # might not be freed, except by the gc; p_list is always at the
        # beginning of the snapshot, so break if we reached a different pyobj
        for i in range(0, self.total_objs):
            snapobj = self.snapshot_objs[i]
            if snapobj.pypy_link == 0:
                break  # only look for objects in p_list
            pyobj = llmemory.cast_adr_to_ptr(snapobj.pyobj, self.PYOBJ_HDR_PTR)
            pygchdr = self.pyobj_as_gc(pyobj)
            if (pygchdr != lltype.nullptr(self.PYOBJ_GC_HDR) and
                    pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_UNTRACKED and
                    pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_REACHABLE):
                break  # only look for non-gc
            addr = llmemory.cast_int_to_adr(snapobj.pypy_link)
            if (self.gc.header(addr).tid &
                    (self.GCFLAG_VISITED | self.GCFLAG_NO_HEAP_PTRS)):
                continue # keep proxy if obj is marked
            if snapobj.refcnt == 0:
                # check consistency
                consistent = pyobj.c_ob_refcnt == snapobj.refcnt_original
                if not consistent:
                    break
                # move to separate list
                #self.p_list_old.remove(snapobj.pyobj) # TODO: this might be evil... do something different... -> unlink? special link?

                # remove link, to free non-gc (so they won't get marked and are freed)
                pyobj = llmemory.cast_adr_to_ptr(snapobj.pyobj, self.PYOBJ_HDR_PTR)
                link = llmemory.cast_int_to_adr(pyobj.c_ob_pypy_link)
                self.p_dict_old_free.setitem(snapobj.pyobj, link)
                pyobj.c_ob_pypy_link = 0
                debug_print("free p_list", pyobj, "refcnt", pyobj.c_ob_refcnt)

        debug_print("time sync p_list_old", time.time() - start)
        start = time.time()

        # look if there is a (newly) linked non-gc proxy, where the non-rc obj
        # is unmarked
        self.p_list_old_consistent = True
        self.p_list_old.foreach(self._check_consistency_p_list_old, None)
        consistent &= self.p_list_old_consistent

        debug_print("time consistency p_list_old", time.time() - start)
        start = time.time()

        # sync gc objects
        pygchdr = self.pyobj_list.c_gc_next
        while pygchdr <> self.pyobj_list and consistent:
            next_old = pygchdr.c_gc_next
            if pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_REACHABLE and \
                    pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_UNTRACKED:  # object is in snapshot
                consistent = self._check_consistency_gc(pygchdr,
                                                        self.pyobj_old_list)
                if not consistent:
                    break
            else:
                # new object, keep alive
                self._pyobj_gc_refcnt_set(pygchdr, 1)
                #pygchdr.c_gc_refs = 1 << self.RAWREFCOUNT_REFS_SHIFT
                pyobj = self.gc_as_pyobj(pygchdr)
                if pyobj.c_ob_pypy_link != 0:
                    addr = llmemory.cast_int_to_adr(pyobj.c_ob_pypy_link)
                    if not (self.gc.header(addr).tid &
                            (self.GCFLAG_VISITED | self.GCFLAG_NO_HEAP_PTRS)):
                        consistent = False
                        debug_print("inconsistency found",
                                    "marked new object", pyobj)
                        break
            pygchdr = next_old
        pygchdr_continue_gc = pygchdr


        debug_print("time sync gc objs", time.time() - start)
        start = time.time()

        # sync isolate objs
        debug_print("check isolate")
        isolate_consistent = True
        pygchdr = self.pyobj_isolate_old_list.c_gc_next
        while pygchdr <> self.pyobj_isolate_old_list and isolate_consistent:
            next_old = pygchdr.c_gc_next
            isolate_consistent = \
                self._check_consistency_gc(pygchdr,
                                           self.pyobj_isolate_dead_list)
            pygchdr = next_old
        pygchdr_continue_isolate = pygchdr
        consistent &= isolate_consistent
        self._debug_check_consistency(print_label="end-check-consistency")

        debug_print("time sync isolate objs", time.time() - start)
        start = time.time()

        if consistent:
            debug_print("consistent")
        else:
            debug_print("inconsistent")
            # fix link
            self.p_dict_old_free.foreach(self._fix_p_list, None)
            # continue previous loop, keep objects alive
            pygchdr = pygchdr_continue_gc
            while pygchdr <> self.pyobj_list:
                self._pyobj_gc_refcnt_set(pygchdr, 1)
                #pygchdr.c_gc_refs = 1 << self.RAWREFCOUNT_REFS_SHIFT
                pygchdr = pygchdr.c_gc_next
            pygchdr = self.pyobj_old_list.c_gc_next
            # resurrect "dead" objects
            while pygchdr <> self.pyobj_old_list:
                self._pyobj_gc_refcnt_set(pygchdr, 1)
                #pygchdr.c_gc_refs = 1 << self.RAWREFCOUNT_REFS_SHIFT
                pygchdr = pygchdr.c_gc_next
            # merge lists
            if not self._gc_list_is_empty(self.pyobj_old_list):
                self._gc_list_merge(self.pyobj_old_list, self.pyobj_list)

        self.p_dict_old_free.delete()
        self.p_dict_old_free = self.gc.AddressDict()

        debug_print("time free/inconsistent", time.time() - start)
        start = time.time()

        if isolate_consistent:
            if not self._gc_list_is_empty(self.pyobj_isolate_old_list):
                self._gc_list_merge(self.pyobj_isolate_old_list,
                                    self.pyobj_list)
            if not self._gc_list_is_empty(self.pyobj_isolate_dead_list):
                self._gc_list_merge(self.pyobj_isolate_dead_list,
                                    self.pyobj_dead_list)
        else:
            # continue previous loop, keep objects alive
            pygchdr = pygchdr_continue_isolate
            while pygchdr <> self.pyobj_isolate_old_list:
                self._pyobj_gc_refcnt_set(pygchdr, 1)
                #pygchdr.c_gc_refs = 1 << self.RAWREFCOUNT_REFS_SHIFT
                pygchdr = pygchdr.c_gc_next
            # resurrect "dead" objects
            while pygchdr <> self.pyobj_isolate_dead_list:
                self._pyobj_gc_refcnt_set(pygchdr, 1)
                #pygchdr.c_gc_refs = 1 << self.RAWREFCOUNT_REFS_SHIFT
                pygchdr = pygchdr.c_gc_next
            # merge lists
            if not self._gc_list_is_empty(self.pyobj_isolate_old_list):
                self._gc_list_merge(self.pyobj_isolate_old_list,
                                    self.pyobj_list)
            if not self._gc_list_is_empty(self.pyobj_isolate_dead_list):
                self._gc_list_merge(self.pyobj_isolate_dead_list,
                                    self.pyobj_list)

        debug_print("time sync isolate", time.time() - start)

    def _check_consistency_gc(self, pygchdr, pylist_dead_target):
        c_gc_refs = self._pyobj_gc_refcnt_get(pygchdr)
        snapobj = self.snapshot_objs[c_gc_refs - 1]
        #snapobj = self.snapshot_objs[pygchdr.c_gc_refs - 1]
        self._pyobj_gc_refcnt_set(pygchdr, snapobj.refcnt)
        #pygchdr.c_gc_refs = snapobj.refcnt
        if snapobj.refcnt == 0:  # object considered dead
            # check consistency (dead subgraphs can never change):
            pyobj = self.gc_as_pyobj(pygchdr)
            # refcount equal
            consistent = snapobj.refcnt_original == pyobj.c_ob_refcnt
            if not consistent:
                debug_print("inconsistency found", "refcount not equal", pyobj)
                return False
            # outgoing (internal) references equal
            self.snapshot_curr = snapobj
            self.snapshot_curr_index = 0
            self._check_snapshot_traverse(pyobj)
            consistent = self.snapshot_consistent
            if not consistent:
                debug_print("inconsistency found", "references not equal", pyobj)
                return False
            # consistent -> prepare object for collection
            self._gc_list_remove(pygchdr)
            self._gc_list_add(pylist_dead_target, pygchdr)
        return True

    def _debug_print_snap(self, print_label=None):
        debug_start("snap " + print_label)
        for i in range(0, self.total_objs):
            snapobj = self.snapshot_objs[i]
            debug_print("item", snapobj.pyobj, ": snapobj", snapobj,
                        "refcnt", snapobj.refcnt,
                        "refcnt original", snapobj.refcnt_original,
                        "link", snapobj.pypy_link)
        debug_stop("snap " + print_label)

    def _check_consistency_p_list_old(self, pyobject, foo):
        pyobj = llmemory.cast_adr_to_ptr(pyobject, self.PYOBJ_HDR_PTR)
        pygchdr = self.pyobj_as_gc(pyobj)
        if (pygchdr == lltype.nullptr(self.PYOBJ_GC_HDR) and
                pyobj.c_ob_pypy_link != 0):
            addr = llmemory.cast_int_to_adr(pyobj.c_ob_pypy_link)
            if not (self.gc.header(addr).tid &
                    (self.GCFLAG_VISITED | self.GCFLAG_NO_HEAP_PTRS)):
                self.p_list_old_consistent = False
                debug_print("inconsistency found", "marked p_list", pyobj)

    def _fix_p_list(self, pyobject, addr_link, foo):
        pyobj = llmemory.cast_adr_to_ptr(pyobject, self.PYOBJ_HDR_PTR)
        pyobj.c_ob_pypy_link = llmemory.cast_adr_to_int(addr_link, "symbolic")

    def _collect_roots(self):
        # Subtract all internal refcounts from the cyclic refcount
        # of rawrefcounted objects
        for i in range(0, self.total_objs):
            obj = self.snapshot_objs[i]
            for j in range(0, obj.refs_len):
                addr = self.snapshot_refs[obj.refs_index + j]
                obj_ref = llmemory.cast_adr_to_ptr(addr,
                                                   self.PYOBJ_SNAPSHOT_OBJ_PTR)
                if obj_ref != lltype.nullptr(self.PYOBJ_SNAPSHOT_OBJ):
                    obj_ref.refcnt -= 1

        # now all rawrefcounted roots or live border objects have a
        # refcount > 0

    def _mark_rawrefcount(self):
        # as long as new objects with cyclic a refcount > 0 or alive border
        # objects are found, increment the refcount of all referenced objects
        # of those newly found objects
        reached_limit = False
        simple_limit = 0
        first = True # rescan proxies, in case only non-rc have been marked
        #
        while self.p_list_old_added.non_empty():
            addr = self.p_list_old_added.pop()
            pyobj = llmemory.cast_adr_to_ptr(addr, self.PYOBJ_HDR_PTR)
            obj = llmemory.cast_int_to_adr(pyobj.c_ob_pypy_link)
            debug_print("trace p_list", pyobj)
            self.gc.objects_to_trace.append(obj)
        #
        while first or (self.pyobj_to_trace.non_empty() and not reached_limit):
            while self.pyobj_to_trace.non_empty() and not reached_limit:
                addr = self.pyobj_to_trace.pop()
                snapobj = llmemory.cast_adr_to_ptr(addr,
                                                   self.PYOBJ_SNAPSHOT_OBJ_PTR)
                snapobj.refcnt += 1
                self._mark_rawrefcount_obj(snapobj)
                simple_limit += 1
                if simple_limit > self.inc_limit: # TODO: add test
                    reached_limit = True
            self.gc.visit_all_objects()  # TODO: implement sane limit (ex. half of normal limit), retrace proxies
            self.p_list_old.foreach(self._mark_rawrefcount_linked, None)
            self.o_list_old.foreach(self._mark_rawrefcount_linked, None)
            first = False
        return not reached_limit # are there any objects left?

    def _mark_rawrefcount_obj(self, snapobj):
        if snapobj.status == 0: # already processed
            return False

        alive = snapobj.refcnt > 0
        if snapobj.pypy_link <> 0:
            intobj = snapobj.pypy_link
            obj = llmemory.cast_int_to_adr(intobj)
            if not alive and self.gc.header(obj).tid & (
                    self.GCFLAG_VISITED | self.GCFLAG_NO_HEAP_PTRS):
                alive = True
                snapobj.refcnt += 1
        if alive:
            # increment refcounts
            for j in range(0, snapobj.refs_len):
                addr = self.snapshot_refs[snapobj.refs_index + j]
                obj_ref = llmemory.cast_adr_to_ptr(addr,
                                                   self.PYOBJ_SNAPSHOT_OBJ_PTR)
                if obj_ref != lltype.nullptr(self.PYOBJ_SNAPSHOT_OBJ):
                    if obj_ref.refcnt == 0:
                        addr = llmemory.cast_ptr_to_adr(obj_ref)
                        self.pyobj_to_trace.append(addr)
                    else:
                        obj_ref.refcnt += 1
            # mark recursively, if it is a pypyobj
            if snapobj.pypy_link <> 0:
                intobj = snapobj.pypy_link
                obj = llmemory.cast_int_to_adr(intobj)
                self.gc.objects_to_trace.append(obj)
            # mark as processed
            snapobj.status = 0
        return alive

    def _mark_rawrefcount_linked(self, pyobject, ignore):
        # we only have to take gc-objs into consideration, rc-proxies only
        # keep their non-rc objs alive (see _major_free)
        pyobj = self._pyobj(pyobject)
        addr = llmemory.cast_int_to_adr(pyobj.c_ob_pypy_link)
        if self.gc.header(addr).tid & (self.GCFLAG_VISITED |
                                       self.GCFLAG_NO_HEAP_PTRS):
            pygchdr = self.pyobj_as_gc(pyobj)
            if (pygchdr != lltype.nullptr(self.PYOBJ_GC_HDR) and
                    #c_gc_refs > 0 and
                    pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_UNTRACKED and
                    pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_REACHABLE):
                c_gc_refs = self._pyobj_gc_refcnt_get(pygchdr)
                index = c_gc_refs - 1
                snapobj = self.snapshot_objs[index]
                if snapobj.refcnt == 0:
                    addr = llmemory.cast_ptr_to_adr(snapobj)
                    self.pyobj_to_trace.append(addr)

    def _take_snapshot(self):
        total_refcnt = 0
        total_objs = 0

        # calculate size of memory buffer for snapshot
        pygchdr = self.pyobj_list.c_gc_next
        while pygchdr <> self.pyobj_list:
            total_refcnt += self._take_snapshot_count_gc(pygchdr)
            total_objs += 1
            pygchdr = pygchdr.c_gc_next
        pygchdr = self.tuple_list.c_gc_next
        while pygchdr <> self.tuple_list:
            total_refcnt += self._take_snapshot_count_gc(pygchdr)
            pygchdr = pygchdr.c_gc_next
        pygchdr = self.pyobj_isolate_old_list.c_gc_next
        while pygchdr <> self.pyobj_isolate_old_list:
            total_refcnt += self._take_snapshot_count_gc(pygchdr)
            total_objs += 1
            pygchdr = pygchdr.c_gc_next
        self.p_list_count = 0
        self.p_list_refcnt = 0
        self.p_list_old.foreach(self._take_snapshot_count, None)
        total_objs += self.p_list_count
        total_refcnt += self.p_list_refcnt

        # initialize memory
        self.snapshot_refs = lltype.malloc(self._ADDRARRAY, total_refcnt,
                                           flavor='raw',
                                           track_allocation=False)
        self.snapshot_objs = lltype.malloc(self.PYOBJ_SNAPSHOT, total_objs,
                                           flavor='raw',
                                           track_allocation=False)
        self.total_objs = total_objs
        self.objs_index = 0
        self.refs_index = 0
        debug_print("take snapshot, count:", self.total_objs)

        # take snapshot of p_list_old
        self.p_list_old.foreach(self._take_snapshot_pyobject, None)

        # set pypy_link for o_list_old to zero, in case they are encountered
        # during tp_traverse (so they are excluded from the snapshot)
        self.o_list_old.foreach(self._take_snapshot_o_clearlink, None)

        # take snapshot of gc objs
        pygchdr = self.pyobj_list.c_gc_next
        while pygchdr <> self.pyobj_list:
            self._take_snapshot_gc(pygchdr)
            pygchdr = pygchdr.c_gc_next

        # include isolates from last cycle
        pygchdr = self.pyobj_isolate_old_list.c_gc_next
        while pygchdr <> self.pyobj_isolate_old_list:
            self._take_snapshot_gc(pygchdr)
            pygchdr = pygchdr.c_gc_next

        # fix references
        debug_print("fix references, count:", self.refs_index)
        for i in range(0, self.refs_index):
            addr = self.snapshot_refs[i]
            pyobj = llmemory.cast_adr_to_ptr(addr, self.PYOBJ_HDR_PTR)
            pygchdr = self.pyobj_as_gc(pyobj)
            if pygchdr != lltype.nullptr(self.PYOBJ_GC_HDR):
                if (#c_gc_refs > 0 and
                        pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_UNTRACKED and
                        pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_REACHABLE):
                    c_gc_refs = self._pyobj_gc_refcnt_get(pygchdr)
                    obj = self.snapshot_objs[c_gc_refs - 1]
                    debug_print("fix reference", i, "from", obj, "gc",
                                pygchdr.c_gc_refs)
                else:
                    obj = lltype.nullptr(self.PYOBJ_SNAPSHOT_OBJ)
            else:
                obj = self.snapshot_objs[pyobj.c_ob_pypy_link - 1]
                debug_print("fix reference", i, "from", obj, "non-gc",
                            pyobj.c_ob_pypy_link - 1)
            self.snapshot_refs[i] = llmemory.cast_ptr_to_adr(obj)

        # fix links of p_list_old and o_list_old back
        self.p_list_old.foreach(self._take_snapshot_fixlink, None)
        self.pypy_link_dict.foreach(self._take_snapshot_o_fixlink, None)
        self.pypy_link_dict.delete()
        self.pypy_link_dict = self.gc.AddressDict()

    def _take_snapshot_count_gc(self, pygchdr):
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT
        #
        refcnt = self.gc_as_pyobj(pygchdr).c_ob_refcnt
        if refcnt >= REFCNT_FROM_PYPY_LIGHT:
            refcnt -= REFCNT_FROM_PYPY_LIGHT
        elif refcnt >= REFCNT_FROM_PYPY:
            refcnt -= REFCNT_FROM_PYPY
        return refcnt

    def _take_snapshot_gc(self, pygchdr):
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT
        #
        pyobj = self.gc_as_pyobj(pygchdr)
        refcnt = pyobj.c_ob_refcnt
        if refcnt >= REFCNT_FROM_PYPY_LIGHT:
            refcnt -= REFCNT_FROM_PYPY_LIGHT
        elif refcnt >= REFCNT_FROM_PYPY:
            refcnt -= REFCNT_FROM_PYPY
        if pyobj.c_ob_pypy_link != 0:
            addr = llmemory.cast_int_to_adr(pyobj.c_ob_pypy_link)
            if self.gc.header(addr).tid & (self.GCFLAG_VISITED |
                                           self.GCFLAG_NO_HEAP_PTRS):
                refcnt += 1
        debug_print("take snapshot", self.objs_index, "gc", pyobj)
        self._pyobj_gc_refcnt_set(pygchdr, self.objs_index + 1)
        #pygchdr.c_gc_refs = self.objs_index + 1
        obj = self.snapshot_objs[self.objs_index]
        obj.pyobj = llmemory.cast_ptr_to_adr(pyobj)
        obj.status = 1
        obj.refcnt_original = pyobj.c_ob_refcnt
        obj.refcnt = refcnt
        obj.refs_index = self.refs_index
        obj.refs_len = 0
        obj.pypy_link = pyobj.c_ob_pypy_link
        self.snapshot_curr = obj
        self._take_snapshot_traverse(pyobj)
        self.objs_index += 1
        self.refs_index += obj.refs_len

    def _take_snapshot_count(self, pyobject, foo):
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT
        #
        pyobj = self._pyobj(pyobject)
        pygchdr = self.pyobj_as_gc(pyobj)
        # only include non-gc
        if pygchdr == lltype.nullptr(self.PYOBJ_GC_HDR):
            self.p_list_count += 1
            refcnt = pyobj.c_ob_refcnt
            if refcnt >= REFCNT_FROM_PYPY_LIGHT:
                refcnt -= REFCNT_FROM_PYPY_LIGHT
            elif refcnt >= REFCNT_FROM_PYPY:
                refcnt -= REFCNT_FROM_PYPY
            self.p_list_refcnt += refcnt

    def _take_snapshot_pyobject(self, pyobject, foo):
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT
        #
        pyobj = self._pyobj(pyobject)
        pygchdr = self.pyobj_as_gc(pyobj)
        # only include non-gc
        if pygchdr == lltype.nullptr(self.PYOBJ_GC_HDR):
            refcnt = pyobj.c_ob_refcnt
            if refcnt >= REFCNT_FROM_PYPY_LIGHT:
                refcnt -= REFCNT_FROM_PYPY_LIGHT
            elif refcnt >= REFCNT_FROM_PYPY:
                refcnt -= REFCNT_FROM_PYPY
            if pyobj.c_ob_pypy_link != 0:
                addr = llmemory.cast_int_to_adr(pyobj.c_ob_pypy_link)
                if self.gc.header(addr).tid & (self.GCFLAG_VISITED |
                                               self.GCFLAG_NO_HEAP_PTRS):
                    refcnt += 1
            debug_print("take snapshot", self.objs_index, "non-gc", pyobj)
            obj = self.snapshot_objs[self.objs_index]
            obj.pyobj = llmemory.cast_ptr_to_adr(pyobj)
            obj.status = 1
            obj.refcnt_original = pyobj.c_ob_refcnt
            obj.refcnt = refcnt
            obj.refs_index = 0
            obj.refs_len = 0
            obj.pypy_link = pyobj.c_ob_pypy_link
            pyobj.c_ob_pypy_link = self.objs_index + 1
            self.objs_index += 1

    def _take_snapshot_fixlink(self, pyobject, foo):
        pyobj = self._pyobj(pyobject)
        pygchdr = self.pyobj_as_gc(pyobj)
        # only include non-gc
        if pygchdr == lltype.nullptr(self.PYOBJ_GC_HDR):
            obj_index = pyobj.c_ob_pypy_link - 1
            obj = self.snapshot_objs[obj_index]
            pyobj.c_ob_pypy_link = obj.pypy_link

    def _take_snapshot_o_clearlink(self, pyobject, foo):
        pyobj = self._pyobj(pyobject)
        pygchdr = self.pyobj_as_gc(pyobj)
        # only for non-gc
        if pygchdr == lltype.nullptr(self.PYOBJ_GC_HDR):
            debug_print("clear link", pyobj)
            link = llmemory.cast_int_to_adr(pyobj.c_ob_pypy_link)
            self.pypy_link_dict.setitem(pyobject, link)
            pyobj.c_ob_pypy_link = 0

    def _take_snapshot_o_fixlink(self, pyobject, link, foo):
        pyobj = self._pyobj(pyobject)
        link_int = llmemory.cast_adr_to_int(link, "symbolic")
        pyobj.c_ob_pypy_link = link_int

    def _take_snapshot_visit(pyobj, self_ptr):
        from rpython.rtyper.annlowlevel import cast_adr_to_nongc_instance
        #
        self_adr = rffi.cast(llmemory.Address, self_ptr)
        self = cast_adr_to_nongc_instance(RawRefCountIncMarkGC, self_adr)
        self._take_snapshot_visit_action(pyobj, None)
        return rffi.cast(rffi.INT_real, 0)

    def _take_snapshot_visit_action(self, pyobj, ignore):
        pygchdr = self.pyobj_as_gc(pyobj)
        curr = self.snapshot_curr
        index = curr.refs_index + curr.refs_len
        if ((pygchdr != lltype.nullptr(self.PYOBJ_GC_HDR) and
             pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_UNTRACKED) or
                (pygchdr == lltype.nullptr(self.PYOBJ_GC_HDR) and
                pyobj.c_ob_pypy_link != 0)):
            debug_print("take ref", index, "curr refs_index", curr.refs_index,
                        "curr refs_len", curr.refs_len, "whatever", pyobj)
            self.snapshot_refs[index] = llmemory.cast_ptr_to_adr(pyobj)
            curr.refs_len += 1

    def _take_snapshot_traverse(self, pyobj):
        from rpython.rlib.objectmodel import we_are_translated
        from rpython.rtyper.annlowlevel import (cast_nongc_instance_to_adr,
                                                llhelper)
        #
        if we_are_translated():
            callback_ptr = llhelper(self.RAWREFCOUNT_VISIT,
                                    RawRefCountIncMarkGC._take_snapshot_visit)
            self_ptr = rffi.cast(rffi.VOIDP, cast_nongc_instance_to_adr(self))
            self.tp_traverse(pyobj, callback_ptr, self_ptr)
        else:
            self.tp_traverse(pyobj, self._take_snapshot_visit_action, None)

    def _check_snapshot_visit(pyobj, self_ptr):
        from rpython.rtyper.annlowlevel import cast_adr_to_nongc_instance
        #
        self_adr = rffi.cast(llmemory.Address, self_ptr)
        self = cast_adr_to_nongc_instance(RawRefCountIncMarkGC, self_adr)
        self._check_snapshot_visit_action(pyobj, None)
        return rffi.cast(rffi.INT_real, 0)

    def _check_snapshot_visit_action(self, pyobj, ignore):
        pygchdr = self.pyobj_as_gc(pyobj)
        if pygchdr <> lltype.nullptr(self.PYOBJ_GC_HDR) and \
                pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_UNTRACKED and \
                    pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_REACHABLE:
            # check consistency with snapshot
            curr = self.snapshot_curr
            curr_index = self.snapshot_curr_index
            if curr_index < curr.refs_len:
                # ref changed? -> issue, if traversal order is not stable!!!
                index = curr.refs_index + curr_index
                ref_addr = self.snapshot_refs[index]
                ref = llmemory.cast_adr_to_ptr(ref_addr,
                                               self.PYOBJ_SNAPSHOT_OBJ_PTR)
                old_value = ref.pyobj
                new_value = llmemory.cast_ptr_to_adr(pyobj)
                if old_value != new_value:
                    self.snapshot_consistent = False # reference changed
            else:
                self.snapshot_consistent = False # references added
            self.snapshot_curr_index += 1

    def _check_snapshot_traverse(self, pyobj):
        from rpython.rlib.objectmodel import we_are_translated
        from rpython.rtyper.annlowlevel import (cast_nongc_instance_to_adr,
                                                llhelper)
        #
        if we_are_translated():
            callback_ptr = llhelper(self.RAWREFCOUNT_VISIT,
                                    RawRefCountIncMarkGC._check_snapshot_visit)
            self_ptr = rffi.cast(rffi.VOIDP, cast_nongc_instance_to_adr(self))
            self.tp_traverse(pyobj, callback_ptr, self_ptr)
        else:
            self.tp_traverse(pyobj, self._check_snapshot_visit_action, None)

    def _discard_snapshot(self):
        lltype.free(self.snapshot_objs, flavor='raw', track_allocation=False)
        lltype.free(self.snapshot_refs, flavor='raw', track_allocation=False)