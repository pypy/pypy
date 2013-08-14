import os
from rpython.rlib import rgc
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi, rclass, rstr
from rpython.rtyper.lltypesystem import llgroup
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.annlowlevel import (llhelper, cast_instance_to_gcref,
                                        cast_base_ptr_to_instance)
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.jit.codewriter import heaptracker
from rpython.jit.metainterp.history import ConstPtr, AbstractDescr
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.backend.llsupport import symbolic, jitframe
from rpython.jit.backend.llsupport.symbolic import WORD
from rpython.jit.backend.llsupport.descr import SizeDescr, ArrayDescr
from rpython.jit.backend.llsupport.descr import GcCache, get_field_descr
from rpython.jit.backend.llsupport.descr import get_array_descr
from rpython.jit.backend.llsupport.descr import get_call_descr
from rpython.memory.gctransform import asmgcroot

# ____________________________________________________________

class GcLLDescription(GcCache):
    stm = False

    def __init__(self, gcdescr, translator=None, rtyper=None):
        GcCache.__init__(self, translator is not None, rtyper)
        self.gcdescr = gcdescr
        if translator and translator.config.translation.gcremovetypeptr:
            self.fielddescr_vtable = None
        else:
            self.fielddescr_vtable = get_field_descr(self, rclass.OBJECT,
                                                     'typeptr')
        self._generated_functions = []

    def _setup_str(self):
        self.str_descr     = get_array_descr(self, rstr.STR)
        self.unicode_descr = get_array_descr(self, rstr.UNICODE)

    def generate_function(self, funcname, func, ARGS, RESULT=llmemory.GCREF):
        """Generates a variant of malloc with the given name and the given
        arguments.  It should return NULL if out of memory.  If it raises
        anything, it must be an optional MemoryError.
        """
        FUNCPTR = lltype.Ptr(lltype.FuncType(ARGS, RESULT))
        descr = get_call_descr(self, ARGS, RESULT)
        setattr(self, funcname, func)
        setattr(self, funcname + '_FUNCPTR', FUNCPTR)
        setattr(self, funcname + '_descr', descr)
        self._generated_functions.append(funcname)

    @specialize.arg(1)
    def get_malloc_fn(self, funcname):
        func = getattr(self, funcname)
        FUNC = getattr(self, funcname + '_FUNCPTR')
        return llhelper(FUNC, func)

    @specialize.arg(1)
    def get_malloc_fn_addr(self, funcname):
        ll_func = self.get_malloc_fn(funcname)
        return heaptracker.adr2int(llmemory.cast_ptr_to_adr(ll_func))

    def _freeze_(self):
        return True
    def initialize(self):
        pass
    @specialize.argtype(1)
    def do_stm_barrier(self, gcref, cat):
        return gcref
    def do_write_barrier(self, gcref_struct, gcref_newptr):
        pass
    def can_use_nursery_malloc(self, size):
        return False
    def has_write_barrier_class(self):
        return None
    def get_nursery_free_addr(self):
        raise NotImplementedError
    def get_nursery_top_addr(self):
        raise NotImplementedError

    def freeing_block(self, rawstart, rawstop):
        pass

    def gc_malloc(self, sizedescr):
        """Blackhole: do a 'bh_new'.  Also used for 'bh_new_with_vtable',
        with the vtable pointer set manually afterwards."""
        assert isinstance(sizedescr, SizeDescr)
        return self._bh_malloc(sizedescr)

    def gc_malloc_array(self, num_elem, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        return self._bh_malloc_array(num_elem, arraydescr)

    def gc_malloc_str(self, num_elem):
        return self._bh_malloc_array(num_elem, self.str_descr)

    def gc_malloc_unicode(self, num_elem):
        return self._bh_malloc_array(num_elem, self.unicode_descr)

    def _record_constptrs(self, op, gcrefs_output_list):
        for i in range(op.numargs()):
            v = op.getarg(i)
            if isinstance(v, ConstPtr) and bool(v.value):
                p = v.value
                new_p = rgc._make_sure_does_not_move(p)
                v.value = new_p
                gcrefs_output_list.append(new_p)
                
        if op.is_guard() or op.getopnum() == rop.FINISH:
            # the only ops with descrs that get recorded in a trace
            from rpython.jit.metainterp.history import AbstractDescr
            descr = op.getdescr()
            llref = cast_instance_to_gcref(descr)
            new_llref = rgc._make_sure_does_not_move(llref)
            if we_are_translated():
                new_d = cast_base_ptr_to_instance(AbstractDescr, new_llref)
                # tests don't allow this:
                op.setdescr(new_d)
            else:
                assert llref == new_llref
            gcrefs_output_list.append(new_llref)

    def rewrite_assembler(self, cpu, operations, gcrefs_output_list):
        if not self.stm:
            from rpython.jit.backend.llsupport.rewrite import GcRewriterAssembler
        else:
            from rpython.jit.backend.llsupport import stmrewrite
            GcRewriterAssembler = stmrewrite.GcStmRewriterAssembler
        rewriter = GcRewriterAssembler(self, cpu)
        newops = rewriter.rewrite(operations)
        # record all GCREFs, because the GC (or Boehm) cannot see them and
        # keep them alive if they end up as constants in the assembler
        for op in newops:
            self._record_constptrs(op, gcrefs_output_list)
        return newops

    @specialize.memo()
    def getframedescrs(self, cpu):
        descrs = JitFrameDescrs()
        descrs.arraydescr = cpu.arraydescrof(jitframe.JITFRAME)
        for name in ['jf_descr', 'jf_guard_exc', 'jf_force_descr',
                     'jf_frame_info', 'jf_gcmap', 'jf_extra_stack_depth']:
            setattr(descrs, name, cpu.fielddescrof(jitframe.JITFRAME, name))
        descrs.jfi_frame_size = cpu.fielddescrof(jitframe.JITFRAMEINFO,
                                                  'jfi_frame_size')
        descrs.jfi_frame_depth = cpu.fielddescrof(jitframe.JITFRAMEINFO,
                                                  'jfi_frame_depth')
        return descrs

    def getarraydescr_for_frame(self, type):
        """ This functions retuns an arraydescr of type for the JITFRAME"""
        raise NotImplementedError

    def malloc_jitframe(self, frame_info):
        """ Allocate a new frame, overwritten by tests
        """
        frame = jitframe.JITFRAME.allocate(frame_info)
        llop.gc_assume_young_pointers(lltype.Void, frame)
        return frame

class JitFrameDescrs:
    def _freeze_(self):
        return True

# ____________________________________________________________

class GcLLDescr_boehm(GcLLDescription):
    kind                  = 'boehm'
    moving_gc             = False
    round_up              = False
    write_barrier_descr   = None
    fielddescr_tid        = None
    gcrootmap             = None
    str_type_id           = 0
    unicode_type_id       = 0

    def is_shadow_stack(self):
        return False

    @classmethod
    def configure_boehm_once(cls):
        """ Configure boehm only once, since we don't cache failures
        """
        if hasattr(cls, 'malloc_fn_ptr'):
            return cls.malloc_fn_ptr
        from rpython.rtyper.tool import rffi_platform
        compilation_info = rffi_platform.configure_boehm()

        # on some platform GC_init is required before any other
        # GC_* functions, call it here for the benefit of tests
        # XXX move this to tests
        init_fn_ptr = rffi.llexternal("GC_init",
                                      [], lltype.Void,
                                      compilation_info=compilation_info,
                                      sandboxsafe=True,
                                      _nowrapper=True)
        init_fn_ptr()

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
        return malloc_fn_ptr

    def __init__(self, gcdescr, translator, rtyper):
        GcLLDescription.__init__(self, gcdescr, translator, rtyper)
        # grab a pointer to the Boehm 'malloc' function
        self.malloc_fn_ptr = self.configure_boehm_once()
        self._setup_str()
        self._make_functions()
        self.memory = 0

    def _make_functions(self):

        def malloc_fixedsize(size):
            return self.malloc_fn_ptr(size)
        self.generate_function('malloc_fixedsize', malloc_fixedsize,
                               [lltype.Signed])

        def malloc_array(basesize, num_elem, itemsize, ofs_length):
            try:
                totalsize = ovfcheck(basesize + ovfcheck(itemsize * num_elem))
            except OverflowError:
                return lltype.nullptr(llmemory.GCREF.TO)
            res = self.malloc_fn_ptr(totalsize)
            if res:
                arrayptr = rffi.cast(rffi.CArrayPtr(lltype.Signed), res)
                arrayptr[ofs_length/WORD] = num_elem
            return res
        self.generate_function('malloc_array', malloc_array,
                               [lltype.Signed] * 4)

    def _bh_malloc(self, sizedescr):
        return self.malloc_fixedsize(sizedescr.size)

    def _bh_malloc_array(self, num_elem, arraydescr):
        return self.malloc_array(arraydescr.basesize, num_elem,
                                 arraydescr.itemsize,
                                 arraydescr.lendescr.offset)
    
    def get_malloc_slowpath_addr(self):
        return None

# ____________________________________________________________
# All code below is for the hybrid or minimark GC

class GcRootMap_asmgcc(object):
    is_shadow_stack = False
    is_stm = False

    def __init__(self, gcdescr):
        pass

    def register_asm_addr(self, start, mark):
        pass

class GcRootMap_shadowstack(object):
    is_shadow_stack = True
    is_stm = False
    
    def __init__(self, gcdescr):
        pass

    def register_asm_addr(self, start, mark):
        pass

    def get_root_stack_top_addr(self):
        rst_addr = llop.gc_adr_of_root_stack_top(llmemory.Address)
        return rffi.cast(lltype.Signed, rst_addr)

class GcRootMap_stm(object):
    is_shadow_stack = True
    is_stm = True
    
    def __init__(self, gcdescr):
        pass

    def register_asm_addr(self, start, mark):
        pass

    def get_root_stack_top_addr(self):
        rst_addr = llop.gc_adr_of_root_stack_top(llmemory.Address)
        return rffi.cast(lltype.Signed, rst_addr)
        
        
class BarrierDescr(AbstractDescr):
    def __init__(self, gc_ll_descr):
        self.llop1 = gc_ll_descr.llop1

        self.returns_modified_object = False
        self.gcheaderbuilder = gc_ll_descr.gcheaderbuilder
        self.HDRPTR = gc_ll_descr.HDRPTR
        self.b_slowpath = [0, 0, 0, 0, 0]

    def repr_of_descr(self):
        raise NotImplementedError

    def __repr(self):
        raise NotImplementedError

    def get_b_slowpath(self, num):
        return self.b_slowpath[num]

    def set_b_slowpath(self, num, addr):
        self.b_slowpath[num] = addr

    def get_barrier_funcptr(self, returns_modified_object):
        raise NotImplementedError
        
    def get_barrier_fn(self, cpu, returns_modified_object):
        # must pass in 'self.returns_modified_object', to make sure that
        # the callers are fixed for this case
        funcptr = self.get_barrier_funcptr(returns_modified_object)
        funcaddr = llmemory.cast_ptr_to_adr(funcptr)
        return cpu.cast_adr_to_int(funcaddr)

    def get_barrier_from_array_fn(self, cpu):
        # returns a function with arguments [array, index, newvalue]
        llop1 = self.llop1
        funcptr = llop1.get_write_barrier_from_array_failing_case(
            self.FUNCPTR)
        funcaddr = llmemory.cast_ptr_to_adr(funcptr)
        return cpu.cast_adr_to_int(funcaddr)    # this may return 0

    def has_barrier_from_array(self, cpu):
        return self.get_barrier_from_array_fn(cpu) != 0


        
class WriteBarrierDescr(BarrierDescr):
    def __init__(self, gc_ll_descr):
        BarrierDescr.__init__(self, gc_ll_descr)
        self.fielddescr_tid = gc_ll_descr.fielddescr_tid
        self.FUNCPTR = lltype.Ptr(lltype.FuncType(
            [llmemory.Address], lltype.Void))

        GCClass = gc_ll_descr.GCClass
        self.jit_wb_if_flag = GCClass.JIT_WB_IF_FLAG
        self.jit_wb_if_flag_byteofs, self.jit_wb_if_flag_singlebyte = (
            self.extract_flag_byte(self.jit_wb_if_flag))
        #
        if hasattr(GCClass, 'JIT_WB_CARDS_SET'):
            self.jit_wb_cards_set = GCClass.JIT_WB_CARDS_SET
            self.jit_wb_card_page_shift = GCClass.JIT_WB_CARD_PAGE_SHIFT
            self.jit_wb_cards_set_byteofs, self.jit_wb_cards_set_singlebyte = (
                self.extract_flag_byte(self.jit_wb_cards_set))
            #
            # the x86 backend uses the following "accidental" facts to
            # avoid one instruction:
            assert self.jit_wb_cards_set_byteofs == self.jit_wb_if_flag_byteofs
            assert self.jit_wb_cards_set_singlebyte == -0x80
        else:
            self.jit_wb_cards_set = 0

    def repr_of_descr(self):
        return 'wbdescr'

    def __repr__(self):
        return '<WriteBarrierDescr %r>' % (self.repr_of_descr(),)

    def extract_flag_byte(self, flag_word):
        # if convenient for the backend, we compute the info about
        # the flag as (byte-offset, single-byte-flag).
        if flag_word == 0:
            return (0, 0)
        import struct
        value = struct.pack(lltype.SignedFmt, flag_word)
        assert value.count('\x00') == len(value) - 1    # only one byte is != 0
        i = 0
        while value[i] == '\x00': i += 1
        return (i, struct.unpack('b', value[i])[0])

    def get_barrier_funcptr(self, returns_modified_object):
        assert not returns_modified_object
        FUNCTYPE = self.FUNCPTR
        return self.llop1.get_write_barrier_failing_case(FUNCTYPE)

    @specialize.arg(2)
    def _do_barrier(self, gcref_struct, returns_modified_object):
        assert self.returns_modified_object == returns_modified_object
        hdr_addr = llmemory.cast_ptr_to_adr(gcref_struct)
        hdr_addr -= self.gcheaderbuilder.size_gc_header
        hdr = llmemory.cast_adr_to_ptr(hdr_addr, self.HDRPTR)
        if self.jit_wb_if_flag == 0 or hdr.tid & self.jit_wb_if_flag:
            # get a pointer to the 'remember_young_pointer' function from
            # the GC, and call it immediately
            funcptr = self.get_barrier_funcptr(returns_modified_object)
            funcptr(llmemory.cast_ptr_to_adr(gcref_struct))

            
class STMBarrierDescr(BarrierDescr):
    def __init__(self, gc_ll_descr, stmcat, cfunc_name):
        BarrierDescr.__init__(self, gc_ll_descr)
        self.stmcat = stmcat
        self.returns_modified_object = True
        self.B_FUNCPTR_MOD = lltype.Ptr(lltype.FuncType(
            [llmemory.Address], llmemory.Address))

        self.b_failing_case_ptr = rffi.llexternal(
            cfunc_name,
            self.B_FUNCPTR_MOD.TO.ARGS,
            self.B_FUNCPTR_MOD.TO.RESULT,
            sandboxsafe=True,
            _nowrapper=True)

    def repr_of_descr(self):
        return self.stmcat

    def __repr__(self):
        return '<STMBarrierDescr %r>' % (self.repr_of_descr(),)

    def get_barrier_funcptr(self, returns_modified_object):
        assert returns_modified_object
        return self.b_failing_case_ptr

    @specialize.arg(2)
    def _do_barrier(self, gcref_struct, returns_modified_object):
        assert self.returns_modified_object == returns_modified_object
        # XXX: fastpath for Read and Write variants
        funcptr = self.get_barrier_funcptr(returns_modified_object)
        res = funcptr(llmemory.cast_ptr_to_adr(gcref_struct))
        return llmemory.cast_adr_to_ptr(res, llmemory.GCREF)


class STMReadBarrierDescr(STMBarrierDescr):
    def __init__(self, gc_ll_descr, stmcat):
        assert stmcat == 'P2R'
        STMBarrierDescr.__init__(self, gc_ll_descr, stmcat,
                                 'stm_DirectReadBarrier') 
        # XXX: implement fastpath then change to stm_DirectReadBarrier

    @specialize.arg(2)
    def _do_barrier(self, gcref_struct, returns_modified_object):
        assert returns_modified_object
        from rpython.memory.gc.stmgc import StmGC
        objadr = llmemory.cast_ptr_to_adr(gcref_struct)
        objhdr = rffi.cast(StmGC.GCHDRP, gcref_struct)

        # if h_revision == privat_rev of transaction
        priv_rev = self.llop1.stm_get_adr_of_private_rev_num(rffi.SIGNEDP)
        if objhdr.h_revision == priv_rev[0]:
            return gcref_struct

        # XXX: readcache!
        funcptr = self.get_barrier_funcptr(returns_modified_object)
        res = funcptr(objadr)
        return llmemory.cast_adr_to_ptr(res, llmemory.GCREF)

        
class STMWriteBarrierDescr(STMBarrierDescr):
    def __init__(self, gc_ll_descr, stmcat):
        assert stmcat in ['P2W']
        STMBarrierDescr.__init__(self, gc_ll_descr, stmcat,
                                 'stm_WriteBarrier')

    @specialize.arg(2)
    def _do_barrier(self, gcref_struct, returns_modified_object):
        assert returns_modified_object
        from rpython.memory.gc.stmgc import StmGC
        objadr = llmemory.cast_ptr_to_adr(gcref_struct)
        objhdr = rffi.cast(StmGC.GCHDRP, gcref_struct)
        
        # if h_revision == privat_rev of transaction
        priv_rev = self.llop1.stm_get_adr_of_private_rev_num(rffi.SIGNEDP)
        if objhdr.h_revision == priv_rev[0]:
            # also WRITE_BARRIER not set?
            if not (objhdr.h_tid & StmGC.GCFLAG_WRITE_BARRIER):
                return gcref_struct
        
        funcptr = self.get_barrier_funcptr(returns_modified_object)
        res = funcptr(objadr)
        return llmemory.cast_adr_to_ptr(res, llmemory.GCREF)
    
        
class GcLLDescr_framework(GcLLDescription):
    DEBUG = False    # forced to True by x86/test/test_zrpy_gc.py
    kind = 'framework'
    round_up = True

    def is_shadow_stack(self):
        return self.gcrootmap.is_shadow_stack

    def __init__(self, gcdescr, translator, rtyper, llop1=llop,
                 really_not_translated=False):
        GcLLDescription.__init__(self, gcdescr, translator, rtyper)
        self.translator = translator
        self.llop1 = llop1
        #try:
        self.stm = gcdescr.config.translation.stm
        #except AttributeError:
        #    pass      # keep the default of False
        if really_not_translated:
            assert not self.translate_support_code  # but half does not work
            self._initialize_for_tests()
        else:
            assert self.translate_support_code,"required with the framework GC"
            self._check_valid_gc()
            self._make_layoutbuilder()
            self._make_gcrootmap()
            self._setup_gcclass()
            if not self.stm:
                # XXX: not needed with stm/shadowstack??
                self._setup_tid()
            else:
                self.fielddescr_tid = None
        self._setup_write_barrier()
        self._setup_str()
        self._make_functions(really_not_translated)

    def _make_gcrootmap(self):
        # to find roots in the assembler, make a GcRootMap
        name = self.gcdescr.config.translation.gcrootfinder
        try:
            cls = globals()['GcRootMap_' + name]
        except KeyError:
            raise NotImplementedError("--gcrootfinder=%s not implemented"
                                      " with the JIT" % (name,))
        gcrootmap = cls(self.gcdescr)
        self.gcrootmap = gcrootmap

    def _initialize_for_tests(self):
        self.layoutbuilder = None
        self.fielddescr_tid = AbstractDescr()
        if self.stm:
            self.max_size_of_young_obj = None
        else:
            self.max_size_of_young_obj = 1000
        self.GCClass = None
        self.gcheaderbuilder = None
        self.HDRPTR = None

    def _check_valid_gc(self):
        # we need the hybrid or minimark GC for rgc._make_sure_does_not_move()
        # to work.  Additionally, 'hybrid' is missing some stuff like
        # jit_remember_young_pointer() for now.
        if self.gcdescr.config.translation.gc not in ('minimark', 'stmgc'):
            raise NotImplementedError("--gc=%s not implemented with the JIT" %
                                      (self.gcdescr.config.translation.gc,))

    def _make_layoutbuilder(self):
        # make a TransformerLayoutBuilder and save it on the translator
        # where it can be fished and reused by the FrameworkGCTransformer
        from rpython.memory.gctransform import framework
        translator = self.translator
        self.layoutbuilder = framework.TransformerLayoutBuilder(translator)
        self.layoutbuilder.delay_encoding()
        translator._jit2gc = {'layoutbuilder': self.layoutbuilder}

    def _setup_gcclass(self):
        from rpython.memory.gcheader import GCHeaderBuilder
        self.GCClass = self.layoutbuilder.GCClass
        self.moving_gc = self.GCClass.moving_gc
        self.HDRPTR = lltype.Ptr(self.GCClass.HDR)
        self.gcheaderbuilder = GCHeaderBuilder(self.HDRPTR.TO)
        self.max_size_of_young_obj = self.GCClass.JIT_max_size_of_young_obj()
        self.minimal_size_in_nursery=self.GCClass.JIT_minimal_size_in_nursery()

        # for the fast path of mallocs, the following must be true, at least
        assert self.GCClass.inline_simple_malloc
        assert self.GCClass.inline_simple_malloc_varsize

    def _setup_tid(self):
        self.fielddescr_tid = get_field_descr(self, self.GCClass.HDR, 'tid')
        frame_tid = self.layoutbuilder.get_type_id(jitframe.JITFRAME)
        self.translator._jit2gc['frame_tid'] = frame_tid

    def _setup_write_barrier(self):
        if self.stm:
            self._setup_barriers_for_stm()
        else:
            self.write_barrier_descr = WriteBarrierDescr(self)
            def do_write_barrier(gcref_struct, gcref_newptr):
                self.write_barrier_descr._do_barrier(gcref_struct, False)
            self.do_write_barrier = do_write_barrier

    def _setup_barriers_for_stm(self):
        self.P2Rdescr = STMReadBarrierDescr(self, 'P2R')
        self.P2Wdescr = STMWriteBarrierDescr(self, 'P2W')
        self.write_barrier_descr = "wbdescr: do not use"
        #
        @specialize.argtype(0)
        def do_stm_barrier(gcref, cat):
            if lltype.typeOf(gcref) is lltype.Signed:   # ignore if 'raw'
                # we are inevitable already because llmodel
                # does everything with raw-references
                return gcref
            if cat == 'W':
                descr = self.P2Wdescr
            else:
                descr = self.P2Rdescr
            return descr._do_barrier(gcref, True)
        self.do_stm_barrier = do_stm_barrier

    def _make_functions(self, really_not_translated):
        from rpython.memory.gctypelayout import check_typeid
        llop1 = self.llop1
        (self.standard_array_basesize, _, self.standard_array_length_ofs) = \
             symbolic.get_array_token(lltype.GcArray(lltype.Signed),
                                      not really_not_translated)

        def malloc_nursery_slowpath(size):
            """Allocate 'size' null bytes out of the nursery.
            Note that the fast path is typically inlined by the backend."""
            assert size >= self.minimal_size_in_nursery
            if self.DEBUG:
                self._random_usage_of_xmm_registers()
            type_id = rffi.cast(llgroup.HALFWORD, 0)    # missing here
            return llop1.do_malloc_fixedsize_clear(llmemory.GCREF,
                                                   type_id, size,
                                                   False, False, False)

        self.generate_function('malloc_nursery', malloc_nursery_slowpath,
                               [lltype.Signed])

        def malloc_array(itemsize, tid, num_elem):
            """Allocate an array with a variable-size num_elem.
            Only works for standard arrays."""
            assert num_elem >= 0, 'num_elem should be >= 0'
            type_id = llop.extract_ushort(llgroup.HALFWORD, tid)
            check_typeid(type_id)
            return llop1.do_malloc_varsize_clear(
                llmemory.GCREF,
                type_id, num_elem, self.standard_array_basesize, itemsize,
                self.standard_array_length_ofs)
        self.generate_function('malloc_array', malloc_array,
                               [lltype.Signed] * 3)

        def malloc_array_nonstandard(basesize, itemsize, lengthofs, tid,
                                     num_elem):
            """For the rare case of non-standard arrays, i.e. arrays where
            self.standard_array_{basesize,length_ofs} is wrong.  It can
            occur e.g. with arrays of floats on Win32."""
            type_id = llop.extract_ushort(llgroup.HALFWORD, tid)
            check_typeid(type_id)
            return llop1.do_malloc_varsize_clear(
                llmemory.GCREF,
                type_id, num_elem, basesize, itemsize, lengthofs)
        self.generate_function('malloc_array_nonstandard',
                               malloc_array_nonstandard,
                               [lltype.Signed] * 5)

        str_type_id    = self.str_descr.tid
        str_basesize   = self.str_descr.basesize
        str_itemsize   = self.str_descr.itemsize
        str_ofs_length = self.str_descr.lendescr.offset
        unicode_type_id    = self.unicode_descr.tid
        unicode_basesize   = self.unicode_descr.basesize
        unicode_itemsize   = self.unicode_descr.itemsize
        unicode_ofs_length = self.unicode_descr.lendescr.offset

        
        def malloc_str(length):
            return llop1.do_malloc_varsize_clear(
                llmemory.GCREF,
                str_type_id, length, str_basesize, str_itemsize,
                str_ofs_length)
        self.generate_function('malloc_str', malloc_str,
                               [lltype.Signed])
            
        def malloc_unicode(length):
            return llop1.do_malloc_varsize_clear(
                llmemory.GCREF,
                unicode_type_id, length, unicode_basesize, unicode_itemsize,
                unicode_ofs_length)
        self.generate_function('malloc_unicode', malloc_unicode,
                               [lltype.Signed])

        # Never called as far as I can tell, but there for completeness:
        # allocate a fixed-size object, but not in the nursery, because
        # it is too big.
        def malloc_big_fixedsize(size, tid):
            if self.DEBUG:
                self._random_usage_of_xmm_registers()
            type_id = llop.extract_ushort(llgroup.HALFWORD, tid)
            check_typeid(type_id)
            return llop1.do_malloc_fixedsize_clear(llmemory.GCREF,
                                                   type_id, size,
                                                   False, False, False)
        self.generate_function('malloc_big_fixedsize', malloc_big_fixedsize,
                               [lltype.Signed] * 2)

        if self.stm:
            # XXX remove the indirections in the following calls
            from rpython.rlib import rstm
            self.generate_function('stm_try_inevitable',
                                   rstm.become_inevitable, [],
                                   RESULT=lltype.Void)
            def ptr_eq(x, y): return x == y
            def ptr_ne(x, y): return x != y
            self.generate_function('stm_ptr_eq', ptr_eq, [llmemory.GCREF] * 2,
                                   RESULT=lltype.Bool)
            self.generate_function('stm_ptr_ne', ptr_ne, [llmemory.GCREF] * 2,
                                   RESULT=lltype.Bool)

    def _bh_malloc(self, sizedescr):
        from rpython.memory.gctypelayout import check_typeid
        llop1 = self.llop1
        type_id = llop.extract_ushort(llgroup.HALFWORD, sizedescr.tid)
        check_typeid(type_id)
        return llop1.do_malloc_fixedsize_clear(llmemory.GCREF,
                                               type_id, sizedescr.size,
                                               False, False, False)

    def _bh_malloc_array(self, num_elem, arraydescr):
        from rpython.memory.gctypelayout import check_typeid
        llop1 = self.llop1
        type_id = llop.extract_ushort(llgroup.HALFWORD, arraydescr.tid)
        check_typeid(type_id)
        return llop1.do_malloc_varsize_clear(llmemory.GCREF,
                                             type_id, num_elem,
                                             arraydescr.basesize,
                                             arraydescr.itemsize,
                                             arraydescr.lendescr.offset)


    class ForTestOnly:
        pass
    for_test_only = ForTestOnly()
    for_test_only.x = 1.23

    def _random_usage_of_xmm_registers(self):
        x0 = self.for_test_only.x
        x1 = x0 * 0.1
        x2 = x0 * 0.2
        x3 = x0 * 0.3
        self.for_test_only.x = x0 + x1 + x2 + x3

    def get_nursery_free_addr(self):
        nurs_addr = llop.gc_adr_of_nursery_free(llmemory.Address)
        return rffi.cast(lltype.Signed, nurs_addr)

    def get_nursery_top_addr(self):
        nurs_top_addr = llop.gc_adr_of_nursery_top(llmemory.Address)
        return rffi.cast(lltype.Signed, nurs_top_addr)

    def initialize(self):
        pass
        #self.gcrootmap.initialize()

    def init_size_descr(self, S, descr):
        if self.layoutbuilder is not None:
            type_id = self.layoutbuilder.get_type_id(S)
            assert not self.layoutbuilder.is_weakref_type(S)
            assert not self.layoutbuilder.has_finalizer(S)
            descr.tid = llop.combine_ushort(lltype.Signed, type_id, 0)

    def init_array_descr(self, A, descr):
        if self.layoutbuilder is not None:
            type_id = self.layoutbuilder.get_type_id(A)
            descr.tid = llop.combine_ushort(lltype.Signed, type_id, 0)

    def _set_tid(self, gcptr, tid):
        hdr_addr = llmemory.cast_ptr_to_adr(gcptr)
        hdr_addr -= self.gcheaderbuilder.size_gc_header
        hdr = llmemory.cast_adr_to_ptr(hdr_addr, self.HDRPTR)
        hdr.tid = tid

    def can_use_nursery_malloc(self, size):
        return (self.max_size_of_young_obj is not None and
                size < self.max_size_of_young_obj)
        
    def has_write_barrier_class(self):
        return WriteBarrierDescr

    def get_malloc_slowpath_addr(self):
        if self.max_size_of_young_obj is None:    # stm
            return None
        return self.get_malloc_fn_addr('malloc_nursery')

    def get_malloc_slowpath_array_addr(self):
        return self.get_malloc_fn_addr('malloc_array')
    
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
