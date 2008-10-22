#!/usr/bin/env python 
        
from pypy.lang.gameboy.gameboy import GameBoy
from pypy.lang.gameboy.joypad import JoypadDriver
from pypy.lang.gameboy.video import VideoDriver
from pypy.lang.gameboy.sound import SoundDriver
from pypy.lang.gameboy.timer import Clock
from pypy.lang.gameboy import constants

from pypy.rlib.rsdl import RSDL, RSDL_helper
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import specialize
import time

# GAMEBOY ----------------------------------------------------------------------

class GameBoyImplementation(GameBoy):
    
    def __init__(self):
        GameBoy.__init__(self)
        self.is_running = False
        self.init_sdl()
        
    def init_sdl(self):
        assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
        self.event = lltype.malloc(RSDL.Event, flavor='raw')

    def create_drivers(self):
        self.clock = Clock()
        self.joypad_driver = JoypadDriverImplementation()
        self.video_driver  = VideoDriverImplementation()
        self.sound_driver  = SoundDriverImplementation()
    
    def mainLoop(self):
        self.reset()
        self.is_running = True
        try:
            while self.is_running:
            	self.emulate_cycle()
        except Exception, error:
            self.is_running = False
            self.handle_execution_error(error)
        return 0
    
    def emulate_cycle(self):
    	self.handle_events()
    	self.emulate(constants.GAMEBOY_CLOCK >> 2)
    	RSDL.Delay(1)
    
    def handle_execution_error(self, error): 
    	lltype.free(self.event, flavor='raw')
    	RSDL.Quit()
    
    def handle_events(self):
        self.poll_event()
        if self.check_for_escape():
            self.is_running = False 
        self.joypad_driver.update(self.event)
    
    
    def poll_event(self):
        ok = rffi.cast(lltype.Signed, RSDL.PollEvent(self.event))
        return ok > 0
             
    def check_for_escape(self):
        c_type = rffi.getintfield(self.event, 'c_type')
        if c_type == RSDL.KEYDOWN:
            p = rffi.cast(RSDL.KeyboardEventPtr, self.event)
            if rffi.getintfield(p.c_keysym, 'c_sym') == RSDL.K_ESCAPE:
                return True
        return False
            
        
# VIDEO DRIVER -----------------------------------------------------------------

class VideoDriverImplementation(VideoDriver):
    
    COLOR_MAP = [0xFFFFFF, 0xCCCCCC, 0x666666, 0x000000]
    
    def __init__(self):
        VideoDriver.__init__(self)
        self.create_screen()
        self.map = []
    
    def create_screen(self):
        self.screen = RSDL.SetVideoMode(self.width, self.height, 32, 0)
        
    def update_display(self):
        RSDL.LockSurface(self.screen)
        self.draw_pixels()
        RSDL.UnlockSurface(self.screen)
        RSDL.Flip(self.screen)
            
    def draw_pixels(self):
        #pass
        str = ""
        for y in range(self.height):
           # str += "\n"
            for x in range(self.width):
                #if y%2 == 0 or True:
                #    px = self.get_pixel_color(x, y)
                #    str += ["#", "%", "+", " ", " "][px]
                #RSDL_helper.set_pixel(self.screen, x, y, self.get_pixel_color(x, y))
                pass
        #print str;
             
    @specialize.arg(3)   
    def get_pixel_color(self, x, y, string=False):
        if string:
            return self.pixels[x+self.width*y]
        else:
            return self.pixels[x+self.width*y]
    
    def pixel_to_byte(self, int_number):
        return struct.pack("B", (int_number) & 0xFF, 
                                (int_number >> 8) & 0xFF, 
                                (int_number >> 16) & 0xFF)
        
        
# JOYPAD DRIVER ----------------------------------------------------------------

class JoypadDriverImplementation(JoypadDriver):
    
    def __init__(self):
        JoypadDriver.__init__(self)
        self.last_key = 0
        
    def update(self, event):
        # fetch the event from sdl
        type = rffi.getintfield(event, 'c_type')
        if type == RSDL.KEYDOWN:
            self.create_called_key(event)
            self.on_key_down()
        elif type == RSDL.KEYUP:
            self.create_called_key(event)
            self.on_key_up()
        pass
    
    def create_called_key(self, event):
        p = rffi.cast(RSDL.KeyboardEventPtr, event)
        self.last_key = rffi.getintfield(p.c_keysym, 'c_sym')
        
    def on_key_down(self):
        self.toggleButton(self.get_button_handler(self.last_key), True)
    
    def on_key_up(self): 
        self.toggleButton(self.get_button_handler(self.last_key), False)
    
    def toggleButton(self, pressButtonFunction, enabled):
        if pressButtonFunction is not None:
            pressButtonFunction(self, enabled)
    
    def get_button_handler(self, key):
        if key == RSDL.K_UP:
            return JoypadDriver.button_up
        elif key == RSDL.K_RIGHT: 
            return JoypadDriver.button_right
        elif key == RSDL.K_DOWN:
            return JoypadDriver.button_down
        elif key == RSDL.K_LEFT:
            return JoypadDriver.button_left
        elif key == RSDL.K_RETURN:
            return JoypadDriver.button_start
        elif key == RSDL.K_SPACE:
            return JoypadDriver.button_select
        elif key == RSDL.K_a:
            return JoypadDriver.button_a
        elif key == RSDL.K_b:
            return JoypadDriver.button_b
        return None
        
        
# SOUND DRIVER -----------------------------------------------------------------

class SoundDriverImplementation(SoundDriver):
    """
    The current implementation doesnt handle sound yet
    """
    def __init__(self):
        SoundDriver.__init__(self)
        self.create_sound_driver()
        self.enabled = True
        self.sampleRate = 44100
        self.channelCount = 2
        self.bitsPerSample = 8

    def create_sound_driver(self):
        pass
    
    def start(self):
        pass
        
    def stop(self):
        pass
    
    def write(self, buffer, length):
        pass
    
    
# ==============================================================================
