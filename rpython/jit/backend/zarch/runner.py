from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.rtyper.lltypesystem import lltype, llmemory

class AbstractZARCHCPU(AbstractLLCPU):
    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return adr
    cast_ptr_to_int._annspecialcase_ = 'specialize:arglltype(0)'
    cast_ptr_to_int = staticmethod(cast_ptr_to_int)

class CPU_S390_64(AbstractZARCHCPU):
    pass
