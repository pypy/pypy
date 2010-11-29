from pypy.jit.backend.arm.assembler import AssemblerARM
from pypy.jit.backend.arm.arch import WORD
from pypy.jit.backend.arm.registers import all_regs
from pypy.jit.backend.llsupport.llmodel import AbstractLLCPU
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.lltypesystem import lltype, rffi, llmemory


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
        self.assembler.fail_boxes_int.setitem(index, intvalue)

    def set_future_value_ref(self, index, ptrvalue):
        self.assembler.fail_boxes_ptr.setitem(index, ptrvalue)

    def get_latest_value_int(self, index):
        return self.assembler.fail_boxes_int.getitem(index)

    def get_latest_value_ref(self, index):
        return self.assembler.fail_boxes_ptr.getitem(index)

    def get_latest_value_count(self):
        return self.assembler.fail_boxes_count

    def clear_latest_values(self, count):
        # XXX TODO
        pass

    def execute_token(self, executable_token):
        #i = [self.get_latest_value_int(x) for x in range(10)]
        #print 'Inputargs: %r for token %r' % (i, executable_token)
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

    @staticmethod
    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return self.cast_adr_to_int(adr)

    def force(self, addr_of_force_index):
        TP = rffi.CArrayPtr(lltype.Signed)
        fail_index = rffi.cast(TP, addr_of_force_index)[0]
        assert fail_index >= 0, "already forced!"
        faildescr = self.get_fail_descr_from_number(fail_index)
        rffi.cast(TP, addr_of_force_index)[0] = -1
        # start of "no gc operation!" block
        addr_end_of_frame = (addr_of_force_index -
                            (faildescr._arm_frame_depth+len(all_regs))*WORD)
        fail_index_2 = self.assembler.failure_recovery_func(
            faildescr._failure_recovery_code,
            addr_of_force_index,
            addr_end_of_frame)
        self.assembler.leave_jitted_hook()
        # end of "no gc operation!" block
        #assert fail_index == fail_index_2
        return faildescr
