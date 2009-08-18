import sys
import ctypes
import py
from pypy.rpython.lltypesystem import lltype, llmemory, ll2ctypes, rffi, rstr
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.objectmodel import CDefinedIntSymbolic, specialize, Symbolic
from pypy.rlib.objectmodel import we_are_translated, keepalive_until_here
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import rclass
from pypy.jit.metainterp import history, codewriter
from pypy.jit.metainterp.history import (ResOperation, Box, Const,
     ConstInt, ConstPtr, BoxInt, BoxPtr, ConstAddr, AbstractDescr)
from pypy.jit.backend.x86.assembler import Assembler386, WORD, MAX_FAIL_BOXES
from pypy.jit.backend.x86 import symbolic
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.rlib.objectmodel import r_dict

history.TreeLoop._x86_compiled = 0
history.TreeLoop._x86_bootstrap_code = 0

class ConstDescr3(AbstractDescr):
    call_loop = None
    
    def __init__(self, v0, v1, flag2):
        self.v0 = v0
        self.v1 = v1
        self.flag2 = flag2

    def _v(self):
        l = []
        for i in (self.v0, self.v1, self.flag2):
            if isinstance(i, Symbolic):
                l.append(id(i))
            else:
                l.append(i)
        return tuple(l)

    def sort_key(self):
        return self.v0    # the ofs field for fielddescrs

    def is_pointer_field(self):
        return self.flag2     # for fielddescrs

    def is_array_of_pointers(self):
        return self.flag2     # for arraydescrs

    def equals(self, other):
        if not isinstance(other, ConstDescr3):
            return False
        return self.sort_key() == other.sort_key()

    def __repr__(self):
        return '<ConstDescr3 %s, %s, %s>' % (self.v0, self.v1, self.flag2)


def _check_addr_range(x):
    if sys.platform == 'linux2':
        # this makes assumption about address ranges that are valid
        # only on linux (?)
        assert x == 0 or x > (1<<20) or x < (-1<<20)        

class CPU386(object):
    debug = True
    is_oo = False

    BOOTSTRAP_TP = lltype.FuncType([], lltype.Signed)

    def __init__(self, rtyper, stats, translate_support_code=False,
                 mixlevelann=None, gcdescr=None):
        from pypy.jit.backend.x86.gc import get_ll_description
        self.rtyper = rtyper
        self.stats = stats
        self.translate_support_code = translate_support_code
        if translate_support_code:
            assert mixlevelann
            self.mixlevelann = mixlevelann
        else:
            self.current_interpreter = LLInterpreter(self.rtyper)

            def _store_exception(lle):
                tp_i = self.cast_ptr_to_int(lle.args[0])
                v_i = self.cast_gcref_to_int(lle.args[1])
                self.assembler._exception_data[0] = tp_i
                self.assembler._exception_data[1] = v_i
            
            self.current_interpreter._store_exception = _store_exception
        TP = lltype.GcArray(llmemory.GCREF)
        self._bootstrap_cache = {}
        self._guard_list = []
        self._compiled_ops = {}
        self._builtin_implementations = {}
        self.setup()
        self.caught_exception = None
        if rtyper is not None: # for tests
            self.lltype2vtable = rtyper.lltype_to_vtable_mapping()
        self._setup_prebuilt_error('ovf', OverflowError)
        self._setup_prebuilt_error('zer', ZeroDivisionError)
        self._descr_caches = {}
        self.gc_ll_descr = get_ll_description(gcdescr, self)
        self.vtable_offset, _ = symbolic.get_field_token(rclass.OBJECT,
                                                         'typeptr',
                                                        translate_support_code)

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
        setattr(self.assembler, '_%s_error_vtable' % prefix,
                llmemory.cast_ptr_to_adr(ll_inst.typeptr))
        setattr(self.assembler, '_%s_error_inst' % prefix,
                llmemory.cast_ptr_to_adr(ll_inst))

    def setup(self):
        self.assembler = Assembler386(self, self.translate_support_code)

    def setup_once(self):
        pass

    def get_exception(self):
        self.assembler.make_sure_mc_exists()
        return self.assembler._exception_bck[0]

    def get_exc_value(self):
        self.assembler.make_sure_mc_exists()
        return self.cast_int_to_gcref(self.assembler._exception_bck[1])

    def clear_exception(self):
        self.assembler.make_sure_mc_exists()
        self.assembler._exception_bck[0] = 0
        self.assembler._exception_bck[1] = 0

    def get_overflow_error(self):
        self.assembler.make_sure_mc_exists()
        ovf_vtable = self.cast_adr_to_int(self.assembler._ovf_error_vtable)
        ovf_inst = self.cast_int_to_gcref(
            self.cast_adr_to_int(self.assembler._ovf_error_inst))
        return ovf_vtable, ovf_inst

    def get_zero_division_error(self):
        self.assembler.make_sure_mc_exists()
        zer_vtable = self.cast_adr_to_int(self.assembler._zer_error_vtable)
        zer_inst = self.cast_int_to_gcref(
            self.cast_adr_to_int(self.assembler._zer_error_inst))
        return zer_vtable, zer_inst

    _overflow_flag = False

    def get_overflow_flag(self):
        return self._overflow_flag

    def set_overflow_flag(self, flag):
        self._overflow_flag = flag

    def compile_operations(self, tree, bridge=None):
        old_loop = tree._x86_compiled
        if old_loop:
            olddepth = tree._x86_stack_depth
            oldlocs = tree.arglocs
        else:
            oldlocs = None
            olddepth = 0
        stack_depth = self.assembler.assemble(tree)
        newlocs = tree.arglocs
        if old_loop != 0:
            self.assembler.patch_jump(old_loop, tree._x86_compiled,
                                      oldlocs, newlocs, olddepth,
                                      tree._x86_stack_depth)

    def get_bootstrap_code(self, loop):
        addr = loop._x86_bootstrap_code
        if not addr:
            arglocs = loop.arglocs
            addr = self.assembler.assemble_bootstrap_code(loop._x86_compiled,
                                                          arglocs,
                                                          loop.inputargs,
                                                          loop._x86_stack_depth)
            loop._x86_bootstrap_code = addr
        func = rffi.cast(lltype.Ptr(self.BOOTSTRAP_TP), addr)
        return func

    def _new_box(self, ptr):
        if ptr:
            return BoxPtr(lltype.nullptr(llmemory.GCREF.TO))
        return BoxInt(0)
    
    def _get_loop_for_call(self, args, calldescr, ptr):
        if calldescr.call_loop is not None:
            if not we_are_translated():
                assert (calldescr.shape ==
                        ([arg.type == history.PTR for arg in args[1:]], ptr))
            return calldescr.call_loop
        args = [arg.clonebox() for arg in args]
        result = self._new_box(ptr)
        operations = [
            ResOperation(rop.CALL, args, result, calldescr),
            ResOperation(rop.GUARD_NO_EXCEPTION, [], None),
            ResOperation(rop.FAIL, [result], None)]
        operations[1].suboperations = [ResOperation(rop.FAIL, [], None)]
        loop = history.TreeLoop('call')
        loop.inputargs = args
        loop.operations = operations
        self.compile_operations(loop)
        calldescr.call_loop = loop
        return loop

    def execute_operations(self, loop, verbose=False):
        assert isinstance(verbose, bool)
        func = self.get_bootstrap_code(loop)
        # debug info
        #if self.debug and not we_are_translated():
        #    values_repr = ", ".join([str(values_as_int[i]) for i in
        #                             range(len(valueboxes))])
        #    llop.debug_print(lltype.Void, 'exec:', name, values_repr)
        #self.assembler.logger.log_call(valueboxes) --- XXX
        guard_index = self.execute_call(loop, func, verbose)
        self._guard_index = guard_index # for tests
        op = self._guard_list[guard_index]
        if verbose:
            print "Leaving at: %d" % self.assembler.fail_boxes_int[
                len(op.args)]
        return op

    def set_future_value_int(self, index, intvalue):
        assert index < MAX_FAIL_BOXES, "overflow!"
        self.assembler.fail_boxes_int[index] = intvalue

    def set_future_value_ptr(self, index, ptrvalue):
        assert index < MAX_FAIL_BOXES, "overflow!"
        self.assembler.fail_boxes_ptr[index] = ptrvalue

    def get_latest_value_int(self, index):
        return self.assembler.fail_boxes_int[index]

    def get_latest_value_ptr(self, index):
        ptrvalue = self.assembler.fail_boxes_ptr[index]
        # clear after reading
        self.assembler.fail_boxes_ptr[index] = lltype.nullptr(
            llmemory.GCREF.TO)
        return ptrvalue

    def execute_call(self, loop, func, verbose):
        # help flow objspace
        prev_interpreter = None
        if not self.translate_support_code:
            prev_interpreter = LLInterpreter.current_interpreter
            LLInterpreter.current_interpreter = self.current_interpreter
        res = 0
        try:
            self.caught_exception = None
            if verbose:
                print "Entering: %d" % rffi.cast(lltype.Signed, func)
            #llop.debug_print(lltype.Void, ">>>> Entering",
            #                 rffi.cast(lltype.Signed, func))
            res = func()
            #llop.debug_print(lltype.Void, "<<<< Back")
            self.reraise_caught_exception()
        finally:
            if not self.translate_support_code:
                LLInterpreter.current_interpreter = prev_interpreter
        return res

    def reraise_caught_exception(self):
        # this helper is in its own function so that the call to it
        # shows up in traceback -- useful to avoid confusing tracebacks,
        # which are typical when using the 3-arguments raise.
        if self.caught_exception is not None:
            if not we_are_translated():
                exc, val, tb = self.caught_exception
                raise exc, val, tb
            else:
                exc = self.caught_exception
                raise exc

    def make_guard_index(self, guard_op):
        index = len(self._guard_list)
        self._guard_list.append(guard_op)
        return index

    def sizeof(self, S):
        try:
            return self._descr_caches['sizeof', S]
        except KeyError:
            pass
        descr = self.gc_ll_descr.sizeof(S, self.translate_support_code)
        self._descr_caches['sizeof', S] = descr
        return descr

    # ------------------- backend-specific ops ------------------------

    def do_arraylen_gc(self, args, arraydescr):
        ofs = self.gc_ll_descr.array_length_ofs
        gcref = args[0].getptr(llmemory.GCREF)
        length = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)[ofs/WORD]
        return BoxInt(length)

    def do_getarrayitem_gc(self, args, arraydescr):
        field = args[1].getint()
        gcref = args[0].getptr(llmemory.GCREF)
        shift, ofs, ptr = self.unpack_arraydescr(arraydescr)
        size = 1 << shift
        if size == 1:
            return BoxInt(ord(rffi.cast(rffi.CArrayPtr(lltype.Char), gcref)
                          [ofs + field]))
        elif size == WORD:
            val = (rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)
                   [ofs/WORD + field])
            if not ptr:
                return BoxInt(val)
            else:
                return BoxPtr(self.cast_int_to_gcref(val))
        else:
            raise NotImplementedError("size = %d" % size)

    def do_setarrayitem_gc(self, args, arraydescr):
        field = args[1].getint()
        gcref = args[0].getptr(llmemory.GCREF)
        shift, ofs, ptr = self.unpack_arraydescr(arraydescr)
        size = 1 << shift
        vbox = args[2]
        if size == 1:
            v = vbox.getint()
            rffi.cast(rffi.CArrayPtr(lltype.Char), gcref)[ofs + field] = chr(v)
        elif size == WORD:
            if not ptr:
                a = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)
                a[ofs/WORD + field] = vbox.getint()
            else:
                ptr = vbox.getptr(llmemory.GCREF)
                self.gc_ll_descr.do_write_barrier(gcref, ptr)
                a = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)
                a[ofs/WORD + field] = self.cast_gcref_to_int(ptr)
        else:
            raise NotImplementedError("size = %d" % size)

    def _new_do_len(TP):
        def do_strlen(self, args, descr=None):
            basesize, itemsize, ofs_length = symbolic.get_array_token(TP,
                                                self.translate_support_code)
            gcref = args[0].getptr(llmemory.GCREF)
            v = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)[ofs_length/WORD]
            return BoxInt(v)
        return do_strlen

    do_strlen = _new_do_len(rstr.STR)
    do_unicodelen = _new_do_len(rstr.UNICODE)

    def do_strgetitem(self, args, descr=None):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                    self.translate_support_code)
        gcref = args[0].getptr(llmemory.GCREF)
        i = args[1].getint()
        v = rffi.cast(rffi.CArrayPtr(lltype.Char), gcref)[basesize + i]
        return BoxInt(ord(v))

    def do_unicodegetitem(self, args, descr=None):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                                    self.translate_support_code)
        gcref = args[0].getptr(llmemory.GCREF)
        i = args[1].getint()
        basesize = basesize // itemsize
        v = rffi.cast(rffi.CArrayPtr(lltype.UniChar), gcref)[basesize + i]
        return BoxInt(ord(v))

    @specialize.argtype(1)
    def _base_do_getfield(self, gcref, fielddescr):
        ofs, size, ptr = self.unpack_fielddescr(fielddescr)
        if size == 1:
            v = ord(rffi.cast(rffi.CArrayPtr(lltype.Char), gcref)[ofs])
        elif size == 2:
            v = rffi.cast(rffi.CArrayPtr(rffi.USHORT), gcref)[ofs/2]
            v = rffi.cast(lltype.Signed, v)
        elif size == WORD:
            v = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)[ofs/WORD]
            if ptr:
                return BoxPtr(self.cast_int_to_gcref(v))
        else:
            raise NotImplementedError("size = %d" % size)
        return BoxInt(v)

    def do_getfield_gc(self, args, fielddescr):
        gcref = args[0].getptr(llmemory.GCREF)
        return self._base_do_getfield(gcref, fielddescr)

    def do_getfield_raw(self, args, fielddescr):
        return self._base_do_getfield(args[0].getint(), fielddescr)

    @specialize.argtype(2)
    def _base_do_setfield(self, fielddescr, gcref, vbox):
        ofs, size, ptr = self.unpack_fielddescr(fielddescr)
        if size == 1:
            v = vbox.getint()
            rffi.cast(rffi.CArrayPtr(lltype.Char), gcref)[ofs] = chr(v)
        elif size == 2:
            v = rffi.cast(rffi.USHORT, vbox.getint())
            rffi.cast(rffi.CArrayPtr(rffi.USHORT), gcref)[ofs/2] = v
        elif size == WORD:
            if ptr:
                assert lltype.typeOf(gcref) is not lltype.Signed, (
                    "can't handle write barriers for setfield_raw")
                ptr = vbox.getptr(llmemory.GCREF)
                self.gc_ll_descr.do_write_barrier(gcref, ptr)
                a = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)
                a[ofs/WORD] = self.cast_gcref_to_int(ptr)
            else:
                a = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)
                a[ofs/WORD] = vbox.getint()
        else:
            raise NotImplementedError("size = %d" % size)

    def do_setfield_gc(self, args, fielddescr):
        gcref = args[0].getptr(llmemory.GCREF)
        self._base_do_setfield(fielddescr, gcref, args[1])

    def do_setfield_raw(self, args, fielddescr):
        self._base_do_setfield(fielddescr, args[0].getint(), args[1])

    def do_new(self, args, descrsize):
        res = self.gc_ll_descr.gc_malloc(descrsize)
        return BoxPtr(res)

    def do_new_with_vtable(self, args, descr=None):
        assert descr is None
        classint = args[0].getint()
        descrsize = self.class_sizes[classint]
        res = self.gc_ll_descr.gc_malloc(descrsize)
        as_array = rffi.cast(rffi.CArrayPtr(lltype.Signed), res)
        as_array[self.vtable_offset/WORD] = classint
        return BoxPtr(res)

    def do_new_array(self, args, arraydescr):
        num_elem = args[0].getint()
        res = self.gc_ll_descr.gc_malloc_array(arraydescr, num_elem)
        return BoxPtr(self.cast_adr_to_gcref(res))

    def do_newstr(self, args, descr=None):
        num_elem = args[0].getint()
        tsc = self.translate_support_code
        res = self.gc_ll_descr.gc_malloc_str(num_elem, tsc)
        return BoxPtr(self.cast_adr_to_gcref(res))

    def do_newunicode(self, args, descr=None):
        num_elem = args[0].getint()
        tsc = self.translate_support_code
        res = self.gc_ll_descr.gc_malloc_unicode(num_elem, tsc)
        return BoxPtr(self.cast_adr_to_gcref(res))

    def do_strsetitem(self, args, descr=None):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                self.translate_support_code)
        index = args[1].getint()
        v = args[2].getint()
        a = args[0].getptr(llmemory.GCREF)
        rffi.cast(rffi.CArrayPtr(lltype.Char), a)[index + basesize] = chr(v)

    def do_unicodesetitem(self, args, descr=None):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                                self.translate_support_code)
        index = args[1].getint()
        v = args[2].getint()
        a = args[0].getptr(llmemory.GCREF)
        basesize = basesize // itemsize
        rffi.cast(rffi.CArrayPtr(lltype.UniChar), a)[index + basesize] = unichr(v)

    def do_call(self, args, calldescr):
        assert isinstance(calldescr, ConstDescr3)
        num_args, size, ptr = self.unpack_calldescr(calldescr)
        assert num_args == len(args) - 1
        loop = self._get_loop_for_call(args, calldescr, ptr)
        history.set_future_values(self, args)
        self.execute_operations(loop, verbose=False)
        # Note: if an exception is set, the rest of the code does a bit of
        # nonsense but nothing wrong (the return value should be ignored)
        if size == 0:
            return None
        elif ptr:
            return BoxPtr(self.get_latest_value_ptr(0))
        else:
            return BoxInt(self.get_latest_value_int(0))

    def do_cast_ptr_to_int(self, args, descr=None):
        return BoxInt(self.cast_gcref_to_int(args[0].getptr_base()))

    def do_cast_int_to_ptr(self, args, descr=None):
        return BoxPtr(self.cast_int_to_gcref(args[0].getint()))

    # ------------------- helpers and descriptions --------------------

    @staticmethod
    def cast_adr_to_int(x):
        res = rffi.cast(lltype.Signed, x)
        return res

    @staticmethod
    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return CPU386.cast_adr_to_int(adr)

    def arraydescrof(self, A):
        try:
            return self._descr_caches['array', A]
        except KeyError:
            pass
        assert isinstance(A, lltype.GcArray)
        descr = self.gc_ll_descr.arraydescrof(A, self.translate_support_code)
        self._descr_caches['array', A] = descr
        return descr

    @staticmethod
    def unpack_arraydescr(arraydescr):
        assert isinstance(arraydescr, ConstDescr3)
        basesize = arraydescr.v0
        itemsize = arraydescr.v1
        ptr = arraydescr.flag2
        counter = 0
        while itemsize != 1:
            itemsize >>= 1
            counter += 1
        return counter, basesize, ptr

    @staticmethod
    def _is_ptr(TP):
        if isinstance(TP, lltype.Ptr) and TP.TO._gckind == 'gc':
            return True
        else:
            return False

    def calldescrof(self, functype, argtypes, resulttype):
        cachekey = ('call', functype, tuple(argtypes), resulttype)
        try:
            return self._descr_caches[cachekey]
        except KeyError:
            pass
        for argtype in argtypes:
            if rffi.sizeof(argtype) > WORD:
                raise NotImplementedError("bigger than lltype.Signed")
        if resulttype is not lltype.Void and rffi.sizeof(resulttype) > WORD:
            raise NotImplementedError("bigger than lltype.Signed")
        if resulttype is lltype.Void:
            size = 0
        else:
            size = symbolic.get_size(resulttype, self.translate_support_code)
        ptr = self._is_ptr(resulttype)
        descr = ConstDescr3(len(argtypes), size, ptr)
        shape = ([self._is_ptr(arg) for arg in argtypes], ptr)
        self._descr_caches[cachekey] = descr
        descr.shape = shape
        return descr

    @staticmethod
    def unpack_calldescr(calldescr):
        assert isinstance(calldescr, ConstDescr3)
        return calldescr.v0, calldescr.v1, calldescr.flag2

    def fielddescrof(self, S, fieldname):
        try:
            return self._descr_caches['field', S, fieldname]
        except KeyError:
            pass
        ofs, size = symbolic.get_field_token(S, fieldname,
                                             self.translate_support_code)
        assert rffi.sizeof(getattr(S, fieldname)) in [1, 2, WORD]
        if (isinstance(getattr(S, fieldname), lltype.Ptr) and
            getattr(S, fieldname).TO._gckind == 'gc'):
            ptr = True
        else:
            ptr = False
        descr = ConstDescr3(ofs, size, ptr)
        self._descr_caches['field', S, fieldname] = descr
        return descr

    @staticmethod
    def unpack_fielddescr(fielddescr):
        assert isinstance(fielddescr, ConstDescr3)
        return fielddescr.v0, fielddescr.v1, fielddescr.flag2

    @staticmethod
    def cast_int_to_adr(x):
        if not we_are_translated():
            _check_addr_range(x)
        if we_are_translated():
            return rffi.cast(llmemory.Address, x)
        else:
            # indirect casting because the above doesn't work with ll2ctypes
            return llmemory.cast_ptr_to_adr(rffi.cast(llmemory.GCREF, x))

    def cast_gcref_to_int(self, x):
        return rffi.cast(lltype.Signed, x)

    def cast_int_to_gcref(self, x):
        if not we_are_translated():
            _check_addr_range(x)
        return rffi.cast(llmemory.GCREF, x)

    def cast_adr_to_gcref(self, x):
        if not we_are_translated():
            _check_addr_range(x)
        return rffi.cast(llmemory.GCREF, x)

def uhex(x):
    if we_are_translated():
        return hex(x)
    else:
        if x < 0:
            x += 0x100000000
        return hex(x)

CPU = CPU386

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(CPU)
