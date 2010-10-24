from pypy.jit.backend.arm.assembler import AssemblerARM
from pypy.jit.backend.llsupport.llmodel import AbstractLLCPU
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.lltypesystem import lltype, rffi


class ArmCPU(AbstractLLCPU):

    BOOTSTRAP_TP = lltype.FuncType([], lltype.Signed)
    supports_floats = False

    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)
        self.assembler = AssemblerARM(self)

    def compile_loop(self, inputargs, operations, looptoken):
        self.assembler.assemble_loop(inputargs, operations, looptoken)

    def compile_bridge(self, faildescr, inputargs, operations):
        self.assembler.assemble_bridge(faildescr, inputargs, operations)

    def set_future_value_int(self, index, intvalue):
        self.assembler.input_arg_boxes_int.setitem(index, intvalue)

    def get_latest_value_int(self, index):
        return self.assembler.fail_boxes_int.getitem(index)

    def execute_token(self, executable_token):
        addr = executable_token._arm_bootstrap_code
        assert addr % 8 == 0
        func = rffi.cast(lltype.Ptr(self.BOOTSTRAP_TP), addr)
        fail_index = self._execute_call(func)
        return self.get_fail_descr_from_number(fail_index)

    def _execute_call(self, func):
        #prev_interpreter = LLInterpreter.current_interpreter
        #LLInterpreter.current_interpreter = self.debug_ll_interpreter
        res = 0
        #try:
        res = func()
        #finally:
        #    LLInterpreter.current_interpreter = prev_interpreter
        return res

