from pypy.rlib import rgc
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass, rstr
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.jit.backend.x86 import symbolic
from pypy.jit.backend.x86.runner import ConstDescr3
from pypy.jit.backend.x86.ri386 import MODRM, IMM32, mem, imm32, rel32, heap
from pypy.jit.backend.x86.ri386 import REG, eax, ecx, edx
from pypy.jit.backend.x86.assembler import WORD

# ____________________________________________________________

class GcLLDescription:
    def __init__(self, gcdescr, cpu):
        self.gcdescr = gcdescr
    def _freeze_(self):
        return True
    def do_write_barrier(self, gcref_struct, gcref_newptr):
        pass
    def gen_write_barrier(self, regalloc, base_reg, value_reg):
        pass

# ____________________________________________________________

class GcLLDescr_boehm(GcLLDescription):
    moving_gc = False
    gcrootmap = None
    array_length_ofs = 0

    def __init__(self, gcdescr, cpu):
        # grab a pointer to the Boehm 'malloc' function
        compilation_info = ExternalCompilationInfo(libraries=['gc'])
        malloc_fn_ptr = rffi.llexternal("GC_malloc",
                                        [lltype.Signed], # size_t, but good enough
                                        llmemory.GCREF,
                                        compilation_info=compilation_info,
                                        sandboxsafe=True,
                                        _nowrapper=True)
        self.funcptr_for_new = malloc_fn_ptr

        # on some platform GC_init is required before any other
        # GC_* functions, call it here for the benefit of tests
        init_fn_ptr = rffi.llexternal("GC_init",
                                      [], lltype.Void,
                                      compilation_info=compilation_info,
                                      sandboxsafe=True,
                                      _nowrapper=True)

        init_fn_ptr()

    def sizeof(self, S, translate_support_code):
        size = symbolic.get_size(S, translate_support_code)
        return ConstDescr3(size, 0, False)

    def arraydescrof(self, A, translate_support_code):
        basesize, itemsize, ofs_length = symbolic.get_array_token(A,
                                                       translate_support_code)
        assert rffi.sizeof(A.OF) in [1, 2, WORD]
        # assert ofs_length == 0 --- but it's symbolic...
        if isinstance(A.OF, lltype.Ptr) and A.OF.TO._gckind == 'gc':
            ptr = True
        else:
            ptr = False
        return ConstDescr3(basesize, itemsize, ptr)

    def gc_malloc(self, descrsize):
        assert isinstance(descrsize, ConstDescr3)
        size = descrsize.v0
        return self.funcptr_for_new(size)

    def gc_malloc_array(self, arraydescr, num_elem):
        assert isinstance(arraydescr, ConstDescr3)
        basesize = arraydescr.v0
        itemsize = arraydescr.v1
        size = basesize + itemsize * num_elem
        res = self.funcptr_for_new(size)
        rffi.cast(rffi.CArrayPtr(lltype.Signed), res)[0] = num_elem
        return res

    def gc_malloc_str(self, num_elem, translate_support_code):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                      translate_support_code)
        assert itemsize == 1
        size = basesize + num_elem
        res = self.funcptr_for_new(size)
        rffi.cast(rffi.CArrayPtr(lltype.Signed), res)[ofs_length/WORD] = num_elem
        return res

    def gc_malloc_unicode(self, num_elem, translate_support_code):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                                      translate_support_code)
        size = basesize + num_elem * itemsize
        res = self.funcptr_for_new(size)
        rffi.cast(rffi.CArrayPtr(lltype.Signed), res)[ofs_length/WORD] = num_elem
        return res

    def args_for_new(self, descrsize):
        assert isinstance(descrsize, ConstDescr3)
        size = descrsize.v0
        return [size]

    def get_funcptr_for_new(self):
        return self.funcptr_for_new

    get_funcptr_for_newarray = None
    get_funcptr_for_newstr = None
    get_funcptr_for_newunicode = None

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
        start = self.gcmapstart()
        return start + llmemory.sizeof(llmemory.Address)*self._gcmap_curlength

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
        newlength = 128 + self._gcmap_maxlength * 5 // 4
        newgcmap = lltype.malloc(self.GCMAP_ARRAY, newlength, flavor='raw')
        oldgcmap = self._gcmap
        for i in range(self._gcmap_curlength):
            newgcmap[i] = oldgcmap[i]
        self._gcmap = newgcmap
        self._gcmap_maxlength = newlength
        if oldgcmap:
            lltype.free(oldgcmap, flavor='raw')

    def encode_callshape(self, gclocs):
        """Encode a callshape from the list of locations containing GC
        pointers."""
        shape = self._get_callshape(gclocs)
        return self._compress_callshape(shape)

    def _get_callshape(self, gclocs):
        # The return address is always found at 4(%ebp); and
        # the three registers %ebx, %esi, %edi are not used at all
        # so far, so their value always comes from the caller.
        shape = [self.LOC_EBP_BASED | 4,
                 self.LOC_REG | 0,
                 self.LOC_REG | 4,
                 self.LOC_REG | 8,
                 self.LOC_EBP_BASED | 0,
                 0]
        for loc in gclocs:
            assert isinstance(loc, MODRM)
            assert loc.is_relative_to_ebp()
            shape.append(self.LOC_EBP_BASED | (-4 * (1 + loc.position)))
        return shape

    def _compress_callshape(self, shape):
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


class GcLLDescr_framework(GcLLDescription):
    GcRefList = GcRefList

    def __init__(self, gcdescr, cpu):
        from pypy.rpython.memory.gc.base import choose_gc_from_config
        from pypy.rpython.memory.gctransform import framework
        self.cpu = cpu
        self.translator = cpu.mixlevelann.rtyper.annotator.translator

        # to find roots in the assembler, make a GcRootMap
        name = gcdescr.config.translation.gcrootfinder
        try:
            cls = globals()['GcRootMap_' + name]
        except KeyError:
            raise NotImplementedError("--gcrootfinder=%s not implemented"
                                      " with the JIT" % (name,))
        gcrootmap = cls()
        self.gcrootmap = gcrootmap

        # make a TransformerLayoutBuilder and save it on the translator
        # where it can be fished and reused by the FrameworkGCTransformer
        self.layoutbuilder = framework.TransformerLayoutBuilder()
        self.layoutbuilder.delay_encoding()
        self.translator._jit2gc = {
            'layoutbuilder': self.layoutbuilder,
            'gcmapstart': lambda: gcrootmap.gcmapstart(),
            'gcmapend': lambda: gcrootmap.gcmapend(),
            }
        self.GCClass, _ = choose_gc_from_config(gcdescr.config)
        self.moving_gc = self.GCClass.moving_gc
        self.HDRPTR = lltype.Ptr(self.GCClass.HDR)
        self.fielddescr_tid = cpu.fielddescrof(self.GCClass.HDR, 'tid')
        _, _, self.array_length_ofs = symbolic.get_array_token(
            lltype.GcArray(lltype.Signed), True)

        # make a malloc function, with three arguments
        def malloc_basic(size, type_id, has_finalizer):
            res = llop.do_malloc_fixedsize_clear(llmemory.GCREF,
                                                 type_id, size, True,
                                                 has_finalizer, False)
            #llop.debug_print(lltype.Void, "\tmalloc_basic", size, type_id,
            #                 "-->", res)
            return res
        self.malloc_basic = malloc_basic
        self.GC_MALLOC_BASIC = lltype.Ptr(lltype.FuncType(
            [lltype.Signed, lltype.Signed, lltype.Bool], llmemory.GCREF))
        self.WB_FUNCPTR = lltype.Ptr(lltype.FuncType(
            [llmemory.Address, llmemory.Address], lltype.Void))
        #
        def malloc_array(basesize, itemsize, type_id, num_elem):
            return llop.do_malloc_varsize_clear(
                llmemory.GCREF,
                type_id, num_elem, basesize, itemsize,
                self.array_length_ofs, True, False)
        self.malloc_array = malloc_array
        self.GC_MALLOC_ARRAY = lltype.Ptr(lltype.FuncType(
            [lltype.Signed] * 4, llmemory.GCREF))
        #
        (str_basesize, str_itemsize, str_ofs_length
         ) = symbolic.get_array_token(rstr.STR, True)
        (unicode_basesize, unicode_itemsize, unicode_ofs_length
         ) = symbolic.get_array_token(rstr.UNICODE, True)
        str_type_id = self.layoutbuilder.get_type_id(rstr.STR)
        unicode_type_id = self.layoutbuilder.get_type_id(rstr.UNICODE)
        #
        def malloc_str(length):
            return llop.do_malloc_varsize_clear(
                llmemory.GCREF,
                str_type_id, length, str_basesize, str_itemsize,
                str_ofs_length, True, False)
        def malloc_unicode(length):
            return llop.do_malloc_varsize_clear(
                llmemory.GCREF,
                unicode_type_id, length, unicode_basesize, unicode_itemsize,
                unicode_ofs_length, True, False)
        self.malloc_str = malloc_str
        self.malloc_unicode = malloc_unicode
        self.GC_MALLOC_STR_UNICODE = lltype.Ptr(lltype.FuncType(
            [lltype.Signed], llmemory.GCREF))

    def sizeof(self, S, translate_support_code):
        from pypy.rpython.memory.gctypelayout import weakpointer_offset
        assert translate_support_code, "required with the framework GC"
        size = symbolic.get_size(S, True)
        type_id = self.layoutbuilder.get_type_id(S)
        has_finalizer = bool(self.layoutbuilder.has_finalizer(S))
        assert weakpointer_offset(S) == -1     # XXX
        descr = ConstDescr3(size, 0, has_finalizer)
        descr.type_id = type_id
        return descr

    def arraydescrof(self, A, translate_support_code):
        assert translate_support_code, "required with the framework GC"
        basesize, itemsize, ofs_length = symbolic.get_array_token(A, True)
        assert rffi.sizeof(A.OF) in [1, 2, WORD]
        # assert ofs_length == self.array_length_ofs --- but it's symbolics...
        if isinstance(A.OF, lltype.Ptr) and A.OF.TO._gckind == 'gc':
            ptr = True
        else:
            ptr = False
        type_id = self.layoutbuilder.get_type_id(A)
        descr = ConstDescr3(basesize, itemsize, ptr)
        descr.type_id = type_id
        return descr

    def gc_malloc(self, descrsize):
        assert isinstance(descrsize, ConstDescr3)
        size = descrsize.v0
        type_id = descrsize.type_id
        has_finalizer = descrsize.flag2
        assert type_id > 0
        return self.malloc_basic(size, type_id, has_finalizer)

    def gc_malloc_array(self, arraydescr, num_elem):
        assert isinstance(arraydescr, ConstDescr3)
        basesize = arraydescr.v0
        itemsize = arraydescr.v1
        type_id = arraydescr.type_id
        assert type_id > 0
        return self.malloc_array(basesize, itemsize, type_id, num_elem)

    def gc_malloc_str(self, num_elem, translate_support_code):
        assert translate_support_code, "required with the framework GC"
        return self.malloc_str(num_elem)

    def gc_malloc_unicode(self, num_elem, translate_support_code):
        assert translate_support_code, "required with the framework GC"
        return self.malloc_unicode(num_elem)

    def args_for_new(self, descrsize):
        assert isinstance(descrsize, ConstDescr3)
        size = descrsize.v0
        type_id = descrsize.type_id
        has_finalizer = descrsize.flag2
        return [size, type_id, has_finalizer]

    def args_for_new_array(self, arraydescr):
        assert isinstance(arraydescr, ConstDescr3)
        basesize = arraydescr.v0
        itemsize = arraydescr.v1
        type_id = arraydescr.type_id
        return [basesize, itemsize, type_id]

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
        hdr = llmemory.cast_adr_to_ptr(hdr_addr, self.HDRPTR)
        if hdr.tid & self.GCClass.JIT_WB_IF_FLAG:
            # get a pointer to the 'remember_young_pointer' function from
            # the GC, and call it immediately
            funcptr = llop.get_write_barrier_failing_case(self.WB_FUNCPTR)
            funcptr(llmemory.cast_ptr_to_adr(gcref_struct),
                    llmemory.cast_ptr_to_adr(gcref_newptr))

    def gen_write_barrier(self, assembler, base_reg, value_reg):
        from pypy.jit.backend.x86.regalloc import REGS
        bytes_count = 11
        #
        if isinstance(value_reg, IMM32):
            if value_reg.value == 0:
                return      # writing NULL: don't need the write barrier at all
            bytes_count += 4
        else:
            assert isinstance(value_reg, REG)
        #
        if isinstance(base_reg, IMM32):
            bytes_count += 4
            tidaddr = heap(base_reg.value + 0)
        else:
            assert isinstance(base_reg, REG)
            tidaddr = mem(base_reg, 0)
        #
        assembler.mc.TEST(tidaddr, imm32(self.GCClass.JIT_WB_IF_FLAG))
        # do the rest using 'mc._mc' directly instead of 'mc', to avoid
        # bad surprizes if the code buffer is mostly full
        mc = assembler.mc._mc
        mc.write('\x74')             # JZ label_end
        mc.write(chr(bytes_count))
        start = mc.tell()
        mc.PUSHA()                   # 1 byte
        mc.PUSH(value_reg)           # 1 or 5 bytes
        mc.PUSH(base_reg)            # 1 or 5 bytes
        funcptr = llop.get_write_barrier_failing_case(self.WB_FUNCPTR)
        funcaddr = rffi.cast(lltype.Signed, funcptr)
        mc.CALL(rel32(funcaddr))     # 5 bytes
        mc.POP(eax)                  # 1 byte
        mc.POP(eax)                  # 1 byte
        mc.POPA()                    # 1 byte
                              # total: 11+(4?)+(4?) bytes
        assert mc.tell() == start + bytes_count

# ____________________________________________________________

def get_ll_description(gcdescr, cpu):
    if gcdescr is not None:
        name = gcdescr.config.translation.gctransformer
    else:
        name = "boehm"
    try:
        cls = globals()['GcLLDescr_' + name]
    except KeyError:
        raise NotImplementedError("GC transformer %r not supported by "
                                  "the x86 backend" % (name,))
    return cls(gcdescr, cpu)
