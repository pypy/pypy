from pypy.rpython.lltypesystem import lltype, llmemory

class GCBase(object):
    _alloc_flavor_ = "raw"
    moving_gc = False

    def set_query_functions(self, is_varsize, getfinalizer,
                            offsets_to_gc_pointers,
                            fixed_size, varsize_item_sizes,
                            varsize_offset_to_variable_part,
                            varsize_offset_to_length,
                            varsize_offsets_to_gcpointers_in_var_part,
                            weakpointer_offset):
        self.getfinalizer = getfinalizer
        self.is_varsize = is_varsize
        self.offsets_to_gc_pointers = offsets_to_gc_pointers
        self.fixed_size = fixed_size
        self.varsize_item_sizes = varsize_item_sizes
        self.varsize_offset_to_variable_part = varsize_offset_to_variable_part
        self.varsize_offset_to_length = varsize_offset_to_length
        self.varsize_offsets_to_gcpointers_in_var_part = varsize_offsets_to_gcpointers_in_var_part
        self.weakpointer_offset = weakpointer_offset

    def write_barrier(self, addr, addr_to, addr_struct):
        addr_to.address[0] = addr

    def setup(self):
        pass

    def statistics(self, index):
        return -1

    def size_gc_header(self, typeid=0):
        return self.gcheaderbuilder.size_gc_header

    def malloc(self, typeid, length=0, zero=False):
        """For testing.  The interface used by the gctransformer is
        the four malloc_[fixed,var]size[_clear]() functions.
        """
        size = self.fixed_size(typeid)
        needs_finalizer = bool(self.getfinalizer(typeid))
        weakptr_offset = self.weakpointer_offset(typeid)
        #XXX cannot compare weakptr_offset with -1
        #contains_weakptr = weakpointer_offset. != -1
        if isinstance(weakptr_offset, int):
            assert weakptr_offset == -1
            contains_weakptr = False
        else:
            contains_weakptr = True
        assert not (needs_finalizer and contains_weakptr)
        if self.is_varsize(typeid):
            assert not contains_weakptr
            itemsize = self.varsize_item_sizes(typeid)
            offset_to_length = self.varsize_offset_to_length(typeid)
            if zero:
                malloc_varsize = self.malloc_varsize_clear
            else:
                malloc_varsize = self.malloc_varsize
            ref = malloc_varsize(typeid, length, size, itemsize,
                                 offset_to_length, True, needs_finalizer)
        else:
            if zero:
                malloc_fixedsize = self.malloc_fixedsize_clear
            else:
                malloc_fixedsize = self.malloc_fixedsize
            ref = malloc_fixedsize(typeid, size, True, needs_finalizer,
                                   contains_weakptr)
        # lots of cast and reverse-cast around...
        return llmemory.cast_ptr_to_adr(ref)

    def id(self, ptr):
        return lltype.cast_ptr_to_int(ptr)

    def x_swap_pool(self, newpool):
        return newpool

    def x_clone(self, clonedata):
        raise RuntimeError("no support for x_clone in the GC")

    def x_become(self, target_addr, source_addr):
        raise RuntimeError("no support for x_become in the GC")


class MovingGCBase(GCBase):
    moving_gc = True

    def __init__(self):
        self.wr_to_objects_with_id = []

    def id(self, ptr):
        # XXX linear search! this is probably too slow to be reasonable :-(
        # On the other hand, it punishes you for using 'id', so that's good :-)
        # XXX this may explode if --no-translation-rweakref is specified
        lst = self.wr_to_objects_with_id
        i = len(lst)
        freeentry = -1
        while i > 0:
            i -= 1
            target = llmemory.weakref_deref(llmemory.GCREF, lst[i])
            if not target:
                freeentry = i
            elif target == ptr:
                break               # found
        else:
            # not found
            wr = llmemory.weakref_create(ptr)
            if freeentry == -1:
                i = len(lst)
                lst.append(wr)
            else:
                i = freeentry       # reuse the id() of a dead object
                lst[i] = wr
        return i + 1       # this produces id() values 1, 2, 3, 4...


def choose_gc_from_config(config):
    """Return a (GCClass, GC_PARAMS) from the given config object.
    """
    config.translation.gc = "framework"
    if config.translation.frameworkgc == "marksweep":
        GC_PARAMS = {'start_heap_size': 8*1024*1024} # XXX adjust
        from pypy.rpython.memory.gc.marksweep import MarkSweepGC
        return MarkSweepGC, GC_PARAMS
    elif config.translation.frameworkgc == "semispace":
        GC_PARAMS = {'space_size': 8*1024*1024} # XXX adjust
        from pypy.rpython.memory.gc.semispace import SemiSpaceGC
        return SemiSpaceGC, GC_PARAMS
    else:
        raise ValueError("unknown value for frameworkgc: %r" % (
            config.translation.frameworkgc,))
