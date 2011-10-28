import py
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.llinterp import LLInterpreter
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.metainterp import history, compile
from pypy.jit.metainterp.history import BoxPtr
from pypy.jit.backend.x86.assembler import Assembler386
from pypy.jit.backend.x86.arch import FORCE_INDEX_OFS
from pypy.jit.backend.x86.profagent import ProfileAgent
from pypy.jit.backend.llsupport.llmodel import AbstractLLCPU
from pypy.jit.backend.x86 import regloc
from pypy.jit.backend.x86.support import values_array
from pypy.jit.backend.ppc.ppcgen.ppc_assembler import AssemblerPPC
from pypy.jit.backend.ppc.ppcgen.arch import NONVOLATILES, GPR_SAVE_AREA, WORD
from pypy.jit.backend.ppc.ppcgen.regalloc import PPCRegisterManager, PPCFrameManager
import sys

from pypy.tool.ansi_print import ansi_log
log = py.log.Producer('jitbackend')
py.log.setconsumer('jitbackend', ansi_log)

class PPC_64_CPU(AbstractLLCPU):

    BOOTSTRAP_TP = lltype.FuncType([], lltype.Signed)

    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        if gcdescr is not None:
            gcdescr.force_index_ofs = FORCE_INDEX_OFS
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

        # floats are not supported yet
        self.supports_floats = False
        self.total_compiled_loops = 0
        self.total_compiled_bridges = 0
        self.asm = AssemblerPPC(self)

    def setup_once(self):
        self.asm.setup_once()

    def compile_loop(self, inputargs, operations, looptoken, log=False):
        self.saved_descr = {}
        self.asm.assemble_loop(inputargs, operations, looptoken, log)

    def compile_bridge(self, faildescr, inputargs, operations, 
                      original_loop_token, log=False):
        clt = original_loop_token.compiled_loop_token
        clt.compiling_a_bridge()
        self.asm.assemble_bridge(faildescr, inputargs, operations,
                                       original_loop_token, log=log)

    # set value in fail_boxes_int
    def set_future_value_int(self, index, value_int):
        self.asm.fail_boxes_int.setitem(index, value_int)

    def set_future_value_ref(self, index, pointer):
        self.asm.fail_boxes_ptr.setitem(index, pointer)

    def clear_latest_values(self, count):
        null = lltype.nullptr(llmemory.GCREF.TO)
        for index in range(count):
            self.asm.fail_boxes_ptr.setitem(index, null)

    # executes the stored machine code in the token
    def execute_token(self, looptoken):   
        addr = looptoken.ppc_code
        func = rffi.cast(lltype.Ptr(self.BOOTSTRAP_TP), addr)
        fail_index = self._execute_call(func)
        return self.get_fail_descr_from_number(fail_index)

    def _execute_call(self, func):
        prev_interpreter = None
        if not self.translate_support_code:
            prev_interpreter = LLInterpreter.current_interpreter
            LLInterpreter.current_interpreter = self.debug_ll_interpreter
        res = 0
        try:
            res = func()
        finally:
            if not self.translate_support_code:
                LLInterpreter.current_interpreter = prev_interpreter
        return res

    @staticmethod
    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return PPC_64_CPU.cast_adr_to_int(adr)

    # return the number of values that can be returned
    def get_latest_value_count(self):
        return self.asm.fail_boxes_count

    # fetch the result of the computation and return it
    def get_latest_value_int(self, index):
        value = self.asm.fail_boxes_int.getitem(index)
        return value

    def get_latest_value_ref(self, index):
        return self.asm.fail_boxes_ptr.getitem(index)
    
    # walk through the given trace and generate machine code
    def _walk_trace_ops(self, codebuilder, operations):
        for op in operations:
            codebuilder.build_op(op, self)
                
    def get_box_index(self, box):
        return self.arg_to_box[box]

    def teardown(self):
        self.patch_list = None
        self.reg_map = None
