from pypy.lang.gameboy.cpu import CPU
from pypy.lang.gameboy.video import Video
from pypy.lang.gameboy.debug import debug_util
from pypy.lang.gameboy.video_register import *
from pypy.lang.gameboy.video_mode import *

class DebugCPU(CPU):
    def fetch_execute(self):
        CPU.fetch_execute(self)
        debug_util.log(self.last_fetch_execute_op_code, is_fetch_execute=True)
        self.memory.handle_executed_op_code(is_fetch_execute=True)
        
    
    def execute(self, opCode):
        CPU.execute(self, opCode)
        debug_util.log(self.last_op_code)
        self.memory.handle_executed_op_code(is_fetch_execute=False)
        

class DebugVideo(Video):
    def __init__(self, video_driver, interrupt, memory):
        Video.__init__(self, video_driver, interrupt, memory)
        self.status = DebugStatusRegister(self)
        self.ini_debug_fields()
           
    def ini_debug_fields(self):
        self.last_read_address = 0
        self.last_write_address = 0
        self.last_write_data = 0
        self.reset_emulate_tracking_fields()
        
    def reset_emulate_tracking_fields(self):
        self.emulated_hblank   = False
        self.emulated_vblank   = False
        self.emulated_oam      = False
        self.emulated_transfer = False
        self.drew_background   = False
        
    def write(self, address, data):
        Video.write(self, address, data)
        self.last_write_address = address
        self.last_write_data    = data
        
    def read(self, address):
        self.last_read_address = address
        return Video.read(self, address)
    
    def emulate(self, ticks):
        self.reset_emulate_tracking_fields()
        Video.emulate(self, ticks)
        
        
class DebugStatusRegister(StatusRegister):
    def __init__(self, debug_video):
        StatusRegister.__init__(self, debug_video)
        
    def create_modes(self, video):
        self.mode0 = DebugMode0(video)
        self.mode1 = DebugMode1(video)
        self.mode2 = DebugMode2(video)
        self.mode3 = DebugMode3(video)
        self.modes = [self.mode0, self.mode1, self.mode2, self.mode3]
        
        
class DebugMode0(Mode0):
    def __init__(self, debug_video):
        Mode0.__init__(self, debug_video)
    
    def emulate_hblank(self):
        self.video.emulated_hblank = True
        Mode0.emulate_hblank(self)


class DebugMode1(Mode1):
    def __init__(self, debug_video):
        Mode1.__init__(self, debug_video)
        
    def emulate_v_blank(self):
        self.video.emulated_vblank = True
        Mode1.emulate_v_blank(self)
 
 
class DebugMode2(Mode2):
    def __init__(self, debug_video):
        Mode2.__init__(self, debug_video)
    
    def emulate_oam(self):
        self.video.emulated_oam = True
        Mode2.emulate_oam(self)


class DebugMode3(Mode3):
    def __init__(self, debug_video):
        Mode3.__init__(self, debug_video)    
       
    def emulate_transfer(self):
        self.video.emulated_transfer = True
        Mode3.emulate_transfer(self)
