from pypy.rpython.lltypesystem import lltype, llmemory, llarena, rffi
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance, base_ptr_lltype
from pypy.rlib.objectmodel import we_are_translated, free_non_gc_object
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.debug import ll_assert, debug_start, debug_stop, fatalerror

from pypy.rpython.memory.gc.stmgc import WORD, NULL
from pypy.rpython.memory.gc.stmgc import always_inline, dont_inline
from pypy.rpython.memory.gc.stmgc import GCFLAG_GLOBAL


class StmGCTLS(object):
    """The thread-local structure: we have one instance of these per thread,
    including one for the main thread."""

    _alloc_flavor_ = 'raw'

    nontranslated_dict = {}

    def __init__(self, gc, in_main_thread):
        self.gc = gc
        self.in_main_thread = in_main_thread
        self.stm_operations = self.gc.stm_operations
        self.null_address_dict = self.gc.null_address_dict
        self.AddressStack = self.gc.AddressStack
        self.AddressDict = self.gc.AddressDict
        #
        # --- current position and end of nursery, or NULL when
        #     mallocs are forbidden
        self.nursery_free = NULL
        self.nursery_top  = NULL
        self.nursery_pending_clear = 0
        # --- the start and size of the nursery belonging to this thread.
        #     never changes.
        self.nursery_size  = self.gc.nursery_size
        self.nursery_start = self._alloc_nursery(self.nursery_size)
        #
        # --- the local raw-malloced objects (chained list via hdr.version)
        self.rawmalloced_objects = NULL
        # --- the local "normal" old objects (chained list via hdr.version)
        self.old_objects = NULL
        # --- the local objects with weakrefs (chained list via hdr.version)
        #self.young_objects_with_weakrefs = NULL
        #self.old_objects_with_weakrefs = NULL
        #
        self._register_with_C_code()

    def teardown_thread(self):
        self._cleanup_state()
        self._unregister_with_C_code()
        self._free_nursery(self.nursery_start)
        free_non_gc_object(self)

    def _alloc_nursery(self, nursery_size):
        nursery = llarena.arena_malloc(nursery_size, 1)
        if not nursery:
            raise MemoryError("cannot allocate nursery")
        return nursery

    def _free_nursery(self, nursery):
        llarena.arena_free(nursery)

    def _register_with_C_code(self):
        if we_are_translated():
            tls = cast_instance_to_base_ptr(self)
            tlsaddr = llmemory.cast_ptr_to_adr(tls)
        else:
            n = 10000 + len(StmGCTLS.nontranslated_dict)
            tlsaddr = rffi.cast(llmemory.Address, n)
            StmGCTLS.nontranslated_dict[n] = self
        self.stm_operations.set_tls(tlsaddr, int(self.in_main_thread))

    def _unregister_with_C_code(self):
        ll_assert(self.gc.get_tls() is self,
                  "unregister_with_C_code: wrong thread")
        self.stm_operations.del_tls()

    @staticmethod
    @always_inline
    def cast_address_to_tls_object(tlsaddr):
        if we_are_translated():
            tls = llmemory.cast_adr_to_ptr(tlsaddr, base_ptr_lltype())
            return cast_base_ptr_to_instance(tls)
        else:
            n = rffi.cast(lltype.Signed, tlsaddr)
            return StmGCTLS.nontranslated_dict[n]

    def _disable_mallocs(self):
        ll_assert(bool(self.nursery_free), "disable_mallocs: already disabled")
        self.nursery_pending_clear = self.nursery_free - self.nursery_start
        self.nursery_free = NULL
        self.nursery_top  = NULL

    # ------------------------------------------------------------

    def enter_transactional_mode(self):
        """Called on the main thread, just before spawning the other
        threads."""
        self.local_collection()
        if not self.local_nursery_is_empty():
            self.local_collection(run_finalizers=False)
        self._promote_locals_to_globals()
        self._disable_mallocs()

    def leave_transactional_mode(self):
        """Restart using the main thread for mallocs."""
        if not we_are_translated():
            for key, value in StmGCTLS.nontranslated_dict.items():
                if value is not self:
                    del StmGCTLS.nontranslated_dict[key]
        self.start_transaction()

    def start_transaction(self):
        """Enter a thread: performs any pending cleanups, and set
        up a fresh state for allocating.  Called at the start of
        each transaction, and at the start of the main thread."""
        # Note that the calls to enter() and
        # end_of_transaction_collection() are not balanced: if a
        # transaction is aborted, the latter might never be called.
        # Be ready here to clean up any state.
        self._cleanup_state()
        if self.nursery_free:
            clear_size = self.nursery_free - self.nursery_start
        else:
            clear_size = self.nursery_pending_clear
        self.nursery_pending_clear = 0
        if clear_size > 0:
            llarena.arena_reset(self.nursery_start, clear_size, 2)
        self.nursery_free = self.nursery_start
        self.nursery_top  = self.nursery_start + self.nursery_size

    def local_nursery_is_empty(self):
        ll_assert(self.nursery_free, "local_nursery_is_empty: gc not running")
        return self.nursery_free == self.nursery_start

    # ------------------------------------------------------------

    def local_collection(self, run_finalizers=True):
        """Do a local collection.  Finds all surviving young objects
        and make them old.  Also looks for roots from the stack.
        The flag GCFLAG_WAS_COPIED is kept and the C tree is updated
        if the local young object moves.
        """
        #
        debug_start("gc-local")
        #
        # First, find the roots that point to young objects.  All nursery
        # objects found are copied out of the nursery, and the occasional
        # young raw-malloced object is flagged with GCFLAG_VISITED.
        # Note that during this step, we ignore references to further
        # young objects; only objects directly referenced by roots
        # are copied out or flagged.  They are also added to the list
        # 'old_objects_pointing_to_young'.
        self.collect_roots_in_nursery()
        #
        while True:
            # If we are using card marking, do a partial trace of the arrays
            # that are flagged with GCFLAG_CARDS_SET.
            if self.card_page_indices > 0:
                self.collect_cardrefs_to_nursery()
            #
            # Now trace objects from 'old_objects_pointing_to_young'.
            # All nursery objects they reference are copied out of the
            # nursery, and again added to 'old_objects_pointing_to_young'.
            # All young raw-malloced object found are flagged GCFLAG_VISITED.
            # We proceed until 'old_objects_pointing_to_young' is empty.
            self.collect_oldrefs_to_nursery()
            #
            # We have to loop back if collect_oldrefs_to_nursery caused
            # new objects to show up in old_objects_with_cards_set
            if self.card_page_indices > 0:
                if self.old_objects_with_cards_set.non_empty():
                    continue
            break
        #
        # Now all live nursery objects should be out.  Update the young
        # weakrefs' targets.
        if self.young_objects_with_weakrefs.non_empty():
            self.invalidate_young_weakrefs()
        if self.young_objects_with_light_finalizers.non_empty():
            self.deal_with_young_objects_with_finalizers()
        #
        # Clear this mapping.
        if self.nursery_objects_shadows.length() > 0:
            self.nursery_objects_shadows.clear()
        #
        # Walk the list of young raw-malloced objects, and either free
        # them or make them old.
        if self.young_rawmalloced_objects:
            self.free_young_rawmalloced_objects()
        #
        # All live nursery objects are out, and the rest dies.  Fill
        # the whole nursery with zero and reset the current nursery pointer.
        llarena.arena_reset(self.nursery, self.nursery_size, 2)
        self.debug_rotate_nursery()
        self.nursery_free = self.nursery
        #
        debug_print("minor collect, total memory used:",
                    self.get_total_memory_used())
        if self.DEBUG >= 2:
            self.debug_check_consistency()     # expensive!
        debug_stop("gc-minor")

    def end_of_transaction_collection(self):
        """Do an end-of-transaction collection.  Finds all surviving
        non-GCFLAG_WAS_COPIED young objects and make them old.  Assumes
        that there are no roots from the stack.  This guarantees that the
        nursery will end up empty, apart from GCFLAG_WAS_COPIED objects.
        To finish the commit, the C code will need to copy them over the
        global objects (or abort in case of conflict, which is still ok).

        No more mallocs are allowed after this is called.
        """
        xxx

    # ------------------------------------------------------------

    @always_inline
    def allocate_bump_pointer(self, size):
        free = self.nursery_free
        top  = self.nursery_top
        if (top - free) < llmemory.raw_malloc_usage(size):
            free = self.allocate_object_of_size(size)
        self.nursery_free = free + size
        return free

    @dont_inline
    def allocate_object_of_size(self, size):
        if not self.nursery_free:
            fatalerror("malloc in a non-main thread but outside a transaction")
        if size > self.nursery_size:
            fatalerror("object too large to ever fit in the nursery")
        while True:
            self.local_collection()
            free = self.nursery_free
            top  = self.nursery_top
            if (top - free) < llmemory.raw_malloc_usage(size):
                continue         # try again
            return free

    # ------------------------------------------------------------

    def _promote_locals_to_globals(self):
        ll_assert(self.local_nursery_is_empty(), "nursery must be empty [1]")
        #
        obj = self.old_objects
        self.old_objects = NULL
        while obj:
            hdr = self.header(obj)
            hdr.tid |= GCFLAG_GLOBAL
            obj = hdr.version
        #
        obj = self.rawmalloced_objects
        self.rawmalloced_objects = NULL
        while obj:
            hdr = self.header(obj)
            hdr.tid |= GCFLAG_GLOBAL
            obj = hdr.version

    def _cleanup_state(self):
        if self.rawmalloced_objects:
            xxx     # free the rawmalloced_objects still around
