from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rlib.debug import ll_assert


class GCData(object):
    """The GC information tables, and the query functions that the GC
    calls to decode their content.  The encoding of this information
    is done by encode_type_shape().  These two places should be in sync,
    obviously, but in principle no other code should depend on the
    details of the encoding in TYPE_INFO.
    """
    _alloc_flavor_ = 'raw'

    OFFSETS_TO_GC_PTR = lltype.Array(lltype.Signed)
    ADDRESS_VOID_FUNC = lltype.FuncType([llmemory.Address], lltype.Void)
    FINALIZERTYPE = lltype.Ptr(ADDRESS_VOID_FUNC)

    # structure describing the layout of a typeid
    TYPE_INFO = lltype.Struct("type_info",
        ("finalizer",      FINALIZERTYPE),
        ("fixedsize",      lltype.Signed),
        ("ofstoptrs",      lltype.Ptr(OFFSETS_TO_GC_PTR)),
        ("varitemsize",    lltype.Signed),
        ("ofstovar",       lltype.Signed),
        ("ofstolength",    lltype.Signed),
        ("varofstoptrs",   lltype.Ptr(OFFSETS_TO_GC_PTR)),
        ("weakptrofs",     lltype.Signed),
        )
    TYPE_INFO_TABLE = lltype.Array(TYPE_INFO)

    def __init__(self, type_info_table):
        self.type_info_table = type_info_table
        # 'type_info_table' is a list of TYPE_INFO structures when
        # running with gcwrapper, or a real TYPE_INFO_TABLE after
        # the gctransformer.

    def q_is_varsize(self, typeid):
        ll_assert(typeid > 0, "invalid type_id")
        return (typeid & T_IS_FIXSIZE) == 0

    def q_has_gcptr_in_varsize(self, typeid):
        ll_assert(typeid > 0, "invalid type_id")
        return (typeid & (T_IS_FIXSIZE|T_NO_GCPTR_IN_VARSIZE)) == 0

    def q_is_gcarrayofgcptr(self, typeid):
        ll_assert(typeid > 0, "invalid type_id")
        return (typeid &
                (T_IS_FIXSIZE|T_NO_GCPTR_IN_VARSIZE|T_NOT_SIMPLE_GCARRAY)) == 0

    def q_finalizer(self, typeid):
        ll_assert(typeid > 0, "invalid type_id")
        return self.type_info_table[typeid].finalizer

    def q_offsets_to_gc_pointers(self, typeid):
        ll_assert(typeid > 0, "invalid type_id")
        return self.type_info_table[typeid].ofstoptrs

    def q_fixed_size(self, typeid):
        ll_assert(typeid > 0, "invalid type_id")
        return self.type_info_table[typeid].fixedsize

    def q_varsize_item_sizes(self, typeid):
        ll_assert(typeid > 0, "invalid type_id")
        return self.type_info_table[typeid].varitemsize

    def q_varsize_offset_to_variable_part(self, typeid):
        ll_assert(typeid > 0, "invalid type_id")
        return self.type_info_table[typeid].ofstovar

    def q_varsize_offset_to_length(self, typeid):
        ll_assert(typeid > 0, "invalid type_id")
        return self.type_info_table[typeid].ofstolength

    def q_varsize_offsets_to_gcpointers_in_var_part(self, typeid):
        ll_assert(typeid > 0, "invalid type_id")
        return self.type_info_table[typeid].varofstoptrs

    def q_weakpointer_offset(self, typeid):
        ll_assert(typeid > 0, "invalid type_id")
        return self.type_info_table[typeid].weakptrofs

    def set_query_functions(self, gc):
        gc.set_query_functions(
            self.q_is_varsize,
            self.q_has_gcptr_in_varsize,
            self.q_is_gcarrayofgcptr,
            self.q_finalizer,
            self.q_offsets_to_gc_pointers,
            self.q_fixed_size,
            self.q_varsize_item_sizes,
            self.q_varsize_offset_to_variable_part,
            self.q_varsize_offset_to_length,
            self.q_varsize_offsets_to_gcpointers_in_var_part,
            self.q_weakpointer_offset)

# For the q_xxx functions that return flags, we use bit patterns
# in the typeid instead of entries in the type_info_table.  The
# following flag combinations are used (the idea being that it's
# very fast on CPUs to check if all flags in a set are all zero):

#   * if T_IS_FIXSIZE is set, the gc object is not var-sized
#   * if T_IS_FIXSIZE and T_NO_GCPTR_IN_VARSIZE are both cleared,
#           there are gc ptrs in the var-sized part
#   * if T_IS_FIXSIZE, T_NO_GCPTR_IN_VARSIZE and T_NOT_SIMPLE_GCARRAY
#           are all cleared, the shape is just like GcArray(gcptr)

T_IS_FIXSIZE          = 0x4
T_NO_GCPTR_IN_VARSIZE = 0x2
T_NOT_SIMPLE_GCARRAY  = 0x1

def get_typeid_bitmask(TYPE):
    """Return the bits that we would like to be set or cleared in the type_id
    corresponding to TYPE.  This returns (mask, expected_value), where
    the condition is that 'type_id & mask == expected_value'.
    """
    if not TYPE._is_varsize():
        return (T_IS_FIXSIZE, T_IS_FIXSIZE)     # not var-sized

    if (isinstance(TYPE, lltype.GcArray)
        and isinstance(TYPE.OF, lltype.Ptr)
        and TYPE.OF.TO._gckind == 'gc'):
        # a simple GcArray(gcptr)
        return (T_IS_FIXSIZE|T_NO_GCPTR_IN_VARSIZE|T_NOT_SIMPLE_GCARRAY, 0)

    if isinstance(TYPE, lltype.Struct):
        ARRAY = TYPE._flds[TYPE._arrayfld]
    else:
        ARRAY = TYPE
    assert isinstance(ARRAY, lltype.Array)
    if ARRAY.OF != lltype.Void and len(offsets_to_gc_pointers(ARRAY.OF)) > 0:
        # var-sized, with gc pointers in the variable part
        return (T_IS_FIXSIZE|T_NO_GCPTR_IN_VARSIZE|T_NOT_SIMPLE_GCARRAY,
                T_NOT_SIMPLE_GCARRAY)
    else:
        # var-sized, but no gc pointer in the variable part
        return (T_IS_FIXSIZE|T_NO_GCPTR_IN_VARSIZE, T_NO_GCPTR_IN_VARSIZE)


def encode_type_shape(builder, info, TYPE):
    """Encode the shape of the TYPE into the TYPE_INFO structure 'info'."""
    offsets = offsets_to_gc_pointers(TYPE)
    info.ofstoptrs = builder.offsets2table(offsets, TYPE)
    info.finalizer = builder.make_finalizer_funcptr_for_type(TYPE)
    info.weakptrofs = weakpointer_offset(TYPE)
    if not TYPE._is_varsize():
        #info.isvarsize = False
        #info.gcptrinvarsize = False
        info.fixedsize = llarena.round_up_for_allocation(
            llmemory.sizeof(TYPE))
        info.ofstolength = -1
        # note about round_up_for_allocation(): in the 'info' table
        # we put a rounded-up size only for fixed-size objects.  For
        # varsize ones, the GC must anyway compute the size at run-time
        # and round up that result.
    else:
        #info.isvarsize = True
        info.fixedsize = llmemory.sizeof(TYPE, 0)
        if isinstance(TYPE, lltype.Struct):
            ARRAY = TYPE._flds[TYPE._arrayfld]
            ofs1 = llmemory.offsetof(TYPE, TYPE._arrayfld)
            info.ofstolength = ofs1 + llmemory.ArrayLengthOffset(ARRAY)
            info.ofstovar = ofs1 + llmemory.itemoffsetof(ARRAY, 0)
        else:
            ARRAY = TYPE
            info.ofstolength = llmemory.ArrayLengthOffset(ARRAY)
            info.ofstovar = llmemory.itemoffsetof(TYPE, 0)
        assert isinstance(ARRAY, lltype.Array)
        if ARRAY.OF != lltype.Void:
            offsets = offsets_to_gc_pointers(ARRAY.OF)
        else:
            offsets = ()
        info.varofstoptrs = builder.offsets2table(offsets, ARRAY.OF)
        info.varitemsize = llmemory.sizeof(ARRAY.OF)
        #info.gcptrinvarsize = len(offsets) > 0
    #info.gcarrayofgcptr = (isinstance(TYPE, lltype.GcArray)
    #                       and isinstance(TYPE.OF, lltype.Ptr)
    #                       and TYPE.OF.TO._gckind == 'gc')

# ____________________________________________________________


class TypeLayoutBuilder(object):
    can_add_new_types = True

    def __init__(self):
        self.type_info_list = [None]   # don't use typeid 0, helps debugging
        self.id_of_type = {}      # {LLTYPE: type_id}
        self.seen_roots = {}
        # the following are lists of addresses of gc pointers living inside the
        # prebuilt structures.  It should list all the locations that could
        # possibly point to a GC heap object.
        # this lists contains pointers in GcStructs and GcArrays
        self.addresses_of_static_ptrs = []
        # this lists contains pointers in raw Structs and Arrays
        self.addresses_of_static_ptrs_in_nongc = []
        # for debugging, the following list collects all the prebuilt
        # GcStructs and GcArrays
        self.all_prebuilt_gc = []
        self.finalizer_funcptrs = {}
        self.offsettable_cache = {}
        self.next_typeid_cache = {}

    def get_type_id(self, TYPE):
        try:
            return self.id_of_type[TYPE]
        except KeyError:
            assert self.can_add_new_types
            assert isinstance(TYPE, (lltype.GcStruct, lltype.GcArray))
            # Record the new type_id description as a TYPE_INFO structure.
            # It goes into a list for now, which will be turned into a
            # TYPE_INFO_TABLE in flatten_table() by the gc transformer.

            # pick the next type_id with the correct bits set or cleared
            mask, expected = get_typeid_bitmask(TYPE)
            type_id = self.next_typeid_cache.get((mask, expected), 1)
            while True:
                if type_id == len(self.type_info_list):
                    self.type_info_list.append(None)
                if (self.type_info_list[type_id] is None and
                    (type_id & mask) == expected):
                    break         # can use this type_id
                else:
                    type_id += 1  # continue searching
            self.next_typeid_cache[mask, expected] = type_id + 1
            assert type_id & 0xffff == type_id # make sure it fits into 2 bytes

            # build the TYPE_INFO structure
            info = lltype.malloc(GCData.TYPE_INFO, immortal=True, zero=True)
            encode_type_shape(self, info, TYPE)
            self.type_info_list[type_id] = info
            self.id_of_type[TYPE] = type_id
            return type_id

    def offsets2table(self, offsets, TYPE):
        if len(offsets) == 0:
            TYPE = lltype.Void    # we can share all zero-length arrays
        try:
            return self.offsettable_cache[TYPE]
        except KeyError:
            cachedarray = lltype.malloc(GCData.OFFSETS_TO_GC_PTR,
                                        len(offsets), immortal=True)
            for i, value in enumerate(offsets):
                cachedarray[i] = value
            self.offsettable_cache[TYPE] = cachedarray
            return cachedarray

    def flatten_table(self):
        self.can_add_new_types = False
        self.offsettable_cache = None
        table = lltype.malloc(GCData.TYPE_INFO_TABLE, len(self.type_info_list),
                              immortal=True)
        fieldnames = GCData.TYPE_INFO._names
        for tableentry, newcontent in zip(table, self.type_info_list):
            if newcontent is None:    # empty entry
                tableentry.weakptrofs = -1
                tableentry.ofstolength = -1
            else:
                for name in fieldnames:
                    setattr(tableentry, name, getattr(newcontent, name))
        return table

    def finalizer_funcptr_for_type(self, TYPE):
        if TYPE in self.finalizer_funcptrs:
            return self.finalizer_funcptrs[TYPE]
        fptr = self.make_finalizer_funcptr_for_type(TYPE)
        self.finalizer_funcptrs[TYPE] = fptr
        return fptr

    def make_finalizer_funcptr_for_type(self, TYPE):
        # must be overridden for proper finalizer support
        return lltype.nullptr(GCData.ADDRESS_VOID_FUNC)

    def initialize_gc_query_function(self, gc):
        return GCData(self.type_info_list).set_query_functions(gc)

    def consider_constant(self, TYPE, value, gc):
        if value is not lltype.top_container(value):
            return
        if id(value) in self.seen_roots:
            return
        self.seen_roots[id(value)] = True

        if isinstance(TYPE, (lltype.GcStruct, lltype.GcArray)):
            typeid = self.get_type_id(TYPE)
            hdr = gc.gcheaderbuilder.new_header(value)
            adr = llmemory.cast_ptr_to_adr(hdr)
            gc.init_gc_object_immortal(adr, typeid)
            self.all_prebuilt_gc.append(value)

        # The following collects the addresses of all the fields that have
        # a GC Pointer type, inside the current prebuilt object.  All such
        # fields are potential roots: unless the structure is immutable,
        # they could be changed later to point to GC heap objects.
        adr = llmemory.cast_ptr_to_adr(value._as_ptr())
        if TYPE._gckind == "gc":
            if gc.prebuilt_gc_objects_are_static_roots or gc.DEBUG:
                appendto = self.addresses_of_static_ptrs
            else:
                return
        else:
            appendto = self.addresses_of_static_ptrs_in_nongc
        for a in gc_pointers_inside(value, adr, mutable_only=True):
            appendto.append(a)

# ____________________________________________________________
#
# Helpers to discover GC pointers inside structures

def offsets_to_gc_pointers(TYPE):
    offsets = []
    if isinstance(TYPE, lltype.Struct):
        for name in TYPE._names:
            FIELD = getattr(TYPE, name)
            if isinstance(FIELD, lltype.Array):
                continue    # skip inlined array
            baseofs = llmemory.offsetof(TYPE, name)
            suboffsets = offsets_to_gc_pointers(FIELD)
            for s in suboffsets:
                try:
                    knownzero = s == 0
                except TypeError:
                    knownzero = False
                if knownzero:
                    offsets.append(baseofs)
                else:
                    offsets.append(baseofs + s)
        # sanity check
        #ex = lltype.Ptr(TYPE)._example()
        #adr = llmemory.cast_ptr_to_adr(ex)
        #for off in offsets:
        #    (adr + off)
    elif isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc':
        offsets.append(0)
    return offsets

def weakpointer_offset(TYPE):
    if TYPE == WEAKREF:
        return llmemory.offsetof(WEAKREF, "weakptr")
    return -1

def gc_pointers_inside(v, adr, mutable_only=False):
    t = lltype.typeOf(v)
    if isinstance(t, lltype.Struct):
        if mutable_only and t._hints.get('immutable'):
            return
        for n, t2 in t._flds.iteritems():
            if isinstance(t2, lltype.Ptr) and t2.TO._gckind == 'gc':
                yield adr + llmemory.offsetof(t, n)
            elif isinstance(t2, (lltype.Array, lltype.Struct)):
                for a in gc_pointers_inside(getattr(v, n),
                                            adr + llmemory.offsetof(t, n),
                                            mutable_only):
                    yield a
    elif isinstance(t, lltype.Array):
        if mutable_only and t._hints.get('immutable'):
            return
        if isinstance(t.OF, lltype.Ptr) and t.OF.TO._gckind == 'gc':
            for i in range(len(v.items)):
                yield adr + llmemory.itemoffsetof(t, i)
        elif isinstance(t.OF, lltype.Struct):
            for i in range(len(v.items)):
                for a in gc_pointers_inside(v.items[i],
                                            adr + llmemory.itemoffsetof(t, i),
                                            mutable_only):
                    yield a

def zero_gc_pointers(p):
    TYPE = lltype.typeOf(p).TO
    zero_gc_pointers_inside(p, TYPE)

def zero_gc_pointers_inside(p, TYPE):
    if isinstance(TYPE, lltype.Struct):
        for name, FIELD in TYPE._flds.items():
            if isinstance(FIELD, lltype.Ptr) and FIELD.TO._gckind == 'gc':
                setattr(p, name, lltype.nullptr(FIELD.TO))
            elif isinstance(FIELD, lltype.ContainerType):
                zero_gc_pointers_inside(getattr(p, name), FIELD)
    elif isinstance(TYPE, lltype.Array):
        ITEM = TYPE.OF
        if isinstance(ITEM, lltype.Ptr) and ITEM.TO._gckind == 'gc':
            null = lltype.nullptr(ITEM.TO)
            for i in range(p._obj.getlength()):
                p[i] = null
        elif isinstance(ITEM, lltype.ContainerType):
            for i in range(p._obj.getlength()):
                zero_gc_pointers_inside(p[i], ITEM)

########## weakrefs ##########
# framework: weakref objects are small structures containing only an address

WEAKREF = lltype.GcStruct("weakref", ("weakptr", llmemory.Address))
WEAKREFPTR = lltype.Ptr(WEAKREF)
sizeof_weakref= llmemory.sizeof(WEAKREF)
empty_weakref = lltype.malloc(WEAKREF, immortal=True)
empty_weakref.weakptr = llmemory.NULL

def ll_weakref_deref(wref):
    wref = llmemory.cast_weakrefptr_to_ptr(WEAKREFPTR, wref)
    return wref.weakptr

def convert_weakref_to(targetptr):
    # Prebuilt weakrefs don't really need to be weak at all,
    # but we need to emulate the structure expected by ll_weakref_deref().
    if not targetptr:
        return empty_weakref
    else:
        link = lltype.malloc(WEAKREF, immortal=True)
        link.weakptr = llmemory.cast_ptr_to_adr(targetptr)
        return link
