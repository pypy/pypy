from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.llmemory import raw_malloc_usage
from pypy.rpython.memory.gc.base import GCBase
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.rlib.debug import ll_assert, debug_start, debug_stop
from pypy.module.thread import ll_thread


WORD = LONG_BIT // 8
NULL = llmemory.NULL

first_gcflag = 1 << (LONG_BIT//2)

GCFLAG_GLOBAL     = first_gcflag << 0
GCFLAG_WAS_COPIED = first_gcflag << 1


def always_inline(fn):
    fn._always_inline_ = True
    return fn
def dont_inline(fn):
    fn._dont_inline_ = True
    return fn


class StmOperations(object):
    def _freeze_(self):
        return True


class StmGC(GCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    needs_write_barrier = "stm"
    prebuilt_gc_objects_are_static_roots = False
    malloc_zero_filled = True    # xxx?

    HDR = lltype.Struct('header', ('tid', lltype.Signed),
                                  ('version', llmemory.Address))
    typeid_is_in_field = 'tid'
    withhash_flag_is_in_field = 'tid', 'XXX'

    GCTLS = lltype.Struct('GCTLS', ('nursery_free', llmemory.Address),
                                   ('nursery_top', llmemory.Address),
                                   ('nursery_start', llmemory.Address),
                                   ('nursery_size', lltype.Signed),
                                   ('malloc_flags', lltype.Signed),
                                   ('pending_list', llmemory.Address),
                          )

    def __init__(self, config, stm_operations,
                 max_nursery_size=1024,
                 **kwds):
        GCBase.__init__(self, config, **kwds)
        self.stm_operations = stm_operations
        self.collector = Collector(self)
        self.max_nursery_size = max_nursery_size
        #
        self.declare_readers()
        self.declare_write_barrier()

    def setup(self):
        """Called at run-time to initialize the GC."""
        GCBase.setup(self)
        self.main_thread_tls = self.setup_thread(True)
        self.mutex_lock = ll_thread.allocate_ll_lock()

    def _alloc_nursery(self):
        nursery = llarena.arena_malloc(self.max_nursery_size, 1)
        if not nursery:
            raise MemoryError("cannot allocate nursery")
        return nursery

    def _free_nursery(self, nursery):
        llarena.arena_free(nursery)

    def setup_thread(self, in_main_thread):
        """Setup a thread.  Allocates the thread-local data structures.
        Must be called only once per OS-level thread."""
        tls = lltype.malloc(self.GCTLS, flavor='raw')
        self.stm_operations.set_tls(self, llmemory.cast_ptr_to_adr(tls))
        tls.nursery_start = self._alloc_nursery()
        tls.nursery_size  = self.max_nursery_size
        tls.nursery_free  = tls.nursery_start
        tls.nursery_top   = tls.nursery_start + tls.nursery_size
        #
        # XXX for now, we use as the "global area" the nursery of the
        # main thread.  So allocation in the main thread is the same as
        # allocation in another thread, except that the new objects
        # should be immediately marked as GCFLAG_GLOBAL.
        if in_main_thread:
            tls.malloc_flags = GCFLAG_GLOBAL
        else:
            tls.malloc_flags = 0
        return tls

    @staticmethod
    def reset_nursery(tls):
        """Clear and forget all locally allocated objects."""
        size = tls.nursery_free - tls.nursery_start
        llarena.arena_reset(tls.nursery_start, size, 2)
        tls.nursery_free = tls.nursery_start

    def teardown_thread(self):
        """Teardown a thread.  Call this just before the OS-level thread
        disappears."""
        tls = self.collector.get_tls()
        self.stm_operations.set_tls(self, NULL)
        self._free_nursery(tls.nursery_start)
        lltype.free(tls, flavor='raw')

    # ----------

    def allocate_bump_pointer(self, size):
        return self._allocate_bump_pointer(self.collector.get_tls(), size)

    @always_inline
    def _allocate_bump_pointer(self, tls, size):
        free = tls.nursery_free
        top  = tls.nursery_top
        new  = free + size
        tls.nursery_free = new
        if new > top:
            free = self.local_collection(free)
        return free

    @dont_inline
    def local_collection(self, oldfree):
        raise MemoryError("nursery exhausted")   # XXX for now


    def malloc_fixedsize_clear(self, typeid, size,
                               needs_finalizer=False,
                               is_finalizer_light=False,
                               contains_weakptr=False):
        assert not needs_finalizer, "XXX"
        assert not contains_weakptr, "XXX"
        #
        # Check the mode: either in a transactional thread, or in
        # the main thread.  For now we do the same thing in both
        # modes, but set different flags.
        tls = self.collector.get_tls()
        flags = tls.malloc_flags
        #
        # Get the memory from the nursery.
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        result = self._allocate_bump_pointer(tls, totalsize)
        #
        # Build the object.
        llarena.arena_reserve(result, totalsize)
        obj = result + size_gc_header
        self.init_gc_object(result, typeid, flags=flags)
        #
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)


    def _malloc_local_raw(self, tls, size):
        # for _stm_write_barrier_global(): a version of malloc that does
        # no initialization of the malloc'ed object
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        result = self._allocate_bump_pointer(tls, totalsize)
        llarena.arena_reserve(result, totalsize)
        obj = result + size_gc_header
        return obj


    @always_inline
    def combine(self, typeid16, flags):
        return llop.combine_ushort(lltype.Signed, typeid16, flags)

    @always_inline
    def init_gc_object(self, addr, typeid16, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = self.combine(typeid16, flags)

    # ----------

    def declare_readers(self):
        # Reading functions.  Defined here to avoid the extra burden of
        # passing 'self' explicitly.
        stm_operations = self.stm_operations
        #
        @always_inline
        def read_signed(obj, offset):
            if self.header(obj).tid & GCFLAG_GLOBAL == 0:
                return (obj + offset).signed[0]    # local obj: read directly
            else:
                return _read_word_global(obj, offset)   # else: call a helper
        self.read_signed = read_signed
        #
        @dont_inline
        def _read_word_global(obj, offset):
            hdr = self.header(obj)
            if hdr.tid & GCFLAG_WAS_COPIED != 0:
                #
                # Look up in the thread-local dictionary.
                localobj = stm_operations.tldict_lookup(obj)
                if localobj:
                    ll_assert(self.header(localobj).tid & GCFLAG_GLOBAL == 0,
                              "stm_read: tldict_lookup() -> GLOBAL obj")
                    return (localobj + offset).signed[0]
            #
            return stm_operations.stm_read_word(obj, offset)


    def declare_write_barrier(self):
        # Write barrier.  Defined here to avoid the extra burden of
        # passing 'self' explicitly.
        stm_operations = self.stm_operations
        #
        @always_inline
        def write_barrier(obj):
            if self.header(obj).tid & GCFLAG_GLOBAL != 0:
                obj = _stm_write_barrier_global(obj)
            return obj
        self.write_barrier = write_barrier
        #
        @dont_inline
        def _stm_write_barrier_global(obj):
            # we need to find of make a local copy
            hdr = self.header(obj)
            if hdr.tid & GCFLAG_WAS_COPIED == 0:
                # in this case, we are sure that we don't have a copy
                hdr.tid |= GCFLAG_WAS_COPIED
                # ^^^ non-protected write, but concurrent writes should
                #     have the same effect, so fine
            else:
                # in this case, we need to check first
                localobj = stm_operations.tldict_lookup(obj)
                if localobj:
                    hdr = self.header(localobj)
                    ll_assert(hdr.tid & GCFLAG_GLOBAL == 0,
                              "stm_write: tldict_lookup() -> GLOBAL obj")
                    ll_assert(hdr.tid & GCFLAG_WAS_COPIED != 0,
                              "stm_write: tldict_lookup() -> non-COPIED obj")
                    return localobj
            #
            # Here, we need to really make a local copy
            size = self.get_size(obj)
            tls = self.collector.get_tls()
            try:
                localobj = self._malloc_local_raw(tls, size)
            except MemoryError:
                # XXX
                fatalerror("MemoryError in _stm_write_barrier_global -- sorry")
                return llmemory.NULL
            #
            # Initialize the copy by doing an stm raw copy of the bytes
            stm_operations.stm_copy_transactional_to_raw(obj, localobj, size)
            #
            # The raw copy done above includes all header fields.
            # Check at least the gc flags of the copy.
            hdr = self.header(obj)
            localhdr = self.header(localobj)
            GCFLAGS = (GCFLAG_GLOBAL | GCFLAG_WAS_COPIED)
            ll_assert(hdr.tid & GCFLAGS == GCFLAGS,
                      "stm_write: bogus flags on source object")
            ll_assert(localhdr.tid & GCFLAGS == GCFLAGS,
                      "stm_write: flags not copied!")
            #
            # Remove the GCFLAG_GLOBAL from the copy
            localhdr.tid &= ~GCFLAG_GLOBAL
            #
            # Set the 'version' field of the local copy to be a pointer
            # to the global obj.  (The field is called 'version' because
            # of its use by the C STM library: on global objects (only),
            # it is a version number.)
            localhdr.version = obj
            #
            # Register the object as a valid copy
            stm_operations.tldict_add(obj, localobj)
            #
            return localobj

    # ----------

    def acquire(self, lock):
        ll_thread.c_thread_acquirelock(lock, 1)

    def release(self, lock):
        ll_thread.c_thread_releaselock(lock)


# ------------------------------------------------------------


class Collector(object):
    """A separate frozen class.  Useful to prevent any buggy concurrent
    access to GC data.  The methods here use the GCTLS instead for
    storing things in a thread-local way."""

    def __init__(self, gc):
        self.gc = gc
        self.stm_operations = gc.stm_operations

    def _freeze_(self):
        return True

    def get_tls(self):
        tls = self.stm_operations.get_tls()
        return llmemory.cast_adr_to_ptr(tls, lltype.Ptr(StmGC.GCTLS))

    def is_in_nursery(self, tls, addr):
        ll_assert(llmemory.cast_adr_to_int(addr) & 1 == 0,
                  "odd-valued (i.e. tagged) pointer unexpected here")
        return tls.nursery_start <= addr < tls.nursery_top

    def header(self, obj):
        return self.gc.header(obj)


    def start_transaction(self):
        """Start a transaction, by clearing and resetting the tls nursery."""
        tls = self.get_tls()
        self.gc.reset_nursery(tls)


    def commit_transaction(self):
        """End of a transaction, just before its end.  No more GC
        operations should occur afterwards!  Note that the C code that
        does the commit runs afterwards, and may still abort."""
        #
        debug_start("gc-collect-commit")
        #
        tls = self.get_tls()
        #
        # Do a mark-and-move minor collection out of the tls' nursery
        # into the main thread's global area (which is right now also
        # called a nursery).  To simplify things, we use a global lock
        # around the whole mark-and-move.
        self.gc.acquire(self.gc.mutex_lock)
        #
        # We are starting from the tldict's local objects as roots.  At
        # this point, these objects have GCFLAG_WAS_COPIED, and the other
        # local objects don't.  We want to move all reachable local objects
        # to the global area.
        #
        # Start from tracing the root objects
        self.collect_roots_from_tldict(tls)
        #
        # Continue iteratively until we have reached all the reachable
        # local objects
        self.collect_from_pending_list(tls)
        #
        self.gc.release(self.gc.mutex_lock)
        #
        # Now, all indirectly reachable local objects have been copied into
        # the global area, and all pointers have been fixed to point to the
        # global copies, including in the local copy of the roots.  What
        # remains is only overwriting of the global copy of the roots.
        # This is done by the C code.
        debug_stop("gc-collect-commit")


    def collect_roots_from_tldict(self, tls):
        tls.pending_list = NULL
        # Enumerate the roots, which are the local copies of global objects.
        # For each root, trace it.
        self.stm_operations.enum_tldict_start()
        while self.stm_operations.enum_tldict_find_next():
            globalobj = self.stm_operations.enum_tldict_globalobj()
            localobj = self.stm_operations.enum_tldict_localobj()
            #
            localhdr = self.header(localobj)
            ll_assert(localhdr.version == globalobj,
                      "in a root: localobj.version != globalobj")
            ll_assert(localhdr.tid & GCFLAG_GLOBAL == 0,
                      "in a root: unexpected GCFLAG_GLOBAL")
            ll_assert(localhdr.tid & GCFLAG_WAS_COPIED != 0,
                      "in a root: missing GCFLAG_WAS_COPIED")
            #
            self.trace_and_drag_out_of_nursery(tls, localobj)


    def collect_from_pending_list(self, tls):
        while tls.pending_list != NULL:
            pending_obj = tls.pending_list
            pending_hdr = self.header(pending_obj)
            #
            # 'pending_list' is a chained list of fresh global objects,
            # linked together via their 'version' field.  The 'version'
            # must be replaced with NULL after we pop the object from
            # the linked list.
            tls.pending_list = pending_hdr.version
            pending_hdr.version = NULL
            #
            # Check the flags of pending_obj: it should be a fresh global
            # object, without GCFLAG_WAS_COPIED
            ll_assert(pending_hdr.tid & GCFLAG_GLOBAL != 0,
                      "from pending list: missing GCFLAG_GLOBAL")
            ll_assert(pending_hdr.tid & GCFLAG_WAS_COPIED == 0,
                      "from pending list: unexpected GCFLAG_WAS_COPIED")
            #
            self.trace_and_drag_out_of_nursery(tls, pending_obj)


    def trace_and_drag_out_of_nursery(self, tls, obj):
        # This is called to fix the references inside 'obj', to ensure that
        # they are global.  If necessary, the referenced objects are copied
        # into the global area first.  This is called on the *local* copy of
        # the roots, and on the fresh *global* copy of all other reached
        # objects.
        self.gc.trace(obj, self._trace_drag_out, tls)

    def _trace_drag_out(self, root, tls):
        obj = root.address[0]
        hdr = self.header(obj)
        #
        # Figure out if the object is GLOBAL or not by looking at its
        # address, not at its header --- to avoid cache misses and
        # pollution for all global objects
        if not self.is_in_nursery(tls, obj):
            ll_assert(hdr.tid & GCFLAG_GLOBAL != 0,
                      "trace_and_mark: non-GLOBAL obj is not in nursery")
            return        # ignore global objects
        #
        ll_assert(hdr.tid & GCFLAG_GLOBAL == 0,
                  "trace_and_mark: GLOBAL obj in nursery")
        #
        if hdr.tid & GCFLAG_WAS_COPIED != 0:
            # this local object is a root or was already marked.  Either
            # way, its 'version' field should point to the corresponding
            # global object.
            globalobj = hdr.version
            #
        else:
            # First visit to a local-only 'obj': copy it into the global area
            size = self.gc.get_size(obj)
            main_tls = self.gc.main_thread_tls
            globalobj = self.gc._malloc_local_raw(main_tls, size)
            llmemory.raw_memcopy(obj, globalobj, size)
            #
            # Initialize the header of the 'globalobj'
            globalhdr = self.header(globalobj)
            globalhdr.tid = hdr.tid | GCFLAG_GLOBAL
            #
            # Add the flags to 'localobj' to say 'has been copied now'
            hdr.tid |= GCFLAG_WAS_COPIED
            hdr.version = globalobj
            #
            # Set a temporary linked list through the globalobj's version
            # numbers.  This is normally not allowed, but it works here
            # because these new globalobjs are not visible to any other
            # thread before the commit is really complete.
            globalhdr.version = tls.pending_list
            tls.pending_list = globalobj
        #
        # Fix the original root.address[0] to point to the globalobj
        root.address[0] = globalobj
