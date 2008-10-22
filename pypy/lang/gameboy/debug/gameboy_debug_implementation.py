#!/usr/bin/env python 
from __future__ import generators
        
from pypy.lang.gameboy.gameboy_implementation import *
from pypy.lang.gameboy.debug.debug_cpu import DebugCPU
from pypy.lang.gameboy.debug import debug
from pypy.lang.gameboy.debug.debug_socket_memory import *
import time
import pdb

# GAMEBOY ----------------------------------------------------------------------

class GameBoyDebugImplementation(GameBoyImplementation):
    
    def __init__(self, debuggerPort, skipExecs=0, memory_class=DebugSocketMemory):
        GameBoyImplementation.__init__(self)
        self.cpu = DebugCPU(self.interrupt, self)
        self.init_sdl()
        self.memory = memory_class(self, debuggerPort, skipExecs)
        
    def init_sdl(self):
        pass;
    
    def create_drivers(self):
        # make sure only the debug drivers are implemented
        self.clock = Clock()
        self.joypad_driver = JoypadDriverDebugImplementation()
        self.video_driver  = VideoDriverDebugImplementation()
        self.sound_driver  = SoundDriverImplementation()
        
    def emulate_cycle(self):
       	self.emulate(constants.GAMEBOY_CLOCK >> 2)
   
    def handle_execution_error(self, error):
    	print error
        print "closing socket connections"
        pdb.set_trace()
        self.is_running = False
        debug.print_results()
        self.memory.close()
    
    def handle_executed_op_code(self, is_fetch_execute=True):
        self.memory.handle_executed_op_code(is_fetch_execute)
        
    def mainLoop(self):
        self.memory.start_debug_session()
        GameBoyImplementation.mainLoop(self)
        
    
    
        
# VIDEO DRIVER -----------------------------------------------------------------

class VideoDriverDebugImplementation(VideoDriver):
    
    
    def __init__(self):
        # do not initialize any libsdl stuff
        VideoDriver.__init__(self)
    
    def update_display(self):
        # dont update the display, we're here only for testing
        pass
    
             
        
# JOYPAD DRIVER ----------------------------------------------------------------

class JoypadDriverDebugImplementation(JoypadDriver):
    
    def __init__(self):
        JoypadDriver.__init__(self)
      
    def update(self, event):
      	pass;  
        
        
# SOUND DRIVER -----------------------------------------------------------------

class SoundDriverDebugImplementation(SoundDriverImplementation):
    pass
    
    
# ==============================================================================
