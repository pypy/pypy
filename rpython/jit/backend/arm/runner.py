from rpython.jit.backend.arm.arch import JITFRAME_FIXED_SIZE
from rpython.jit.backend.arm.assembler import AssemblerARM
from rpython.jit.backend.arm.registers import all_regs
from rpython.jit.backend.llsupport import jitframe
from rpython.jit.backend.llsupport.symbolic import WORD
from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.jit.metainterp import history
from rpython.rlib.jit_hooks import LOOP_RUN_CONTAINER
from rpython.rlib.unroll import unrolling_iterable
from rpython.rtyper.llinterp import LLInterpreter
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory


jitframe.STATICSIZE = JITFRAME_FIXED_SIZE

class AbstractARMCPU(AbstractLLCPU):

    supports_floats = True
    supports_longlong = False # XXX requires an implementation of
                              # read_timestamp that works in user mode
    supports_singlefloats = True

    from rpython.jit.backend.arm.arch import JITFRAME_FIXED_SIZE
    all_reg_indexes = range(16)

    use_hf_abi = False        # use hard float abi flag

    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)


    def set_debug(self, flag):
        return self.assembler.set_debug(flag)

    def get_failargs_limit(self):
        if self.opts is not None:
            return self.opts.failargs_limit
        else:
            return 1000

    def setup(self):
        self.assembler = AssemblerARM(self, self.translate_support_code)

    def setup_once(self):
        self.assembler.setup_once()

    def finish_once(self):
        self.assembler.finish_once()

    def compile_loop(self, inputargs, operations, looptoken,
                                                    log=True, name=''):
        return self.assembler.assemble_loop(name, inputargs, operations,
                                                    looptoken, log=log)

    def compile_bridge(self, faildescr, inputargs, operations,
                                       original_loop_token, log=True):
        clt = original_loop_token.compiled_loop_token
        clt.compiling_a_bridge()
        return self.assembler.assemble_bridge(faildescr, inputargs, operations,
                                                original_loop_token, log=log)

    def clear_latest_values(self, count):
        setitem = self.assembler.fail_boxes_ptr.setitem
        null = lltype.nullptr(llmemory.GCREF.TO)
        for index in range(count):
            setitem(index, null)

    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return ArmCPU.cast_adr_to_int(adr)
    cast_ptr_to_int._annspecialcase_ = 'specialize:arglltype(0)'
    cast_ptr_to_int = staticmethod(cast_ptr_to_int)

    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        self.assembler.redirect_call_assembler(oldlooptoken, newlooptoken)

    def invalidate_loop(self, looptoken):
        """Activate all GUARD_NOT_INVALIDATED in the loop and its attached
        bridges.  Before this call, all GUARD_NOT_INVALIDATED do nothing;
        after this call, they all fail.  Note that afterwards, if one such
        guard fails often enough, it has a bridge attached to it; it is
        possible then to re-call invalidate_loop() on the same looptoken,
        which must invalidate all newer GUARD_NOT_INVALIDATED, but not the
        old one that already has a bridge attached to it."""
        from rpython.jit.backend.arm.codebuilder import ARMv7Builder

        for jmp, tgt  in looptoken.compiled_loop_token.invalidate_positions:
            mc = ARMv7Builder()
            mc.B_offs(tgt)
            mc.copy_to_raw_memory(jmp)
        # positions invalidated
        looptoken.compiled_loop_token.invalidate_positions = []

    # should be combined with other ll backends
    def get_all_loop_runs(self):
        l = lltype.malloc(LOOP_RUN_CONTAINER,
                          len(self.assembler.loop_run_counters))
        for i, ll_s in enumerate(self.assembler.loop_run_counters):
            l[i].type = ll_s.type
            l[i].number = ll_s.number
            l[i].counter = ll_s.i
        return l

class CPU_ARM(AbstractARMCPU):
    """ARM v7 uses softfp ABI, requires vfp"""
    pass
ArmCPU = CPU_ARM

class CPU_ARMHF(AbstractARMCPU):
    """ARM v7 uses hardfp ABI, requires vfp"""
    use_hf_abi = True
    supports_floats = False
