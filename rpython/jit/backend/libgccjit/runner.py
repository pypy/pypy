#from rpython.jit.backend import model
from rpython.jit.backend.libgccjit.assembler import AssemblerLibgccjit
from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU

#class CPU(model.AbstractCPU):
class CPU(AbstractLLCPU):

    supports_floats = True

    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

    def setup(self):
        self.assembler = AssemblerLibgccjit(self)

    def compile_loop(self, inputargs, operations, looptoken,
                     log=True, name='', logger=None):
        return self.assembler.assemble_loop(inputargs, operations, looptoken, log,
                                            name, logger)

    def compile_bridge(self, faildescr, inputargs, operations,
                       original_loop_token, log=True, logger=None):
        clt = original_loop_token.compiled_loop_token
        clt.compiling_a_bridge()
        return self.assembler.assemble_bridge(logger, faildescr, inputargs,
                                              operations,
                                              original_loop_token, log=log)
