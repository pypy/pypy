from pypy.rlib import rgc
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.jit.backend.x86 import symbolic
from pypy.jit.backend.x86.runner import ConstDescr3

# ____________________________________________________________

class GcLLDescription:
    def __init__(self, gcdescr, mixlevelann):
        self.gcdescr = gcdescr
    def _freeze_(self):
        return True

# ____________________________________________________________

class GcLLDescr_boehm(GcLLDescription):
    moving_gc = False

    def __init__(self, gcdescr, mixlevelann):
        # grab a pointer to the Boehm 'malloc' function
        compilation_info = ExternalCompilationInfo(libraries=['gc'])
        malloc_fn_ptr = rffi.llexternal("GC_malloc",
                                        [lltype.Signed], # size_t, but good enough
                                        llmemory.GCREF,
                                        compilation_info=compilation_info,
                                        sandboxsafe=True,
                                        _nowrapper=True)
        self.funcptr_for_new = malloc_fn_ptr

    def sizeof(self, S, translate_support_code):
        size = symbolic.get_size(S, translate_support_code)
        return ConstDescr3(size, 0, False)

    def gc_malloc(self, descrsize):
        assert isinstance(descrsize, ConstDescr3)
        size = descrsize.v0
        return self.funcptr_for_new(size)

    def gc_malloc_array(self, arraydescr, num_elem):
        assert isinstance(arraydescr, ConstDescr3)
        size_of_field = arraydescr.v0
        ofs = arraydescr.v1
        size = ofs + (1 << size_of_field) * num_elem
        return self.funcptr_for_new(size)

    def args_for_new(self, descrsize):
        assert isinstance(descrsize, ConstDescr3)
        size = descrsize.v0
        return [size]

    def get_funcptr_for_new(self):
        return self.funcptr_for_new

# ____________________________________________________________

class GcRefList:
    """Handles all references from the generated assembler to GC objects.
    This is implemented as a nonmovable, but GC, list; the assembler contains
    code that will (for now) always read from this list."""

    GCREF_LIST = lltype.GcArray(llmemory.GCREF)     # followed by the GC

    HASHTABLE = rffi.CArray(llmemory.Address)      # ignored by the GC
    HASHTABLE_BITS = 10
    HASHTABLE_SIZE = 1 << HASHTABLE_BITS

    def __init__(self):
        self.list = self.alloc_gcref_list(2000)
        self.nextindex = 0
        self.oldlists = []
        # A pseudo dictionary: it is fixed size, and it may contain
        # random nonsense after a collection moved the objects.  It is only
        # used to avoid too many duplications in the GCREF_LISTs.
        self.hashtable = lltype.malloc(self.HASHTABLE,
                                       self.HASHTABLE_SIZE+1,
                                       flavor='raw')
        dummy = lltype.direct_ptradd(lltype.direct_arrayitems(self.hashtable),
                                     self.HASHTABLE_SIZE)
        dummy = llmemory.cast_ptr_to_adr(dummy)
        for i in range(self.HASHTABLE_SIZE+1):
            self.hashtable[i] = dummy

    def alloc_gcref_list(self, n):
        # Important: the GRREF_LISTs allocated are *non-movable*.  This
        # requires support in the gc (only the hybrid GC supports it so far).
        list = rgc.malloc_nonmovable(self.GCREF_LIST, n)
        assert list, "malloc_nonmovable failed!"
        return list

    def get_address_of_gcref(self, gcref):
        assert lltype.typeOf(gcref) == llmemory.GCREF
        # first look in the hashtable, using an inexact hash (fails after
        # the object moves)
        addr = llmemory.cast_ptr_to_adr(gcref)
        hash = llmemory.cast_adr_to_int(addr)
        hash -= hash >> self.HASHTABLE_BITS
        hash &= self.HASHTABLE_SIZE - 1
        addr_ref = self.hashtable[hash]
        # the following test is safe anyway, because the addresses found
        # in the hashtable are always the addresses of nonmovable stuff:
        if addr_ref.address[0] == addr:
            return addr_ref
        # if it fails, add an entry to the list
        if self.nextindex == len(self.list):
            # reallocate first, increasing a bit the size every time
            self.oldlists.append(self.list)
            self.list = self.alloc_gcref_list(len(self.list) // 4 * 5)
            self.nextindex = 0
        # add it
        index = self.nextindex
        self.list[index] = gcref
        addr_ref = lltype.direct_ptradd(lltype.direct_arrayitems(self.list),
                                        index)
        addr_ref = llmemory.cast_ptr_to_adr(addr_ref)
        self.nextindex = index + 1
        # record it in the hashtable
        self.hashtable[hash] = addr_ref
        return addr_ref


class GcLLDescr_framework(GcLLDescription):
    GcRefList = GcRefList

    def __init__(self, gcdescr, mixlevelann):
        from pypy.rpython.memory.gc.base import choose_gc_from_config
        from pypy.rpython.memory.gctransform import framework
        self.translator = mixlevelann.rtyper.annotator.translator

        # make a TransformerLayoutBuilder and save it on the translator
        # where it can be fished and reused by the FrameworkGCTransformer
        self.layoutbuilder = framework.TransformerLayoutBuilder()
        self.translator._transformerlayoutbuilder_from_jit = self.layoutbuilder
        GCClass, _ = choose_gc_from_config(gcdescr.config)
        self.moving_gc = GCClass.moving_gc

        # make a malloc function, with three arguments
        def malloc_basic(size, type_id, has_finalizer):
            return llop.do_malloc_fixedsize_clear(llmemory.GCREF,
                                                  type_id, size, True,
                                                  has_finalizer, False)
        self.malloc_basic = malloc_basic
        self.GC_MALLOC_BASIC = lltype.Ptr(lltype.FuncType(
            [lltype.Signed, lltype.Signed, lltype.Bool], llmemory.GCREF))

        assert gcdescr.config.translation.gcrootfinder == "asmgcc", (
            "with the framework GCs, you must use"
            " --gcrootfinder=asmgcc for now")

    def sizeof(self, S, translate_support_code):
        from pypy.rpython.memory.gctypelayout import weakpointer_offset
        assert translate_support_code, "required with the framework GC"
        size = symbolic.get_size(S, True)
        type_id = self.layoutbuilder.get_type_id(S)
        has_finalizer = bool(self.layoutbuilder.has_finalizer(S))
        assert weakpointer_offset(S) == -1     # XXX
        return ConstDescr3(size, type_id, has_finalizer)

    def gc_malloc(self, descrsize):
        assert isinstance(descrsize, ConstDescr3)
        size = descrsize.v0
        type_id = descrsize.v1
        has_finalizer = descrsize.flag2
        assert type_id > 0
        return self.malloc_basic(size, type_id, has_finalizer)

    def gc_malloc_array(self, arraydescr, num_elem):
        raise NotImplementedError

    def args_for_new(self, descrsize):
        assert isinstance(descrsize, ConstDescr3)
        size = descrsize.v0
        type_id = descrsize.v1
        has_finalizer = descrsize.flag2
        return [size, type_id, has_finalizer]

    def get_funcptr_for_new(self):
        return llhelper(self.GC_MALLOC_BASIC, self.malloc_basic)

# ____________________________________________________________

def get_ll_description(gcdescr, mixlevelann):
    if gcdescr is not None:
        name = gcdescr.config.translation.gctransformer
    else:
        name = "boehm"
    try:
        cls = globals()['GcLLDescr_' + name]
    except KeyError:
        raise NotImplementedError("GC transformer %r not supported by "
                                  "the x86 backend" % (name,))
    return cls(gcdescr, mixlevelann)
