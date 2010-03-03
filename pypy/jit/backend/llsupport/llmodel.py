import sys
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass, rstr
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.annlowlevel import llhelper
from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.jit.metainterp.history import BoxInt, BoxPtr, set_future_values,\
     BoxFloat
from pypy.jit.backend.model import AbstractCPU
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.llsupport.symbolic import WORD, unroll_basic_sizes
from pypy.jit.backend.llsupport.descr import get_size_descr,  BaseSizeDescr
from pypy.jit.backend.llsupport.descr import get_field_descr, BaseFieldDescr
from pypy.jit.backend.llsupport.descr import get_array_descr, BaseArrayDescr
from pypy.jit.backend.llsupport.descr import get_call_descr,  BaseCallDescr

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
        self.gc_ll_descr = get_ll_description(gcdescr, translator)
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
        self.clear_exception()
        self.setup()
        if translate_support_code:
            self._setup_on_leave_jitted_translated()
        else:
            self._setup_on_leave_jitted_untranslated()

    def setup(self):
        pass

    def set_class_sizes(self, class_sizes):
        self.class_sizes = class_sizes

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
                                            zero=True, flavor='raw')
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
            tp_i = _exception_emulator[0]
            v_i  = _exception_emulator[1]
            _exception_emulator[0] = 0
            _exception_emulator[1] = 0
            self.saved_exception = tp_i
            self.saved_exc_value = self._cast_int_to_gcref(v_i)

        self.pos_exception = pos_exception
        self.pos_exc_value = pos_exc_value
        self.save_exception = save_exception


    def _setup_exception_handling_translated(self):

        def pos_exception():
            addr = llop.get_exception_addr(llmemory.Address)
            return llmemory.cast_adr_to_int(addr)

        def pos_exc_value():
            addr = llop.get_exc_value_addr(llmemory.Address)
            return llmemory.cast_adr_to_int(addr)

        def save_exception():
            addr = llop.get_exception_addr(llmemory.Address)
            exception = rffi.cast(lltype.Signed, addr.address[0])
            addr.address[0] = llmemory.NULL
            addr = llop.get_exc_value_addr(llmemory.Address)
            exc_value = rffi.cast(llmemory.GCREF, addr.address[0])
            addr.address[0] = llmemory.NULL
            # from now on, the state is again consistent -- no more RPython
            # exception is set.  The following code produces a write barrier
            # in the assignment to self.saved_exc_value, as needed.
            self.saved_exception = exception
            self.saved_exc_value = exc_value

        self.pos_exception = pos_exception
        self.pos_exc_value = pos_exc_value
        self.save_exception = save_exception

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

    def get_exception(self):
        return self.saved_exception

    def get_exc_value(self):
        return self.saved_exc_value

    def clear_exception(self):
        self.saved_exception = 0
        self.saved_exc_value = lltype.nullptr(llmemory.GCREF.TO)


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
        ofs = fielddescr.offset
        size = fielddescr.get_field_size(self.translate_support_code)
        ptr = fielddescr.is_pointer_field()
        float = fielddescr.is_float_field()
        return ofs, size, ptr, float
    unpack_fielddescr._always_inline_ = True

    def arraydescrof(self, A):
        return get_array_descr(self.gc_ll_descr, A)

    def unpack_arraydescr(self, arraydescr):
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs = arraydescr.get_base_size(self.translate_support_code)
        size = arraydescr.get_item_size(self.translate_support_code)
        ptr = arraydescr.is_array_of_pointers()
        float = arraydescr.is_array_of_floats()
        return ofs, size, ptr, float
    unpack_arraydescr._always_inline_ = True

    def calldescrof(self, FUNC, ARGS, RESULT, extrainfo=None):
        return get_call_descr(self.gc_ll_descr, ARGS, RESULT, extrainfo)

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

    def do_arraylen_gc(self, arraybox, arraydescr):
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs = arraydescr.get_ofs_length(self.translate_support_code)
        gcref = arraybox.getref_base()
        length = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)[ofs/WORD]
        return BoxInt(length)

    def do_getarrayitem_gc(self, arraybox, indexbox, arraydescr):
        itemindex = indexbox.getint()
        gcref = arraybox.getref_base()
        ofs, size, ptr, float = self.unpack_arraydescr(arraydescr)
        # --- start of GC unsafe code (no GC operation!) ---
        items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        #
        if ptr:
            items = rffi.cast(rffi.CArrayPtr(lltype.Signed), items)
            pval = self._cast_int_to_gcref(items[itemindex])
            # --- end of GC unsafe code ---
            return BoxPtr(pval)
        #
        if float:
            items = rffi.cast(rffi.CArrayPtr(lltype.Float), items)
            fval = items[itemindex]
            # --- end of GC unsafe code ---
            return BoxFloat(fval)
        #
        for TYPE, itemsize in unroll_basic_sizes:
            if size == itemsize:
                items = rffi.cast(rffi.CArrayPtr(TYPE), items) 
                val = items[itemindex]
                # --- end of GC unsafe code ---
                return BoxInt(rffi.cast(lltype.Signed, val))
        else:
            raise NotImplementedError("size = %d" % size)

    def do_setarrayitem_gc(self, arraybox, indexbox, vbox, arraydescr):
        itemindex = indexbox.getint()
        gcref = arraybox.getref_base()
        ofs, size, ptr, float = self.unpack_arraydescr(arraydescr)
        #
        if ptr:
            vboxptr = vbox.getref_base()
            self.gc_ll_descr.do_write_barrier(gcref, vboxptr)
            # --- start of GC unsafe code (no GC operation!) ---
            items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
            items = rffi.cast(rffi.CArrayPtr(lltype.Signed), items)
            items[itemindex] = self.cast_gcref_to_int(vboxptr)
            # --- end of GC unsafe code ---
            return
        #
        if float:
            fval = vbox.getfloat()
            # --- start of GC unsafe code (no GC operation!) ---
            items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
            items = rffi.cast(rffi.CArrayPtr(lltype.Float), items)
            items[itemindex] = fval
            # --- end of GC unsafe code ---
            return
        #
        val = vbox.getint()
        for TYPE, itemsize in unroll_basic_sizes:
            if size == itemsize:
                # --- start of GC unsafe code (no GC operation!) ---
                items = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
                items = rffi.cast(rffi.CArrayPtr(TYPE), items)
                items[itemindex] = rffi.cast(TYPE, val)
                # --- end of GC unsafe code ---
                return
        else:
            raise NotImplementedError("size = %d" % size)

    def _new_do_len(TP):
        def do_strlen(self, stringbox):
            basesize, itemsize, ofs_length = symbolic.get_array_token(TP,
                                                self.translate_support_code)
            gcref = stringbox.getref_base()
            v = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)[ofs_length/WORD]
            return BoxInt(v)
        return do_strlen

    do_strlen = _new_do_len(rstr.STR)
    do_unicodelen = _new_do_len(rstr.UNICODE)

    def do_strgetitem(self, stringbox, indexbox):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                    self.translate_support_code)
        gcref = stringbox.getref_base()
        i = indexbox.getint()
        v = rffi.cast(rffi.CArrayPtr(lltype.Char), gcref)[basesize + i]
        return BoxInt(ord(v))

    def do_unicodegetitem(self, stringbox, indexbox):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                                    self.translate_support_code)
        gcref = stringbox.getref_base()
        i = indexbox.getint()
        basesize = basesize // itemsize
        v = rffi.cast(rffi.CArrayPtr(lltype.UniChar), gcref)[basesize + i]
        return BoxInt(ord(v))

    @specialize.argtype(1)
    def _base_do_getfield(self, gcref, fielddescr):
        ofs, size, ptr, float = self.unpack_fielddescr(fielddescr)
        # --- start of GC unsafe code (no GC operation!) ---
        field = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
        #
        if ptr:
            pval = rffi.cast(rffi.CArrayPtr(lltype.Signed), field)[0]
            pval = self._cast_int_to_gcref(pval)
            # --- end of GC unsafe code ---
            return BoxPtr(pval)
        #
        if float:
            fval = rffi.cast(rffi.CArrayPtr(lltype.Float), field)[0]
            # --- end of GC unsafe code ---
            return BoxFloat(fval)
        #
        for TYPE, itemsize in unroll_basic_sizes:
            if size == itemsize:
                val = rffi.cast(rffi.CArrayPtr(TYPE), field)[0]
                # --- end of GC unsafe code ---
                val = rffi.cast(lltype.Signed, val)
                return BoxInt(val)
        else:
            raise NotImplementedError("size = %d" % size)

    def do_getfield_gc(self, structbox, fielddescr):
        gcref = structbox.getref_base()
        return self._base_do_getfield(gcref, fielddescr)

    def do_getfield_raw(self, structbox, fielddescr):
        return self._base_do_getfield(structbox.getint(), fielddescr)

    @specialize.argtype(1)
    def _base_do_setfield(self, gcref, vbox, fielddescr):
        ofs, size, ptr, float = self.unpack_fielddescr(fielddescr)
        #
        if ptr:
            assert lltype.typeOf(gcref) is not lltype.Signed, (
                "can't handle write barriers for setfield_raw")
            ptr = vbox.getref_base()
            self.gc_ll_descr.do_write_barrier(gcref, ptr)
            # --- start of GC unsafe code (no GC operation!) ---
            field = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
            field = rffi.cast(rffi.CArrayPtr(lltype.Signed), field)
            field[0] = self.cast_gcref_to_int(ptr)
            # --- end of GC unsafe code ---
            return
        #
        if float:
            fval = vbox.getfloat()
            # --- start of GC unsafe code (no GC operation!) ---
            field = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
            field = rffi.cast(rffi.CArrayPtr(lltype.Float), field)
            field[0] = fval
            # --- end of GC unsafe code ---
            return
        #
        val = vbox.getint()
        for TYPE, itemsize in unroll_basic_sizes:
            if size == itemsize:
                # --- start of GC unsafe code (no GC operation!) ---
                field = rffi.ptradd(rffi.cast(rffi.CCHARP, gcref), ofs)
                field = rffi.cast(rffi.CArrayPtr(TYPE), field)
                field[0] = rffi.cast(TYPE, val)
                # --- end of GC unsafe code ---
                return
        else:
            raise NotImplementedError("size = %d" % size)

    def do_setfield_gc(self, structbox, vbox, fielddescr):
        gcref = structbox.getref_base()
        self._base_do_setfield(gcref, vbox, fielddescr)

    def do_setfield_raw(self, structbox, vbox, fielddescr):
        self._base_do_setfield(structbox.getint(), vbox, fielddescr)

    def do_new(self, sizedescr):
        res = self.gc_ll_descr.gc_malloc(sizedescr)
        return BoxPtr(res)

    def do_new_with_vtable(self, classbox):
        classint = classbox.getint()
        descrsize = self.class_sizes[classint]
        res = self.gc_ll_descr.gc_malloc(descrsize)
        if self.vtable_offset is not None:
            as_array = rffi.cast(rffi.CArrayPtr(lltype.Signed), res)
            as_array[self.vtable_offset/WORD] = classint
        return BoxPtr(res)

    def do_new_array(self, countbox, arraydescr):
        num_elem = countbox.getint()
        res = self.gc_ll_descr.gc_malloc_array(arraydescr, num_elem)
        return BoxPtr(res)

    def do_newstr(self, countbox):
        num_elem = countbox.getint()
        res = self.gc_ll_descr.gc_malloc_str(num_elem)
        return BoxPtr(res)

    def do_newunicode(self, countbox):
        num_elem = countbox.getint()
        res = self.gc_ll_descr.gc_malloc_unicode(num_elem)
        return BoxPtr(res)

    def do_strsetitem(self, stringbox, indexbox, vbox):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                self.translate_support_code)
        index = indexbox.getint()
        v = vbox.getint()
        a = stringbox.getref_base()
        rffi.cast(rffi.CArrayPtr(lltype.Char), a)[index + basesize] = chr(v)

    def do_unicodesetitem(self, stringbox, indexbox, vbox):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                                self.translate_support_code)
        index = indexbox.getint()
        v = vbox.getint()
        a = stringbox.getref_base()
        basesize = basesize // itemsize
        rffi.cast(rffi.CArrayPtr(lltype.UniChar), a)[index + basesize] = unichr(v)

    def do_call(self, args, calldescr):
        assert isinstance(calldescr, BaseCallDescr)
        assert len(args) == 1 + len(calldescr.arg_classes)
        if not we_are_translated():
            assert (list(calldescr.arg_classes) ==
                    [arg.type for arg in args[1:]])
        loop_token = calldescr.get_token_for_call(self)
        set_future_values(self, args)
        self.execute_token(loop_token)
        # Note: if an exception is set, the rest of the code does a bit of
        # nonsense but nothing wrong (the return value should be ignored)
        if calldescr.returns_a_pointer():
            return BoxPtr(self.get_latest_value_ref(0))
        elif calldescr.returns_a_float():
            return BoxFloat(self.get_latest_value_float(0))
        elif calldescr.get_result_size(self.translate_support_code) > 0:
            return BoxInt(self.get_latest_value_int(0))
        else:
            return None

    def do_cast_ptr_to_int(self, ptrbox):
        return BoxInt(self.cast_gcref_to_int(ptrbox.getref_base()))


import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(AbstractLLCPU)
