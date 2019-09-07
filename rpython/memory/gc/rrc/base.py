from rpython.rtyper.lltypesystem import lltype, llmemory, llgroup, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rlib.debug import ll_assert, debug_print, debug_start, debug_stop

def choose_rrc_gc_from_config(config):
    if config.translation.rrcgc:
        classes = {"mark": "mark.RawRefCountMarkGC",
                   "incmark": "incmark.RawRefCountIncMarkGC",
                   }
        try:
            modulename, classname = classes[config.translation.rrcgc].split(
                '.')
        except KeyError:
            raise ValueError("unknown value for translation.rrcgc: %r" % (
                config.translation.rrcgc,))
        module = __import__("rpython.memory.gc.rrc." + modulename,
                            globals(), locals(), [classname])
        GCClass = getattr(module, classname)
        return GCClass
    else:
        return None

class RawRefCountBaseGC(object):
    # Default state.
    STATE_DEFAULT = 0

    # Marking state.
    STATE_MARKING = 1

    # Here cyclic garbage only reachable from legacy finalizers is marked.
    STATE_GARBAGE_MARKING = 2

    # The state in which cyclic garbage with legacy finalizers is traced.
    # Do not mark objects during this state, because we remove the flag
    # during tracing and we do not want to trace those objects again. Also
    # during this phase no new objects can be marked, as we are only building
    # the list of cyclic garbage.
    STATE_GARBAGE = 3

    _ADDRARRAY = lltype.Array(llmemory.Address, hints={'nolength': True})
    PYOBJ_SNAPSHOT_OBJ = lltype.Struct('PyObject_Snapshot',
                                       ('pyobj', llmemory.Address),
                                       ('status', lltype.Signed),
                                       ('refcnt', lltype.Signed),
                                       ('refcnt_external', lltype.Signed),
                                       ('refs_index', lltype.Signed),
                                       ('refs_len', lltype.Signed),
                                       ('pypy_link', lltype.Signed))
    PYOBJ_SNAPSHOT_OBJ_PTR = lltype.Ptr(PYOBJ_SNAPSHOT_OBJ)
    PYOBJ_SNAPSHOT = lltype.Array(PYOBJ_SNAPSHOT_OBJ,
                                  hints={'nolength': True})
    PYOBJ_HDR = lltype.Struct('GCHdr_PyObject',
                              ('c_ob_refcnt', lltype.Signed),
                              ('c_ob_pypy_link', lltype.Signed))
    PYOBJ_HDR_PTR = lltype.Ptr(PYOBJ_HDR)
    RAWREFCOUNT_DEALLOC_TRIGGER = lltype.Ptr(lltype.FuncType([], lltype.Void))
    RAWREFCOUNT_VISIT = lltype.Ptr(lltype.FuncType([PYOBJ_HDR_PTR, rffi.VOIDP],
                                                   rffi.INT_real))
    RAWREFCOUNT_TRAVERSE = lltype.Ptr(lltype.FuncType([PYOBJ_HDR_PTR,
                                                       RAWREFCOUNT_VISIT,
                                                       rffi.VOIDP],
                                                      lltype.Void))
    PYOBJ_GC_HDR_PTR = lltype.Ptr(lltype.ForwardReference())
    PYOBJ_GC_HDR = lltype.Struct('PyGC_Head',
                                 ('c_gc_next', PYOBJ_GC_HDR_PTR),
                                 ('c_gc_prev', PYOBJ_GC_HDR_PTR),
                                 ('c_gc_refs', lltype.Signed))
    PYOBJ_GC_HDR_PTR.TO.become(PYOBJ_GC_HDR)
    RAWREFCOUNT_GC_AS_PYOBJ = lltype.Ptr(lltype.FuncType([PYOBJ_GC_HDR_PTR],
                                                         PYOBJ_HDR_PTR))
    RAWREFCOUNT_PYOBJ_AS_GC = lltype.Ptr(lltype.FuncType([PYOBJ_HDR_PTR],
                                                         PYOBJ_GC_HDR_PTR))
    RAWREFCOUNT_FINALIZER_TYPE = lltype.Ptr(lltype.FuncType([PYOBJ_GC_HDR_PTR],
                                                            lltype.Signed))
    RAWREFCOUNT_CLEAR_WR_TYPE = lltype.Ptr(lltype.FuncType([llmemory.GCREF],
                                                           lltype.Void))
    RAWREFCOUNT_MAYBE_UNTRACK_TUPLE = \
        lltype.Ptr(lltype.FuncType([PYOBJ_HDR_PTR], lltype.Signed))
    RAWREFCOUNT_FINALIZER_NONE = 0
    RAWREFCOUNT_FINALIZER_MODERN = 1
    RAWREFCOUNT_FINALIZER_LEGACY = 2
    RAWREFCOUNT_REFS_SHIFT = 1
    RAWREFCOUNT_REFS_MASK_FINALIZED = 1
    RAWREFCOUNT_REFS_UNTRACKED = -2 << RAWREFCOUNT_REFS_SHIFT

    def _pyobj(self, pyobjaddr):
        return llmemory.cast_adr_to_ptr(pyobjaddr, self.PYOBJ_HDR_PTR)
    def _pygchdr(self, pygchdraddr):
        return llmemory.cast_adr_to_ptr(pygchdraddr, self.PYOBJ_GC_HDR_PTR)

    def init(self, gc, gc_flags, dealloc_trigger_callback, tp_traverse,
             pyobj_list, tuple_list, gc_as_pyobj, pyobj_as_gc, finalizer_type,
             clear_weakref_callback, tuple_maybe_untrack):
        # see pypy/doc/discussion/rawrefcount.rst
        self.gc = gc
        (self.GCFLAG_VISITED_RMY, self.GCFLAG_VISITED,
         self.GCFLAG_NO_HEAP_PTRS, self.GCFLAG_GARBAGE) = gc_flags
        self.p_list_young = self.gc.AddressStack()
        self.p_list_old = self.gc.AddressStack()
        self.o_list_young = self.gc.AddressStack()
        self.o_list_old = self.gc.AddressStack()
        self.p_dict = self.gc.AddressDict()  # non-nursery keys only
        self.p_dict_nurs = self.gc.AddressDict()  # nursery keys only
        self.dealloc_trigger_callback = dealloc_trigger_callback
        self.dealloc_pending = self.gc.AddressStack()
        self.refcnt_dict = self.gc.AddressDict()
        self.tp_traverse = tp_traverse
        self.pyobj_list = self._pygchdr(pyobj_list)
        self.tuple_list = self._pygchdr(tuple_list)
        self.pyobj_old_list = self._gc_list_new()
        self.pyobj_isolate_list = self._gc_list_new()
        self.pyobj_dead_list = self._gc_list_new()
        self.pyobj_garbage_list = self._gc_list_new()
        self.garbage_to_trace = self.gc.AddressStack()
        self.gc_as_pyobj = gc_as_pyobj
        self.pyobj_as_gc = pyobj_as_gc
        self.finalizer_type = finalizer_type
        self.clear_weakref_callback = clear_weakref_callback
        self.tuple_maybe_untrack = tuple_maybe_untrack
        self.state = self.STATE_DEFAULT
        self.cycle_enabled = True

    def create_link_pypy(self, gcobj, pyobject):
        obj = llmemory.cast_ptr_to_adr(gcobj)
        objint = llmemory.cast_adr_to_int(obj, "symbolic")
        self._pyobj(pyobject).c_ob_pypy_link = objint
        #
        lst = self.p_list_young
        if self.gc.is_in_nursery(obj):
            dct = self.p_dict_nurs
        else:
            dct = self.p_dict
            if not self.gc.is_young_object(obj):
                lst = self.p_list_old
        lst.append(pyobject)
        dct.setitem(obj, pyobject)

    def create_link_pyobj(self, gcobj, pyobject):
        obj = llmemory.cast_ptr_to_adr(gcobj)
        if self.gc.is_young_object(obj):
            self.o_list_young.append(pyobject)
        else:
            self.o_list_old.append(pyobject)
        objint = llmemory.cast_adr_to_int(obj, "symbolic")
        self._pyobj(pyobject).c_ob_pypy_link = objint
        # there is no o_dict

    def from_obj(self, gcobj):
        obj = llmemory.cast_ptr_to_adr(gcobj)
        if self.gc.is_in_nursery(obj):
            dct = self.p_dict_nurs
        else:
            dct = self.p_dict
        return dct.get(obj)

    def to_obj(self, pyobject):
        obj = llmemory.cast_int_to_adr(self._pyobj(pyobject).c_ob_pypy_link)
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)

    def mark_deallocating(self, gcobj, pyobject):
        obj = llmemory.cast_ptr_to_adr(gcobj)  # should be a prebuilt obj
        objint = llmemory.cast_adr_to_int(obj, "symbolic")
        self._pyobj(pyobject).c_ob_pypy_link = objint

    def invoke_callback(self):
        if (self.dealloc_pending.non_empty() or
                not self._gc_list_is_empty(self.pyobj_isolate_list) or
                not self._gc_list_is_empty(self.pyobj_dead_list) or
                not self._gc_list_is_empty(self.pyobj_garbage_list)):
            self.dealloc_trigger_callback()

    def next_dead(self):
        if self.dealloc_pending.non_empty():
            return self.dealloc_pending.pop()
        return llmemory.NULL

    def next_cyclic_isolate(self):
        if not self._gc_list_is_empty(self.pyobj_isolate_list):
            gchdr = self._gc_list_pop(self.pyobj_isolate_list)
            self._gc_list_add(self.pyobj_old_list, gchdr)
            return llmemory.cast_ptr_to_adr(self.gc_as_pyobj(gchdr))
        return llmemory.NULL

    def cyclic_garbage_head(self):
        if not self._gc_list_is_empty(self.pyobj_dead_list):
            return llmemory.cast_ptr_to_adr(
                self.gc_as_pyobj(self.pyobj_dead_list.c_gc_next))
        else:
            return llmemory.NULL

    def cyclic_garbage_remove(self):
        gchdr = self.pyobj_dead_list.c_gc_next
        # remove from old list
        next = gchdr.c_gc_next
        next.c_gc_prev = gchdr.c_gc_prev
        gchdr.c_gc_prev.c_gc_next = next
        # add to new list, may die later
        next = self.pyobj_list.c_gc_next
        self.pyobj_list.c_gc_next = gchdr
        gchdr.c_gc_prev = self.pyobj_list
        gchdr.c_gc_next = next
        next.c_gc_prev = gchdr

    def next_garbage_pypy(self):
        if self.garbage_to_trace.non_empty():
            # remove one object from the wavefront and move the wavefront
            obj = self.garbage_to_trace.pop()
            if self._garbage_visit(obj):
                return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)
            else:
                return lltype.nullptr(llmemory.GCREF.TO)
        else:
            return lltype.nullptr(llmemory.GCREF.TO)

    def next_garbage_pyobj(self):
        if self._gc_list_is_empty(self.pyobj_garbage_list):
            return llmemory.NULL
        else:
            # pyobj_garbage_list is not a real list, it just points to
            # the first (c_gc_next) and last (c_gc_prev) pyobject in the list
            # of live objects that are garbage, so just fix the references
            list = self.pyobj_garbage_list
            gchdr = list.c_gc_next
            if list.c_gc_prev == gchdr:
                list.c_gc_next = list # reached end of list, reset it
            else:
                list.c_gc_next = gchdr.c_gc_next # move pointer foward
            return llmemory.cast_ptr_to_adr(self.gc_as_pyobj(gchdr))

    # --- Tracing ---

    def minor_trace(self):
        length_estimate = self.p_dict_nurs.length()
        self.p_dict_nurs.delete()
        self.p_dict_nurs = self.gc.AddressDict(length_estimate)
        self.p_list_young.foreach(self._minor_trace, self.gc.singleaddr)

    def _minor_trace(self, pyobject, singleaddr):
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT
        #
        rc = self._pyobj(pyobject).c_ob_refcnt
        if rc == REFCNT_FROM_PYPY or rc == REFCNT_FROM_PYPY_LIGHT:
            pass     # the corresponding object may die
        else:
            # force the corresponding object to be alive
            intobj = self._pyobj(pyobject).c_ob_pypy_link
            singleaddr.address[0] = llmemory.cast_int_to_adr(intobj)
            self.gc._trace_drag_out1(singleaddr)

    def minor_collection_free(self):
        ll_assert(self.p_dict_nurs.length() == 0,
                  "p_dict_nurs not empty 1")
        lst = self.p_list_young
        while lst.non_empty():
            self._minor_free(lst.pop(), self.p_list_old, self.p_dict)
        lst = self.o_list_young
        no_o_dict = self.gc.null_address_dict()
        while lst.non_empty():
            self._minor_free(lst.pop(), self.o_list_old, no_o_dict)

    def _minor_free(self, pyobject, surviving_list, surviving_dict):
        intobj = self._pyobj(pyobject).c_ob_pypy_link
        obj = llmemory.cast_int_to_adr(intobj)
        if self.gc.is_in_nursery(obj):
            if self.gc.is_forwarded(obj):
                # Common case: survives and moves
                obj = self.gc.get_forwarding_address(obj)
                intobj = llmemory.cast_adr_to_int(obj, "symbolic")
                self._pyobj(pyobject).c_ob_pypy_link = intobj
                surviving = True
                if surviving_dict:
                    # Surviving nursery object: was originally in
                    # p_dict_nurs and now must be put into p_dict
                    surviving_dict.setitem(obj, pyobject)
            else:
                surviving = False
        elif (bool(self.gc.young_rawmalloced_objects) and
              self.gc.young_rawmalloced_objects.contains(obj)):
            # young weakref to a young raw-malloced object
            if self.gc.header(obj).tid & self.GCFLAG_VISITED_RMY:
                surviving = True    # survives, but does not move
            else:
                surviving = False
                if surviving_dict:
                    # Dying young large object: was in p_dict,
                    # must be deleted
                    surviving_dict.setitem(obj, llmemory.NULL)
        else:
            ll_assert(False, "X_list_young contains non-young obj")
            return
        #
        if surviving:
            surviving_list.append(pyobject)
        else:
            self._free(pyobject)

    def _free(self, pyobject, major=False):
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT
        #
        rc = self._pyobj(pyobject).c_ob_refcnt
        if rc >= REFCNT_FROM_PYPY_LIGHT:
            rc -= REFCNT_FROM_PYPY_LIGHT
            if rc == 0:
                pygchdr = self.pyobj_as_gc(self._pyobj(pyobject))
                if pygchdr <> lltype.nullptr(self.PYOBJ_GC_HDR):
                    next = pygchdr.c_gc_next
                    next.c_gc_prev = pygchdr.c_gc_prev
                    pygchdr.c_gc_prev.c_gc_next = next
                lltype.free(self._pyobj(pyobject), flavor='raw')
            else:
                # can only occur if LIGHT is used in create_link_pyobj()
                self._pyobj(pyobject).c_ob_refcnt = rc
                self._pyobj(pyobject).c_ob_pypy_link = 0
        else:
            ll_assert(rc >= REFCNT_FROM_PYPY, "refcount underflow?")
            ll_assert(rc < int(REFCNT_FROM_PYPY_LIGHT * 0.99),
                      "refcount underflow from REFCNT_FROM_PYPY_LIGHT?")
            rc -= REFCNT_FROM_PYPY
            self._pyobj(pyobject).c_ob_pypy_link = 0
            if rc == 0:
                self.dealloc_pending.append(pyobject)
                # an object with refcnt == 0 cannot stay around waiting
                # for its deallocator to be called.  Some code (lxml)
                # expects that tp_dealloc is called immediately when
                # the refcnt drops to 0.  If it isn't, we get some
                # uncleared raw pointer that can still be used to access
                # the object; but (PyObject *)raw_pointer is then bogus
                # because after a Py_INCREF()/Py_DECREF() on it, its
                # tp_dealloc is also called!
                rc = 1
            self._pyobj(pyobject).c_ob_refcnt = rc
    _free._always_inline_ = True

    def major_collection_trace_step(self):
        return True

    def _fix_refcnt_back(self, pyobject, link, ignore):
        pyobj = self._pyobj(pyobject)
        link_int = llmemory.cast_adr_to_int(link, "symbolic")
        pyobj.c_ob_refcnt = pyobj.c_ob_pypy_link
        pyobj.c_ob_pypy_link = link_int

    def _major_trace(self, pyobject, flags):
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT
        (use_cylicrefcnt, use_dict) = flags
        #
        pyobj = self._pyobj(pyobject)
        cyclic_rc = -42
        if use_cylicrefcnt:
            pygchdr = self.pyobj_as_gc(pyobj)
            if pygchdr != lltype.nullptr(self.PYOBJ_GC_HDR):
                if pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_UNTRACKED:
                    rc = pygchdr.c_gc_refs >> self.RAWREFCOUNT_REFS_SHIFT
                    cyclic_rc = rc
                else:
                    rc = pyobj.c_ob_refcnt
            else:
                rc = pyobj.c_ob_refcnt
        else:
            rc = pyobj.c_ob_refcnt

        if rc == REFCNT_FROM_PYPY or rc == REFCNT_FROM_PYPY_LIGHT or rc == 0:
            pass  # the corresponding object may die
        else:
            # force the corresponding object to be alive
            debug_print("pyobj stays alive", pyobj, "rc", rc, "cyclic_rc",
                        cyclic_rc)
            if use_dict:
                obj = self.refcnt_dict.get(pyobject)
            else:
                intobj = pyobj.c_ob_pypy_link
                obj = llmemory.cast_int_to_adr(intobj)
            self.gc.objects_to_trace.append(obj)
            self.gc.visit_all_objects()

    def _major_trace_nongc(self, pyobject, use_dict):
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT
        #
        pyobj = self._pyobj(pyobject)
        pygchdr = self.pyobj_as_gc(pyobj)
        if pygchdr != lltype.nullptr(self.PYOBJ_GC_HDR):
            if pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_UNTRACKED:
                rc = 0
            else:
                rc = pyobj.c_ob_refcnt
        else:
            rc = pyobj.c_ob_refcnt

        if rc == REFCNT_FROM_PYPY or rc == REFCNT_FROM_PYPY_LIGHT or rc == 0:
            pass  # the corresponding object may die
        else:
            # force the corresponding object to be alive
            debug_print("pyobj stays alive", pyobj, "rc", rc)
            if use_dict:
                obj = self.refcnt_dict.get(pyobject)
            else:
                intobj = pyobj.c_ob_pypy_link
                obj = llmemory.cast_int_to_adr(intobj)
            self.gc.objects_to_trace.append(obj)
            self.gc.visit_all_objects()

    def major_collection_free(self):
        if self.state == self.STATE_DEFAULT:
            self._debug_check_consistency()
            if not self._gc_list_is_empty(self.pyobj_old_list):
                self._gc_list_merge(self.pyobj_old_list, self.pyobj_dead_list)
            self._debug_check_consistency(print_label="before-sweep")

        ll_assert(self.p_dict_nurs.length() == 0, "p_dict_nurs not empty 2")
        length_estimate = self.p_dict.length()
        self.p_dict.delete()
        self.p_dict = new_p_dict = self.gc.AddressDict(length_estimate)
        new_p_list = self.gc.AddressStack()
        while self.p_list_old.non_empty():
            self._major_free(self.p_list_old.pop(), new_p_list,
                                                              new_p_dict)
        self.p_list_old.delete()
        self.p_list_old = new_p_list
        #
        new_o_list = self.gc.AddressStack()
        no_o_dict = self.gc.null_address_dict()
        while self.o_list_old.non_empty():
            self._major_free(self.o_list_old.pop(), new_o_list, no_o_dict)
        self.o_list_old.delete()
        self.o_list_old = new_o_list

    def _major_free(self, pyobject, surviving_list, surviving_dict):
        # The pyobject survives if the corresponding obj survives.
        # This is true if the obj has one of the following two flags:
        #  * GCFLAG_VISITED: was seen during tracing
        #  * GCFLAG_NO_HEAP_PTRS: immortal object never traced (so far)
        intobj = self._pyobj(pyobject).c_ob_pypy_link
        obj = llmemory.cast_int_to_adr(intobj)
        if self.gc.header(obj).tid & \
                (self.GCFLAG_VISITED | self.GCFLAG_NO_HEAP_PTRS):
            surviving_list.append(pyobject)
            if surviving_dict:
                surviving_dict.insertclean(obj, pyobject)
        else:
            self._free(pyobject, True)

    def _untrack_tuples(self):
        gchdr = self.tuple_list.c_gc_next
        while gchdr <> self.tuple_list:
            gchdr_next = gchdr.c_gc_next
            pyobj = self.gc_as_pyobj(gchdr)
            result = self.tuple_maybe_untrack(pyobj)
            if result == 1: # contains gc objects -> promote to pyobj list
                next = gchdr.c_gc_next
                next.c_gc_prev = gchdr.c_gc_prev
                gchdr.c_gc_prev.c_gc_next = next
                self._gc_list_add(self.pyobj_list, gchdr)
            gchdr = gchdr_next

    def _find_garbage(self, use_dict):
        found_garbage = False
        gchdr = self.pyobj_old_list.c_gc_next
        while gchdr <> self.pyobj_old_list:
            next_old = gchdr.c_gc_next
            garbage = self.finalizer_type(gchdr) == \
                      self.RAWREFCOUNT_FINALIZER_LEGACY
            if garbage:
                self._move_to_garbage(gchdr, use_dict)
                found_garbage = True
            gchdr = next_old
        return found_garbage

    def _mark_garbage(self, use_dict):
        found_garbage = True
        #
        while found_garbage:
            found_garbage = False
            gchdr = self.pyobj_old_list.c_gc_next
            while gchdr <> self.pyobj_old_list:
                next_old = gchdr.c_gc_next
                alive = (gchdr.c_gc_refs >> self.RAWREFCOUNT_REFS_SHIFT) > 0
                pyobj = self.gc_as_pyobj(gchdr)
                if pyobj.c_ob_pypy_link <> 0:
                    if use_dict:
                        pyobject = llmemory.cast_ptr_to_adr(pyobj)
                        obj = self.refcnt_dict.get(pyobject)
                    else:
                        intobj = pyobj.c_ob_pypy_link
                        obj = llmemory.cast_int_to_adr(intobj)
                    if not alive and self.gc.header(obj).tid & (
                            self.GCFLAG_VISITED | self.GCFLAG_NO_HEAP_PTRS):
                        # add fake refcount, to mark it as live
                        gchdr.c_gc_refs += 1 << self.RAWREFCOUNT_REFS_SHIFT
                        alive = True
                if alive:
                    self._move_to_garbage(gchdr, use_dict)
                    found_garbage = True
                gchdr = next_old

    def _move_to_garbage(self, gchdr, use_dict):
        pyobj = self.gc_as_pyobj(gchdr)
        # remove from old list
        next = gchdr.c_gc_next
        next.c_gc_prev = gchdr.c_gc_prev
        gchdr.c_gc_prev.c_gc_next = next
        # add to beginning of pyobj_list
        self._gc_list_add(self.pyobj_list, gchdr)
        # set as new beginning (and optionally end) of
        # pyobj_garbage_list (not a real list, just pointers to
        # begin and end)
        if self._gc_list_is_empty(self.pyobj_garbage_list):
            self.pyobj_garbage_list.c_gc_prev = gchdr
        self.pyobj_garbage_list.c_gc_next = gchdr
        # mark referenced objects alive (so objects in the old list
        # will be detected as garbage, as they should have a cyclic
        # refcount of zero or an unmarked linked pypy object)
        self._traverse(pyobj, 1)
        if pyobj.c_ob_pypy_link <> 0:
            if use_dict:
                pyobject = llmemory.cast_ptr_to_adr(pyobj)
                obj = self.refcnt_dict.get(pyobject)
            else:
                intobj = pyobj.c_ob_pypy_link
                obj = llmemory.cast_int_to_adr(intobj)
            self.garbage_to_trace.append(obj)
            self.gc.objects_to_trace.append(obj)
            self.gc.visit_all_objects()

    def _collect_obj(self, obj, ignored):
        llop.debug_nonnull_pointer(lltype.Void, obj)
        self.garbage_to_trace.append(obj)
    _collect_obj._always_inline_ = True

    def _collect_ref_rec(self, root, ignored):
        self._collect_obj(root.address[0], None)

    def _garbage_visit(self, obj):
        # If GCFLAG_GARBAGE is set, remove the flag and trace the object
        hdr = self.gc.header(obj)
        if not (hdr.tid & self.GCFLAG_GARBAGE):
            return False
        hdr.tid &= ~self.GCFLAG_GARBAGE
        if self.gc.has_gcptr(llop.extract_ushort(llgroup.HALFWORD, hdr.tid)):
            self.gc.trace(obj, self._collect_ref_rec, None)
        return True

    def _find_finalizer(self):
        gchdr = self.pyobj_old_list.c_gc_next
        while gchdr <> self.pyobj_old_list:
            if self.finalizer_type(gchdr) == self.RAWREFCOUNT_FINALIZER_MODERN:
                return True
            gchdr = gchdr.c_gc_next
        return False

    def _visit(pyobj, self_ptr):
        from rpython.rtyper.annlowlevel import cast_adr_to_nongc_instance
        #
        self_adr = rffi.cast(llmemory.Address, self_ptr)
        self = cast_adr_to_nongc_instance(RawRefCountBaseGC, self_adr)
        self._visit_action(pyobj, None)
        return rffi.cast(rffi.INT_real, 0)

    def _visit_action(self, pyobj, ignore):
        pygchdr = self.pyobj_as_gc(pyobj)
        if pygchdr <> lltype.nullptr(self.PYOBJ_GC_HDR):
            if pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_UNTRACKED:
                pygchdr.c_gc_refs += self.refcnt_add << \
                                     self.RAWREFCOUNT_REFS_SHIFT
        elif pyobj.c_ob_pypy_link != 0:
            pyobj.c_ob_refcnt += self.refcnt_add
            if self.refcnt_add > 0:
                #intobj = pyobj.c_ob_pypy_link
                #obj = llmemory.cast_int_to_adr(intobj)
                pyobject = llmemory.cast_ptr_to_adr(pyobj)
                obj = self.refcnt_dict.get(pyobject)
                self.gc.objects_to_trace.append(obj)
                self.gc.visit_all_objects()

    def _traverse(self, pyobj, refcnt_add):
        from rpython.rlib.objectmodel import we_are_translated
        from rpython.rtyper.annlowlevel import (cast_nongc_instance_to_adr,
                                                llhelper)
        #
        self.refcnt_add = refcnt_add
        if we_are_translated():
            callback_ptr = llhelper(self.RAWREFCOUNT_VISIT,
                                    RawRefCountBaseGC._visit)
            self_ptr = rffi.cast(rffi.VOIDP, cast_nongc_instance_to_adr(self))
            self.tp_traverse(pyobj, callback_ptr, self_ptr)
        else:
            self.tp_traverse(pyobj, self._visit_action, None)

    # --- Helpers ---

    def _gc_list_new(self):
        list = lltype.malloc(self.PYOBJ_GC_HDR, flavor='raw', immortal=True)
        self._gc_list_init(list)
        return list

    def _gc_list_init(self, pygclist):
        pygclist.c_gc_next = pygclist
        pygclist.c_gc_prev = pygclist

    def _gc_list_add(self, pygclist, gchdr):
        next = pygclist.c_gc_next
        pygclist.c_gc_next = gchdr
        gchdr.c_gc_prev = pygclist
        gchdr.c_gc_next = next
        next.c_gc_prev = gchdr

    def _gc_list_remove(self, gchdr):
        next = gchdr.c_gc_next
        next.c_gc_prev = gchdr.c_gc_prev
        gchdr.c_gc_prev.c_gc_next = next

    def _gc_list_pop(self, pygclist):
        ret = pygclist.c_gc_next
        pygclist.c_gc_next = ret.c_gc_next
        ret.c_gc_next.c_gc_prev = pygclist
        return ret

    def _gc_list_move(self, pygclist_source, pygclist_dest):
        pygclist_dest.c_gc_next = pygclist_source.c_gc_next
        pygclist_dest.c_gc_prev = pygclist_source.c_gc_prev
        pygclist_dest.c_gc_next.c_gc_prev = pygclist_dest
        pygclist_dest.c_gc_prev.c_gc_next = pygclist_dest
        pygclist_source.c_gc_next = pygclist_source
        pygclist_source.c_gc_prev = pygclist_source

    def _gc_list_merge(self, pygclist_source, pygclist_dest):
        next = pygclist_dest.c_gc_next
        next_old = pygclist_source.c_gc_next
        prev_old = pygclist_source.c_gc_prev
        pygclist_dest.c_gc_next = next_old
        next_old.c_gc_prev = pygclist_dest
        prev_old.c_gc_next = next
        next.c_gc_prev = prev_old
        pygclist_source.c_gc_next = pygclist_source
        pygclist_source.c_gc_prev = pygclist_source

    def _gc_list_is_empty(self, pygclist):
        return pygclist.c_gc_next == pygclist

    # --- Tests / Debugging ---

    def check_no_more_rawrefcount_state(self):
        "NOT_RPYTHON: for tests"
        assert self.p_list_young.length() == 0
        assert self.p_list_old  .length() == 0
        assert self.o_list_young.length() == 0
        assert self.o_list_old  .length() == 0
        def check_value_is_null(key, value, ignore):
            assert value == llmemory.NULL
        self.p_dict.foreach(check_value_is_null, None)
        self.p_dict_nurs.foreach(check_value_is_null, None)

    def _debug_check_consistency(self, print_label=None):
        if self.gc.DEBUG:
            should_print = print_label is not None
            if should_print:
                debug_start("rrc-lists " + print_label)
            self._debug_check_list(self.pyobj_list, should_print, "pyobj_list")
            self._debug_check_list(self.tuple_list, should_print, "tuple_list")
            self._debug_check_list(self.pyobj_old_list, should_print,
                                   "pyobj_old_list")
            self._debug_check_list(self.pyobj_dead_list, should_print,
                                   "pyobj_dead_list")
            self._debug_check_list(self.pyobj_isolate_list, should_print,
                                   "pyobj_isolate_list")
            # pyobj_garbage_list is not a real list, it just marks the
            # first and the last object in pyobj_list, which are garbage

            if should_print:
                debug_stop("rrc-lists " + print_label)

    def _debug_check_list(self, list, should_print, print_label):
        if should_print:
            debug_start(print_label)
        gchdr = list.c_gc_next
        prev = list
        while gchdr <> list:
            if should_print:
                pyobj = self.gc_as_pyobj(gchdr)
                intobj = pyobj.c_ob_pypy_link
                debug_print("item", gchdr, ": pyobj", pyobj,
                            "cyclic refcnt",
                            gchdr.c_gc_refs >> self.RAWREFCOUNT_REFS_SHIFT,
                            "refcnt", pyobj.c_ob_refcnt,
                            "link", intobj)
                #if intobj: TODO fix
                #    obj = llmemory.cast_int_to_adr(intobj)
                #    marked = self.header(obj).tid & \
                #            (GCFLAG_VISITED | GCFLAG_NO_HEAP_PTRS)
                #   debug_print("  linked obj", obj, ": marked", marked)

            ll_assert(gchdr.c_gc_next != lltype.nullptr(self.PYOBJ_GC_HDR),
                      "gc_next is null")
            ll_assert(gchdr.c_gc_prev == prev, "gc_prev is inconsistent")
            prev = gchdr
            gchdr = gchdr.c_gc_next
        ll_assert(list.c_gc_prev == prev, "gc_prev is inconsistent")
        if should_print:
            debug_stop(print_label)