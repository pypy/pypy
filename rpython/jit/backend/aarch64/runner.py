
from rpython.rtyper.lltypesystem import llmemory, lltype
from rpython.jit.backend.aarch64.assembler import AssemblerARM64
from rpython.jit.backend.aarch64 import registers as r
from rpython.jit.backend.aarch64.regalloc import VFPRegisterManager
from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU

class CPU_ARM64(AbstractLLCPU):
    """ARM 64"""
    backend_name = "aarch64"
    frame_reg = r.fp
    all_reg_indexes = range(len(r.all_regs))
    gen_regs = r.all_regs
    float_regs = VFPRegisterManager.all_regs


    IS_64_BIT = True

    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

    def setup(self):
        self.assembler = AssemblerARM64(self, self.translate_support_code)

    def setup_once(self):
        self.assembler.setup_once()

    def compile_bridge(self, faildescr, inputargs, operations,
                       original_loop_token, log=True, logger=None):
        clt = original_loop_token.compiled_loop_token
        clt.compiling_a_bridge()
        return self.assembler.assemble_bridge(logger, faildescr, inputargs,
                                              operations,
                                              original_loop_token, log=log)

    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return CPU_ARM64.cast_adr_to_int(adr)
    cast_ptr_to_int._annspecialcase_ = 'specialize:arglltype(0)'
    cast_ptr_to_int = staticmethod(cast_ptr_to_int)
