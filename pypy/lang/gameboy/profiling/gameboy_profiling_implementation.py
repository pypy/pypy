#!/usr/bin/env python 
from __future__ import generators
        
from pypy.lang.gameboy.ram import iMemory
from pypy.lang.gameboy.gameboy_implementation import *
from pypy.lang.gameboy.profiling.profiling_cpu import ProfilingCPU
from pypy.lang.gameboy.debug import debug
from pypy.lang.gameboy.debug.debug_socket_memory import *


# GAMEBOY ----------------------------------------------------------------------

class GameBoyProfilingImplementation(GameBoyImplementation):
    
    def __init__(self, op_codes):
        GameBoyImplementation.__init__(self)
        self.op_codes = op_codes
        self.cycleLimit = cycleLimit
        self.cpu = ProfilingCPU(self.interrupt, self)
        self.cpu.cycle_limit = cycleLimit
    
    def handle_execution_error(self):
        self.is_running = False
        debug.print_results()
    

# CUSTOM DRIVER IMPLEMENTATIONS currently not used =============================
      
    
# VIDEO DRIVER -----------------------------------------------------------------

class VideoDriverDebugImplementation(VideoDriverImplementation):
    pass
        
        
# JOYPAD DRIVER ----------------------------------------------------------------

class JoypadDriverDebugImplementation(JoypadDriverImplementation):
    pass
        
        
# SOUND DRIVER -----------------------------------------------------------------

class SoundDriverDebugImplementation(SoundDriverImplementation):
    pass
    
    
# ==============================================================================
