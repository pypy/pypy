from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.jit.backend.zarch import registers as r
from rpython.jit.backend.zarch.assembler import AssemblerZARCH
from rpython.rlib import rgc
from rpython.rtyper.lltypesystem import lltype, llmemory

class AbstractZARCHCPU(AbstractLLCPU):
    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return adr # TODO
    cast_ptr_to_int._annspecialcase_ = 'specialize:arglltype(0)'
    cast_ptr_to_int = staticmethod(cast_ptr_to_int)

class CPU_S390_64(AbstractZARCHCPU):
    dont_keepalive_stuff = True
    supports_floats = True
    from rpython.jit.backend.zarch.registers import JITFRAME_FIXED_SIZE

    IS_64_BIT = True

    frame_reg = r.SP
    all_reg_indexes = [-1] * 32
    for _i, _r in enumerate(r.registers):
        all_reg_indexes[_r.value] = _i
    gen_regs = r.registers
    float_regs = r.MANAGED_FP_REGS

    def setup(self):
        self.assembler = AssemblerZARCH(self)

    @rgc.no_release_gil
    def setup_once(self):
        self.assembler.setup_once()

    @rgc.no_release_gil
    def finish_once(self):
        self.assembler.finish_once()

    def compile_bridge(self, faildescr, inputargs, operations,
                       original_loop_token, log=True, logger=None):
        clt = original_loop_token.compiled_loop_token
        clt.compiling_a_bridge()
        return self.assembler.assemble_bridge(faildescr, inputargs, operations,
                                              original_loop_token, log, logger)

