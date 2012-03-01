import py
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.llinterp import LLInterpreter
from pypy.jit.backend.ppc.arch import FORCE_INDEX_OFS
from pypy.jit.backend.llsupport.llmodel import AbstractLLCPU
from pypy.jit.backend.ppc.ppc_assembler import AssemblerPPC
from pypy.jit.backend.ppc.arch import WORD
from pypy.jit.backend.ppc.codebuilder import PPCBuilder
from pypy.jit.backend.ppc import register as r

from pypy.tool.ansi_print import ansi_log
log = py.log.Producer('jitbackend')
py.log.setconsumer('jitbackend', ansi_log)

class PPC_64_CPU(AbstractLLCPU):

    BOOTSTRAP_TP = lltype.FuncType([], lltype.Signed)

    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        if gcdescr is not None:
            gcdescr.force_index_ofs = FORCE_INDEX_OFS
            # XXX for now the ppc backend does not support the gcremovetypeptr
            # translation option
            # assert gcdescr.config.translation.gcremovetypeptr is False
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

        # floats are not supported yet
        self.supports_floats = False

    def setup(self):
        self.asm = AssemblerPPC(self)

    def setup_once(self):
        self.asm.setup_once()

    def finish_once(self):
        self.asm.finish_once()

    def compile_loop(self, inputargs, operations, looptoken, log=True, name=""):
        return self.asm.assemble_loop(inputargs, operations, looptoken, log)

    def compile_bridge(self, faildescr, inputargs, operations, 
                      original_loop_token, log=False):
        clt = original_loop_token.compiled_loop_token
        clt.compiling_a_bridge()
        return self.asm.assemble_bridge(faildescr, inputargs, operations,
                                       original_loop_token, log=log)

    def clear_latest_values(self, count):
        setitem = self.asm.fail_boxes_ptr.setitem
        null = lltype.nullptr(llmemory.GCREF.TO)
        for index in range(count):
            setitem(index, null)

    # executes the stored machine code in the token
    def make_execute_token(self, *ARGS):
        FUNCPTR = lltype.Ptr(lltype.FuncType(ARGS, lltype.Signed))

        def execute_token(executable_token, *args):
            clt = executable_token.compiled_loop_token
            assert len(args) == clt._debug_nbargs
            #
            addr = executable_token._ppc_func_addr
            func = rffi.cast(FUNCPTR, addr)
            prev_interpreter = None   # help flow space
            if not self.translate_support_code:
                prev_interpreter = LLInterpreter.current_interpreter
                LLInterpreter.current_interpreter = self.debug_ll_interpreter
            try:
                fail_index = func(*args)
            finally:
                if not self.translate_support_code:
                    LLInterpreter.current_interpreter = prev_interpreter
            return self.get_fail_descr_from_number(fail_index)
        return execute_token

    @staticmethod
    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return PPC_64_CPU.cast_adr_to_int(adr)

    # XXX find out how big FP registers are on PPC32
    all_null_registers = lltype.malloc(rffi.LONGP.TO,
                        len(r.MANAGED_REGS),
                        flavor='raw', zero=True, immortal=True)

    def force(self, spilling_pointer):
        TP = rffi.CArrayPtr(lltype.Signed)

        addr_of_force_index = spilling_pointer + len(r.MANAGED_REGS) * WORD

        fail_index = rffi.cast(TP, addr_of_force_index)[0]
        assert fail_index >= 0, "already forced!"
        faildescr = self.get_fail_descr_from_number(fail_index)
        rffi.cast(TP, addr_of_force_index)[0] = ~fail_index

        bytecode = self.asm._find_failure_recovery_bytecode(faildescr)
        addr_all_null_registers = rffi.cast(rffi.LONG, self.all_null_registers)
        # start of "no gc operation!" block
        fail_index_2 = self.asm.decode_registers_and_descr(
                bytecode,
                spilling_pointer,
                self.all_null_registers)
        self.asm.leave_jitted_hook()
        # end of "no gc operation!" block
        assert fail_index == fail_index_2
        return faildescr

    # return the number of values that can be returned
    def get_latest_value_count(self):
        return self.asm.fail_boxes_count

    # fetch the result of the computation and return it
    def get_latest_value_int(self, index):
        value = self.asm.fail_boxes_int.getitem(index)
        return value

    def get_latest_value_ref(self, index):
        return self.asm.fail_boxes_ptr.getitem(index)

    def get_latest_force_token(self):
        return self.asm.fail_force_index
    
    def get_on_leave_jitted_hook(self):
        return self.asm.leave_jitted_hook

    # walk through the given trace and generate machine code
    def _walk_trace_ops(self, codebuilder, operations):
        for op in operations:
            codebuilder.build_op(op, self)
                
    def get_box_index(self, box):
        return self.arg_to_box[box]

    def teardown(self):
        self.patch_list = None
        self.reg_map = None

    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        self.asm.redirect_call_assembler(oldlooptoken, newlooptoken)

    def invalidate_loop(self, looptoken):
        """Activate all GUARD_NOT_INVALIDATED in the loop and its attached
        bridges.  Before this call, all GUARD_NOT_INVALIDATED do nothing;
        after this call, they all fail.  Note that afterwards, if one such
        guard fails often enough, it has a bridge attached to it; it is
        possible then to re-call invalidate_loop() on the same looptoken,
        which must invalidate all newer GUARD_NOT_INVALIDATED, but not the
        old one that already has a bridge attached to it."""

        for jmp, tgt in looptoken.compiled_loop_token.invalidate_positions:
            mc = PPCBuilder()
            mc.b_offset(tgt)
            mc.prepare_insts_blocks()
            mc.copy_to_raw_memory(jmp)
        # positions invalidated
        looptoken.compiled_loop_token.invalidate_positions = []
