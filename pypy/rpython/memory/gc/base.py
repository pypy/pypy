from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rlib.debug import ll_assert
from pypy.rpython.memory.gcheader import GCHeaderBuilder
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rpython.memory.support import get_address_stack, get_address_deque
from pypy.rpython.memory.support import AddressDict
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage

class GCBase(object):
    _alloc_flavor_ = "raw"
    moving_gc = False
    needs_write_barrier = False
    malloc_zero_filled = False
    prebuilt_gc_objects_are_static_roots = True
    can_realloc = False

    def __init__(self, config, chunk_size=DEFAULT_CHUNK_SIZE):
        self.gcheaderbuilder = GCHeaderBuilder(self.HDR)
        self.AddressStack = get_address_stack(chunk_size)
        self.AddressDeque = get_address_deque(chunk_size)
        self.AddressDict = AddressDict
        self.finalizer_lock_count = 0
        self.config = config

    def can_malloc_nonmovable(self):
        return not self.moving_gc

    # The following flag enables costly consistency checks after each
    # collection.  It is automatically set to True by test_gc.py.  The
    # checking logic is translatable, so the flag can be set to True
    # here before translation.
    DEBUG = False

    def set_query_functions(self, is_varsize, has_gcptr_in_varsize,
                            is_gcarrayofgcptr,
                            getfinalizer,
                            offsets_to_gc_pointers,
                            fixed_size, varsize_item_sizes,
                            varsize_offset_to_variable_part,
                            varsize_offset_to_length,
                            varsize_offsets_to_gcpointers_in_var_part,
                            weakpointer_offset):
        self.getfinalizer = getfinalizer
        self.is_varsize = is_varsize
        self.has_gcptr_in_varsize = has_gcptr_in_varsize
        self.is_gcarrayofgcptr = is_gcarrayofgcptr
        self.offsets_to_gc_pointers = offsets_to_gc_pointers
        self.fixed_size = fixed_size
        self.varsize_item_sizes = varsize_item_sizes
        self.varsize_offset_to_variable_part = varsize_offset_to_variable_part
        self.varsize_offset_to_length = varsize_offset_to_length
        self.varsize_offsets_to_gcpointers_in_var_part = varsize_offsets_to_gcpointers_in_var_part
        self.weakpointer_offset = weakpointer_offset

    def set_root_walker(self, root_walker):
        self.root_walker = root_walker

    def write_barrier(self, newvalue, addr_struct):
        pass

    def setup(self):
        self.run_finalizers = self.AddressDeque()

    def statistics(self, index):
        return -1

    def size_gc_header(self, typeid=0):
        return self.gcheaderbuilder.size_gc_header

    def header(self, addr):
        addr -= self.gcheaderbuilder.size_gc_header
        return llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))

    def get_size(self, obj):
        typeid = self.get_type_id(obj)
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            lenaddr = obj + self.varsize_offset_to_length(typeid)
            length = lenaddr.signed[0]
            size += length * self.varsize_item_sizes(typeid)
            size = llarena.round_up_for_allocation(size)
            # XXX maybe we should parametrize round_up_for_allocation()
            # per GC; if we do, we also need to fix the call in
            # gctypelayout.encode_type_shape()
        return size

    def malloc(self, typeid, length=0, zero=False):
        """For testing.  The interface used by the gctransformer is
        the four malloc_[fixed,var]size[_clear]() functions.
        """
        # Rules about fallbacks in case of missing malloc methods:
        #  * malloc_fixedsize_clear() and malloc_varsize_clear() are mandatory
        #  * malloc_fixedsize() and malloc_varsize() fallback to the above
        # XXX: as of r49360, gctransformer.framework never inserts calls
        # to malloc_varsize(), but always uses malloc_varsize_clear()

        size = self.fixed_size(typeid)
        needs_finalizer = bool(self.getfinalizer(typeid))
        contains_weakptr = self.weakpointer_offset(typeid) >= 0
        assert not (needs_finalizer and contains_weakptr)
        if self.is_varsize(typeid):
            assert not contains_weakptr
            itemsize = self.varsize_item_sizes(typeid)
            offset_to_length = self.varsize_offset_to_length(typeid)
            if zero or not hasattr(self, 'malloc_varsize'):
                malloc_varsize = self.malloc_varsize_clear
            else:
                malloc_varsize = self.malloc_varsize
            ref = malloc_varsize(typeid, length, size, itemsize,
                                 offset_to_length, True, needs_finalizer)
        else:
            if zero or not hasattr(self, 'malloc_fixedsize'):
                malloc_fixedsize = self.malloc_fixedsize_clear
            else:
                malloc_fixedsize = self.malloc_fixedsize
            ref = malloc_fixedsize(typeid, size, True, needs_finalizer,
                                   contains_weakptr)
        # lots of cast and reverse-cast around...
        return llmemory.cast_ptr_to_adr(ref)

    def malloc_nonmovable(self, typeid, length=0, zero=False):
        return self.malloc(typeid, length, zero)

    def id(self, ptr):
        return lltype.cast_ptr_to_int(ptr)

    def can_move(self, addr):
        return False

    def set_max_heap_size(self, size):
        pass

    def x_swap_pool(self, newpool):
        return newpool

    def x_clone(self, clonedata):
        raise RuntimeError("no support for x_clone in the GC")

    def trace(self, obj, callback, arg):
        """Enumerate the locations inside the given obj that can contain
        GC pointers.  For each such location, callback(pointer, arg) is
        called, where 'pointer' is an address inside the object.
        Typically, 'callback' is a bound method and 'arg' can be None.
        """
        typeid = self.get_type_id(obj)
        if self.is_gcarrayofgcptr(typeid):
            # a performance shortcut for GcArray(gcptr)
            length = (obj + llmemory.gcarrayofptr_lengthoffset).signed[0]
            item = obj + llmemory.gcarrayofptr_itemsoffset
            while length > 0:
                callback(item, arg)
                item += llmemory.gcarrayofptr_singleitemoffset
                length -= 1
            return
        offsets = self.offsets_to_gc_pointers(typeid)
        i = 0
        while i < len(offsets):
            callback(obj + offsets[i], arg)
            i += 1
        if self.has_gcptr_in_varsize(typeid):
            item = obj + self.varsize_offset_to_variable_part(typeid)
            length = (obj + self.varsize_offset_to_length(typeid)).signed[0]
            offsets = self.varsize_offsets_to_gcpointers_in_var_part(typeid)
            itemlength = self.varsize_item_sizes(typeid)
            while length > 0:
                j = 0
                while j < len(offsets):
                    callback(item + offsets[j], arg)
                    j += 1
                item += itemlength
                length -= 1
    trace._annspecialcase_ = 'specialize:arg(2)'

    def debug_check_consistency(self):
        """To use after a collection.  If self.DEBUG is set, this
        enumerates all roots and traces all objects to check if we didn't
        accidentally free a reachable object or forgot to update a pointer
        to an object that moved.
        """
        if self.DEBUG:
            from pypy.rlib.objectmodel import we_are_translated
            from pypy.rpython.memory.support import AddressDict
            self._debug_seen = AddressDict()
            self._debug_pending = self.AddressStack()
            if not we_are_translated():
                self.root_walker._walk_prebuilt_gc(self._debug_record)
            callback = GCBase._debug_callback
            self.root_walker.walk_roots(callback, callback, callback)
            pending = self._debug_pending
            while pending.non_empty():
                obj = pending.pop()
                self.debug_check_object(obj)
                self.trace(obj, self._debug_callback2, None)
            self._debug_seen.delete()
            self._debug_pending.delete()

    def _debug_record(self, obj):
        seen = self._debug_seen
        if not seen.contains(obj):
            seen.add(obj)
            self._debug_pending.append(obj)
    def _debug_callback(self, root):
        obj = root.address[0]
        ll_assert(bool(obj), "NULL address from walk_roots()")
        self._debug_record(obj)
    def _debug_callback2(self, pointer, ignored):
        obj = pointer.address[0]
        if obj:
            self._debug_record(obj)

    def debug_check_object(self, obj):
        pass

    def execute_finalizers(self):
        self.finalizer_lock_count += 1
        try:
            while self.run_finalizers.non_empty():
                if self.finalizer_lock_count > 1:
                    # the outer invocation of execute_finalizers() will do it
                    break
                obj = self.run_finalizers.popleft()
                finalizer = self.getfinalizer(self.get_type_id(obj))
                finalizer(obj)
        finally:
            self.finalizer_lock_count -= 1


class MovingGCBase(GCBase):
    moving_gc = True

    def setup(self):
        GCBase.setup(self)
        self.objects_with_id = self.AddressDict()
        self.id_free_list = self.AddressStack()
        self.next_free_id = 1

    def can_move(self, addr):
        return True

    def id(self, ptr):
        # Default implementation for id(), assuming that "external" objects
        # never move.  Overriden in the HybridGC.
        obj = llmemory.cast_ptr_to_adr(ptr)
        if self._is_external(obj):
            result = obj
        else:
            result = self._compute_id(obj)
        return llmemory.cast_adr_to_int(result)

    def _next_id(self):
        # return an id not currently in use (as an address instead of an int)
        if self.id_free_list.non_empty():
            result = self.id_free_list.pop()    # reuse a dead id
        else:
            # make up a fresh id number
            result = llmemory.cast_int_to_adr(self.next_free_id)
            self.next_free_id += 2    # only odd numbers, to make lltype
                                      # and llmemory happy and to avoid
                                      # clashes with real addresses
        return result

    def _compute_id(self, obj):
        # look if the object is listed in objects_with_id
        result = self.objects_with_id.get(obj)
        if not result:
            result = self._next_id()
            self.objects_with_id.setitem(obj, result)
        return result

    def update_objects_with_id(self):
        old = self.objects_with_id
        new_objects_with_id = self.AddressDict(old.length())
        old.foreach(self._update_object_id_FAST, new_objects_with_id)
        old.delete()
        self.objects_with_id = new_objects_with_id

    def _update_object_id(self, obj, id, new_objects_with_id):
        # safe version (used by subclasses)
        if self.surviving(obj):
            newobj = self.get_forwarding_address(obj)
            new_objects_with_id.setitem(newobj, id)
        else:
            self.id_free_list.append(id)

    def _update_object_id_FAST(self, obj, id, new_objects_with_id):
        # unsafe version, assumes that the new_objects_with_id is large enough
        if self.surviving(obj):
            newobj = self.get_forwarding_address(obj)
            new_objects_with_id.insertclean(newobj, id)
        else:
            self.id_free_list.append(id)


def choose_gc_from_config(config):
    """Return a (GCClass, GC_PARAMS) from the given config object.
    """
    if config.translation.gctransformer != "framework":   # for tests
        config.translation.gc = "marksweep"     # crash if inconsistent

    classes = {"marksweep": "marksweep.MarkSweepGC",
               "statistics": "marksweep.PrintingMarkSweepGC",
               "semispace": "semispace.SemiSpaceGC",
               "generation": "generation.GenerationGC",
               "hybrid": "hybrid.HybridGC",
               "markcompact" : "markcompact.MarkCompactGC",
               }
    try:
        modulename, classname = classes[config.translation.gc].split('.')
    except KeyError:
        raise ValueError("unknown value for translation.gc: %r" % (
            config.translation.gc,))
    module = __import__("pypy.rpython.memory.gc." + modulename,
                        globals(), locals(), [classname])
    GCClass = getattr(module, classname)
    return GCClass, GCClass.TRANSLATION_PARAMS
