#!/usr/bin/env python 
        
from pypy.lang.gameboy.gameboy import GameBoy
from pypy.lang.gameboy.joypad import JoypadDriver
from pypy.lang.gameboy.video import VideoDriver
from pypy.lang.gameboy.sound import SoundDriver
from pypy.lang.gameboy.timer import Clock
from pypy.lang.gameboy.video_meta import TileDataWindow, SpriteWindow,\
                                         WindowPreview, BackgroundPreview,\
                                         MapAViewer, MapBViewer,\
                                         SpritesWindow
from pypy.lang.gameboy import constants
import time

show_metadata = False # Extends the window with windows visualizing meta-data

if constants.USE_RSDL:
    from pypy.rlib.rsdl import RSDL, RSDL_helper #, RMix
    from pypy.rpython.lltypesystem import lltype, rffi
    get_ticks = RSDL.GetTicks
    def delay(secs):
        return RSDL.Delay(int(secs * 1000))
else:
    delay = time.sleep

FPS = 1<<6 # About 1<<6 to make sure we have a clean distrubution of about
           # 1<<6 frames per second

from pypy.rlib.objectmodel import specialize


# GAMEBOY ----------------------------------------------------------------------

class GameBoyImplementation(GameBoy):
    
    def __init__(self):
        GameBoy.__init__(self)
        self.is_running = False
        self.penalty = 0
        self.sync_time = int(time.time())

    def open_window(self):
        if constants.USE_RSDL:
            self.init_sdl()
        self.video_driver.create_screen()
        
    def init_sdl(self):
        assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
        self.event = lltype.malloc(RSDL.Event, flavor='raw')

    def create_drivers(self):
        self.clock = Clock()
        self.joypad_driver = JoypadDriverImplementation()
        self.video_driver  = VideoDriverImplementation(self)
        self.sound_driver  = SoundDriverImplementation()
    
    def mainLoop(self):
        self.reset()
        self.is_running = True
        while self.is_running:
            self.emulate_cycle()
        #try:
        #    while self.is_running:
        #        self.emulate_cycle()
        #except Exception, error:
        #    self.is_running = False
        #    self.handle_execution_error(error)
        return 0
    
    def emulate_cycle(self):
        self.handle_events()
        # Come back to this cycle every 1/FPS seconds
        self.emulate(constants.GAMEBOY_CLOCK / FPS)
        spent = time.time() - self.sync_time
        left = 1.0/FPS + self.penalty - spent
        if left > 0:
            delay(left)
            self.penalty = 0.0
        else:
            # Fade out penalties over time.
            self.penalty = left - self.penalty / 2
        self.sync_time = time.time()
        
    
    def handle_execution_error(self, error): 
        if constants.USE_RSDL:
            lltype.free(self.event, flavor='raw')
            RSDL.Quit()
    
    def handle_events(self):
        if constants.USE_RSDL:
            self.poll_event()
            if self.check_for_escape():
                self.is_running = False 
            self.joypad_driver.update(self.event)
    
    
    def poll_event(self):
        if constants.USE_RSDL:
            ok = rffi.cast(lltype.Signed, RSDL.PollEvent(self.event))
            return ok > 0
        else:
            return True
             
    def check_for_escape(self):
        if not constants.USE_RSDL: return False
        c_type = rffi.getintfield(self.event, 'c_type')
        if c_type == RSDL.KEYDOWN:
            p = rffi.cast(RSDL.KeyboardEventPtr, self.event)
            if rffi.getintfield(p.c_keysym, 'c_sym') == RSDL.K_ESCAPE:
                return True
        elif c_type == RSDL.QUIT:
            return True
        return False
            
        
# VIDEO DRIVER -----------------------------------------------------------------

class VideoDriverImplementation(VideoDriver):
    
    COLOR_MAP = [(0xff, 0xff, 0xff), (0xCC, 0xCC, 0xCC), (0x66, 0x66, 0x66), (0, 0, 0)]
    
    def __init__(self, gameboy):
        VideoDriver.__init__(self)
        self.scale = 4

        if show_metadata:
            self.create_meta_windows(gameboy)

    def create_screen(self):
        if constants.USE_RSDL:
            self.screen = RSDL.SetVideoMode(self.width*self.scale, self.height*self.scale, 32, 0)
            fmt = self.screen.c_format
            self.colors = []
            for color in self.COLOR_MAP:
                color = RSDL.MapRGB(fmt, *color)
                self.colors.append(color)
            self.blit_rect = RSDL_helper.mallocrect(0, 0, self.scale, self.scale)
 
    def create_meta_windows(self, gameboy):
        upper_meta_windows = [SpritesWindow(gameboy),
                              SpriteWindow(gameboy),
                              TileDataWindow(gameboy),
                              ]
        lower_meta_windows = [
                              WindowPreview(gameboy),
                              BackgroundPreview(gameboy),
                              MapAViewer(gameboy),
                              MapBViewer(gameboy)]
        
        self.meta_windows = upper_meta_windows + lower_meta_windows
        for window in upper_meta_windows:
            window.set_origin(self.width, 0)
            self.height = max(self.height, window.height)
            self.width += window.width
        second_x = 0
        second_y = self.height
        for window in lower_meta_windows:
            window.set_origin(second_x, second_y)
            second_x += window.width
            self.width = max(self.width, second_x)
            self.height = max(self.height, second_y + window.height)
            

    def update_display(self):
        if constants.USE_RSDL:
            RSDL.LockSurface(self.screen)
            if show_metadata:
                for meta_window in self.meta_windows:
                    meta_window.draw()
            self.draw_pixels()
            RSDL.UnlockSurface(self.screen)
            RSDL.Flip(self.screen)
        else:
            print  '\x1b[H\x1b[2J' # Clear screen
            self.draw_ascii_pixels()

    def draw_pixel(self, x, y, color):
        color = self.colors[color]
        start_x = x * self.scale
        start_y = y * self.scale
        dstrect = self.blit_rect
        rffi.setintfield(dstrect, 'c_x',  start_x)
        rffi.setintfield(dstrect, 'c_y',  start_y)
        RSDL.FillRect(self.screen, dstrect, color)

    def draw_pixels(self):
        for y in range(constants.GAMEBOY_SCREEN_HEIGHT):
            for x in range(constants.GAMEBOY_SCREEN_WIDTH):
                if self.changed[y][x]:
                    self.draw_pixel(x, y, self.pixels[y][x])
                    self.changed[y][x] = False

    def draw_ascii_pixels(self):
            str = []
            for y in range(self.height):
                str.append("\n")
                for x in range(self.width):
                    if y%2 == 0 or True:
                        str.append(["#", "%", "+", "."][self.pixels[y][x]])
            print "".join(str)
             
# JOYPAD DRIVER ----------------------------------------------------------------

class JoypadDriverImplementation(JoypadDriver):
    
    def __init__(self):
        JoypadDriver.__init__(self)
        self.last_key = 0
        
    def update(self, event):
        if not constants.USE_RSDL: return 
        # fetch the event from sdl
        type = rffi.getintfield(event, 'c_type')
        if type == RSDL.KEYDOWN:
            self.create_called_key(event)
            self.on_key_down()
        elif type == RSDL.KEYUP:
            self.create_called_key(event)
            self.on_key_up()
    
    def create_called_key(self, event):
        if constants.USE_RSDL: 
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
        if not constants.USE_RSDL: return None
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
        elif key == RSDL.K_s:
            return JoypadDriver.button_b
        return None
        
        
# SOUND DRIVER -----------------------------------------------------------------

class SoundDriverImplementation(SoundDriver):
    """
    The current implementation doesnt handle sound yet
    """
    def __init__(self):
        SoundDriver.__init__(self)
        self.enabled       = False
        self.sampleRate    = 44100
        self.buffersize    = 512
        self.channelCount  = 2
        self.bitsPerSample = 4
        self.sampleSize    = self.bitsPerSample * self.channelCount
        self.create_sound_driver()

    def create_sound_driver(self):
        #if RMix.OpenAudio(self.sampleRate, RSDL.AUDIO_U8, 
        #                  self.channelCount, self.chunksize) != 0:
        #    error = rffi.charp2str(RSDL.GetError())
        #    raise Exception(error)
        #else:
        #    self.enabled = True
        pass
    
    def start(self):
        pass
        
    def stop(self):
        pass
    
    def write(self, buffer, length):
        if not self.enabled: return
        pass
    
    
# ==============================================================================

if __name__ == '__main__':
    import sys
    gameboy = GameBoyImplementation()
    rom = sys.argv[1]
    print rom
    gameboy.load_cartridge_file(rom, verify=True)
    gameboy.mainLoop()
