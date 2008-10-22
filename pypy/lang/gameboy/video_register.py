
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.video_mode import Mode0, Mode1, Mode2, Mode3

# -----------------------------------------------------------------------------

class StatusRegister(object):
    """
    Bit 6 - LYC=LY Coincidence Interrupt (1=Enable) (Read/Write)
    Bit 5 - Mode 2 OAM Interrupt         (1=Enable) (Read/Write)
    Bit 4 - Mode 1 V-Blank Interrupt     (1=Enable) (Read/Write)
    Bit 3 - Mode 0 H-Blank Interrupt     (1=Enable) (Read/Write)
    Bit 2 - Coincidence Flag  (0:LYC<>LY, 1:LYC=LY) (Read Only)
    Bit 1-0 - Mode Flag       (Mode 0-3, see below) (Read Only)
            0: During H-Blank
            1: During V-Blank
            2: During Searching OAM-RAM
            3: During Transfering Data to LCD Driver
    """
    def __init__(self, video):
        self.create_modes(video)
        self.reset()
        
    def create_modes(self, video):
        self.mode0 = Mode0(video)
        self.mode1 = Mode1(video)
        self.mode2 = Mode2(video)
        self.mode3 = Mode3(video)
        self.modes   = [self.mode0, self.mode1, self.mode2, self.mode3]
        
    def reset(self):
        self.current_mode               = self.mode2
        self.line_y_compare_flag      = False
        self.line_y_compare_interrupt = False
        for mode in self.modes:
            mode.reset()
        #self.mode_0_h_blank_interrupt = False
        #self.mode_1_v_blank_interrupt = False
        #self.mode_2_oam_interrupt     = False
        self.status                   = True
        
    def read(self, extend=False):
        value =  self.get_mode()
        value += self.line_y_compare_flag      << 2
        value += self.mode0.h_blank_interrupt  << 3
        value += self.mode1.v_blank_interrupt  << 4
        value += self.mode2.oam_interrupt      << 5
        value += self.line_y_compare_interrupt << 6
        if extend:
            value += int(self.status) << 7
        return value
        
    def write(self, value, write_all=False):
        if write_all:
            self.current_mode          = self.modes[value & 0x03]
            self.line_y_compare_flag   = bool(value & (1 << 2))
            self.status                = bool(value & (1 << 7))
        self.mode0.h_blank_interrupt   = bool(value & (1 << 3))
        self.mode1.v_blank_interrupt   = bool(value & (1 << 4))
        self.mode2.oam_interrupt       = bool(value & (1 << 5))
        self.line_y_compare_interrupt  = bool(value & (1 << 6))
        
    def get_mode(self):
        return self.current_mode.id()
    
    def set_mode(self, mode):
        self.current_mode = self.modes[mode & 0x03]
        self.current_mode.activate()
        
    def line_y_compare_check(self):
        return not (self.line_y_compare_flag and self.line_y_compare_interrupt)

# -----------------------------------------------------------------------------

class ControlRegister(object):
    """
    used for enabled or disabled window or background
    Bit 7 - LCD Display Enable             (0=Off, 1=On)
    Bit 6 - Window Tile Map Display Select (0=9800-9BFF, 1=9C00-9FFF)
    Bit 5 - Window Display Enable          (0=Off, 1=On)
    Bit 4 - BG & Window Tile Data Select   (0=8800-97FF, 1=8000-8FFF)
    Bit 3 - BG Tile Map Display Select     (0=9800-9BFF, 1=9C00-9FFF)
    Bit 2 - OBJ (Sprite) Size              (0=8x8, 1=8x16)
    Bit 1 - OBJ (Sprite) Display Enable    (0=Off, 1=On)
    Bit 0 - BG Display (for CGB see below) (0=Off, 1=On)
    """
    def __init__(self, window, background):
        self.window     = window
        self.background = background
        self.reset()
        
    def reset(self):
        self.lcd_enabled                              = True
        self.window.upper_tile_map_selected           = False
        self.window.enabled                           = False
        self.background_and_window_lower_tile_data_selected  = True
        self.background.upper_tile_map_selected       = False
        self.big_sprite_size_selected                 = False
        self.sprites_enabled                          = False
        self.background.enabled                       = True
        
    def read(self):
        value = 0
        value += int(self.lcd_enabled)                        << 7 
        value += int(self.window.upper_tile_map_selected)     << 6 
        value += int(self.window.enabled)                     << 5
        value += int(self.background_and_window_lower_tile_data_selected)  << 4
        value += int(self.background.upper_tile_map_selected) << 3
        value += int(self.big_sprite_size_selected)           << 2
        value += int(self.sprites_enabled)                    << 1
        value += int(self.background.enabled)                 << 0
        return value
        
    def write(self, value):
        self.lcd_enabled                             = bool(value & (1 << 7))
        self.window.upper_tile_map_selected          = bool(value & (1 << 6))
        self.window.enabled                          = bool(value & (1 << 5))
        self.background_and_window_lower_tile_data_selected = \
                                                       bool(value & (1 << 4))
        self.background.upper_tile_map_selected      = bool(value & (1 << 3))
        self.big_sprite_size_selected                = bool(value & (1 << 2))
        self.sprites_enabled                         = bool(value & (1 << 1))
        self.background.enabled                      = bool(value & (1 << 0))
    
    
    def get_selected_tile_data_space(self):
        if self.window.upper_tile_map_selected:
            return constants.VRAM_DATA_A
        else:
            return  constants.VRAM_DATA_B
