
from __future__ import generators
from pypy.lang.gameboy.cpu import CPU
from pypy.lang.gameboy.debug import debug


class DebugCPU(CPU):
    
    def fetch_execute(self):
        CPU.fetch_execute(self)
        debug.log(self.last_fetch_execute_op_code, is_fetch_execute=True)
        self.memory.handle_executed_op_code(is_fetch_execute=True)
        
    
    def execute(self, opCode):
        CPU.execute(self, opCode)
        debug.log(self.last_op_code)
        self.memory.handle_executed_op_code(is_fetch_execute=False)