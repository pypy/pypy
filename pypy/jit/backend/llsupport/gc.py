from pypy.rlib import rgc
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.debug import fatalerror
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass, rstr
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.jit.metainterp.history import BoxInt, BoxPtr, ConstInt, ConstPtr
from pypy.jit.metainterp.history import AbstractDescr
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.llsupport.symbolic import WORD
from pypy.jit.backend.llsupport.descr import BaseSizeDescr, BaseArrayDescr
from pypy.jit.backend.llsupport.descr import GcCache, get_field_descr
from pypy.jit.backend.llsupport.descr import GcPtrFieldDescr
from pypy.jit.backend.llsupport.descr import get_call_descr
from pypy.rlib.rarithmetic import r_ulonglong, r_uint

# ____________________________________________________________

class GcLLDescription(GcCache):
    def __init__(self, gcdescr, translator=None):
        GcCache.__init__(self, translator is not None)
        self.gcdescr = gcdescr
    def _freeze_(self):
        return True
    def initialize(self):
        pass
    def do_write_barrier(self, gcref_struct, gcref_newptr):
        pass
    def rewrite_assembler(self, cpu, operations):
        pass
    def can_inline_malloc(self, descr):
        return False
    def has_write_barrier_class(self):
        return None

# ____________________________________________________________

class GcLLDescr_boehm(GcLLDescription):
    moving_gc = False
    gcrootmap = None

    def __init__(self, gcdescr, translator):
        GcLLDescription.__init__(self, gcdescr, translator)
        # grab a pointer to the Boehm 'malloc' function
        from pypy.rpython.tool import rffi_platform
        compilation_info = rffi_platform.configure_boehm()

        # Versions 6.x of libgc needs to use GC_local_malloc().
        # Versions 7.x of libgc removed this function; GC_malloc() has
        # the same behavior if libgc was compiled with
        # THREAD_LOCAL_ALLOC.
        class CConfig:
            _compilation_info_ = compilation_info
            HAS_LOCAL_MALLOC = rffi_platform.Has("GC_local_malloc")
        config = rffi_platform.configure(CConfig)
        if config['HAS_LOCAL_MALLOC']:
            GC_MALLOC = "GC_local_malloc"
        else:
            GC_MALLOC = "GC_malloc"

        malloc_fn_ptr = rffi.llexternal(GC_MALLOC,
                                        [lltype.Signed], # size_t, but good enough
                                        llmemory.GCREF,
                                        compilation_info=compilation_info,
                                        sandboxsafe=True,
                                        _nowrapper=True)
        self.funcptr_for_new = malloc_fn_ptr

        # on some platform GC_init is required before any other
        # GC_* functions, call it here for the benefit of tests
        # XXX move this to tests
        init_fn_ptr = rffi.llexternal("GC_init",
                                      [], lltype.Void,
                                      compilation_info=compilation_info,
                                      sandboxsafe=True,
                                      _nowrapper=True)

        init_fn_ptr()

    def gc_malloc(self, sizedescr):
        assert isinstance(sizedescr, BaseSizeDescr)
        return self.funcptr_for_new(sizedescr.size)

    def gc_malloc_array(self, arraydescr, num_elem):
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs_length = arraydescr.get_ofs_length(self.translate_support_code)
        basesize = arraydescr.get_base_size(self.translate_support_code)
        itemsize = arraydescr.get_item_size(self.translate_support_code)
        size = basesize + itemsize * num_elem
        res = self.funcptr_for_new(size)
        rffi.cast(rffi.CArrayPtr(lltype.Signed), res)[ofs_length/WORD] = num_elem
        return res

    def gc_malloc_str(self, num_elem):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                   self.translate_support_code)
        assert itemsize == 1
        size = basesize + num_elem
        res = self.funcptr_for_new(size)
        rffi.cast(rffi.CArrayPtr(lltype.Signed), res)[ofs_length/WORD] = num_elem
        return res

    def gc_malloc_unicode(self, num_elem):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                                   self.translate_support_code)
        size = basesize + num_elem * itemsize
        res = self.funcptr_for_new(size)
        rffi.cast(rffi.CArrayPtr(lltype.Signed), res)[ofs_length/WORD] = num_elem
        return res

    def args_for_new(self, sizedescr):
        assert isinstance(sizedescr, BaseSizeDescr)
        return [sizedescr.size]

    def get_funcptr_for_new(self):
        return self.funcptr_for_new

    get_funcptr_for_newarray = None
    get_funcptr_for_newstr = None
    get_funcptr_for_newunicode = None


# ____________________________________________________________
# All code below is for the hybrid GC


class GcRefList:
    """Handles all references from the generated assembler to GC objects.
    This is implemented as a nonmovable, but GC, list; the assembler contains
    code that will (for now) always read from this list."""

    GCREF_LIST = lltype.GcArray(llmemory.GCREF)     # followed by the GC

    HASHTABLE = rffi.CArray(llmemory.Address)      # ignored by the GC
    HASHTABLE_BITS = 10
    HASHTABLE_SIZE = 1 << HASHTABLE_BITS

    def initialize(self):
        if we_are_translated(): n = 2000
        else:                   n = 10    # tests only
        self.list = self.alloc_gcref_list(n)
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
        if we_are_translated():
            list = rgc.malloc_nonmovable(self.GCREF_LIST, n)
            assert list, "malloc_nonmovable failed!"
        else:
            list = lltype.malloc(self.GCREF_LIST, n)     # for tests only
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
        # in the hashtable are always the addresses of nonmovable stuff
        # ('addr_ref' is an address inside self.list, not directly the
        # address of a real moving GC object -- that's 'addr_ref.address[0]'.)
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
        self._gcmap = lltype.nullptr(self.GCMAP_ARRAY)
        self._gcmap_curlength = 0
        self._gcmap_maxlength = 0

    def initialize(self):
        # hack hack hack.  Remove these lines and see MissingRTypeAttribute
        # when the rtyper tries to annotate these methods only when GC-ing...
        self.gcmapstart()
        self.gcmapend()

    def gcmapstart(self):
        return llmemory.cast_ptr_to_adr(self._gcmap)

    def gcmapend(self):
        addr = self.gcmapstart()
        if self._gcmap_curlength:
            addr += llmemory.sizeof(llmemory.Address)*self._gcmap_curlength
        return addr

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
        newlength = 250 + self._gcmap_maxlength * 2
        newgcmap = lltype.malloc(self.GCMAP_ARRAY, newlength, flavor='raw')
        oldgcmap = self._gcmap
        for i in range(self._gcmap_curlength):
            newgcmap[i] = oldgcmap[i]
        self._gcmap = newgcmap
        self._gcmap_maxlength = newlength
        if oldgcmap:
            lltype.free(oldgcmap, flavor='raw')

    def get_basic_shape(self):
        return [self.LOC_EBP_BASED | 4,     # return addr: at   4(%ebp)
                self.LOC_EBP_BASED | (-4),  # saved %ebx:  at  -4(%ebp)
                self.LOC_EBP_BASED | (-8),  # saved %esi:  at  -8(%ebp)
                self.LOC_EBP_BASED | (-12), # saved %edi:  at -12(%ebp)
                self.LOC_EBP_BASED | 0,     # saved %ebp:  at    (%ebp)
                0]

    def add_ebp_offset(self, shape, offset):
        assert (offset & 3) == 0
        shape.append(self.LOC_EBP_BASED | offset)

    def add_ebx(self, shape):
        shape.append(self.LOC_REG | 0)

    def add_esi(self, shape):
        shape.append(self.LOC_REG | 4)

    def add_edi(self, shape):
        shape.append(self.LOC_REG | 8)

    def add_ebp(self, shape):
        shape.append(self.LOC_REG | 12)

    def compress_callshape(self, shape):
        # Similar to compress_callshape() in trackgcroot.py.  XXX a bit slowish
        result = []
        for loc in shape:
            if loc < 0:
                loc = (-loc) * 2 - 1
            else:
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


class WriteBarrierDescr(AbstractDescr):
    def __init__(self, gc_ll_descr):
        self.llop1 = gc_ll_descr.llop1
        self.WB_FUNCPTR = gc_ll_descr.WB_FUNCPTR
        self.fielddescr_tid = get_field_descr(gc_ll_descr,
                                              gc_ll_descr.GCClass.HDR, 'tid')
        self.jit_wb_if_flag = gc_ll_descr.GCClass.JIT_WB_IF_FLAG
        # if convenient for the backend, we also compute the info about
        # the flag as (byte-offset, single-byte-flag).
        import struct
        value = struct.pack("i", self.jit_wb_if_flag)
        assert value.count('\x00') == len(value) - 1    # only one byte is != 0
        i = 0
        while value[i] == '\x00': i += 1
        self.jit_wb_if_flag_byteofs = i
        self.jit_wb_if_flag_singlebyte = struct.unpack('b', value[i])[0]

    def get_write_barrier_fn(self, cpu):
        llop1 = self.llop1
        funcptr = llop1.get_write_barrier_failing_case(self.WB_FUNCPTR)
        funcaddr = llmemory.cast_ptr_to_adr(funcptr)
        return cpu.cast_adr_to_int(funcaddr)


class GcLLDescr_framework(GcLLDescription):

    def __init__(self, gcdescr, translator, llop1=llop):
        from pypy.rpython.memory.gctypelayout import _check_typeid
        from pypy.rpython.memory.gcheader import GCHeaderBuilder
        from pypy.rpython.memory.gctransform import framework
        GcLLDescription.__init__(self, gcdescr, translator)
        assert self.translate_support_code, "required with the framework GC"
        self.translator = translator
        self.llop1 = llop1

        # we need the hybrid GC for GcRefList.alloc_gcref_list() to work
        if gcdescr.config.translation.gc != 'hybrid':
            raise NotImplementedError("--gc=%s not implemented with the JIT" %
                                      (gcdescr.config.translation.gc,))

        # to find roots in the assembler, make a GcRootMap
        name = gcdescr.config.translation.gcrootfinder
        try:
            cls = globals()['GcRootMap_' + name]
        except KeyError:
            raise NotImplementedError("--gcrootfinder=%s not implemented"
                                      " with the JIT" % (name,))
        gcrootmap = cls()
        self.gcrootmap = gcrootmap
        self.gcrefs = GcRefList()
        self.single_gcref_descr = GcPtrFieldDescr(0)

        # make a TransformerLayoutBuilder and save it on the translator
        # where it can be fished and reused by the FrameworkGCTransformer
        self.layoutbuilder = framework.TransformerLayoutBuilder(translator)
        self.layoutbuilder.delay_encoding()
        self.translator._jit2gc = {
            'layoutbuilder': self.layoutbuilder,
            'gcmapstart': lambda: gcrootmap.gcmapstart(),
            'gcmapend': lambda: gcrootmap.gcmapend(),
            }
        self.GCClass = self.layoutbuilder.GCClass
        self.moving_gc = self.GCClass.moving_gc
        self.HDRPTR = lltype.Ptr(self.GCClass.HDR)
        self.gcheaderbuilder = GCHeaderBuilder(self.HDRPTR.TO)
        (self.array_basesize, _, self.array_length_ofs) = \
             symbolic.get_array_token(lltype.GcArray(lltype.Signed), True)
        min_ns = self.GCClass.TRANSLATION_PARAMS['min_nursery_size']
        self.max_size_of_young_obj = self.GCClass.get_young_fixedsize(min_ns)

        # make a malloc function, with three arguments
        def malloc_basic(size, tid):
            type_id = llop.extract_ushort(rffi.USHORT, tid)
            has_finalizer = bool(tid & (1<<16))
            _check_typeid(type_id)
            try:
                res = llop1.do_malloc_fixedsize_clear(llmemory.GCREF,
                                                      type_id, size, True,
                                                      has_finalizer, False)
            except MemoryError:
                fatalerror("out of memory (from JITted code)")
                res = lltype.nullptr(llmemory.GCREF.TO)
            #llop.debug_print(lltype.Void, "\tmalloc_basic", size, type_id,
            #                 "-->", res)
            return res
        self.malloc_basic = malloc_basic
        self.GC_MALLOC_BASIC = lltype.Ptr(lltype.FuncType(
            [lltype.Signed, lltype.Signed], llmemory.GCREF))
        self.WB_FUNCPTR = lltype.Ptr(lltype.FuncType(
            [llmemory.Address, llmemory.Address], lltype.Void))
        self.write_barrier_descr = WriteBarrierDescr(self)
        #
        def malloc_array(itemsize, tid, num_elem):
            type_id = llop.extract_ushort(rffi.USHORT, tid)
            _check_typeid(type_id)
            try:
                return llop1.do_malloc_varsize_clear(
                    llmemory.GCREF,
                    type_id, num_elem, self.array_basesize, itemsize,
                    self.array_length_ofs, True)
            except MemoryError:
                fatalerror("out of memory (from JITted code)")
                return lltype.nullptr(llmemory.GCREF.TO)
        self.malloc_array = malloc_array
        self.GC_MALLOC_ARRAY = lltype.Ptr(lltype.FuncType(
            [lltype.Signed] * 3, llmemory.GCREF))
        #
        (str_basesize, str_itemsize, str_ofs_length
         ) = symbolic.get_array_token(rstr.STR, True)
        (unicode_basesize, unicode_itemsize, unicode_ofs_length
         ) = symbolic.get_array_token(rstr.UNICODE, True)
        str_type_id = self.layoutbuilder.get_type_id(rstr.STR)
        unicode_type_id = self.layoutbuilder.get_type_id(rstr.UNICODE)
        #
        def malloc_str(length):
            try:
                return llop1.do_malloc_varsize_clear(
                    llmemory.GCREF,
                    str_type_id, length, str_basesize, str_itemsize,
                    str_ofs_length, True)
            except MemoryError:
                fatalerror("out of memory (from JITted code)")
                return lltype.nullptr(llmemory.GCREF.TO)
        def malloc_unicode(length):
            try:
                return llop1.do_malloc_varsize_clear(
                    llmemory.GCREF,
                    unicode_type_id, length, unicode_basesize,unicode_itemsize,
                    unicode_ofs_length, True)
            except MemoryError:
                fatalerror("out of memory (from JITted code)")
                return lltype.nullptr(llmemory.GCREF.TO)
        self.malloc_str = malloc_str
        self.malloc_unicode = malloc_unicode
        self.GC_MALLOC_STR_UNICODE = lltype.Ptr(lltype.FuncType(
            [lltype.Signed], llmemory.GCREF))
        def malloc_fixedsize_slowpath(size):
            try:
                gcref = llop1.do_malloc_fixedsize_clear(llmemory.GCREF,
                                            0, size, True, False, False)
            except MemoryError:
                fatalerror("out of memory (from JITted code)")
                return r_ulonglong(0)
            res = rffi.cast(lltype.Signed, gcref)
            nurs_free = llop1.gc_adr_of_nursery_free(llmemory.Address).signed[0]
            return r_ulonglong(nurs_free) << 32 | r_ulonglong(r_uint(res))
        self.malloc_fixedsize_slowpath = malloc_fixedsize_slowpath
        self.MALLOC_FIXEDSIZE_SLOWPATH = lltype.FuncType([lltype.Signed],
                                                 lltype.UnsignedLongLong)

    def get_nursery_free_addr(self):
        nurs_addr = llop.gc_adr_of_nursery_free(llmemory.Address)
        return rffi.cast(lltype.Signed, nurs_addr)

    def get_nursery_top_addr(self):
        nurs_top_addr = llop.gc_adr_of_nursery_top(llmemory.Address)
        return rffi.cast(lltype.Signed, nurs_top_addr)

    def get_malloc_fixedsize_slowpath_addr(self):
        fptr = llhelper(lltype.Ptr(self.MALLOC_FIXEDSIZE_SLOWPATH),
                        self.malloc_fixedsize_slowpath)
        return rffi.cast(lltype.Signed, fptr)

    def initialize(self):
        self.gcrefs.initialize()
        self.gcrootmap.initialize()

    def init_size_descr(self, S, descr):
        type_id = self.layoutbuilder.get_type_id(S)
        assert not self.layoutbuilder.is_weakref(type_id)
        has_finalizer = bool(self.layoutbuilder.has_finalizer(S))
        flags = int(has_finalizer) << 16
        descr.tid = llop.combine_ushort(lltype.Signed, type_id, flags)

    def init_array_descr(self, A, descr):
        type_id = self.layoutbuilder.get_type_id(A)
        descr.tid = llop.combine_ushort(lltype.Signed, type_id, 0)

    def gc_malloc(self, sizedescr):
        assert isinstance(sizedescr, BaseSizeDescr)
        return self.malloc_basic(sizedescr.size, sizedescr.tid)

    def gc_malloc_array(self, arraydescr, num_elem):
        assert isinstance(arraydescr, BaseArrayDescr)
        itemsize = arraydescr.get_item_size(self.translate_support_code)
        return self.malloc_array(itemsize, arraydescr.tid, num_elem)

    def gc_malloc_str(self, num_elem):
        return self.malloc_str(num_elem)

    def gc_malloc_unicode(self, num_elem):
        return self.malloc_unicode(num_elem)

    def args_for_new(self, sizedescr):
        assert isinstance(sizedescr, BaseSizeDescr)
        return [sizedescr.size, sizedescr.tid]

    def args_for_new_array(self, arraydescr):
        assert isinstance(arraydescr, BaseArrayDescr)
        itemsize = arraydescr.get_item_size(self.translate_support_code)
        return [itemsize, arraydescr.tid]

    def get_funcptr_for_new(self):
        return llhelper(self.GC_MALLOC_BASIC, self.malloc_basic)

    def get_funcptr_for_newarray(self):
        return llhelper(self.GC_MALLOC_ARRAY, self.malloc_array)

    def get_funcptr_for_newstr(self):
        return llhelper(self.GC_MALLOC_STR_UNICODE, self.malloc_str)

    def get_funcptr_for_newunicode(self):
        return llhelper(self.GC_MALLOC_STR_UNICODE, self.malloc_unicode)

    def do_write_barrier(self, gcref_struct, gcref_newptr):
        hdr_addr = llmemory.cast_ptr_to_adr(gcref_struct)
        hdr_addr -= self.gcheaderbuilder.size_gc_header
        hdr = llmemory.cast_adr_to_ptr(hdr_addr, self.HDRPTR)
        if hdr.tid & self.GCClass.JIT_WB_IF_FLAG:
            # get a pointer to the 'remember_young_pointer' function from
            # the GC, and call it immediately
            llop1 = self.llop1
            funcptr = llop1.get_write_barrier_failing_case(self.WB_FUNCPTR)
            funcptr(llmemory.cast_ptr_to_adr(gcref_struct),
                    llmemory.cast_ptr_to_adr(gcref_newptr))

    def rewrite_assembler(self, cpu, operations):
        # Perform two kinds of rewrites in parallel:
        #
        # - Add COND_CALLs to the write barrier before SETFIELD_GC and
        #   SETARRAYITEM_GC operations.
        #
        # - Remove all uses of ConstPtrs away from the assembler.
        #   Idea: when running on a moving GC, we can't (easily) encode
        #   the ConstPtrs in the assembler, because they can move at any
        #   point in time.  Instead, we store them in 'gcrefs.list', a GC
        #   but nonmovable list; and here, we modify 'operations' to
        #   replace direct usage of ConstPtr with a BoxPtr loaded by a
        #   GETFIELD_RAW from the array 'gcrefs.list'.
        #
        newops = []
        for op in operations:
            if op.opnum == rop.DEBUG_MERGE_POINT:
                continue
            # ---------- replace ConstPtrs with GETFIELD_RAW ----------
            # xxx some performance issue here
            for i in range(len(op.args)):
                v = op.args[i]
                if isinstance(v, ConstPtr) and bool(v.value):
                    addr = self.gcrefs.get_address_of_gcref(v.value)
                    # ^^^even for non-movable objects, to record their presence
                    if rgc.can_move(v.value):
                        box = BoxPtr(v.value)
                        addr = cpu.cast_adr_to_int(addr)
                        newops.append(ResOperation(rop.GETFIELD_RAW,
                                                   [ConstInt(addr)], box,
                                                   self.single_gcref_descr))
                        op.args[i] = box
            # ---------- write barrier for SETFIELD_GC ----------
            if op.opnum == rop.SETFIELD_GC:
                v = op.args[1]
                if isinstance(v, BoxPtr) or (isinstance(v, ConstPtr) and
                                             bool(v.value)): # store a non-NULL
                    self._gen_write_barrier(newops, op.args[0], v)
                    op = ResOperation(rop.SETFIELD_RAW, op.args, None,
                                      descr=op.descr)
            # ---------- write barrier for SETARRAYITEM_GC ----------
            if op.opnum == rop.SETARRAYITEM_GC:
                v = op.args[2]
                if isinstance(v, BoxPtr) or (isinstance(v, ConstPtr) and
                                             bool(v.value)): # store a non-NULL
                    self._gen_write_barrier(newops, op.args[0], v)
                    op = ResOperation(rop.SETARRAYITEM_RAW, op.args, None,
                                      descr=op.descr)
            # ----------
            newops.append(op)
        del operations[:]
        operations.extend(newops)

    def _gen_write_barrier(self, newops, v_base, v_value):
        args = [v_base, v_value]
        newops.append(ResOperation(rop.COND_CALL_GC_WB, args, None,
                                   descr=self.write_barrier_descr))

    def can_inline_malloc(self, descr):
        assert isinstance(descr, BaseSizeDescr)
        if descr.size < self.max_size_of_young_obj:
            has_finalizer = bool(descr.tid & (1<<16))
            if has_finalizer:
                return False
            return True
        return False

    def has_write_barrier_class(self):
        return WriteBarrierDescr

# ____________________________________________________________

def get_ll_description(gcdescr, translator=None):
    # translator is None if translate_support_code is False.
    if gcdescr is not None:
        name = gcdescr.config.translation.gctransformer
    else:
        name = "boehm"
    try:
        cls = globals()['GcLLDescr_' + name]
    except KeyError:
        raise NotImplementedError("GC transformer %r not supported by "
                                  "the JIT backend" % (name,))
    return cls(gcdescr, translator)
