#from rpython.jit.backend import model
from rpython.jit.backend.libgccjit.assembler import AssemblerLibgccjit
from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU

#class CPU(model.AbstractCPU):
class CPU(AbstractLLCPU):
    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

    def setup(self):
        self.assembler = AssemblerLibgccjit(self)

    def compile_loop(self, inputargs, operations, looptoken,
                     log=True, name='', logger=None):
        """
        import sys
        sys.stderr.write('compile_loop:\n')
        for i, arg in enumerate(inputargs):
            sys.stderr.write('  arg[%i] = %r\n' % (i, arg))
            sys.stderr.write('    type(arg[%i]) = %r\n' % (i, type(arg)))
        for i, op in enumerate(operations):
            sys.stderr.write('  op[%i] = %r\n' % (i, op))
            sys.stderr.write('    type(op[%i]) = %r\n' % (i, type(op)))
        sys.stderr.write('  looptoken: %r\n' % (looptoken, ))
        sys.stderr.write('  log: %r\n' % (log, ))
        sys.stderr.write('  name: %r\n' % (name, ))
        sys.stderr.write('  logger: %r\n' % (logger, ))
        sys.stderr.write('compile_loop: %r\n' % locals ())
        """
        return self.assembler.assemble_loop(inputargs, operations, looptoken, log,
                                            name, logger)
