
from __future__ import generators
from pypy.lang.gameboy.cpu import CPU
from pypy.lang.gameboy.debug import debug


class ProfilingCPU(CPU):
    
    
    def __init__(self, interrupt, memory):
        CPU.__init__(self, interrupt, memory)
        self.op_codes = []
        
    def run(self, op_codes):
        self.op_codes = op_codes
        i = 0
        while i < len(op_codes):
            self.pc.set(i)
            self.execute(op_codes[i])
            if op_codes[i] == 0xCB:
                i += 1
            i += 1
        
    def fetch(self, use_cycles=True):
        if use_cycles:
            self.cycles += 1
        data =  self.op_codes[self.pc.get() % len(self.op_codes)];
        self.pc.inc(use_cycles)
        return data