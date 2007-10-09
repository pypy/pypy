from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rpython.memory.gctransform.support import find_gc_ptrs_in_type


class TypeLayoutBuilder(object):
    can_add_new_types = True

    def __init__(self):
        dummy = {"weakptrofs": -1,
                 "ofstolength": -1}
        self.type_info_list = [dummy]   # don't use typeid 0, helps debugging
        self.id_of_type = {}      # {LLTYPE: type_id}
        self.seen_roots = {}
        self.static_gc_roots = []
        self.addresses_of_static_ptrs_in_nongc = []
        self.finalizer_funcptrs = {}

    def get_type_id(self, TYPE):
        try:
            return self.id_of_type[TYPE]
        except KeyError:
            assert self.can_add_new_types
            assert isinstance(TYPE, (lltype.GcStruct, lltype.GcArray))
            # Record the new type_id description as a small dict for now.
            # It will be turned into a Struct("type_info") in finish()
            type_id = len(self.type_info_list)
            info = {}
            self.type_info_list.append(info)
            self.id_of_type[TYPE] = type_id
            offsets = offsets_to_gc_pointers(TYPE)
            info["ofstoptrs"] = self.offsets2table(offsets, TYPE)
            info["finalyzer"] = self.make_finalizer_funcptr_for_type(TYPE)
            info["weakptrofs"] = weakpointer_offset(TYPE)
            if not TYPE._is_varsize():
                info["isvarsize"] = False
                info["fixedsize"] = llarena.round_up_for_allocation(
                    llmemory.sizeof(TYPE))
                info["ofstolength"] = -1
                # note about round_up_for_allocation(): in the 'info' table
                # we put a rounded-up size only for fixed-size objects.  For
                # varsize ones, the GC must anyway compute the size at run-time
                # and round up that result.
            else:
                info["isvarsize"] = True
                info["fixedsize"] = llmemory.sizeof(TYPE, 0)
                if isinstance(TYPE, lltype.Struct):
                    ARRAY = TYPE._flds[TYPE._arrayfld]
                    ofs1 = llmemory.offsetof(TYPE, TYPE._arrayfld)
                    info["ofstolength"] = ofs1 + llmemory.ArrayLengthOffset(ARRAY)
                    if ARRAY.OF != lltype.Void:
                        info["ofstovar"] = ofs1 + llmemory.itemoffsetof(ARRAY, 0)
                    else:
                        info["fixedsize"] = ofs1 + llmemory.sizeof(lltype.Signed)
                    if ARRAY._hints.get('isrpystring'):
                        info["fixedsize"] = llmemory.sizeof(TYPE, 1)
                else:
                    ARRAY = TYPE
                    info["ofstolength"] = llmemory.ArrayLengthOffset(ARRAY)
                    if ARRAY.OF != lltype.Void:
                        info["ofstovar"] = llmemory.itemoffsetof(TYPE, 0)
                    else:
                        info["fixedsize"] = llmemory.ArrayLengthOffset(ARRAY) + llmemory.sizeof(lltype.Signed)
                assert isinstance(ARRAY, lltype.Array)
                if ARRAY.OF != lltype.Void:
                    offsets = offsets_to_gc_pointers(ARRAY.OF)
                    info["varofstoptrs"] = self.offsets2table(offsets, ARRAY.OF)
                    info["varitemsize"] = llmemory.sizeof(ARRAY.OF)
                else:
                    info["varofstoptrs"] = self.offsets2table((), lltype.Void)
                    info["varitemsize"] = llmemory.sizeof(ARRAY.OF)
            return type_id

    def offsets2table(self, offsets, TYPE):
        return offsets

    def finalizer_funcptr_for_type(self, TYPE):
        if TYPE in self.finalizer_funcptrs:
            return self.finalizer_funcptrs[TYPE]
        fptr = self.make_finalizer_funcptr_for_type(TYPE)
        self.finalizer_funcptrs[TYPE] = fptr
        return fptr

    def make_finalizer_funcptr_for_type(self, TYPE):
        return None   # must be overridden for proper finalizer support

    def q_is_varsize(self, typeid):
        assert typeid > 0
        return self.type_info_list[typeid]["isvarsize"]

    def q_finalyzer(self, typeid):
        assert typeid > 0
        return self.type_info_list[typeid]["finalyzer"]

    def q_offsets_to_gc_pointers(self, typeid):
        assert typeid > 0
        return self.type_info_list[typeid]["ofstoptrs"]

    def q_fixed_size(self, typeid):
        assert typeid > 0
        return self.type_info_list[typeid]["fixedsize"]

    def q_varsize_item_sizes(self, typeid):
        assert typeid > 0
        return self.type_info_list[typeid]["varitemsize"]

    def q_varsize_offset_to_variable_part(self, typeid):
        assert typeid > 0
        return self.type_info_list[typeid]["ofstovar"]

    def q_varsize_offset_to_length(self, typeid):
        assert typeid > 0
        return self.type_info_list[typeid]["ofstolength"]

    def q_varsize_offsets_to_gcpointers_in_var_part(self, typeid):
        assert typeid > 0
        return self.type_info_list[typeid]["varofstoptrs"]

    def q_weakpointer_offset(self, typeid):
        assert typeid > 0
        return self.type_info_list[typeid]["weakptrofs"]

    def get_query_functions(self):
        return (self.q_is_varsize,
                self.q_finalyzer,
                self.q_offsets_to_gc_pointers,
                self.q_fixed_size,
                self.q_varsize_item_sizes,
                self.q_varsize_offset_to_variable_part,
                self.q_varsize_offset_to_length,
                self.q_varsize_offsets_to_gcpointers_in_var_part,
                self.q_weakpointer_offset)

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

        if find_gc_ptrs_in_type(TYPE):
            adr = llmemory.cast_ptr_to_adr(value._as_ptr())
            if isinstance(TYPE, (lltype.GcStruct, lltype.GcArray)):
                self.static_gc_roots.append(adr)
            else:
                for a in gc_pointers_inside(value, adr):
                    self.addresses_of_static_ptrs_in_nongc.append(a)

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

def gc_pointers_inside(v, adr):
    t = lltype.typeOf(v)
    if isinstance(t, lltype.Struct):
        for n, t2 in t._flds.iteritems():
            if isinstance(t2, lltype.Ptr) and t2.TO._gckind == 'gc':
                yield adr + llmemory.offsetof(t, n)
            elif isinstance(t2, (lltype.Array, lltype.Struct)):
                for a in gc_pointers_inside(getattr(v, n), adr + llmemory.offsetof(t, n)):
                    yield a
    elif isinstance(t, lltype.Array):
        if isinstance(t.OF, lltype.Ptr) and t2._needsgc():
            for i in range(len(v.items)):
                yield adr + llmemory.itemoffsetof(t, i)
        elif isinstance(t.OF, lltype.Struct):
            for i in range(len(v.items)):
                for a in gc_pointers_inside(v.items[i], adr + llmemory.itemoffsetof(t, i)):
                    yield a

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
