#!/usr/bin/env python 
        
from pypy.lang.gameboy.debug import debug
from pypy.lang.gameboy.gameboy_implementation import *
from pypy.lang.gameboy.debug.debug_socket_memory import *
from pypy.lang.gameboy.profiling.evaluation.evaluation_cpu import EvaluationCPU
from pypy.lang.gameboy.profiling.evaluation.gameboy_evaluation_implementation import *

# GAMEBOY ----------------------------------------------------------------------

class GameBoyEvaluationImplementation(GameBoyImplementation):
    
    def __init__(self, cycleLimit=0):
        GameBoyImplementation.__init__(self)
        self.cycleLimit = cycleLimit
        self.cpu = EvaluationCPU(self.interrupt, self, cycleLimit)
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
