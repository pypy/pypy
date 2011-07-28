import sys
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass, rstr
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.llinterp import LLInterpreter, LLException
from pypy.rpython.annlowlevel import llhelper
from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.jit.metainterp.history import BoxInt, BoxPtr, set_future_values,\
     BoxFloat
from pypy.jit.metainterp import history
from pypy.jit.codewriter import heaptracker, longlong
from pypy.jit.backend.model import AbstractCPU
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.llsupport.symbolic import WORD, unroll_basic_sizes
from pypy.jit.backend.llsupport.descr import get_size_descr,  BaseSizeDescr
from pypy.jit.backend.llsupport.descr import get_field_descr, BaseFieldDescr
from pypy.jit.backend.llsupport.descr import get_array_descr, BaseArrayDescr
from pypy.jit.backend.llsupport.descr import get_call_descr
from pypy.jit.backend.llsupport.descr import BaseIntCallDescr, GcPtrCallDescr
from pypy.jit.backend.llsupport.descr import FloatCallDescr, VoidCallDescr
from pypy.jit.backend.llsupport.asmmemmgr import AsmMemoryManager
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr


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
        if translate_support_code:
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
        self._setup_prebuilt_error('ovf', OverflowError)
        self._setup_prebuilt_error('zer', ZeroDivisionError)
        if translate_support_code:
            self._setup_exception_handling_translated()
        else:
            self._setup_exception_handling_untranslated()
        self.saved_exc_value = lltype.nullptr(llmemory.GCREF.TO)
        self.asmmemmgr = AsmMemoryManager()
        self.setup()
        if translate_support_code:
            self._setup_on_leave_jitted_translated()
        else:
            self._setup_on_leave_jitted_untranslated()

    def setup(self):
        pass

    def _setup_prebuilt_error(self, prefix, Class):
        if self.rtyper is not None:   # normal case
            bk = self.rtyper.annotator.bookkeeper
            clsdef = bk.getuniqueclassdef(Class)
            ll_inst = self.rtyper.exceptiondata.get_standard_ll_exc_instance(
                self.rtyper, clsdef)
        else:
            # for tests, a random emulated ll_inst will do
            ll_inst = lltype.malloc(rclass.OBJECT)
            ll_inst.typeptr = lltype.malloc(rclass.OBJECT_VTABLE,
                                            immortal=True)
        setattr(self, '_%s_error_vtable' % prefix,
                llmemory.cast_ptr_to_adr(ll_inst.typeptr))
        setattr(self, '_%s_error_inst' % prefix, ll_inst)


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

        def save_exception():
            # copy from _exception_emulator to the real attributes on self
            v_i = _exception_emulator[1]
            _exception_emulator[0] = 0
            _exception_emulator[1] = 0
            self.saved_exc_value = rffi.cast(llmemory.GCREF, v_i)

        self.pos_exception = pos_exception
        self.pos_exc_value = pos_exc_value
        self.save_exception = save_exception
        self.insert_stack_check = lambda: (0, 0, 0)


    def _setup_exception_handling_translated(self):

        def pos_exception():
            addr = llop.get_exception_addr(llmemory.Address)
            return heaptracker.adr2int(addr)

        def pos_exc_value():
            addr = llop.get_exc_value_addr(llmemory.Address)
            return heaptracker.adr2int(addr)

        def save_exception():
            addr = llop.get_exception_addr(llmemory.Address)
            addr.address[0] = llmemory.NULL
            addr = llop.get_exc_value_addr(llmemory.Address)
            exc_value = rffi.cast(llmemory.GCREF, addr.address[0])
            addr.address[0] = llmemory.NULL
            # from now on, the state is again consistent -- no more RPython
            # exception is set.  The following code produces a write barrier
            # in the assignment to self.saved_exc_value, as needed.
            self.saved_exc_value = exc_value

        from pypy.rlib import rstack
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
        self.save_exception = save_exception
        self.insert_stack_check = insert_stack_check

    def _setup_on_leave_jitted_untranslated(self):
        # assume we don't need a backend leave in this case
        self.on_leave_jitted_save_exc = self.save_exception
        self.on_leave_jitted_noexc = lambda : None

    def _setup_on_leave_jitted_translated(self):
        on_leave_jitted_hook = self.get_on_leave_jitted_hook()
        save_exception = self.save_exception

        def on_leave_jitted_noexc():
            on_leave_jitted_hook()

        def on_leave_jitted_save_exc():
            save_exception()
            on_leave_jitted_hook()

        self.on_leave_jitted_noexc = on_leave_jitted_noexc
        self.on_leave_jitted_save_exc = on_leave_jitted_save_exc

    def get_on_leave_jitted_hook(self):
        return lambda : None

    _ON_JIT_LEAVE_FUNC = lltype.Ptr(lltype.FuncType([], lltype.Void))

    def get_on_leave_jitted_int(self, save_exception):
        if save_exception:
            f = llhelper(self._ON_JIT_LEAVE_FUNC, self.on_leave_jitted_save_exc)
        else:
            f = llhelper(self._ON_JIT_LEAVE_FUNC, self.on_leave_jitted_noexc)
        return rffi.cast(lltype.Signed, f)

    def grab_exc_value(self):
        exc = self.saved_exc_value
        self.saved_exc_value = lltype.nullptr(llmemory.GCREF.TO)
        return exc

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
        assert isinstance(fielddescr, BaseFieldDescr)
        return fielddescr.offset
    unpack_fielddescr._always_inline_ = True

    def unpack_fielddescr_size(self, fielddescr):
        assert isinstance(fielddescr, BaseFieldDescr)
        ofs = fielddescr.offset
        size = fielddescr.get_field_size(self.translate_support_code)
        sign = fielddescr.is_field_signed()
        return ofs, size, sign
    unpack_fielddescr_size._always_inline_ = True

    def arraydescrof(self, A):
        return get_array_descr(self.gc_ll_descr, A)

    def unpack_arraydescr(self, arraydescr):
        assert isinstance(arraydescr, BaseArrayDescr)
        return arraydescr.get_base_size(self.translate_support_code)
    unpack_arraydescr._always_inline_ = True

    def unpack_arraydescr_size(self, arraydescr):
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs = arraydescr.get_base_size(self.translate_support_code)
        size = arraydescr.get_item_size(self.translate_support_code)
        sign = arraydescr.is_item_signed()
        return ofs, size, sign
    unpack_arraydescr_size._always_inline_ = True

    def calldescrof(self, FUNC, ARGS, RESULT, extrainfo=None):
        return get_call_descr(self.gc_ll_descr, ARGS, RESULT, extrainfo)

    def calldescrof_dynamic(self, ffi_args, ffi_result, extrainfo=None):
        from pypy.jit.backend.llsupport import ffisupport
        return ffisupport.get_call_descr_dynamic(ffi_args, ffi_result,
                                                 extrainfo)

    def get_overflow_error(self):
        ovf_vtable = self.cast_adr_to_int(self._ovf_error_vtable)
        ovf_inst = lltype.cast_opaque_ptr(llmemory.GCREF,
                                          self._ovf_error_inst)
        return ovf_vtable, ovf_inst

    def get_zero_division_error(self):
        zer_vtable = self.cast_adr_to_int(self._zer_error_vtable)
        zer_inst = lltype.cast_opaque_ptr(llmemory.GCREF,
                                          self._zer_error_inst)
        return zer_vtable, zer_inst

    # ____________________________________________________________

    def bh_arraylen_gc(self, arraydescr, array):
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs = arraydescr.get_ofs_length(self.translate_support_code)
        return rffi.cast(rffi.CArrayPtr(lltype.Signed), array)[ofs/WORD]

    @specialize.argtype(2)
    def bh_getarrayitem_gc_i(self, arraydescr, gcref, itemindex):
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

    def bh_getarrayitem_gc_r(self, arraydescr, gcref, itemindex):
        ofs = self.unpack_arraydescr(arraydescr)
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        items = rffi.cast(rffi.CArrayPtr(lltype.Signed), items)
        pval = self._cast_int_to_gcref(items[itemindex])
        # --- end of GC unsafe code ---
        return pval

    @specialize.argtype(2)
    def bh_getarrayitem_gc_f(self, arraydescr, gcref, itemindex):
        ofs = self.unpack_arraydescr(arraydescr)
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        items = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), items)
        fval = items[itemindex]
        # --- end of GC unsafe code ---
        return fval

    @specialize.argtype(2)
    def bh_setarrayitem_gc_i(self, arraydescr, gcref, itemindex, newvalue):
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

    def bh_setarrayitem_gc_r(self, arraydescr, gcref, itemindex, newvalue):
        ofs = self.unpack_arraydescr(arraydescr)
        self.gc_ll_descr.do_write_barrier(gcref, newvalue)
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        items = rffi.cast(rffi.CArrayPtr(lltype.Signed), items)
        items[itemindex] = self.cast_gcref_to_int(newvalue)
        # --- end of GC unsafe code ---

    @specialize.argtype(2)
    def bh_setarrayitem_gc_f(self, arraydescr, gcref, itemindex, newvalue):
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
    def _base_do_setfield_i(self, struct, fielddescr, newvalue):
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
    def _base_do_setfield_r(self, struct, fielddescr, newvalue):
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
    def _base_do_setfield_f(self, struct, fielddescr, newvalue):
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

    def bh_new(self, sizedescr):
        return self.gc_ll_descr.gc_malloc(sizedescr)

    def bh_new_with_vtable(self, sizedescr, vtable):
        res = self.gc_ll_descr.gc_malloc(sizedescr)
        if self.vtable_offset is not None:
            as_array = rffi.cast(rffi.CArrayPtr(lltype.Signed), res)
            as_array[self.vtable_offset/WORD] = vtable
        return res

    def bh_classof(self, struct):
        struct = lltype.cast_opaque_ptr(rclass.OBJECTPTR, struct)
        result = struct.typeptr
        result_adr = llmemory.cast_ptr_to_adr(struct.typeptr)
        return heaptracker.adr2int(result_adr)

    def bh_new_array(self, arraydescr, length):
        return self.gc_ll_descr.gc_malloc_array(arraydescr, length)

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

    def bh_call_i(self, func, calldescr, args_i, args_r, args_f):
        assert isinstance(calldescr, BaseIntCallDescr)
        if not we_are_translated():
            calldescr.verify_types(args_i, args_r, args_f, history.INT + 'S')
        return calldescr.call_stub(func, args_i, args_r, args_f)

    def bh_call_r(self, func, calldescr, args_i, args_r, args_f):
        assert isinstance(calldescr, GcPtrCallDescr)
        if not we_are_translated():
            calldescr.verify_types(args_i, args_r, args_f, history.REF)
        return calldescr.call_stub(func, args_i, args_r, args_f)

    def bh_call_f(self, func, calldescr, args_i, args_r, args_f):
        assert isinstance(calldescr, FloatCallDescr)  # or LongLongCallDescr
        if not we_are_translated():
            calldescr.verify_types(args_i, args_r, args_f, history.FLOAT + 'L')
        return calldescr.call_stub(func, args_i, args_r, args_f)

    def bh_call_v(self, func, calldescr, args_i, args_r, args_f):
        assert isinstance(calldescr, VoidCallDescr)
        if not we_are_translated():
            calldescr.verify_types(args_i, args_r, args_f, history.VOID)
        return calldescr.call_stub(func, args_i, args_r, args_f)
