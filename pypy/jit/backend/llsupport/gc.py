import os
from pypy.rlib import rgc
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.debug import fatalerror
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass, rstr
from pypy.rpython.lltypesystem import llgroup
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
from pypy.rpython.memory.gctransform import asmgcroot

# ____________________________________________________________

class GcLLDescription(GcCache):
    minimal_size_in_nursery = 0
    get_malloc_slowpath_addr = None

    def __init__(self, gcdescr, translator=None, rtyper=None):
        GcCache.__init__(self, translator is not None, rtyper)
        self.gcdescr = gcdescr
    def _freeze_(self):
        return True
    def initialize(self):
        pass
    def do_write_barrier(self, gcref_struct, gcref_newptr):
        pass
    def rewrite_assembler(self, cpu, operations, gcrefs_output_list):
        return operations
    def can_inline_malloc(self, descr):
        return False
    def can_inline_malloc_varsize(self, descr, num_elem):
        return False
    def has_write_barrier_class(self):
        return None
    def freeing_block(self, start, stop):
        pass

# ____________________________________________________________

class GcLLDescr_boehm(GcLLDescription):
    moving_gc = False
    gcrootmap = None

    @classmethod
    def configure_boehm_once(cls):
        """ Configure boehm only once, since we don't cache failures
        """
        if hasattr(cls, 'malloc_fn_ptr'):
            return cls.malloc_fn_ptr
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
        cls.malloc_fn_ptr = malloc_fn_ptr
        cls.compilation_info = compilation_info
        return malloc_fn_ptr

    def __init__(self, gcdescr, translator, rtyper):
        GcLLDescription.__init__(self, gcdescr, translator, rtyper)
        # grab a pointer to the Boehm 'malloc' function
        malloc_fn_ptr = self.configure_boehm_once()
        self.funcptr_for_new = malloc_fn_ptr

        # on some platform GC_init is required before any other
        # GC_* functions, call it here for the benefit of tests
        # XXX move this to tests
        init_fn_ptr = rffi.llexternal("GC_init",
                                      [], lltype.Void,
                                      compilation_info=self.compilation_info,
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
# All code below is for the hybrid or minimark GC


class GcRootMap_asmgcc(object):
    """Handles locating the stack roots in the assembler.
    This is the class supporting --gcrootfinder=asmgcc.
    """
    is_shadow_stack = False

    LOC_REG       = 0
    LOC_ESP_PLUS  = 1
    LOC_EBP_PLUS  = 2
    LOC_EBP_MINUS = 3

    GCMAP_ARRAY = rffi.CArray(lltype.Signed)
    CALLSHAPE_ARRAY_PTR = rffi.CArrayPtr(rffi.UCHAR)

    def __init__(self, gcdescr=None):
        # '_gcmap' is an array of length '_gcmap_maxlength' of addresses.
        # '_gcmap_curlength' tells how full the array really is.
        # The addresses are actually grouped in pairs:
        #     (addr-after-the-CALL-in-assembler, addr-of-the-call-shape).
        # '_gcmap_deadentries' counts pairs marked dead (2nd item is NULL).
        # '_gcmap_sorted' is True only if we know the array is sorted.
        self._gcmap = lltype.nullptr(self.GCMAP_ARRAY)
        self._gcmap_curlength = 0
        self._gcmap_maxlength = 0
        self._gcmap_deadentries = 0
        self._gcmap_sorted = True

    def add_jit2gc_hooks(self, jit2gc):
        jit2gc.update({
            'gcmapstart': lambda: self.gcmapstart(),
            'gcmapend': lambda: self.gcmapend(),
            'gcmarksorted': lambda: self.gcmarksorted(),
            })

    def initialize(self):
        # hack hack hack.  Remove these lines and see MissingRTypeAttribute
        # when the rtyper tries to annotate these methods only when GC-ing...
        self.gcmapstart()
        self.gcmapend()
        self.gcmarksorted()

    def gcmapstart(self):
        return rffi.cast(llmemory.Address, self._gcmap)

    def gcmapend(self):
        addr = self.gcmapstart()
        if self._gcmap_curlength:
            addr += rffi.sizeof(lltype.Signed) * self._gcmap_curlength
            if not we_are_translated() and type(addr) is long:
                from pypy.rpython.lltypesystem import ll2ctypes
                addr = ll2ctypes._lladdress(addr)       # XXX workaround
        return addr

    def gcmarksorted(self):
        # Called by the GC when it is about to sort [gcmapstart():gcmapend()].
        # Returns the previous sortedness flag -- i.e. returns True if it
        # is already sorted, False if sorting is needed.
        sorted = self._gcmap_sorted
        self._gcmap_sorted = True
        return sorted

    def put(self, retaddr, callshapeaddr):
        """'retaddr' is the address just after the CALL.
        'callshapeaddr' is the address of the raw 'shape' marker.
        Both addresses are actually integers here."""
        index = self._gcmap_curlength
        if index + 2 > self._gcmap_maxlength:
            index = self._enlarge_gcmap()
        self._gcmap[index] = retaddr
        self._gcmap[index+1] = callshapeaddr
        self._gcmap_curlength = index + 2
        self._gcmap_sorted = False

    @rgc.no_collect
    def _enlarge_gcmap(self):
        oldgcmap = self._gcmap
        if self._gcmap_deadentries * 3 * 2 > self._gcmap_maxlength:
            # More than 1/3rd of the entries are dead.  Don't actually
            # enlarge the gcmap table, but just clean up the dead entries.
            newgcmap = oldgcmap
        else:
            # Normal path: enlarge the array.
            newlength = 250 + (self._gcmap_maxlength // 3) * 4
            newgcmap = lltype.malloc(self.GCMAP_ARRAY, newlength, flavor='raw',
                                     track_allocation=False)
            self._gcmap_maxlength = newlength
        #
        j = 0
        i = 0
        end = self._gcmap_curlength
        while i < end:
            if oldgcmap[i + 1]:
                newgcmap[j] = oldgcmap[i]
                newgcmap[j + 1] = oldgcmap[i + 1]
                j += 2
            i += 2
        self._gcmap_curlength = j
        self._gcmap_deadentries = 0
        if oldgcmap != newgcmap:
            self._gcmap = newgcmap
            if oldgcmap:
                lltype.free(oldgcmap, flavor='raw', track_allocation=False)
        return j

    @rgc.no_collect
    def freeing_block(self, start, stop):
        # if [start:stop] is a raw block of assembler, then look up the
        # corresponding gcroot markers, and mark them as freed now in
        # self._gcmap by setting the 2nd address of every entry to NULL.
        gcmapstart = self.gcmapstart()
        gcmapend   = self.gcmapend()
        if gcmapstart == gcmapend:
            return
        if not self.gcmarksorted():
            asmgcroot.sort_gcmap(gcmapstart, gcmapend)
        # A note about gcmarksorted(): the deletion we do here keeps the
        # array sorted.  This avoids needing too many sort_gcmap()s.
        # Indeed, freeing_block() is typically called many times in a row,
        # so it will call sort_gcmap() at most the first time.
        startaddr = rffi.cast(llmemory.Address, start)
        stopaddr  = rffi.cast(llmemory.Address, stop)
        item = asmgcroot.binary_search(gcmapstart, gcmapend, startaddr)
        # 'item' points to one of the entries.  Because the whole array
        # is sorted, we know that it points either to the first entry we
        # want to kill, or to the previous entry.
        if item.address[0] < startaddr:
            item += asmgcroot.arrayitemsize    # go forward one entry
            assert item == gcmapend or item.address[0] >= startaddr
        while item != gcmapend and item.address[0] < stopaddr:
            item.address[1] = llmemory.NULL
            self._gcmap_deadentries += 1
            item += asmgcroot.arrayitemsize

    def get_basic_shape(self, is_64_bit=False):
        # XXX: Should this code even really know about stack frame layout of
        # the JIT?
        if is_64_bit:
            return [chr(self.LOC_EBP_PLUS  | 8),
                    chr(self.LOC_EBP_MINUS | 8),
                    chr(self.LOC_EBP_MINUS | 16),
                    chr(self.LOC_EBP_MINUS | 24),
                    chr(self.LOC_EBP_MINUS | 32),
                    chr(self.LOC_EBP_MINUS | 40),
                    chr(self.LOC_EBP_PLUS  | 0),
                    chr(0)]
        else:
            return [chr(self.LOC_EBP_PLUS  | 4),    # return addr: at   4(%ebp)
                    chr(self.LOC_EBP_MINUS | 4),    # saved %ebx:  at  -4(%ebp)
                    chr(self.LOC_EBP_MINUS | 8),    # saved %esi:  at  -8(%ebp)
                    chr(self.LOC_EBP_MINUS | 12),   # saved %edi:  at -12(%ebp)
                    chr(self.LOC_EBP_PLUS  | 0),    # saved %ebp:  at    (%ebp)
                    chr(0)]

    def _encode_num(self, shape, number):
        assert number >= 0
        flag = 0
        while number >= 0x80:
            shape.append(chr((number & 0x7F) | flag))
            flag = 0x80
            number >>= 7
        shape.append(chr(number | flag))

    def add_frame_offset(self, shape, offset):
        assert (offset & 3) == 0
        if offset >= 0:
            num = self.LOC_EBP_PLUS | offset
        else:
            num = self.LOC_EBP_MINUS | (-offset)
        self._encode_num(shape, num)

    def add_callee_save_reg(self, shape, reg_index):
        assert reg_index > 0
        shape.append(chr(self.LOC_REG | (reg_index << 2)))

    def compress_callshape(self, shape, datablockwrapper):
        # Similar to compress_callshape() in trackgcroot.py.
        # Returns an address to raw memory (as an integer).
        length = len(shape)
        rawaddr = datablockwrapper.malloc_aligned(length, 1)
        p = rffi.cast(self.CALLSHAPE_ARRAY_PTR, rawaddr)
        for i in range(length):
            p[length-1-i] = rffi.cast(rffi.UCHAR, shape[i])
        return rawaddr


class GcRootMap_shadowstack(object):
    """Handles locating the stack roots in the assembler.
    This is the class supporting --gcrootfinder=shadowstack.
    """
    is_shadow_stack = True
    MARKER = 8

    # The "shadowstack" is a portable way in which the GC finds the
    # roots that live in the stack.  Normally it is just a list of
    # pointers to GC objects.  The pointers may be moved around by a GC
    # collection.  But with the JIT, an entry can also be MARKER, in
    # which case the next entry points to an assembler stack frame.
    # During a residual CALL from the assembler (which may indirectly
    # call the GC), we use the force_index stored in the assembler
    # stack frame to identify the call: we can go from the force_index
    # to a list of where the GC pointers are in the frame (this is the
    # purpose of the present class).
    #
    # Note that across CALL_MAY_FORCE or CALL_ASSEMBLER, we can also go
    # from the force_index to a ResumeGuardForcedDescr instance, which
    # is used if the virtualizable or the virtualrefs need to be forced
    # (see pypy.jit.backend.model).  The force_index number in the stack
    # frame is initially set to a non-negative value x, but it is
    # occasionally turned into (~x) in case of forcing.

    INTARRAYPTR = rffi.CArrayPtr(rffi.INT)
    CALLSHAPES_ARRAY = rffi.CArray(INTARRAYPTR)

    def __init__(self, gcdescr):
        self._callshapes = lltype.nullptr(self.CALLSHAPES_ARRAY)
        self._callshapes_maxlength = 0
        self.force_index_ofs = gcdescr.force_index_ofs

    def add_jit2gc_hooks(self, jit2gc):
        #
        # ---------------
        # This is used to enumerate the shadowstack in the presence
        # of the JIT.  It is also used by the stacklet support in
        # rlib/_stacklet_shadowstack.  That's why it is written as
        # an iterator that can also be used with a custom_trace.
        #
        class RootIterator:
            _alloc_flavor_ = "raw"

            def next(iself, gc, next, range_highest):
                # Return the "next" valid GC object' address.  This usually
                # means just returning "next", until we reach "range_highest",
                # except that we are skipping NULLs.  If "next" contains a
                # MARKER instead, then we go into JIT-frame-lookup mode.
                #
                while True:
                    #
                    # If we are not iterating right now in a JIT frame
                    if iself.frame_addr == 0:
                        #
                        # Look for the next shadowstack address that
                        # contains a valid pointer
                        while next != range_highest:
                            if next.signed[0] == self.MARKER:
                                break
                            if gc.points_to_valid_gc_object(next):
                                return next
                            next += llmemory.sizeof(llmemory.Address)
                        else:
                            return llmemory.NULL     # done
                        #
                        # It's a JIT frame.  Save away 'next' for later, and
                        # go into JIT-frame-exploring mode.
                        next += llmemory.sizeof(llmemory.Address)
                        frame_addr = next.signed[0]
                        iself.saved_next = next
                        iself.frame_addr = frame_addr
                        addr = llmemory.cast_int_to_adr(frame_addr +
                                                        self.force_index_ofs)
                        addr = iself.translateptr(iself.context, addr)
                        force_index = addr.signed[0]
                        if force_index < 0:
                            force_index = ~force_index
                        # NB: the next line reads a still-alive _callshapes,
                        # because we ensure that just before we called this
                        # piece of assembler, we put on the (same) stack a
                        # pointer to a loop_token that keeps the force_index
                        # alive.
                        callshape = self._callshapes[force_index]
                    else:
                        # Continuing to explore this JIT frame
                        callshape = iself.callshape
                    #
                    # 'callshape' points to the next INT of the callshape.
                    # If it's zero we are done with the JIT frame.
                    while rffi.cast(lltype.Signed, callshape[0]) != 0:
                        #
                        # Non-zero: it's an offset inside the JIT frame.
                        # Read it and increment 'callshape'.
                        offset = rffi.cast(lltype.Signed, callshape[0])
                        callshape = lltype.direct_ptradd(callshape, 1)
                        addr = llmemory.cast_int_to_adr(iself.frame_addr +
                                                        offset)
                        addr = iself.translateptr(iself.context, addr)
                        if gc.points_to_valid_gc_object(addr):
                            #
                            # The JIT frame contains a valid GC pointer at
                            # this address (as opposed to NULL).  Save
                            # 'callshape' for the next call, and return the
                            # address.
                            iself.callshape = callshape
                            return addr
                    #
                    # Restore 'prev' and loop back to the start.
                    iself.frame_addr = 0
                    next = iself.saved_next
                    next += llmemory.sizeof(llmemory.Address)

        # ---------------
        #
        root_iterator = RootIterator()
        root_iterator.frame_addr = 0
        root_iterator.context = llmemory.NULL
        root_iterator.translateptr = lambda context, addr: addr
        jit2gc.update({
            'root_iterator': root_iterator,
            })

    def initialize(self):
        pass

    def get_basic_shape(self, is_64_bit=False):
        return []

    def add_frame_offset(self, shape, offset):
        assert offset != 0
        shape.append(offset)

    def add_callee_save_reg(self, shape, register):
        msg = "GC pointer in %s was not spilled" % register
        os.write(2, '[llsupport/gc] %s\n' % msg)
        raise AssertionError(msg)

    def compress_callshape(self, shape, datablockwrapper):
        length = len(shape)
        SZINT = rffi.sizeof(rffi.INT)
        rawaddr = datablockwrapper.malloc_aligned((length + 1) * SZINT, SZINT)
        p = rffi.cast(self.INTARRAYPTR, rawaddr)
        for i in range(length):
            p[i] = rffi.cast(rffi.INT, shape[i])
        p[length] = rffi.cast(rffi.INT, 0)
        return p

    def write_callshape(self, p, force_index):
        if force_index >= self._callshapes_maxlength:
            self._enlarge_callshape_list(force_index + 1)
        self._callshapes[force_index] = p

    def _enlarge_callshape_list(self, minsize):
        newlength = 250 + (self._callshapes_maxlength // 3) * 4
        if newlength < minsize:
            newlength = minsize
        newarray = lltype.malloc(self.CALLSHAPES_ARRAY, newlength,
                                 flavor='raw', track_allocation=False)
        if self._callshapes:
            i = self._callshapes_maxlength - 1
            while i >= 0:
                newarray[i] = self._callshapes[i]
                i -= 1
            lltype.free(self._callshapes, flavor='raw', track_allocation=False)
        self._callshapes = newarray
        self._callshapes_maxlength = newlength

    def freeing_block(self, start, stop):
        pass     # nothing needed here

    def get_root_stack_top_addr(self):
        rst_addr = llop.gc_adr_of_root_stack_top(llmemory.Address)
        return rffi.cast(lltype.Signed, rst_addr)


class WriteBarrierDescr(AbstractDescr):
    def __init__(self, gc_ll_descr):
        GCClass = gc_ll_descr.GCClass
        self.llop1 = gc_ll_descr.llop1
        self.WB_FUNCPTR = gc_ll_descr.WB_FUNCPTR
        self.WB_ARRAY_FUNCPTR = gc_ll_descr.WB_ARRAY_FUNCPTR
        self.fielddescr_tid = get_field_descr(gc_ll_descr, GCClass.HDR, 'tid')
        #
        self.jit_wb_if_flag = GCClass.JIT_WB_IF_FLAG
        self.jit_wb_if_flag_byteofs, self.jit_wb_if_flag_singlebyte = (
            self.extract_flag_byte(self.jit_wb_if_flag))
        #
        if hasattr(GCClass, 'JIT_WB_CARDS_SET'):
            self.jit_wb_cards_set = GCClass.JIT_WB_CARDS_SET
            self.jit_wb_card_page_shift = GCClass.JIT_WB_CARD_PAGE_SHIFT
            self.jit_wb_cards_set_byteofs, self.jit_wb_cards_set_singlebyte = (
                self.extract_flag_byte(self.jit_wb_cards_set))
        else:
            self.jit_wb_cards_set = 0

    def extract_flag_byte(self, flag_word):
        # if convenient for the backend, we compute the info about
        # the flag as (byte-offset, single-byte-flag).
        import struct
        value = struct.pack("l", flag_word)
        assert value.count('\x00') == len(value) - 1    # only one byte is != 0
        i = 0
        while value[i] == '\x00': i += 1
        return (i, struct.unpack('b', value[i])[0])

    def get_write_barrier_fn(self, cpu):
        llop1 = self.llop1
        funcptr = llop1.get_write_barrier_failing_case(self.WB_FUNCPTR)
        funcaddr = llmemory.cast_ptr_to_adr(funcptr)
        return cpu.cast_adr_to_int(funcaddr)

    def get_write_barrier_from_array_fn(self, cpu):
        # returns a function with arguments [array, index, newvalue]
        llop1 = self.llop1
        funcptr = llop1.get_write_barrier_from_array_failing_case(
            self.WB_ARRAY_FUNCPTR)
        funcaddr = llmemory.cast_ptr_to_adr(funcptr)
        return cpu.cast_adr_to_int(funcaddr)    # this may return 0


class GcLLDescr_framework(GcLLDescription):
    DEBUG = False    # forced to True by x86/test/test_zrpy_gc.py

    def __init__(self, gcdescr, translator, rtyper, llop1=llop):
        from pypy.rpython.memory.gctypelayout import check_typeid
        from pypy.rpython.memory.gcheader import GCHeaderBuilder
        from pypy.rpython.memory.gctransform import framework
        GcLLDescription.__init__(self, gcdescr, translator, rtyper)
        assert self.translate_support_code, "required with the framework GC"
        self.translator = translator
        self.llop1 = llop1

        # we need the hybrid or minimark GC for rgc._make_sure_does_not_move()
        # to work
        if gcdescr.config.translation.gc not in ('hybrid', 'minimark'):
            raise NotImplementedError("--gc=%s not implemented with the JIT" %
                                      (gcdescr.config.translation.gc,))

        # to find roots in the assembler, make a GcRootMap
        name = gcdescr.config.translation.gcrootfinder
        try:
            cls = globals()['GcRootMap_' + name]
        except KeyError:
            raise NotImplementedError("--gcrootfinder=%s not implemented"
                                      " with the JIT" % (name,))
        gcrootmap = cls(gcdescr)
        self.gcrootmap = gcrootmap

        # make a TransformerLayoutBuilder and save it on the translator
        # where it can be fished and reused by the FrameworkGCTransformer
        self.layoutbuilder = framework.TransformerLayoutBuilder(translator)
        self.layoutbuilder.delay_encoding()
        self.translator._jit2gc = {'layoutbuilder': self.layoutbuilder}
        gcrootmap.add_jit2gc_hooks(self.translator._jit2gc)

        self.GCClass = self.layoutbuilder.GCClass
        self.moving_gc = self.GCClass.moving_gc
        self.HDRPTR = lltype.Ptr(self.GCClass.HDR)
        self.gcheaderbuilder = GCHeaderBuilder(self.HDRPTR.TO)
        (self.array_basesize, _, self.array_length_ofs) = \
             symbolic.get_array_token(lltype.GcArray(lltype.Signed), True)
        self.max_size_of_young_obj = self.GCClass.JIT_max_size_of_young_obj()
        self.minimal_size_in_nursery=self.GCClass.JIT_minimal_size_in_nursery()

        # for the fast path of mallocs, the following must be true, at least
        assert self.GCClass.inline_simple_malloc
        assert self.GCClass.inline_simple_malloc_varsize

        # make a malloc function, with two arguments
        def malloc_basic(size, tid):
            assert size > 0, 'size should be > 0'
            type_id = llop.extract_ushort(llgroup.HALFWORD, tid)
            has_finalizer = bool(tid & (1<<llgroup.HALFSHIFT))
            check_typeid(type_id)
            res = llop1.do_malloc_fixedsize_clear(llmemory.GCREF,
                                                  type_id, size,
                                                  has_finalizer, False)
            # In case the operation above failed, we are returning NULL
            # from this function to assembler.  There is also an RPython
            # exception set, typically MemoryError; but it's easier and
            # faster to check for the NULL return value, as done by
            # translator/exceptiontransform.py.
            #llop.debug_print(lltype.Void, "\tmalloc_basic", size, type_id,
            #                 "-->", res)
            return res
        self.malloc_basic = malloc_basic
        self.GC_MALLOC_BASIC = lltype.Ptr(lltype.FuncType(
            [lltype.Signed, lltype.Signed], llmemory.GCREF))
        self.WB_FUNCPTR = lltype.Ptr(lltype.FuncType(
            [llmemory.Address, llmemory.Address], lltype.Void))
        self.WB_ARRAY_FUNCPTR = lltype.Ptr(lltype.FuncType(
            [llmemory.Address, lltype.Signed, llmemory.Address], lltype.Void))
        self.write_barrier_descr = WriteBarrierDescr(self)
        #
        def malloc_array(itemsize, tid, num_elem):
            assert num_elem >= 0, 'num_elem should be >= 0'
            type_id = llop.extract_ushort(llgroup.HALFWORD, tid)
            check_typeid(type_id)
            return llop1.do_malloc_varsize_clear(
                llmemory.GCREF,
                type_id, num_elem, self.array_basesize, itemsize,
                self.array_length_ofs)
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
            return llop1.do_malloc_varsize_clear(
                llmemory.GCREF,
                str_type_id, length, str_basesize, str_itemsize,
                str_ofs_length)
        def malloc_unicode(length):
            return llop1.do_malloc_varsize_clear(
                llmemory.GCREF,
                unicode_type_id, length, unicode_basesize,unicode_itemsize,
                unicode_ofs_length)
        self.malloc_str = malloc_str
        self.malloc_unicode = malloc_unicode
        self.GC_MALLOC_STR_UNICODE = lltype.Ptr(lltype.FuncType(
            [lltype.Signed], llmemory.GCREF))
        #
        class ForTestOnly:
            pass
        for_test_only = ForTestOnly()
        for_test_only.x = 1.23
        def random_usage_of_xmm_registers():
            x0 = for_test_only.x
            x1 = x0 * 0.1
            x2 = x0 * 0.2
            x3 = x0 * 0.3
            for_test_only.x = x0 + x1 + x2 + x3
        #
        def malloc_slowpath(size):
            if self.DEBUG:
                random_usage_of_xmm_registers()
            assert size >= self.minimal_size_in_nursery
            # NB. although we call do_malloc_fixedsize_clear() here,
            # it's a bit of a hack because we set tid to 0 and may
            # also use it to allocate varsized objects.  The tid
            # and possibly the length are both set afterward.
            gcref = llop1.do_malloc_fixedsize_clear(llmemory.GCREF,
                                        0, size, False, False)
            return rffi.cast(lltype.Signed, gcref)
        self.malloc_slowpath = malloc_slowpath
        self.MALLOC_SLOWPATH = lltype.FuncType([lltype.Signed], lltype.Signed)

    def get_nursery_free_addr(self):
        nurs_addr = llop.gc_adr_of_nursery_free(llmemory.Address)
        return rffi.cast(lltype.Signed, nurs_addr)

    def get_nursery_top_addr(self):
        nurs_top_addr = llop.gc_adr_of_nursery_top(llmemory.Address)
        return rffi.cast(lltype.Signed, nurs_top_addr)

    def get_malloc_slowpath_addr(self):
        fptr = llhelper(lltype.Ptr(self.MALLOC_SLOWPATH), self.malloc_slowpath)
        return rffi.cast(lltype.Signed, fptr)

    def initialize(self):
        self.gcrootmap.initialize()

    def init_size_descr(self, S, descr):
        type_id = self.layoutbuilder.get_type_id(S)
        assert not self.layoutbuilder.is_weakref_type(S)
        has_finalizer = bool(self.layoutbuilder.has_finalizer(S))
        flags = int(has_finalizer) << llgroup.HALFSHIFT
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

    def record_constptrs(self, op, gcrefs_output_list):
        for i in range(op.numargs()):
            v = op.getarg(i)
            if isinstance(v, ConstPtr) and bool(v.value):
                p = v.value
                rgc._make_sure_does_not_move(p)
                gcrefs_output_list.append(p)

    def rewrite_assembler(self, cpu, operations, gcrefs_output_list):
        # Perform two kinds of rewrites in parallel:
        #
        # - Add COND_CALLs to the write barrier before SETFIELD_GC and
        #   SETARRAYITEM_GC operations.
        #
        # - Record the ConstPtrs from the assembler.
        #
        newops = []
        known_lengths = {}
        # we can only remember one malloc since the next malloc can possibly
        # collect
        last_malloc = None
        for op in operations:
            if op.getopnum() == rop.DEBUG_MERGE_POINT:
                continue
            # ---------- record the ConstPtrs ----------
            self.record_constptrs(op, gcrefs_output_list)
            if op.is_malloc():
                last_malloc = op.result
            elif op.can_malloc():
                last_malloc = None
            # ---------- write barrier for SETFIELD_GC ----------
            if op.getopnum() == rop.SETFIELD_GC:
                val = op.getarg(0)
                # no need for a write barrier in the case of previous malloc
                if val is not last_malloc:
                    v = op.getarg(1)
                    if isinstance(v, BoxPtr) or (isinstance(v, ConstPtr) and
                                            bool(v.value)): # store a non-NULL
                        self._gen_write_barrier(newops, op.getarg(0), v)
                        op = op.copy_and_change(rop.SETFIELD_RAW)
            # ---------- write barrier for SETARRAYITEM_GC ----------
            if op.getopnum() == rop.SETARRAYITEM_GC:
                val = op.getarg(0)
                # no need for a write barrier in the case of previous malloc
                if val is not last_malloc:
                    v = op.getarg(2)
                    if isinstance(v, BoxPtr) or (isinstance(v, ConstPtr) and
                                            bool(v.value)): # store a non-NULL
                        self._gen_write_barrier_array(newops, op.getarg(0),
                                                      op.getarg(1), v,
                                                      cpu, known_lengths)
                        op = op.copy_and_change(rop.SETARRAYITEM_RAW)
            elif op.getopnum() == rop.NEW_ARRAY:
                v_length = op.getarg(0)
                if isinstance(v_length, ConstInt):
                    known_lengths[op.result] = v_length.getint()
            # ----------
            newops.append(op)
        return newops

    def _gen_write_barrier(self, newops, v_base, v_value):
        args = [v_base, v_value]
        newops.append(ResOperation(rop.COND_CALL_GC_WB, args, None,
                                   descr=self.write_barrier_descr))

    def _gen_write_barrier_array(self, newops, v_base, v_index, v_value,
                                 cpu, known_lengths):
        if self.write_barrier_descr.get_write_barrier_from_array_fn(cpu) != 0:
            # If we know statically the length of 'v', and it is not too
            # big, then produce a regular write_barrier.  If it's unknown or
            # too big, produce instead a write_barrier_from_array.
            LARGE = 130
            length = known_lengths.get(v_base, LARGE)
            if length >= LARGE:
                # unknown or too big: produce a write_barrier_from_array
                args = [v_base, v_index, v_value]
                newops.append(ResOperation(rop.COND_CALL_GC_WB_ARRAY, args,
                                           None,
                                           descr=self.write_barrier_descr))
                return
        # fall-back case: produce a write_barrier
        self._gen_write_barrier(newops, v_base, v_value)

    def can_inline_malloc(self, descr):
        assert isinstance(descr, BaseSizeDescr)
        if descr.size < self.max_size_of_young_obj:
            has_finalizer = bool(descr.tid & (1<<llgroup.HALFSHIFT))
            if has_finalizer:
                return False
            return True
        return False

    def can_inline_malloc_varsize(self, arraydescr, num_elem):
        assert isinstance(arraydescr, BaseArrayDescr)
        basesize = arraydescr.get_base_size(self.translate_support_code)
        itemsize = arraydescr.get_item_size(self.translate_support_code)
        try:
            size = ovfcheck(basesize + ovfcheck(itemsize * num_elem))
            return size < self.max_size_of_young_obj
        except OverflowError:
            return False

    def has_write_barrier_class(self):
        return WriteBarrierDescr

    def freeing_block(self, start, stop):
        self.gcrootmap.freeing_block(start, stop)

# ____________________________________________________________

def get_ll_description(gcdescr, translator=None, rtyper=None):
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
    return cls(gcdescr, translator, rtyper)
