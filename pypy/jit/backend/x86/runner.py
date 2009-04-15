import sys
import ctypes
import py
from pypy.rpython.lltypesystem import lltype, llmemory, ll2ctypes, rffi, rstr
from pypy.rpython.llinterp import LLInterpreter, LLException
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.objectmodel import CDefinedIntSymbolic, specialize, Symbolic
from pypy.rlib.objectmodel import we_are_translated, keepalive_until_here
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import rclass
from pypy.jit.metainterp import history, codewriter
from pypy.jit.metainterp.history import (ResOperation, Box, Const,
     ConstInt, ConstPtr, BoxInt, BoxPtr, ConstAddr, AbstractDescr)
from pypy.jit.backend.x86.assembler import Assembler386, WORD
from pypy.jit.backend.x86 import symbolic
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.jit.backend.x86.support import gc_malloc_fnaddr
from pypy.jit.metainterp.optimize import av_eq, av_hash
from pypy.rlib.objectmodel import r_dict

GC_MALLOC = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Signed))

VOID = 0
PTR = 1
INT = 2

history.TreeLoop._x86_compiled = 0

class ConstDescr3(AbstractDescr):
    def __init__(self, v):
        # XXX don't use a tuple! that's yet another indirection...
        self.v = v

    def _v(self):
        l = []
        for i in self.v:
            if isinstance(i, Symbolic):
                l.append(id(i))
            else:
                l.append(i)
        return tuple(l)

    def sort_key(self):
        return self.v[0]    # the ofs field for fielddescrs

    def equals(self, other):
        if not isinstance(other, ConstDescr3):
            return False
        return self.sort_key() == other.sort_key()

    def __hash__(self):
        return hash(self._v())

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._v() == other._v()

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return '<ConstDescr3 %r>' % (self.v,)

class CPU386(object):
    debug = True
    has_lltype = True
    has_ootype = False

    BOOTSTRAP_TP = lltype.FuncType([lltype.Ptr(rffi.CArray(lltype.Signed))],
                                   lltype.Signed)

    def __init__(self, rtyper, stats, translate_support_code=False,
                 mixlevelann=None):
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
        self.keepalives = []
        self.keepalives_index = 0
        self._bootstrap_cache = {}
        self._guard_list = []
        self._compiled_ops = {}
        self._builtin_implementations = {}
        self.setup()
        self.caught_exception = None
        if rtyper is not None: # for tests
            self.lltype2vtable = rtyper.lltype_to_vtable_mapping()
        self._setup_ovf_error()
        self.generated_mps = r_dict(av_eq, av_hash)

    def _setup_ovf_error(self):
        if self.rtyper is not None:   # normal case
            bk = self.rtyper.annotator.bookkeeper
            clsdef = bk.getuniqueclassdef(OverflowError)
            ovferror_repr = rclass.getclassrepr(self.rtyper, clsdef)
            ll_inst = self.rtyper.exceptiondata.get_standard_ll_exc_instance(
                self.rtyper, clsdef)
        else:
            # for tests, a random emulated ll_inst will do
            ll_inst = lltype.malloc(rclass.OBJECT)
            ll_inst.typeptr = lltype.malloc(rclass.OBJECT_VTABLE,
                                            immortal=True)
        self.assembler._ovf_error_vtable = llmemory.cast_ptr_to_adr(ll_inst.typeptr)
        self.assembler._ovf_error_inst   = llmemory.cast_ptr_to_adr(ll_inst)

    def setup(self):
        self.assembler = Assembler386(self, self.translate_support_code)
        # the generic assembler stub that just performs a return
#         if self.translate_support_code:
#             mixlevelann = self.mixlevelann
#             s_int = annmodel.SomeInteger()

#             #def failure_recovery_callback(guard_index, frame_addr):
#             #    return self.failure_recovery_callback(guard_index, frame_addr)

#             #fn = mixlevelann.delayedfunction(failure_recovery_callback,
#             #                                 [s_int, s_int], s_int)
#             #self.cfunc_failure_recovery = fn
#         else:
#             import ctypes
#             # the ctypes callback function that handles guard failures
#             fntype = ctypes.CFUNCTYPE(ctypes.c_long,
#                                       ctypes.c_long, ctypes.c_void_p)
#             self.cfunc_failure_recovery = fntype(self.failure_recovery_callback)
#             self.failure_recovery_func_addr = ctypes.cast(
#                         self.cfunc_failure_recovery, ctypes.c_void_p).value

#     def get_failure_recovery_func_addr(self):
#         if self.translate_support_code:
#             fn = self.cfunc_failure_recovery
#             return lltype.cast_ptr_to_int(fn)
#         else:
#             return self.failure_recovery_func_addr

#     def failure_recovery_callback(self, guard_index, frame_addr):
#         """This function is called back from the assembler code when
#         a not-yet-implemented path is followed.  It can either compile
#         the extra path and ask the assembler to jump to it, or ask
#         the assembler to exit the current function.
#         """
#         self.assembler.make_sure_mc_exists()
#         try:
#             del self.keepalives[self.keepalives_index:]
#             guard_op = self._guard_list[guard_index]
#             #if self.debug:
#             #    llop.debug_print(lltype.Void, '.. calling back from',
#             #                     guard_op, 'to the jit')
#             gf = GuardFailed(self, frame_addr, guard_op)
#             self.assembler.log_failure_recovery(gf, guard_index)
#             self.metainterp.handle_guard_failure(gf)
#             self.return_value_type = gf.return_value_type
#             #if self.debug:
#                 #if gf.return_addr == self.assembler.generic_return_addr:
#                 #    llop.debug_print(lltype.Void, 'continuing at generic return address')
#                 #else:
#                 #    llop.debug_print(lltype.Void, 'continuing at',
#                 #                     uhex(gf.return_addr))
#             return gf.return_addr
#         except Exception, e:
#             if not we_are_translated():
#                 self.caught_exception = sys.exc_info()
#             else:
#                 self.caught_exception = e
#             return self.assembler.generic_return_addr

    def set_meta_interp(self, metainterp):
        self.metainterp = metainterp

    def get_exception(self):
        self.assembler.make_sure_mc_exists()
        return self.assembler._exception_bck[0]

    def get_exc_value(self):
        self.assembler.make_sure_mc_exists()
        return self.cast_int_to_gcref(self.assembler._exception_bck[1])

    def clear_exception(self):
        self.assembler.make_sure_mc_exists()
        self.assembler._exception_bck[0] = 0

    def set_overflow_error(self):
        self.assembler.make_sure_mc_exists()
        ovf_vtable = self.cast_adr_to_int(self.assembler._ovf_error_vtable)
        ovf_inst = self.cast_adr_to_int(self.assembler._ovf_error_inst)
        self.assembler._exception_bck[0] = ovf_vtable
        self.assembler._exception_bck[1] = ovf_inst

    def compile_operations(self, tree):
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
        # key is locations of arguments
        key = loop._x86_compiled
        try:
            return self._bootstrap_cache[key]
        except KeyError:
            arglocs = loop.arglocs
            addr = self.assembler.assemble_bootstrap_code(loop._x86_compiled,
                                                          arglocs,
                                                          loop._x86_stack_depth)
            # passing arglist as the only arg
            func = rffi.cast(lltype.Ptr(self.BOOTSTRAP_TP), addr)
            self._bootstrap_cache[key] = func
            return func

    def get_box_value_as_int(self, box):
        if isinstance(box, BoxInt):
            return box.value
        elif isinstance(box, ConstInt):
            return box.value
        elif isinstance(box, BoxPtr):
            self.keepalives.append(box.value)
            return self.cast_gcref_to_int(box.value)
        elif isinstance(box, ConstPtr): 
            self.keepalives.append(box.value)
            return self.cast_gcref_to_int(box.value)
        elif isinstance(box, ConstAddr):
            return self.cast_adr_to_int(box.value)
        else:
            raise ValueError('get_box_value_as_int, wrong arg')

    def set_value_of_box(self, box, index, fail_boxes):
        if isinstance(box, BoxInt):
            box.value = fail_boxes[index]
        elif isinstance(box, BoxPtr):
            box.value = self.cast_int_to_gcref(fail_boxes[index])

    def _new_box(self, ptr):
        if ptr:
            return BoxPtr(lltype.nullptr(llmemory.GCREF.TO))
        return BoxInt(0)
    
    def _get_loop_for_call(self, argnum, calldescr, ptr):
        try:
            loop = self.generated_mps[calldescr]
            box = self._new_box(ptr)
            loop.operations[0].result = box
            loop.operations[-1].args[0] = box
            loop.operations[1].suboperations[0].args[0] = box
            return loop
        except KeyError:
            pass
        args = [BoxInt(0) for i in range(argnum + 1)]
        result = self._new_box(ptr)
        operations = [
            ResOperation(rop.CALL, args, result, calldescr),
            ResOperation(rop.GUARD_NO_EXCEPTION, [], None),
            ResOperation(rop.FAIL, [result], None)]
        operations[1].suboperations = [ResOperation(rop.FAIL, [result], None)]
        loop = history.TreeLoop('call')
        loop.inputargs = args
        loop.operations = operations
        self.compile_operations(loop)
        self.generated_mps[calldescr] = loop
        return loop

    def execute_operations(self, loop, valueboxes):
        func = self.get_bootstrap_code(loop)
        # turn all the values into integers
        TP = rffi.CArray(lltype.Signed)
        oldindex = self.keepalives_index
        values_as_int = lltype.malloc(TP, len(valueboxes), flavor='raw')
        for i in range(len(valueboxes)):
            box = valueboxes[i]
            v = self.get_box_value_as_int(box)
            values_as_int[i] = v
        # debug info
        #if self.debug and not we_are_translated():
        #    values_repr = ", ".join([str(values_as_int[i]) for i in
        #                             range(len(valueboxes))])
        #    llop.debug_print(lltype.Void, 'exec:', name, values_repr)
        self.assembler.log_call(valueboxes)
        self.keepalives_index = len(self.keepalives)
        guard_index = self.execute_call(loop, func, values_as_int)
        self._guard_index = guard_index # for tests
        keepalive_until_here(valueboxes)
        self.keepalives_index = oldindex
        del self.keepalives[oldindex:]
        if guard_index == -1:
            # special case for calls
            op = loop.operations[-1]
        else:
            op = self._guard_list[guard_index]
        for i in range(len(op.args)):
            box = op.args[i]
            self.set_value_of_box(box, i, self.assembler.fail_boxes)
        return op

    def execute_call(self, loop, func, values_as_int):
        # help flow objspace
        prev_interpreter = None
        if not self.translate_support_code:
            prev_interpreter = LLInterpreter.current_interpreter
            LLInterpreter.current_interpreter = self.current_interpreter
        res = 0
        try:
            self.caught_exception = None
            res = func(values_as_int)
            self.reraise_caught_exception()
        finally:
            if not self.translate_support_code:
                LLInterpreter.current_interpreter = prev_interpreter
            lltype.free(values_as_int, flavor='raw')
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

    def convert_box_to_int(self, valuebox):
        if isinstance(valuebox, ConstInt):
            return valuebox.value
        elif isinstance(valuebox, BoxInt):
            return valuebox.value
        elif isinstance(valuebox, BoxPtr):
            x = self.cast_gcref_to_int(valuebox.value)
            self.keepalives.append(valuebox.value)
            return x
        elif isinstance(valuebox, ConstPtr):
            x = self.cast_gcref_to_int(valuebox.value)
            self.keepalives.append(valuebox.value)
            return x
        else:
            raise ValueError(valuebox.type)

#     def getvaluebox(self, frameadr, guard_op, argindex):
#         # XXX that's plain stupid, do we care about the return value???
#         box = guard_op.liveboxes[argindex]
#         frame = getframe(frameadr)
#         pos = guard_op.stacklocs[argindex]
#         intvalue = frame[pos]
#         if isinstance(box, history.BoxInt):
#             return history.BoxInt(intvalue)
#         elif isinstance(box, history.BoxPtr):
#             return history.BoxPtr(self.cast_int_to_gcref(intvalue))
#         else:
#             raise AssertionError('getvalue: box = %s' % (box,))

#     def setvaluebox(self, frameadr, mp, argindex, valuebox):
#         frame = getframe(frameadr)
#         frame[mp.stacklocs[argindex]] = self.convert_box_to_int(valuebox)

    def sizeof(self, S):
        size = symbolic.get_size(S, self.translate_support_code)
        return ConstDescr3((size, 0, False))

    numof = sizeof
#    addresssuffix = str(symbolic.get_size(llmemory.Address))

#    def itemoffsetof(self, A):
#        basesize, itemsize, ofs_length = symbolic.get_array_token(A)
#        return basesize

#    def arraylengthoffset(self, A):
#        basesize, itemsize, ofs_length = symbolic.get_array_token(A)
#        return ofs_length

    # ------------------- backend-specific ops ------------------------

    def do_arraylen_gc(self, args, arraydescr):
        gcref = args[0].getptr(llmemory.GCREF)
        return BoxInt(rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)[0])

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
        if size == 1:
            v = args[2].getint()
            rffi.cast(rffi.CArrayPtr(lltype.Char), gcref)[ofs + field] = chr(v)
        elif size == WORD:
            a = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)
            if not ptr:
                a[ofs/WORD + field] = args[2].getint()
            else:
                p = args[2].getptr(llmemory.GCREF)
                a[ofs/WORD + field] = self.cast_gcref_to_int(p)
        else:
            raise NotImplementedError("size = %d" % size)

    def _new_do_len(TP):
        def do_strlen(self, args, descr=0):
            basesize, itemsize, ofs_length = symbolic.get_array_token(TP,
                                                self.translate_support_code)
            gcref = args[0].getptr(llmemory.GCREF)
            v = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)[ofs_length/WORD]
            return BoxInt(v)
        return do_strlen

    do_strlen = _new_do_len(rstr.STR)
    do_unicodelen = _new_do_len(rstr.UNICODE)

    def do_strgetitem(self, args, descr=0):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                    self.translate_support_code)
        gcref = args[0].getptr(llmemory.GCREF)
        i = args[1].getint()
        v = rffi.cast(rffi.CArrayPtr(lltype.Char), gcref)[basesize + i]
        return BoxInt(ord(v))

    def do_unicodegetitem(self, args, descr=0):
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
            a = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)
            if ptr:
                ptr = vbox.getptr(llmemory.GCREF)
                a[ofs/WORD] = self.cast_gcref_to_int(ptr)
            else:
                a[ofs/WORD] = vbox.getint()
        else:
            raise NotImplementedError("size = %d" % size)

    def do_setfield_gc(self, args, fielddescr):
        gcref = args[0].getptr(llmemory.GCREF)
        self._base_do_setfield(fielddescr, gcref, args[1])

    def do_setfield_raw(self, args, fielddescr):
        self._base_do_setfield(fielddescr, args[0].getint(), args[1])

    def do_new(self, args, descrsize):
        res = rffi.cast(GC_MALLOC, gc_malloc_fnaddr())(descrsize.v[0])
        return BoxPtr(self.cast_int_to_gcref(res))

    def do_new_with_vtable(self, args, descrsize):
        res = rffi.cast(GC_MALLOC, gc_malloc_fnaddr())(descrsize.v[0])
        rffi.cast(rffi.CArrayPtr(lltype.Signed), res)[0] = args[0].getint()
        return BoxPtr(self.cast_int_to_gcref(res))

    def do_new_array(self, args, arraydescr):
        size_of_field, ofs, ptr = self.unpack_arraydescr(arraydescr)
        num_elem = args[0].getint()
        size = ofs + (1 << size_of_field) * num_elem
        res = rffi.cast(GC_MALLOC, gc_malloc_fnaddr())(size)
        rffi.cast(rffi.CArrayPtr(lltype.Signed), res)[0] = num_elem
        return BoxPtr(self.cast_int_to_gcref(res))

    def _new_do_newstr(TP):
        def do_newstr(self, args, descr=0):
            basesize, itemsize, ofs_length = symbolic.get_array_token(TP,
                                             self.translate_support_code)
            num_elem = args[0].getint()
            size = basesize + num_elem * itemsize
            res = rffi.cast(GC_MALLOC, gc_malloc_fnaddr())(size)
            rffi.cast(rffi.CArrayPtr(lltype.Signed), res)[ofs_length/WORD] = num_elem
            return BoxPtr(self.cast_int_to_gcref(res))
        return do_newstr
    do_newstr = _new_do_newstr(rstr.STR)
    do_newunicode = _new_do_newstr(rstr.UNICODE)

    def do_strsetitem(self, args, descr=0):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                self.translate_support_code)
        index = args[1].getint()
        v = args[2].getint()
        a = args[0].getptr(llmemory.GCREF)
        rffi.cast(rffi.CArrayPtr(lltype.Char), a)[index + basesize] = chr(v)

    def do_unicodesetitem(self, args, descr=0):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                                self.translate_support_code)
        index = args[1].getint()
        v = args[2].getint()
        a = args[0].getptr(llmemory.GCREF)
        basesize = basesize // itemsize
        rffi.cast(rffi.CArrayPtr(lltype.UniChar), a)[index + basesize] = unichr(v)

    def do_call(self, args, calldescr):
        num_args, size, ptr = self.unpack_calldescr(calldescr)
        assert isinstance(calldescr, ConstDescr3)
        loop = self._get_loop_for_call(num_args, calldescr, ptr)
        op = self.execute_operations(loop, args)
        if size == 0:
            return None
        return op.args[0]

    def do_cast_ptr_to_int(self, args, descr=None):
        return BoxInt(self.cast_gcref_to_int(args[0].getptr_base()))

    def do_cast_int_to_ptr(self, args, descr=None):
        return BoxPtr(self.cast_int_to_gcref(args[0].getint()))

    # ------------------- helpers and descriptions --------------------

    @staticmethod
    def cast_adr_to_int(x):
        res = ll2ctypes.cast_adr_to_int(x)
        return res

    @staticmethod
    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return CPU386.cast_adr_to_int(adr)

    def arraydescrof(self, A):
        assert isinstance(A, lltype.GcArray)
        basesize, itemsize, ofs_length = symbolic.get_array_token(A,
                                                  self.translate_support_code)
        assert ofs_length == 0
        if isinstance(A.OF, lltype.Ptr):
            ptr = True
        else:
            ptr = False
        return ConstDescr3((basesize, itemsize, ptr))

    @staticmethod
    def unpack_arraydescr(arraydescr):
        assert isinstance(arraydescr, ConstDescr3)
        basesize, itemsize, ptr = arraydescr.v
        counter = 0
        while itemsize != 1:
            itemsize >>= 1
            counter += 1
        return counter, basesize, ptr

    def calldescrof(self, functype, argtypes, resulttype):
        if resulttype is lltype.Void:
            size = 0
        else:
            size = symbolic.get_size(resulttype, self.translate_support_code)
        if isinstance(resulttype, lltype.Ptr):
            ptr = True
        else:
            ptr = False
        return ConstDescr3((len(argtypes), size, ptr))

    @staticmethod
    def unpack_calldescr(calldescr):
        assert isinstance(calldescr, ConstDescr3)
        return calldescr.v

    def fielddescrof(self, S, fieldname):
        ofs, size = symbolic.get_field_token(S, fieldname,
                                             self.translate_support_code)
        if (isinstance(getattr(S, fieldname), lltype.Ptr) and
            getattr(S, fieldname).TO._gckind == 'gc'):
            ptr = True
        else:
            ptr = False
        return ConstDescr3((ofs, size, ptr))

    @staticmethod
    def unpack_fielddescr(fielddescr):
        assert isinstance(fielddescr, ConstDescr3)
        return fielddescr.v

    @staticmethod
    def cast_int_to_adr(x):
        assert x == 0 or x > (1<<20) or x < (-1<<20)
        if we_are_translated():
            return rffi.cast(llmemory.Address, x)
        else:
            # indirect casting because the above doesn't work with ll2ctypes
            return llmemory.cast_ptr_to_adr(rffi.cast(llmemory.GCREF, x))

    def cast_gcref_to_int(self, x):
        return rffi.cast(lltype.Signed, x)

    def cast_int_to_gcref(self, x):
        assert x == 0 or x > (1<<20) or x < (-1<<20)
        return rffi.cast(llmemory.GCREF, x)

    # ---------------------------- tests ------------------------
    def guard_failed(self):
        return self._guard_index != -1

def uhex(x):
    if we_are_translated():
        return hex(x)
    else:
        if x < 0:
            x += 0x100000000
        return hex(x)

# class GuardFailed(object):
#     return_value_type = 0
    
#     def __init__(self, cpu, frame, guard_op):
#         self.cpu = cpu
#         self.frame = frame
#         self.guard_op = guard_op

#     def make_ready_for_return(self, return_value_box):
#         self.cpu.assembler.make_sure_mc_exists()
#         if return_value_box is not None:
#             frame = getframe(self.frame)
#             frame[0] = self.cpu.convert_box_to_int(return_value_box)
#             if (isinstance(return_value_box, ConstInt) or
#                 isinstance(return_value_box, BoxInt)):
#                 self.return_value_type = INT
#             else:
#                 self.return_value_type = PTR
#         else:
#             self.return_value_type = VOID
#         self.return_addr = self.cpu.assembler.generic_return_addr

#     def make_ready_for_continuing_at(self, merge_point):
#         # we need to make sure here that return_addr points to a code
#         # that is ready to grab coorect values
#         self.return_addr = merge_point.comeback_bootstrap_addr

def getframe(frameadr):
    return rffi.cast(rffi.CArrayPtr(lltype.Signed), frameadr)

CPU = CPU386

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(CPU)
