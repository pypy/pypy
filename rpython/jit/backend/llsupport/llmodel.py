from rpython.rtyper.lltypesystem import lltype, llmemory, rffi, rclass, rstr
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.llinterp import LLInterpreter
from rpython.rtyper.annlowlevel import llhelper, MixLevelHelperAnnotator
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.jit.metainterp import history
from rpython.jit.codewriter import heaptracker, longlong
from rpython.jit.backend.model import AbstractCPU
from rpython.jit.backend.llsupport import symbolic, jitframe
from rpython.jit.backend.llsupport.symbolic import WORD, unroll_basic_sizes
from rpython.jit.backend.llsupport.descr import (
    get_size_descr, get_field_descr, get_array_descr,
    get_call_descr, get_interiorfield_descr,
    FieldDescr, ArrayDescr, CallDescr, InteriorFieldDescr,
    FLAG_POINTER, FLAG_FLOAT)
from rpython.jit.backend.llsupport.asmmemmgr import AsmMemoryManager
from rpython.annotator import model as annmodel
from rpython.rlib.unroll import unrolling_iterable


class AbstractLLCPU(AbstractCPU):
    from rpython.jit.metainterp.typesystem import llhelper as ts

    def __init__(self, rtyper, stats, opts, translate_support_code=False,
                 gcdescr=None):
        assert type(opts) is not bool
        self.opts = opts

        from rpython.jit.backend.llsupport.gc import get_ll_description
        AbstractCPU.__init__(self)
        self.rtyper = rtyper
        self.stats = stats
        self.translate_support_code = translate_support_code
        if translate_support_code and rtyper is not None:
            translator = rtyper.annotator.translator
        else:
            translator = None
        self.gc_ll_descr = get_ll_description(gcdescr, translator, rtyper)
        if translator and translator.config.translation.gcremovetypeptr:
            self.vtable_offset = None
        else:
            self.vtable_offset, _ = symbolic.get_field_token(rclass.OBJECT,
                                                             'typeptr',
                                                        translate_support_code)
        if translate_support_code:
            self._setup_exception_handling_translated()
        else:
            self._setup_exception_handling_untranslated()
        self.asmmemmgr = AsmMemoryManager()
        self._setup_frame_realloc(translate_support_code)
        ad = self.gc_ll_descr.getframedescrs(self).arraydescr
        self.signedarraydescr = ad
        # the same as normal JITFRAME, however with an array of pointers
        self.refarraydescr = ArrayDescr(ad.basesize, ad.itemsize, ad.lendescr,
                                        FLAG_POINTER)
        if WORD == 4:
            self.floatarraydescr = ArrayDescr(ad.basesize, ad.itemsize * 2,
                                              ad.lendescr, FLAG_FLOAT)
        else:
            self.floatarraydescr = ArrayDescr(ad.basesize, ad.itemsize,
                                              ad.lendescr, FLAG_FLOAT)
        self.setup()

    def getarraydescr_for_frame(self, type):
        if type == history.FLOAT:
            descr = self.floatarraydescr
        elif type == history.REF:
            descr = self.refarraydescr
        else:
            descr = self.signedarraydescr
        return descr

    def setup(self):
        pass

    def _setup_frame_realloc(self, translate_support_code):
        FUNC_TP = lltype.Ptr(lltype.FuncType([llmemory.GCREF, lltype.Signed],
                                             llmemory.GCREF))
        base_ofs = self.get_baseofs_of_frame_field()

        def realloc_frame(frame, size):
            try:
                if not we_are_translated():
                    assert not self._exception_emulator[0]
                frame = lltype.cast_opaque_ptr(jitframe.JITFRAMEPTR, frame)
                if size > frame.jf_frame_info.jfi_frame_depth:
                    # update the frame_info size, which is for whatever reason
                    # not up to date
                    frame.jf_frame_info.set_frame_depth(base_ofs, size)
                new_frame = jitframe.JITFRAME.allocate(frame.jf_frame_info)
                frame.jf_forward = new_frame
                i = 0
                while i < len(frame.jf_frame):
                    new_frame.jf_frame[i] = frame.jf_frame[i]
                    frame.jf_frame[i] = 0
                    i += 1
                new_frame.jf_savedata = frame.jf_savedata
                new_frame.jf_guard_exc = frame.jf_guard_exc
                # all other fields are empty
                llop.gc_assume_young_pointers(lltype.Void, new_frame)
                return lltype.cast_opaque_ptr(llmemory.GCREF, new_frame)
            except Exception, e:
                print "Unhandled exception", e, "in realloc_frame"
                return lltype.nullptr(llmemory.GCREF.TO)

        if not translate_support_code:
            fptr = llhelper(FUNC_TP, realloc_frame)
        else:
            FUNC = FUNC_TP.TO
            args_s = [annmodel.lltype_to_annotation(ARG) for ARG in FUNC.ARGS]
            s_result = annmodel.lltype_to_annotation(FUNC.RESULT)
            mixlevelann = MixLevelHelperAnnotator(self.rtyper)
            graph = mixlevelann.getgraph(realloc_frame, args_s, s_result)
            fptr = mixlevelann.graph2delayed(graph, FUNC)
            mixlevelann.finish()
        self.realloc_frame = heaptracker.adr2int(llmemory.cast_ptr_to_adr(fptr))

    def _setup_exception_handling_untranslated(self):
        # for running un-translated only, all exceptions occurring in the
        # llinterpreter are stored in '_exception_emulator', which is then
        # read back by the machine code reading at the address given by
        # pos_exception() and pos_exc_value().
        _exception_emulator = lltype.malloc(rffi.CArray(lltype.Signed), 2,
                                            zero=True, flavor='raw',
                                            immortal=True)
        self._exception_emulator = _exception_emulator

        def _store_exception(lle):
            self._last_exception = lle       # keepalive
            tp_i = rffi.cast(lltype.Signed, lle.args[0])
            v_i = rffi.cast(lltype.Signed, lle.args[1])
            _exception_emulator[0] = tp_i
            _exception_emulator[1] = v_i

        self.debug_ll_interpreter = LLInterpreter(self.rtyper)
        self.debug_ll_interpreter._store_exception = _store_exception

        def pos_exception():
            return rffi.cast(lltype.Signed, _exception_emulator)

        def pos_exc_value():
            return (rffi.cast(lltype.Signed, _exception_emulator) +
                    rffi.sizeof(lltype.Signed))

        self.pos_exception = pos_exception
        self.pos_exc_value = pos_exc_value
        self.insert_stack_check = lambda: (0, 0, 0)

    def _setup_exception_handling_translated(self):

        def pos_exception():
            addr = llop.get_exception_addr(llmemory.Address)
            return heaptracker.adr2int(addr)

        def pos_exc_value():
            addr = llop.get_exc_value_addr(llmemory.Address)
            return heaptracker.adr2int(addr)
        
        from rpython.rlib import rstack
        
        STACK_CHECK_SLOWPATH = lltype.Ptr(lltype.FuncType([lltype.Signed],
                                                          lltype.Void))
        def insert_stack_check():
            endaddr = rstack._stack_get_end_adr()
            lengthaddr = rstack._stack_get_length_adr()
            f = llhelper(STACK_CHECK_SLOWPATH, rstack.stack_check_slowpath)
            slowpathaddr = rffi.cast(lltype.Signed, f)
            return endaddr, lengthaddr, slowpathaddr

        self.pos_exception = pos_exception
        self.pos_exc_value = pos_exc_value
        self.insert_stack_check = insert_stack_check

    def grab_exc_value(self, deadframe):
        deadframe = lltype.cast_opaque_ptr(jitframe.JITFRAMEPTR, deadframe)
        return deadframe.jf_guard_exc

    def set_savedata_ref(self, deadframe, data):
        deadframe = lltype.cast_opaque_ptr(jitframe.JITFRAMEPTR, deadframe)
        deadframe.jf_savedata = data

    def get_savedata_ref(self, deadframe):
        deadframe = lltype.cast_opaque_ptr(jitframe.JITFRAMEPTR, deadframe)
        return deadframe.jf_savedata

    def free_loop_and_bridges(self, compiled_loop_token):
        AbstractCPU.free_loop_and_bridges(self, compiled_loop_token)
        blocks = compiled_loop_token.asmmemmgr_blocks
        if blocks is not None:
            compiled_loop_token.asmmemmgr_blocks = None
            for rawstart, rawstop in blocks:
                self.gc_ll_descr.freeing_block(rawstart, rawstop)
                self.asmmemmgr.free(rawstart, rawstop)

    def force(self, addr_of_force_token):
        frame = rffi.cast(jitframe.JITFRAMEPTR, addr_of_force_token)
        frame = frame.resolve()
        frame.jf_descr = frame.jf_force_descr
        return lltype.cast_opaque_ptr(llmemory.GCREF, frame)

    def make_execute_token(self, *ARGS):
        FUNCPTR = lltype.Ptr(lltype.FuncType([llmemory.GCREF],
                                             llmemory.GCREF))

        lst = [(i, history.getkind(ARG)[0]) for i, ARG in enumerate(ARGS)]
        kinds = unrolling_iterable(lst)

        def execute_token(executable_token, *args):
            clt = executable_token.compiled_loop_token
            assert len(args) == clt._debug_nbargs
            #
            addr = executable_token._ll_function_addr
            func = rffi.cast(FUNCPTR, addr)
            #llop.debug_print(lltype.Void, ">>>> Entering", addr)
            frame_info = clt.frame_info
            frame = self.gc_ll_descr.malloc_jitframe(frame_info)
            ll_frame = lltype.cast_opaque_ptr(llmemory.GCREF, frame)
            locs = executable_token.compiled_loop_token._ll_initial_locs
            prev_interpreter = None   # help flow space
            if not self.translate_support_code:
                prev_interpreter = LLInterpreter.current_interpreter
                LLInterpreter.current_interpreter = self.debug_ll_interpreter
            try:
                for i, kind in kinds:
                    arg = args[i]
                    num = locs[i]
                    if kind == history.INT:
                        self.set_int_value(ll_frame, num, arg)
                    elif kind == history.FLOAT:
                        self.set_float_value(ll_frame, num, arg)
                    else:
                        assert kind == history.REF
                        self.set_ref_value(ll_frame, num, arg)
                ll_frame = func(ll_frame)
            finally:
                if not self.translate_support_code:
                    LLInterpreter.current_interpreter = prev_interpreter
            #llop.debug_print(lltype.Void, "<<<< Back")
            return ll_frame
        return execute_token

    # ------------------- helpers and descriptions --------------------

    @staticmethod
    def _cast_int_to_gcref(x):
        # dangerous!  only use if you are sure no collection could occur
        # between reading the integer and casting it to a pointer
        return rffi.cast(llmemory.GCREF, x)

    @staticmethod
    def cast_gcref_to_int(x):
        return rffi.cast(lltype.Signed, x)

    @staticmethod
    def cast_int_to_adr(x):
        return rffi.cast(llmemory.Address, x)

    @staticmethod
    def cast_adr_to_int(x):
        return rffi.cast(lltype.Signed, x)

    def sizeof(self, S):
        return get_size_descr(self.gc_ll_descr, S)

    def fielddescrof(self, STRUCT, fieldname):
        return get_field_descr(self.gc_ll_descr, STRUCT, fieldname)

    def unpack_fielddescr(self, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        return fielddescr.offset
    unpack_fielddescr._always_inline_ = True

    def unpack_fielddescr_size(self, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        ofs = fielddescr.offset
        size = fielddescr.field_size
        sign = fielddescr.is_field_signed()
        return ofs, size, sign
    unpack_fielddescr_size._always_inline_ = True

    def arraydescrof(self, A):
        return get_array_descr(self.gc_ll_descr, A)

    def interiorfielddescrof(self, A, fieldname, arrayfieldname=None):
        return get_interiorfield_descr(self.gc_ll_descr, A, fieldname,
                                       arrayfieldname)

    def unpack_arraydescr(self, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        return arraydescr.basesize
    unpack_arraydescr._always_inline_ = True

    def unpack_arraydescr_size(self, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        ofs = arraydescr.basesize
        size = arraydescr.itemsize
        sign = arraydescr.is_item_signed()
        return ofs, size, sign
    unpack_arraydescr_size._always_inline_ = True

    def calldescrof(self, FUNC, ARGS, RESULT, extrainfo):
        return get_call_descr(self.gc_ll_descr, ARGS, RESULT, extrainfo)

    def calldescrof_dynamic(self, cif_description, extrainfo):
        from rpython.jit.backend.llsupport import ffisupport
        return ffisupport.get_call_descr_dynamic(self, cif_description,
                                                 extrainfo)

    def _calldescr_dynamic_for_tests(self, atypes, rtype,
                                     abiname='FFI_DEFAULT_ABI'):
        from rpython.jit.backend.llsupport import ffisupport
        return ffisupport.calldescr_dynamic_for_tests(self, atypes, rtype,
                                                      abiname)

    def get_latest_descr(self, deadframe):
        deadframe = lltype.cast_opaque_ptr(jitframe.JITFRAMEPTR, deadframe)
        descr = deadframe.jf_descr
        res = history.AbstractDescr.show(self, descr)
        assert isinstance(res, history.AbstractFailDescr)
        return res

    def _decode_pos(self, deadframe, index):
        descr = self.get_latest_descr(deadframe)
        if descr.final_descr:
            assert index == 0
            return 0
        return descr.rd_locs[index]

    def get_int_value(self, deadframe, index):
        pos = self._decode_pos(deadframe, index)
        descr = self.gc_ll_descr.getframedescrs(self).arraydescr
        ofs = self.unpack_arraydescr(descr)
        return self.read_int_at_mem(deadframe, pos + ofs, WORD, 1)

    def get_ref_value(self, deadframe, index):
        pos = self._decode_pos(deadframe, index)
        descr = self.gc_ll_descr.getframedescrs(self).arraydescr
        ofs = self.unpack_arraydescr(descr)
        return self.read_ref_at_mem(deadframe, pos + ofs)

    def get_float_value(self, deadframe, index):
        pos = self._decode_pos(deadframe, index)
        descr = self.gc_ll_descr.getframedescrs(self).arraydescr
        ofs = self.unpack_arraydescr(descr)
        return self.read_float_at_mem(deadframe, pos + ofs)

    # ____________________ RAW PRIMITIVES ________________________

    @specialize.argtype(1)
    def read_int_at_mem(self, gcref, ofs, size, sign):
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        for STYPE, UTYPE, itemsize in unroll_basic_sizes:
            if size == itemsize:
                if sign:
                    items = rffi.cast(rffi.CArrayPtr(STYPE), items)
                    val = items[0]
                    val = rffi.cast(lltype.Signed, val)
                else:
                    items = rffi.cast(rffi.CArrayPtr(UTYPE), items)
                    val = items[0]
                    val = rffi.cast(lltype.Signed, val)
                # --- end of GC unsafe code ---
                return val
        else:
            raise NotImplementedError("size = %d" % size)

    @specialize.argtype(1)
    def write_int_at_mem(self, gcref, ofs, size, sign, newvalue):
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        for TYPE, _, itemsize in unroll_basic_sizes:
            if size == itemsize:
                items = rffi.cast(rffi.CArrayPtr(TYPE), items)
                items[0] = rffi.cast(TYPE, newvalue)
                # --- end of GC unsafe code ---
                return
        else:
            raise NotImplementedError("size = %d" % size)

    def read_ref_at_mem(self, gcref, ofs):
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        items = rffi.cast(rffi.CArrayPtr(lltype.Signed), items)
        pval = self._cast_int_to_gcref(items[0])
        # --- end of GC unsafe code ---
        return pval

    def write_ref_at_mem(self, gcref, ofs, newvalue):
        self.gc_ll_descr.do_write_barrier(gcref, newvalue)
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        items = rffi.cast(rffi.CArrayPtr(lltype.Signed), items)
        items[0] = self.cast_gcref_to_int(newvalue)
        # --- end of GC unsafe code ---

    @specialize.argtype(1)
    def read_float_at_mem(self, gcref, ofs):
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        items = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), items)
        fval = items[0]
        # --- end of GC unsafe code ---
        return fval

    @specialize.argtype(1)
    def write_float_at_mem(self, gcref, ofs, newvalue):
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        items = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), items)
        items[0] = newvalue
        # --- end of GC unsafe code ---

    # ____________________________________________________________

    def set_int_value(self, newframe, index, value):
        """ Note that we keep index multiplied by WORD here mostly
        for completeness with get_int_value and friends
        """
        descr = self.gc_ll_descr.getframedescrs(self).arraydescr
        ofs = self.unpack_arraydescr(descr)
        self.write_int_at_mem(newframe, ofs + index, WORD, 1, value)

    def set_ref_value(self, newframe, index, value):
        descr = self.gc_ll_descr.getframedescrs(self).arraydescr
        ofs = self.unpack_arraydescr(descr)
        self.write_ref_at_mem(newframe, ofs + index, value)

    def set_float_value(self, newframe, index, value):
        descr = self.gc_ll_descr.getframedescrs(self).arraydescr
        ofs = self.unpack_arraydescr(descr)
        self.write_float_at_mem(newframe, ofs + index, value)

    @specialize.arg(1)
    def get_ofs_of_frame_field(self, name):
        descrs = self.gc_ll_descr.getframedescrs(self)
        ofs = self.unpack_fielddescr(getattr(descrs, name))
        return ofs

    def get_baseofs_of_frame_field(self):
        descrs = self.gc_ll_descr.getframedescrs(self)
        base_ofs = self.unpack_arraydescr(descrs.arraydescr)
        return base_ofs
    # ____________________________________________________________


    def bh_arraylen_gc(self, array, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        ofs = arraydescr.lendescr.offset
        return rffi.cast(rffi.CArrayPtr(lltype.Signed), array)[ofs/WORD]

    @specialize.argtype(1)
    def bh_getarrayitem_gc_i(self, gcref, itemindex, arraydescr):
        ofs, size, sign = self.unpack_arraydescr_size(arraydescr)
        return self.read_int_at_mem(gcref, ofs + itemindex * size, size,
                                    sign)

    def bh_getarrayitem_gc_r(self, gcref, itemindex, arraydescr):
        ofs = self.unpack_arraydescr(arraydescr)
        return self.read_ref_at_mem(gcref, itemindex * WORD + ofs)

    @specialize.argtype(1)
    def bh_getarrayitem_gc_f(self, gcref, itemindex, arraydescr):
        ofs = self.unpack_arraydescr(arraydescr)
        fsize = rffi.sizeof(longlong.FLOATSTORAGE)
        return self.read_float_at_mem(gcref, itemindex * fsize + ofs)

    @specialize.argtype(1)
    def bh_setarrayitem_gc_i(self, gcref, itemindex, newvalue, arraydescr):
        ofs, size, sign = self.unpack_arraydescr_size(arraydescr)
        self.write_int_at_mem(gcref, ofs + itemindex * size, size, sign,
                              newvalue)

    def bh_setarrayitem_gc_r(self, gcref, itemindex, newvalue, arraydescr):
        ofs = self.unpack_arraydescr(arraydescr)
        self.write_ref_at_mem(gcref, itemindex * WORD + ofs, newvalue)

    @specialize.argtype(1)
    def bh_setarrayitem_gc_f(self, gcref, itemindex, newvalue, arraydescr):
        ofs = self.unpack_arraydescr(arraydescr)
        fsize = rffi.sizeof(longlong.FLOATSTORAGE)
        self.write_float_at_mem(gcref, ofs + itemindex * fsize, newvalue)

    bh_setarrayitem_raw_i = bh_setarrayitem_gc_i
    bh_setarrayitem_raw_f = bh_setarrayitem_gc_f

    bh_getarrayitem_raw_i = bh_getarrayitem_gc_i
    bh_getarrayitem_raw_f = bh_getarrayitem_gc_f

    def bh_getinteriorfield_gc_i(self, gcref, itemindex, descr):
        assert isinstance(descr, InteriorFieldDescr)
        arraydescr = descr.arraydescr
        ofs, size, _ = self.unpack_arraydescr_size(arraydescr)
        ofs += descr.fielddescr.offset
        fieldsize = descr.fielddescr.field_size
        sign = descr.fielddescr.is_field_signed()
        fullofs = itemindex * size + ofs
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), fullofs)
        for STYPE, UTYPE, itemsize in unroll_basic_sizes:
            if fieldsize == itemsize:
                if sign:
                    item = rffi.cast(rffi.CArrayPtr(STYPE), items)
                    val = item[0]
                    val = rffi.cast(lltype.Signed, val)
                else:
                    item = rffi.cast(rffi.CArrayPtr(UTYPE), items)
                    val = item[0]
                    val = rffi.cast(lltype.Signed, val)
                # --- end of GC unsafe code ---
                return val
        else:
            raise NotImplementedError("size = %d" % fieldsize)

    def bh_getinteriorfield_gc_r(self, gcref, itemindex, descr):
        assert isinstance(descr, InteriorFieldDescr)
        arraydescr = descr.arraydescr
        ofs, size, _ = self.unpack_arraydescr_size(arraydescr)
        ofs += descr.fielddescr.offset
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs +
                            size * itemindex)
        items = rffi.cast(rffi.CArrayPtr(lltype.Signed), items)
        pval = self._cast_int_to_gcref(items[0])
        # --- end of GC unsafe code ---
        return pval

    def bh_getinteriorfield_gc_f(self, gcref, itemindex, descr):
        assert isinstance(descr, InteriorFieldDescr)
        arraydescr = descr.arraydescr
        ofs, size, _ = self.unpack_arraydescr_size(arraydescr)
        ofs += descr.fielddescr.offset
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs +
                            size * itemindex)
        items = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), items)
        fval = items[0]
        # --- end of GC unsafe code ---
        return fval

    def bh_setinteriorfield_gc_i(self, gcref, itemindex, value, descr):
        assert isinstance(descr, InteriorFieldDescr)
        arraydescr = descr.arraydescr
        ofs, size, _ = self.unpack_arraydescr_size(arraydescr)
        ofs += descr.fielddescr.offset
        fieldsize = descr.fielddescr.field_size
        ofs = itemindex * size + ofs
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        for TYPE, _, itemsize in unroll_basic_sizes:
            if fieldsize == itemsize:
                items = rffi.cast(rffi.CArrayPtr(TYPE), items)
                items[0] = rffi.cast(TYPE, value)
                # --- end of GC unsafe code ---
                return
        else:
            raise NotImplementedError("size = %d" % fieldsize)

    def bh_setinteriorfield_gc_r(self, gcref, itemindex, newvalue, descr):
        assert isinstance(descr, InteriorFieldDescr)
        arraydescr = descr.arraydescr
        ofs, size, _ = self.unpack_arraydescr_size(arraydescr)
        ofs += descr.fielddescr.offset
        self.gc_ll_descr.do_write_barrier(gcref, newvalue)
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref),
                            ofs + size * itemindex)
        items = rffi.cast(rffi.CArrayPtr(lltype.Signed), items)
        items[0] = self.cast_gcref_to_int(newvalue)
        # --- end of GC unsafe code ---

    def bh_setinteriorfield_gc_f(self, gcref, itemindex, newvalue, descr):
        assert isinstance(descr, InteriorFieldDescr)
        arraydescr = descr.arraydescr
        ofs, size, _ = self.unpack_arraydescr_size(arraydescr)
        ofs += descr.fielddescr.offset
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref),
                            ofs + size * itemindex)
        items = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), items)
        items[0] = newvalue
        # --- end of GC unsafe code ---

    def bh_strlen(self, string):
        s = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), string)
        return len(s.chars)

    def bh_unicodelen(self, string):
        u = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), string)
        return len(u.chars)

    def bh_strgetitem(self, string, index):
        s = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), string)
        return ord(s.chars[index])

    def bh_unicodegetitem(self, string, index):
        u = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), string)
        return ord(u.chars[index])

    @specialize.argtype(1)
    def _base_do_getfield_i(self, struct, fielddescr):
        ofs, size, sign = self.unpack_fielddescr_size(fielddescr)
        # --- start of GC unsafe code (no GC operation!) ---
        fieldptr = rffi.ptradd(rffi.cast(rffi.CCHARP, struct), ofs)
        for STYPE, UTYPE, itemsize in unroll_basic_sizes:
            if size == itemsize:
                # Note that in the common case where size==sizeof(Signed),
                # both cases of what follows are doing the same thing.
                # But gcc is clever enough to figure this out :-)
                if sign:
                    val = rffi.cast(rffi.CArrayPtr(STYPE), fieldptr)[0]
                    val = rffi.cast(lltype.Signed, val)
                else:
                    val = rffi.cast(rffi.CArrayPtr(UTYPE), fieldptr)[0]
                    val = rffi.cast(lltype.Signed, val)
                # --- end of GC unsafe code ---
                return val
        else:
            raise NotImplementedError("size = %d" % size)

    @specialize.argtype(1)
    def _base_do_getfield_r(self, struct, fielddescr):
        ofs = self.unpack_fielddescr(fielddescr)
        # --- start of GC unsafe code (no GC operation!) ---
        fieldptr = rffi.ptradd(rffi.cast(rffi.CCHARP, struct), ofs)
        pval = rffi.cast(rffi.CArrayPtr(lltype.Signed), fieldptr)[0]
        pval = self._cast_int_to_gcref(pval)
        # --- end of GC unsafe code ---
        return pval

    @specialize.argtype(1)
    def _base_do_getfield_f(self, struct, fielddescr):
        ofs = self.unpack_fielddescr(fielddescr)
        # --- start of GC unsafe code (no GC operation!) ---
        fieldptr = rffi.ptradd(rffi.cast(rffi.CCHARP, struct), ofs)
        fval = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), fieldptr)[0]
        # --- end of GC unsafe code ---
        return fval

    bh_getfield_gc_i = _base_do_getfield_i
    bh_getfield_gc_r = _base_do_getfield_r
    bh_getfield_gc_f = _base_do_getfield_f
    bh_getfield_raw_i = _base_do_getfield_i
    bh_getfield_raw_r = _base_do_getfield_r
    bh_getfield_raw_f = _base_do_getfield_f

    @specialize.argtype(1)
    def _base_do_setfield_i(self, struct, newvalue, fielddescr):
        ofs, size, sign = self.unpack_fielddescr_size(fielddescr)
        # --- start of GC unsafe code (no GC operation!) ---
        fieldptr = rffi.ptradd(rffi.cast(rffi.CCHARP, struct), ofs)
        for TYPE, _, itemsize in unroll_basic_sizes:
            if size == itemsize:
                fieldptr = rffi.cast(rffi.CArrayPtr(TYPE), fieldptr)
                fieldptr[0] = rffi.cast(TYPE, newvalue)
                # --- end of GC unsafe code ---
                return
        else:
            raise NotImplementedError("size = %d" % size)

    @specialize.argtype(1)
    def _base_do_setfield_r(self, struct, newvalue, fielddescr):
        ofs = self.unpack_fielddescr(fielddescr)
        assert lltype.typeOf(struct) is not lltype.Signed, (
            "can't handle write barriers for setfield_raw")
        self.gc_ll_descr.do_write_barrier(struct, newvalue)
        # --- start of GC unsafe code (no GC operation!) ---
        fieldptr = rffi.ptradd(rffi.cast(rffi.CCHARP, struct), ofs)
        fieldptr = rffi.cast(rffi.CArrayPtr(lltype.Signed), fieldptr)
        fieldptr[0] = self.cast_gcref_to_int(newvalue)
        # --- end of GC unsafe code ---

    @specialize.argtype(1)
    def _base_do_setfield_f(self, struct, newvalue, fielddescr):
        ofs = self.unpack_fielddescr(fielddescr)
        # --- start of GC unsafe code (no GC operation!) ---
        fieldptr = rffi.ptradd(rffi.cast(rffi.CCHARP, struct), ofs)
        fieldptr = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), fieldptr)
        fieldptr[0] = newvalue
        # --- end of GC unsafe code ---

    bh_setfield_gc_i = _base_do_setfield_i
    bh_setfield_gc_r = _base_do_setfield_r
    bh_setfield_gc_f = _base_do_setfield_f
    bh_setfield_raw_i = _base_do_setfield_i
    bh_setfield_raw_r = _base_do_setfield_r
    bh_setfield_raw_f = _base_do_setfield_f

    def bh_raw_store_i(self, addr, offset, newvalue, descr):
        ofs, size, sign = self.unpack_arraydescr_size(descr)
        items = addr + offset
        for TYPE, _, itemsize in unroll_basic_sizes:
            if size == itemsize:
                items = rffi.cast(rffi.CArrayPtr(TYPE), items)
                items[0] = rffi.cast(TYPE, newvalue)
                break

    def bh_raw_store_f(self, addr, offset, newvalue, descr):
        items = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), addr + offset)
        items[0] = newvalue

    def bh_raw_load_i(self, addr, offset, descr):
        ofs, size, sign = self.unpack_arraydescr_size(descr)
        items = addr + offset
        for TYPE, _, itemsize in unroll_basic_sizes:
            if size == itemsize:
                items = rffi.cast(rffi.CArrayPtr(TYPE), items)
                return rffi.cast(lltype.Signed, items[0])
        assert False # unreachable code

    def bh_raw_load_f(self, addr, offset, descr):
        items = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), addr + offset)
        return items[0]

    def bh_new(self, sizedescr):
        return self.gc_ll_descr.gc_malloc(sizedescr)

    def bh_new_with_vtable(self, vtable, sizedescr):
        res = self.gc_ll_descr.gc_malloc(sizedescr)
        if self.vtable_offset is not None:
            as_array = rffi.cast(rffi.CArrayPtr(lltype.Signed), res)
            as_array[self.vtable_offset/WORD] = vtable
        return res

    def bh_classof(self, struct):
        struct = lltype.cast_opaque_ptr(rclass.OBJECTPTR, struct)
        result_adr = llmemory.cast_ptr_to_adr(struct.typeptr)
        return heaptracker.adr2int(result_adr)

    def bh_new_array(self, length, arraydescr):
        return self.gc_ll_descr.gc_malloc_array(length, arraydescr)

    def bh_newstr(self, length):
        return self.gc_ll_descr.gc_malloc_str(length)

    def bh_newunicode(self, length):
        return self.gc_ll_descr.gc_malloc_unicode(length)

    def bh_strsetitem(self, string, index, newvalue):
        s = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), string)
        s.chars[index] = chr(newvalue)

    def bh_unicodesetitem(self, string, index, newvalue):
        u = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), string)
        u.chars[index] = unichr(newvalue)

    def bh_copystrcontent(self, src, dst, srcstart, dststart, length):
        src = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), src)
        dst = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), dst)
        rstr.copy_string_contents(src, dst, srcstart, dststart, length)

    def bh_copyunicodecontent(self, src, dst, srcstart, dststart, length):
        src = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), src)
        dst = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), dst)
        rstr.copy_unicode_contents(src, dst, srcstart, dststart, length)

    def bh_call_i(self, func, args_i, args_r, args_f, calldescr):
        assert isinstance(calldescr, CallDescr)
        if not we_are_translated():
            calldescr.verify_types(args_i, args_r, args_f, history.INT + 'S')
        return calldescr.call_stub_i(func, args_i, args_r, args_f)

    def bh_call_r(self, func, args_i, args_r, args_f, calldescr):
        assert isinstance(calldescr, CallDescr)
        if not we_are_translated():
            calldescr.verify_types(args_i, args_r, args_f, history.REF)
        return calldescr.call_stub_r(func, args_i, args_r, args_f)

    def bh_call_f(self, func, args_i, args_r, args_f, calldescr):
        assert isinstance(calldescr, CallDescr)
        if not we_are_translated():
            calldescr.verify_types(args_i, args_r, args_f, history.FLOAT + 'L')
        return calldescr.call_stub_f(func, args_i, args_r, args_f)

    def bh_call_v(self, func, args_i, args_r, args_f, calldescr):
        assert isinstance(calldescr, CallDescr)
        if not we_are_translated():
            calldescr.verify_types(args_i, args_r, args_f, history.VOID)
        # the 'i' return value is ignored (and nonsense anyway)
        calldescr.call_stub_i(func, args_i, args_r, args_f)
