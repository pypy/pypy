#!/usr/bin/env python 
        
from pypy.lang.gameboy.gameboy import GameBoy
from pypy.lang.gameboy.joypad import JoypadDriver
from pypy.lang.gameboy.video import VideoDriver
from pypy.lang.gameboy.sound import SoundDriver
from pypy.lang.gameboy.timer import Clock
from pypy.lang.gameboy import constants

from pypy.rlib.objectmodel import specialize


# GAMEBOY ----------------------------------------------------------------------

FPS = 1 << 6

class GameBoyProfiler(GameBoy):
    
    def __init__(self):
        GameBoy.__init__(self)
        self.is_running = False


    def create_drivers(self):
        self.clock = Clock()
        self.joypad_driver = JoypadDriver()
        self.video_driver  = VideoDriver()
        self.sound_driver  = SoundDriver()
    
    def mainLoop(self, execution_seconds):
        self.reset()
        self.is_running = True
        for i in range(int(execution_seconds * FPS)):
            self.emulate_cycle()
    
    def emulate_cycle(self):
        self.emulate(constants.GAMEBOY_CLOCK / FPS)
