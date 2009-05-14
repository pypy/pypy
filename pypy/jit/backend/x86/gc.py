from pypy.rlib import rgc
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.jit.backend.x86 import symbolic
from pypy.jit.backend.x86.runner import ConstDescr3
from pypy.jit.backend.x86.ri386 import MODRM

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
        basesize = arraydescr.v0
        itemsize = arraydescr.v1
        size = basesize + itemsize * num_elem
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


class GcRootMap_asmgcc:
    """Handles locating the stack roots in the assembler.
    This is the class supporting --gcrootfinder=asmgcc.
    """
    LOC_NOWHERE   = 0
    LOC_REG       = 1
    LOC_EBP_BASED = 2
    LOC_ESP_BASED = 3

    GCMAP_ARRAY = rffi.CArray(llmemory.Address)
    CALLSHAPE_ARRAY = rffi.CArray(rffi.UCHAR)

    def __init__(self):
        self._gcmap = lltype.malloc(self.GCMAP_ARRAY, 0, flavor='raw')
        self._gcmap_curlength = 0
        self._gcmap_maxlength = 0

    def gcmapstart(self):
        return llmemory.cast_ptr_to_adr(self._gcmap)

    def gcmapend(self):
        start = self.gcmapstart()
        return start + llmemory.sizeof(lltype.Signed) * self._gcmap_curlength

    def put(self, retaddr, callshapeaddr):
        """'retaddr' is the address just after the CALL.
        'callshapeaddr' is the address returned by encode_callshape()."""
        index = self._gcmap_curlength
        if index + 2 > self._gcmap_maxlength:
            self._enlarge_gcmap()
        self._gcmap[index] = retaddr
        self._gcmap[index+1] = callshapeaddr
        self._gcmap_curlength = index + 2

    def _enlarge_gcmap(self):
        newlength = 128 + self._gcmap_maxlength // 4
        newgcmap = lltype.malloc(self.GCMAP_ARRAY, newlength, flavor='raw')
        oldgcmap = self._gcmap
        for i in range(self._gcmap_curlength):
            newgcmap[i] = oldgcmap[i]
        self._gcmap = newgcmap
        self._gcmap_maxlength = newlength
        lltype.free(oldgcmap, flavor='raw')

    def encode_callshape(self, gclocs, framesize):
        """Encode a callshape from the list of locations containing GC
        pointers and from the frame size of the current (caller) frame.
        The framesize gives the offset from %esp to the return address
        of the current frame."""
        shape = self._get_callshape(gclocs, framesize)
        return self._compress_callshape(shape)

    def _get_callshape(self, gclocs, framesize):
        # the four registers %ebx, %esi, %edi, %ebp are not used at all
        # so far, so their value always comes from the caller.
        shape = [self.LOC_ESP_BASED | framesize,
                 self.LOC_REG | 0,
                 self.LOC_REG | 4,
                 self.LOC_REG | 8,
                 self.LOC_REG | 12,
                 0]
        for loc in gclocs:
            assert isinstance(loc, MODRM)
            shape.append(self.LOC_ESP_BASED | (4 * loc.position))
        return shape

    def _compress_callshape(self, shape):
        # Similar to compress_callshape() in trackgcroot.py.  XXX a bit slowish
        result = []
        for loc in shape:
            assert loc >= 0
            loc = loc * 2
            flag = 0
            while loc >= 0x80:
                result.append(int(loc & 0x7F) | flag)
                flag = 0x80
                loc >>= 7
            result.append(int(loc) | flag)
        # XXX so far, we always allocate a new small array (we could regroup
        # them inside bigger arrays) and we never try to share them.
        length = len(result)
        compressed = lltype.malloc(self.CALLSHAPE_ARRAY, length,
                                   flavor='raw')
        for i in range(length):
            compressed[length-1-i] = rffi.cast(rffi.UCHAR, result[i])
        return llmemory.cast_ptr_to_adr(compressed)


class GcLLDescr_framework(GcLLDescription):
    GcRefList = GcRefList

    def __init__(self, gcdescr, mixlevelann):
        from pypy.rpython.memory.gc.base import choose_gc_from_config
        from pypy.rpython.memory.gctransform import framework
        self.translator = mixlevelann.rtyper.annotator.translator

        # to find roots in the assembler, make a GcRootMap
        name = gcdescr.config.translation.gcrootfinder
        try:
            cls = globals()['GcRootMap_' + name]
        except KeyError:
            raise NotImplementedError("--gcrootfinder=%s not implemented"
                                      " with the JIT" % (name,))
        self.gcrootmap = cls()

        # make a TransformerLayoutBuilder and save it on the translator
        # where it can be fished and reused by the FrameworkGCTransformer
        self.layoutbuilder = framework.TransformerLayoutBuilder()
        self.translator._jit2gc = {
            'layoutbuilder': self.layoutbuilder,
            'gcmapstart': self.gcrootmap.gcmapstart,
            'gcmapend': self.gcrootmap.gcmapend,
            }
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
