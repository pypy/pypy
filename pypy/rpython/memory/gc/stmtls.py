from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance, base_ptr_lltype
from pypy.rlib import objectmodel
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.debug import ll_assert

from pypy.rpython.memory.gc.stmgc import WORD, NULL


class StmGCTLS(object):
    """The thread-local structure: we have one instance of these per thread,
    including one for the main thread."""

    _alloc_flavor_ = 'raw'

    def __init__(self, gc, in_main_thread):
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
        # --- the start and size of the nursery belonging to this thread.
        #     never changes.
        self.nursery_size  = self.gc.nursery_size
        self.nursery_start = self._alloc_nursery(self.nursery_size)
        #
        # --- the local raw-malloced objects, young and old
        self.rawmalloced_young_objects = self.null_address_dict()
        self.rawmalloced_old_objects = self.AddressStack()
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
        objectmodel.free_non_gc_object(self)

    def _alloc_nursery(self, nursery_size):
        nursery = llarena.arena_malloc(nursery_size, 1)
        if not nursery:
            raise MemoryError("cannot allocate nursery")
        return nursery

    def _free_nursery(self, nursery):
        llarena.arena_free(nursery)

    def _register_with_C_code(self):
        tls = cast_instance_to_base_ptr(self)
        self.stm_operations.set_tls(llmemory.cast_ptr_to_adr(tls),
                                    int(self.in_main_thread))

    def _unregister_with_C_code(self):
        ll_assert(self.gc.get_tls() is self,
                  "unregister_with_C_code: wrong thread")
        self.stm_operations.del_tls()

    @staticmethod
    def cast_address_to_tls_object(self, tlsaddr):
        tls = llmemory.cast_adr_to_ptr(tlsaddr, base_ptr_lltype())
        return cast_base_ptr_to_instance(tls)

    # ------------------------------------------------------------

    def enter(self):
        """Enter a thread: performs any pending cleanups, and set
        up a fresh state for allocating.  Called at the start of
        transactions, and at the start of the main thread."""
        # Note that the calls to enter() and leave() are not balanced:
        # if a transaction is aborted, leave() might never be called.
        # Be ready here to clean up any state.
        xxx

    def leave(self):
        """Leave a thread: no more allocations are allowed.
        Called when a transaction finishes."""
        xxx

    # ------------------------------------------------------------

    def end_of_transaction_collection(self):
        """Do an end-of-transaction collection.  Finds all surviving
        young objects and make them old.  This guarantees that the
        nursery is empty afterwards.  (Even if there are finalizers, XXX)
        Assumes that there are no roots from the stack.
        """
        xxx

    def local_collection(self):
        """Do a local collection.  Finds all surviving young objects
        and make them old.  Also looks for roots from the stack.
        """
        xxx

    # ------------------------------------------------------------
