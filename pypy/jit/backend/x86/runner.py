import sys
import ctypes
import py
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.llinterp import LLInterpreter
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.metainterp import history
from pypy.jit.backend.x86.assembler import Assembler386
from pypy.jit.backend.llsupport.llmodel import AbstractLLCPU


class CPU386(AbstractLLCPU):
    debug = True
    supports_floats = True

    BOOTSTRAP_TP = lltype.FuncType([], lltype.Signed)
    dont_keepalive_stuff = False # for tests

    def __init__(self, rtyper, stats, translate_support_code=False,
                 gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, translate_support_code,
                               gcdescr)
        self._bootstrap_cache = {}

    def setup(self):
        self.assembler = Assembler386(self, self.translate_support_code)

    def get_on_leave_jitted_hook(self):
        return self.assembler.leave_jitted_hook

    def setup_once(self):
        pass

    def compile_loop(self, inputargs, operations, looptoken):
        self.assembler.assemble_loop(inputargs, operations, looptoken)

    def compile_bridge(self, faildescr, inputargs, operations):
        self.assembler.assemble_bridge(faildescr, inputargs, operations)

    def set_future_value_int(self, index, intvalue):
        self.assembler.fail_boxes_int.setitem(index, intvalue)

    def set_future_value_float(self, index, floatvalue):
        self.assembler.fail_boxes_float.setitem(index, floatvalue)

    def set_future_value_ref(self, index, ptrvalue):
        self.assembler.fail_boxes_ptr.setitem(index, ptrvalue)

    def get_latest_value_int(self, index):
        return self.assembler.fail_boxes_int.getitem(index)

    def get_latest_value_float(self, index):
        return self.assembler.fail_boxes_float.getitem(index)

    def get_latest_value_ref(self, index):
        ptrvalue = self.assembler.fail_boxes_ptr.getitem(index)
        # clear after reading
        self.assembler.fail_boxes_ptr.setitem(index, lltype.nullptr(
            llmemory.GCREF.TO))
        return ptrvalue

    def execute_token(self, executable_token):
        addr = executable_token._x86_bootstrap_code
        func = rffi.cast(lltype.Ptr(self.BOOTSTRAP_TP), addr)
        fail_index = self._execute_call(func)
        return fail_index

    def _execute_call(self, func):
        # help flow objspace
        prev_interpreter = None
        if not self.translate_support_code:
            prev_interpreter = LLInterpreter.current_interpreter
            LLInterpreter.current_interpreter = self.debug_ll_interpreter
        res = 0
        try:
            #llop.debug_print(lltype.Void, ">>>> Entering",
            #                 rffi.cast(lltype.Signed, func))
            res = func()
            #llop.debug_print(lltype.Void, "<<<< Back")
        finally:
            if not self.translate_support_code:
                LLInterpreter.current_interpreter = prev_interpreter
        return res

    @staticmethod
    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return CPU386.cast_adr_to_int(adr)


class CPU386_NO_SSE2(CPU386):
    supports_floats = False


CPU = CPU386

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(CPU)
