from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass, rstr
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.annlowlevel import llhelper, cast_instance_to_base_ptr
from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.jit.metainterp import history
from pypy.jit.codewriter import heaptracker, longlong
from pypy.jit.backend.model import AbstractCPU
from pypy.jit.backend.llsupport import symbolic, jitframe
from pypy.jit.backend.llsupport.symbolic import WORD, unroll_basic_sizes
from pypy.jit.backend.llsupport.descr import (
    get_size_descr, get_field_descr, get_array_descr,
    get_call_descr, get_interiorfield_descr,
    FieldDescr, ArrayDescr, CallDescr, InteriorFieldDescr)
from pypy.jit.backend.llsupport.asmmemmgr import AsmMemoryManager


class AbstractLLCPU(AbstractCPU):
    from pypy.jit.metainterp.typesystem import llhelper as ts

    def __init__(self, rtyper, stats, opts, translate_support_code=False,
                 gcdescr=None):
        assert type(opts) is not bool
        self.opts = opts

        from pypy.jit.backend.llsupport.gc import get_ll_description
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
        self.setup()

    def setup(self):
        pass


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

        # XXX I think we don't need it any more
        #self._memoryerror_emulated = rffi.cast(llmemory.GCREF, -123)
        #self.deadframe_memoryerror = lltype.malloc(jitframe.DEADFRAME, 0)
        #self.deadframe_memoryerror.jf_guard_exc = self._memoryerror_emulated

        def propagate_exception():
            exc = _exception_emulator[1]
            _exception_emulator[0] = 0
            _exception_emulator[1] = 0
            assert self.propagate_exception_v >= 0
            faildescr = self.get_fail_descr_from_number(
                self.propagate_exception_v)
            faildescr = faildescr.hide(self)
            if not exc:
                deadframe = self.deadframe_memoryerror
                if not deadframe.jf_descr:
                    deadframe.jf_descr = faildescr
                else:
                    assert deadframe.jf_descr == faildescr
            else:
                XXX
                deadframe = lltype.malloc(jitframe.DEADFRAME, 0)
                deadframe.jf_guard_exc = rffi.cast(llmemory.GCREF, exc)
                deadframe.jf_descr = faildescr
            return lltype.cast_opaque_ptr(llmemory.GCREF, deadframe)

        self.pos_exception = pos_exception
        self.pos_exc_value = pos_exc_value
        self.insert_stack_check = lambda: (0, 0, 0)
        self._propagate_exception = propagate_exception

    def _setup_exception_handling_translated(self):

        def pos_exception():
            addr = llop.get_exception_addr(llmemory.Address)
            return heaptracker.adr2int(addr)

        def pos_exc_value():
            addr = llop.get_exc_value_addr(llmemory.Address)
            return heaptracker.adr2int(addr)

        from pypy.rlib import rstack
        STACK_CHECK_SLOWPATH = lltype.Ptr(lltype.FuncType([lltype.Signed],
                                                          lltype.Void))
        def insert_stack_check():
            endaddr = rstack._stack_get_end_adr()
            lengthaddr = rstack._stack_get_length_adr()
            f = llhelper(STACK_CHECK_SLOWPATH, rstack.stack_check_slowpath)
            slowpathaddr = rffi.cast(lltype.Signed, f)
            return endaddr, lengthaddr, slowpathaddr

        #self.deadframe_memoryerror = lltype.malloc(jitframe.DEADFRAME, 0)

        def propagate_exception():
            addr = llop.get_exception_addr(llmemory.Address)
            addr.address[0] = llmemory.NULL
            addr = llop.get_exc_value_addr(llmemory.Address)
            exc = rffi.cast(llmemory.GCREF, addr.address[0])
            addr.address[0] = llmemory.NULL
            assert self.propagate_exception_v >= 0
            faildescr = self.get_fail_descr_from_number(
                self.propagate_exception_v)
            faildescr = faildescr.hide(self)
            XXX
            deadframe = lltype.nullptr(jitframe.DEADFRAME)
            if exc:
                try:
                    deadframe = lltype.malloc(jitframe.DEADFRAME, 0)
                    deadframe.jf_guard_exc = rffi.cast(llmemory.GCREF, exc)
                    deadframe.jf_descr = faildescr
                except MemoryError:
                    deadframe = lltype.nullptr(jitframe.DEADFRAME)
            if not deadframe:
                deadframe = self.deadframe_memoryerror
                if not deadframe.jf_descr:
                    exc = MemoryError()
                    exc = cast_instance_to_base_ptr(exc)
                    exc = lltype.cast_opaque_ptr(llmemory.GCREF, exc)
                    deadframe.jf_guard_exc = exc
                    deadframe.jf_descr = faildescr
                else:
                    assert deadframe.jf_descr == faildescr
            return lltype.cast_opaque_ptr(llmemory.GCREF, deadframe)

        self.pos_exception = pos_exception
        self.pos_exc_value = pos_exc_value
        self.insert_stack_check = insert_stack_check
        self._propagate_exception = propagate_exception

    PROPAGATE_EXCEPTION = lltype.Ptr(lltype.FuncType([], llmemory.GCREF))

    def get_propagate_exception(self):
        return llhelper(self.PROPAGATE_EXCEPTION, self._propagate_exception)

    def grab_exc_value(self, deadframe):
        XXX
        deadframe = lltype.cast_opaque_ptr(jitframe.DEADFRAMEPTR, deadframe)
        if not we_are_translated() and deadframe == self.deadframe_memoryerror:
            return "memoryerror!"       # for tests
        return deadframe.jf_guard_exc

    def set_savedata_ref(self, deadframe, data):
        XXX
        deadframe = lltype.cast_opaque_ptr(jitframe.DEADFRAMEPTR, deadframe)
        deadframe.jf_savedata = data

    def get_savedata_ref(self, deadframe):
        XXXX
        deadframe = lltype.cast_opaque_ptr(jitframe.DEADFRAMEPTR, deadframe)
        return deadframe.jf_savedata

    def free_loop_and_bridges(self, compiled_loop_token):
        AbstractCPU.free_loop_and_bridges(self, compiled_loop_token)
        blocks = compiled_loop_token.asmmemmgr_blocks
        if blocks is not None:
            compiled_loop_token.asmmemmgr_blocks = None
            for rawstart, rawstop in blocks:
                self.gc_ll_descr.freeing_block(rawstart, rawstop)
                self.asmmemmgr.free(rawstart, rawstop)

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
        from pypy.jit.backend.llsupport import ffisupport
        return ffisupport.get_call_descr_dynamic(self, cif_description,
                                                 extrainfo)

    def _calldescr_dynamic_for_tests(self, atypes, rtype,
                                     abiname='FFI_DEFAULT_ABI'):
        from pypy.jit.backend.llsupport import ffisupport
        return ffisupport.calldescr_dynamic_for_tests(self, atypes, rtype,
                                                      abiname)

    def get_latest_descr(self, deadframe):
        XXX
        deadframe = lltype.cast_opaque_ptr(jitframe.DEADFRAMEPTR, deadframe)
        descr = deadframe.jf_descr
        return history.AbstractDescr.show(self, descr)

    def get_latest_value_int(self, deadframe, index):
        XXX
        deadframe = lltype.cast_opaque_ptr(jitframe.DEADFRAMEPTR, deadframe)
        return deadframe.jf_values[index].int

    def get_latest_value_ref(self, deadframe, index):
        XXX
        deadframe = lltype.cast_opaque_ptr(jitframe.DEADFRAMEPTR, deadframe)
        return deadframe.jf_values[index].ref

    def get_latest_value_float(self, deadframe, index):
        XXX
        deadframe = lltype.cast_opaque_ptr(jitframe.DEADFRAMEPTR, deadframe)
        return deadframe.jf_values[index].float

    def get_latest_value_count(self, deadframe):
        XXX
        deadframe = lltype.cast_opaque_ptr(jitframe.DEADFRAMEPTR, deadframe)
        return len(deadframe.jf_values)

    # ____________________________________________________________

    def bh_arraylen_gc(self, array, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        ofs = arraydescr.lendescr.offset
        return rffi.cast(rffi.CArrayPtr(lltype.Signed), array)[ofs/WORD]

    @specialize.argtype(1)
    def bh_getarrayitem_gc_i(self, gcref, itemindex, arraydescr):
        ofs, size, sign = self.unpack_arraydescr_size(arraydescr)
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        for STYPE, UTYPE, itemsize in unroll_basic_sizes:
            if size == itemsize:
                if sign:
                    items = rffi.cast(rffi.CArrayPtr(STYPE), items)
                    val = items[itemindex]
                    val = rffi.cast(lltype.Signed, val)
                else:
                    items = rffi.cast(rffi.CArrayPtr(UTYPE), items)
                    val = items[itemindex]
                    val = rffi.cast(lltype.Signed, val)
                # --- end of GC unsafe code ---
                return val
        else:
            raise NotImplementedError("size = %d" % size)

    def bh_getarrayitem_gc_r(self, gcref, itemindex, arraydescr):
        ofs = self.unpack_arraydescr(arraydescr)
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        items = rffi.cast(rffi.CArrayPtr(lltype.Signed), items)
        pval = self._cast_int_to_gcref(items[itemindex])
        # --- end of GC unsafe code ---
        return pval

    @specialize.argtype(1)
    def bh_getarrayitem_gc_f(self, gcref, itemindex, arraydescr):
        ofs = self.unpack_arraydescr(arraydescr)
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        items = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), items)
        fval = items[itemindex]
        # --- end of GC unsafe code ---
        return fval

    @specialize.argtype(1)
    def bh_setarrayitem_gc_i(self, gcref, itemindex, newvalue, arraydescr):
        ofs, size, sign = self.unpack_arraydescr_size(arraydescr)
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        for TYPE, _, itemsize in unroll_basic_sizes:
            if size == itemsize:
                items = rffi.cast(rffi.CArrayPtr(TYPE), items)
                items[itemindex] = rffi.cast(TYPE, newvalue)
                # --- end of GC unsafe code ---
                return
        else:
            raise NotImplementedError("size = %d" % size)

    def bh_setarrayitem_gc_r(self, gcref, itemindex, newvalue, arraydescr):
        ofs = self.unpack_arraydescr(arraydescr)
        self.gc_ll_descr.do_write_barrier(gcref, newvalue)
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        items = rffi.cast(rffi.CArrayPtr(lltype.Signed), items)
        items[itemindex] = self.cast_gcref_to_int(newvalue)
        # --- end of GC unsafe code ---

    @specialize.argtype(1)
    def bh_setarrayitem_gc_f(self, gcref, itemindex, newvalue, arraydescr):
        ofs = self.unpack_arraydescr(arraydescr)
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        items = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), items)
        items[itemindex] = newvalue
        # --- end of GC unsafe code ---

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
