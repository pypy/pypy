from pypy.rpython.lltypesystem import lltype, llmemory, llarena, rffi
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance, base_ptr_lltype
from pypy.rlib.objectmodel import we_are_translated, free_non_gc_object
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.debug import ll_assert

from pypy.rpython.memory.gc.stmgc import WORD, NULL


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
        # --- the local raw-malloced objects, young and old
        self.rawmalloced_young_objects = self.null_address_dict()
        self.rawmalloced_old_objects = None
        self.rawmalloced_total_size = r_uint(0)
        # --- the local objects with weakrefs, young and old
        self.young_objects_with_weakrefs = self.AddressStack()
        self.old_objects_with_weakrefs = self.AddressStack()
        # --- support for id and identityhash: maps nursery objects with
        #     GCFLAG_HAS_SHADOW to their future location at the next
        #     local collection
        self.nursery_objects_shadows = self.AddressDict()
        #
        self._register_with_C_code()

    def teardown_thread(self):
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
            n = 10000 + len(self.nontranslated_dict)
            tlsaddr = rffi.cast(llmemory.Address, n)
            self.nontranslated_dict[n] = self
        self.stm_operations.set_tls(tlsaddr, int(self.in_main_thread))

    def _unregister_with_C_code(self):
        ll_assert(self.gc.get_tls() is self,
                  "unregister_with_C_code: wrong thread")
        self.stm_operations.del_tls()

    @staticmethod
    def cast_address_to_tls_object(self, tlsaddr):
        if we_are_translated():
            tls = llmemory.cast_adr_to_ptr(tlsaddr, base_ptr_lltype())
            return cast_base_ptr_to_instance(tls)
        else:
            n = rffi.cast(lltype.Signed, tlsaddr)
            return self.nontranslated_dict[n]

    # ------------------------------------------------------------

    def start_transaction(self):
        """Enter a thread: performs any pending cleanups, and set
        up a fresh state for allocating.  Called at the start of
        each transaction, and at the start of the main thread."""
        # Note that the calls to enter() and
        # end_of_transaction_collection() are not balanced: if a
        # transaction is aborted, the latter might never be called.
        # Be ready here to clean up any state.
        if self.nursery_free:
            clear_size = self.nursery_free - self.nursery_start
        else:
            clear_size = self.nursery_pending_clear
        if clear_size > 0:
            llarena.arena_reset(self.nursery_start, clear_size, 2)
            self.nursery_pending_clear = 0
        if self.rawmalloced_young_objects:
            xxx
        if self.rawmalloced_old_objects:
            xxx
        self.nursery_free = self.nursery_start
        self.nursery_top  = self.nursery_start + self.nursery_size

    # ------------------------------------------------------------

    def local_collection(self):
        """Do a local collection.  Finds all surviving young objects
        and make them old.  Also looks for roots from the stack.
        The flag GCFLAG_WAS_COPIED is kept and the C tree is updated
        if the local young object moves.
        """
        xxx

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
