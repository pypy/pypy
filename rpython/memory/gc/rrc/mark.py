from rpython.memory.gc.rrc.base import RawRefCountBaseGC
from rpython.rtyper.lltypesystem import lltype, llmemory, llgroup, rffi
from rpython.rlib.debug import ll_assert, debug_print, debug_start, debug_stop

class RawRefCountMarkGC(RawRefCountBaseGC):

    use_refcntdict = False

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
        if self.state == self.STATE_MARKING and self.cycle_enabled:

            # check if objects with finalizers from last collection cycle
            # have been resurrected
            dead_list_empty = True
            if not self._gc_list_is_empty(self.pyobj_old_list):
                dead_list_empty = self._check_finalizer()

            # collect all rawrefcounted roots
            self._collect_roots()
            self._debug_check_consistency(print_label="roots-marked")

            if not dead_list_empty:
                # set all refcounts to zero for objects in dead list
                # (might have been incremented) by fix_refcnt
                gchdr = self.pyobj_dead_list.c_gc_next
                while gchdr <> self.pyobj_dead_list:
                    gchdr.c_gc_refs = 0
                    gchdr = gchdr.c_gc_next

            # mark all objects reachable from rawrefcounted roots
            self._mark_rawrefcount()
            self._debug_check_consistency(print_label="before-fin")

            # handle legacy finalizer
            self.state = self.STATE_GARBAGE_MARKING
            if self._find_garbage(True):
                self._mark_garbage(True)
                self._debug_check_consistency(print_label="end-legacy-fin")
            self.state = self.STATE_MARKING

            # handle modern finalizer
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
        self.use_refcntdict = False

        self.state = self.STATE_DEFAULT
        return True

    def to_obj(self, pyobject):
        if self.use_refcntdict:
            obj = self.refcnt_dict.get(pyobject)
        else:
            obj = llmemory.cast_int_to_adr(
                self._pyobj(pyobject).c_ob_pypy_link)
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)

    def _collect_roots(self):
        # Initialize the cyclic refcount with the real refcount.
        self._collect_roots_init_list(self.pyobj_list)

        # Save the real refcount of objects at border
        self.p_list_old.foreach(self._obj_save_refcnt, None)
        self.o_list_old.foreach(self._obj_save_refcnt, None)
        self.use_refcntdict = True

        # Subtract all internal refcounts from the cyclic refcount
        # of rawrefcounted objects
        self._collect_roots_subtract_internal(self.pyobj_list)

        # For all non-gc pyobjects which have a refcount > 0,
        # mark all reachable objects on the pypy side
        self.p_list_old.foreach(self._major_trace_nongc, True)

        # For every object in this set, if it is marked, add 1 as a real
        # refcount (p_list => pyobj stays alive if obj stays alive).
        self.p_list_old.foreach(self._obj_fix_refcnt, None)
        self.o_list_old.foreach(self._obj_fix_refcnt, None)

        # now all rawrefcounted roots or live border objects have a
        # refcount > 0
        self._debug_check_consistency(print_label="rc-initialized")

    def _collect_roots_init_list(self, pygclist):
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT
        pygchdr = pygclist.c_gc_next
        while pygchdr <> pygclist:
            refcnt = self.gc_as_pyobj(pygchdr).c_ob_refcnt
            if refcnt >= REFCNT_FROM_PYPY_LIGHT:
                refcnt -= REFCNT_FROM_PYPY_LIGHT
            elif refcnt >= REFCNT_FROM_PYPY:
                refcnt -= REFCNT_FROM_PYPY
            self._pyobj_gc_refcnt_set(pygchdr, refcnt)
            pygchdr = pygchdr.c_gc_next

    def _collect_roots_subtract_internal(self, pygclist):
        pygchdr = pygclist.c_gc_next
        while pygchdr <> pygclist:
            pyobj = self.gc_as_pyobj(pygchdr)
            self._traverse(pyobj, -1)
            pygchdr = pygchdr.c_gc_next

    def _pyobj_gc_refcnt_set(self, pygchdr, refcnt):
        pygchdr.c_gc_refs &= self.RAWREFCOUNT_REFS_MASK_FINALIZED
        pygchdr.c_gc_refs |= refcnt << self.RAWREFCOUNT_REFS_SHIFT

    def _obj_save_refcnt(self, pyobject, ignore):
        pyobj = self._pyobj(pyobject)
        link = llmemory.cast_int_to_adr(pyobj.c_ob_pypy_link)
        self.refcnt_dict.setitem(pyobject, link)
        pyobj.c_ob_pypy_link = pyobj.c_ob_refcnt

    def _obj_fix_refcnt(self, pyobject, ignore):
        pyobj = self._pyobj(pyobject)
        #intobj = pyobj.c_ob_pypy_link
        #obj = llmemory.cast_int_to_adr(intobj)
        obj = self.refcnt_dict.get(pyobject)
        gchdr = self.pyobj_as_gc(pyobj)
        if gchdr <> lltype.nullptr(self.PYOBJ_GC_HDR):
            rc = gchdr.c_gc_refs
            refcnt = gchdr.c_gc_refs >> self.RAWREFCOUNT_REFS_SHIFT
            if rc == self.RAWREFCOUNT_REFS_UNTRACKED:
                debug_print("gc obj not tracked", gchdr, ": obj", obj,
                            "cyclic-rc", rc)
            else:
                debug_print("gc obj tracked", gchdr, ": obj", obj, "real-rc",
                            refcnt, "gc-next",
                            gchdr.c_gc_next, "gc-prev", gchdr.c_gc_prev)
                if self.gc.header(obj).tid & (self.GCFLAG_VISITED |
                                              self.GCFLAG_NO_HEAP_PTRS):
                    refcnt += 1
                self._pyobj_gc_refcnt_set(gchdr, refcnt)

    def _mark_rawrefcount(self):
        if self._gc_list_is_empty(self.pyobj_list):
            self._gc_list_init(self.pyobj_old_list)
        else:
            self._gc_list_move(self.pyobj_list, self.pyobj_old_list)
        # as long as new objects with cyclic a refcount > 0 or alive border
        # objects are found, increment the refcount of all referenced objects
        # of those newly found objects
        found_alive = True
        pyobj_old = self.pyobj_list
        #
        while found_alive: # TODO: working set to improve performance?
            found_alive = False
            gchdr = self.pyobj_old_list.c_gc_next
            while gchdr <> self.pyobj_old_list:
                next_old = gchdr.c_gc_next
                found_alive |= self._mark_rawrefcount_obj(gchdr, pyobj_old)
                gchdr = next_old
        #
        # now all rawrefcounted objects, which are alive, have a cyclic
        # refcount > 0 or are marked

    def _mark_rawrefcount_obj(self, gchdr, gchdr_move):
        alive = (gchdr.c_gc_refs >> self.RAWREFCOUNT_REFS_SHIFT) > 0
        pyobj = self.gc_as_pyobj(gchdr)
        obj = llmemory.NULL
        if pyobj.c_ob_pypy_link <> 0:
            #intobj = pyobj.c_ob_pypy_link
            #obj = llmemory.cast_int_to_adr(intobj)
            pyobject = llmemory.cast_ptr_to_adr(pyobj)
            obj = self.refcnt_dict.get(pyobject)
            if not alive and self.gc.header(obj).tid & (
                    self.GCFLAG_VISITED | self.GCFLAG_NO_HEAP_PTRS):
                # add fake refcount, to mark it as live
                gchdr.c_gc_refs += 1 << self.RAWREFCOUNT_REFS_SHIFT
                alive = True
        if alive:
            # remove from old list
            next = gchdr.c_gc_next
            next.c_gc_prev = gchdr.c_gc_prev
            gchdr.c_gc_prev.c_gc_next = next
            # add to new list (or not, if it is a tuple)
            self._gc_list_add(gchdr_move, gchdr)
            # increment refcounts
            self._traverse(pyobj, 1)
            # mark recursively, if it is a pypyobj
            if pyobj.c_ob_pypy_link <> 0:
                #intobj = pyobj.c_ob_pypy_link
                #obj = llmemory.cast_int_to_adr(intobj)
                self.gc.objects_to_trace.append(obj)
                self.gc.visit_all_objects()
        return alive
