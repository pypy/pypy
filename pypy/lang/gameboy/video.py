"""
 PyGirl Emulator
 constants.LCD Video Display Processor
"""
import math
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.ram import iMemory
from pypy.lang.gameboy.cpu import process_2_complement

# -----------------------------------------------------------------------------
class VideoCallWraper(object):
    def call(self, pos, color, mask):
        pass
    

class set_overlapped_object_line_call_wrapper(VideoCallWraper):
    def __init__(self, video):
        self.video = video
    
    def call(self, pos, color, mask):
        self.video. set_overlapped_object_line(pos, color, mask)


class set_tile_line_call_wrapper(VideoCallWraper):
    def __init__(self, video):
        self.video = video
    
    def call(self, pos, color, mask):
        self.video.set_tile_line(pos, color, mask)
    

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
        self.sprites_enabled                           = False
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

# -----------------------------------------------------------------------------
class InvalidModeOrderException(Exception):
    def __init__(self, mode, previous_mode):
        Exception.__init__(self, \
                           "Wrong Mode order! No valid transition %i => %i" \
                           % (previous_mode.id(), mode.id()))
       
class HandleSubclassException(Exception): 
    def __init__(self):
        Exception.__init__(self, "")
        
class Mode(object):

    """
    The two lower STAT bits show the current status of the LCD controller.
    """

    def __init__(self, video):
        self.video = video
        self.reset()
        
    def reset(self):
        raise Exception("unimplemented method")
                        
    def id(self):
        raise Exception("unimplemented method")
    
    def activate(self, previous_mode):
        raise Exception("unimplemented method")
    
    def emulate(self):
        raise Exception("unimplemented method")

    def emulate_hblank_line_y_compare(self, stat_check=False):
        if self.video.line_y == self.video.line_y_compare:
            if not (stat_check and self.video.status.line_y_compare_flag):
                self.line_y_line_y_compare_interrupt_check()
        else:
            self.video.status.line_y_compare_flag = False
            
    def line_y_line_y_compare_interrupt_check(self):
        self.video.status.line_y_compare_flag = True
        if self.video.status.line_y_compare_interrupt:
            self.video.lcd_interrupt_flag.set_pending()

class Mode0(Mode):
    """
     Mode 0: The LCD controller is in the H-Blank period and
          the CPU can access both the display RAM (8000h-9FFFh)
          and OAM (FE00h-FE9Fh)
    """
    
    def reset(self):
        self.h_blank_interrupt = False
    
    def id(self):
        return 0
    
    def activate(self, previous_mode):
        #if previous_mode.id() == 3:
            self.video.cycles += constants.MODE_0_TICKS
            self.h_blank_interrupt_check()
        #else:
            # video.reset_control() can be called in any position
         #   pass
            #raise InvalidModeOrderException(self, previous_mode)
    
    def h_blank_interrupt_check(self):
        if self.h_blank_interrupt and \
        self.video.status.line_y_compare_check():
            self.video.lcd_interrupt_flag.set_pending()
            
    def emulate(self):
        #self.video.emulate_hblank()
        self.emulate_hblank()
        
    def emulate_hblank(self):
        self.video.line_y += 1
        self.emulate_hblank_line_y_compare()
        if self.video.line_y < 144:
            self.video.status.set_mode(2)
        else:
            self.emulate_hblank_part_2()
            
    def emulate_hblank_part_2(self):
        if self.video.display:
            self.video.draw_frame()
        self.video.frames += 1
        if self.video.frames >= self.video.frame_skip:
            self.video.display = True
            self.video.frames = 0
        else:
            self.video.display = False
        self.video.status.set_mode(1)
        self.video.v_blank  = True
                 
class Mode1(Mode):
    """
    Mode 1: The LCD contoller is in the V-Blank period (or the
          display is disabled) and the CPU can access both the
          display RAM (8000h-9FFFh) and OAM (FE00h-FE9Fh)
    """
    
    def reset(self):
        self.v_blank_interrupt = False
        
    def id(self):
        return 1
    
    def activate(self, previous_mode):
        #if previous_mode.id() == 0:
            self.set_begin()
        #else:
        #    pass
            #raise InvalidModeOrderException(self, previous_mode)

    def set_begin(self):
        self.video.cycles += constants.MODE_1_BEGIN_TICKS
    
    def set_between(self):
        self.video.cycles += constants.MODE_1_TICKS - constants.MODE_1_BEGIN_TICKS
        
    def set_end(self):
        self.video.cycles += constants.MODE_1_END_TICKS
    
    def emulate(self):
        self.emulate_v_blank()
   
    def emulate_v_blank(self):
        if self.video.v_blank:
            self.emulate_v_blank_v_blank()
        elif self.video.line_y == 0:
            self.video.status.set_mode(2)
        else:
            self.emulate_v_blank_other()
 
    def emulate_v_blank_v_blank(self):
        self.video.v_blank  = False
        self.set_between()
        self.v_blank_interrupt_check()
                  
    def v_blank_interrupt_check(self):
        if self.v_blank_interrupt:
            self.video.lcd_interrupt_flag.set_pending()
        self.video.v_blank_interrupt_flag.set_pending()
        
    def emulate_v_blank_other(self):
        if self.video.line_y < 153:
            self.emulate_v_blank_mode_1()
        else:
            self.video.line_y        = 0
            self.video.window.line_y = 0
            self.set_between()
        self.emulate_hblank_line_y_compare() 
                
    def emulate_v_blank_mode_1(self):
        self.video.line_y += 1
        if self.video.line_y != 153:
            self.video.cycles += constants.MODE_1_TICKS
        else:
            self.set_end()
            
class Mode2(Mode):
    """
    Mode 2: The LCD controller is reading from OAM memory.
          The CPU <cannot> access OAM memory (FE00h-FE9Fh)
          during this period.
    """
    
    def reset(self):
        self.oam_interrupt = False
        
    def id(self):
        return 2
    
    def activate(self, previous_mode):
        #if previous_mode.id() == 0 or previous_mode.id() == 1:
            self.video.cycles += constants.MODE_2_TICKS
            self.oam_interrupt_check()
        #else:
        #    pass
            #raise InvalidModeOrderException(self, previous_mode)
     
    def oam_interrupt_check(self):
        if self.oam_interrupt and \
        self.video.status.line_y_compare_check():
            self.video.lcd_interrupt_flag.set_pending()
            
    def emulate(self):
        self.emulate_oam()
        
    def emulate_oam(self):
        self.video.status.set_mode(3)

class Mode3(Mode):
    """
       Mode 3: The LCD controller is reading from both OAM and VRAM,
          The CPU <cannot> access OAM and VRAM during this period.
          CGB Mode: Cannot access Palette Data (FF69,FF6B) either.
    """
    
    def reset(self):
        pass
    
    def id(self):
        return 3
    
    def activate(self, previous_mode):
        #if previous_mode.id() == 2:
            self.set_begin()
        #else:
        #    pass
        #    #raise InvalidModeOrderException(self, previous_mode)
    
    def set_begin(self):
        self.video.cycles  += constants.MODE_3_BEGIN_TICKS
        self.video.transfer = True
        
    def set_end(self):
        self.video.cycles  += constants.MODE_3_END_TICKS
        self.video.transfer = False
        
    def emulate(self):
        self.emulate_transfer()
        
    def emulate_transfer(self):
        if self.video.transfer:
            if self.video.display:
                self.video.draw_line()
                #print "mode 3 ", self.video.status.get_mode() 
            self.set_end()
        else:
            self.video.status.set_mode(0)
        
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
        
        
    def write(self, value, write_all=False,
              keep_mode_0_h_blank_interrupt=False):
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
        old_mode = self.current_mode
        self.current_mode = self.modes[mode & 0x03]
        self.current_mode.activate(old_mode)
        
    def line_y_compare_check(self):
        return not self.line_y_compare_flag or not self.line_y_compare_interrupt

# -----------------------------------------------------------------------------

class Sprite(object):
    
    def __init__(self, video):
        self.video = video
        self.big_size = False
        self.reset()

    def reset(self):
        self.x              = 0
        self.y              = 0
        self.tile           = None
        self.object_behind_background = False
        self.x_flipped      = False
        self.y_flipped      = False
        self.palette_number = 0
        self.hidden         = True
        
        
    def set_data(self, byte0=-1, byte1=-1, byte2=-1, byte3=-1):
        """
        extracts the sprite data from an oam entry
        """
        if byte0 is not -1:
            self.extract_y_position(byte0)
        if byte0 is not -1:
            self.extract_x_position(byte1)
        if byte0 is not -1:
            self.extract_tile_number(byte2)
        if byte0 is not -1:
            self.extract_attributes_and_flags(byte3)
        
    def extract_y_position(self, data):
        """
        extracts the  Y Position
        Specifies the sprites vertical position on the screen (minus 16).
        An offscreen value (for example, Y=0 or Y>=160) hides the sprite.
        """
        self.y = data # - 16
        self.hide_check()
    
    def extract_x_position(self, data):
        """
        extracts the  X Position
        Specifies the sprites horizontal position on the screen (minus 8).
        An offscreen value (X=0 or X>=168) hides the sprite, but the sprite
        still affects the priority ordering - a better way to hide a sprite is 
        to set its Y-coordinate offscreen.
        """
        self.x = data # - 8
        self.hide_check()
    
    def extract_tile_number(self, data):
        """
        extracts the Tile/Pattern Number
        Specifies the sprites Tile Number (00-FF). This (unsigned) value selects
        a tile from memory at 8000h-8FFFh. In CGB Mode this could be either in
        VRAM Bank 0 or 1, depending on Bit 3 of the following byte.
        In 8x16 mode, the lower bit of the tile number is ignored. Ie. the 
        upper 8x8 tile is "NN AND FEh", and the lower 8x8 tile is "NN OR 01h".
        """
        self.tile_number = data
    
    def extract_attributes_and_flags(self, data):
        """
        extracts the Attributes/Flags:
        Bit7   OBJ-to-BG Priority (0=OBJ Above BG, 1=OBJ Behind BG color 1-3)
                 (Used for both BG and Window. BG color 0 is always behind OBJ)
        Bit6   Y flip          (0=Normal, 1=Vertically mirrored)
        Bit5   X flip          (0=Normal, 1=Horizontally mirrored)
        Bit4   Palette number  **Non CGB Mode Only** (0=OBP0, 1=OBP1)
        """
        self.object_behind_background   = bool(data  & (1 << 7))
        self.x_flipped                  = bool(data  & (1 << 6))
        self.y_flipped                  = bool(data  & (1 << 5))
        self.palette_number             = bool(data  & (1 << 3)) 
        
        
    def hide_check(self):
        if self.y <= 0  or self.y >= 160:
            self.hidden = True
        elif self.x <= 0  or self.x >= 168:
            self.hidden = True
        else:
            self.hidden = False
        
    def get_tile_number(self):
        return self.tile.id
    
    def set_tile_number(self, tile_number):
        self.tile = self.video.tiles[tile_number]
        
    def get_width(self):
        return 8
    
    def get_height(self):
        if self.big_size:
            return 2*8
        else:
            return 8
         
    def overlaps_on_line(self, sprite, line):
        return False
    
    def intersects_line(self, line):
        return line >= self.y and line <= self.y + self.get_height()
    
    def draw(self):
        pass
    
    def draw_overlapped(self):
        pass
    
# -----------------------------------------------------------------------------
    
    
class Tile(object):
    
    def __init__(self):
        pass

    def set_tile_data(self, data):
        pass

    def get_selected_tile_map_space(self):
        pass
# -----------------------------------------------------------------------------

class Window(object):
    
    def __init__(self, video):
        self.video = video
        self.reset()

    def reset(self):
        self.x       = 0
        self.y       = 0
        self.line_y  = 0
        self.enabled = False
        self.upper_tile_map_selected  = False
        
    def update_line_y(self, data):
         # don't draw window if it was not enabled and not being drawn before
        if not self.enabled and (data & 0x20) != 0 and \
        self.line_y == 0 and self.video.line_y > self.y:
            self.line_y = 144    
    
    def get_tile_map_space(self):
        #if (self.control.read() & mask) != 0:
        if self.upper_tile_map_selected:
            return constants.VRAM_MAP_B
        else:
            return constants.VRAM_MAP_A
        
    def draw_line(self, line_y):
        if line_y  < self.y or self.x >= 167 or \
           self.line_y >= 144:
                return
        else:
            tile_map, tile_data = self.prepare_window_data()
            self.video.draw_tiles(self.x + 1, tile_map, tile_data)
            self.line_y += 1

    def prepare_window_data(self):
        tile_map   = self.get_tile_map_space()
        tile_map  += (self.line_y >> 3) << 5
        tile_data  = self.video.control.get_selected_tile_data_space()
        tile_data += (self.line_y & 7) << 1
        return tile_map, tile_data;
        
# -----------------------------------------------------------------------------

class Background(object):
    
    def __init__(self, video):
        self.video = video
        self.reset()
        
    def reset(self):
        # SCROLLX and SCROLLY hold the coordinates of background to
        # be displayed in the left upper corner of the screen.
        self.scroll_x   = 0
        self.scroll_y   = 0
        self.enabled    = True
        self.upper_tile_map_selected = False
      
    def get_tile_map_space(self):
        #if (self.control.read() & mask) != 0:
        if self.upper_tile_map_selected:
            return constants.VRAM_MAP_B
        else:
            return constants.VRAM_MAP_A
          
    def draw_clean_line(self, line_y):
        for x in range(8+160+8):
            self.video.line[x] = 0x00
    
    def draw_line(self, line_y):
        y          = (self.scroll_y + line_y) & 0xFF
        x          = self.scroll_x            & 0xFF
        tile_map, tile_data = self.prepare_background_data(x, y)
        self.video.draw_tiles(8 - (x & 7), tile_map, tile_data)
        
    def prepare_background_data(self, x, y):
        tile_map   = self.get_tile_map_space()
        tile_map  += ((y >> 3) << 5) + (x >> 3)
        tile_data  = self.video.control.get_selected_tile_data_space()
        tile_data += (y & 7) << 1
        return tile_map, tile_data
    
        
# -----------------------------------------------------------------------------

class Video(iMemory):

    def __init__(self, video_driver, interrupt, memory):
        assert isinstance(video_driver, VideoDriver)
        self.driver                 = video_driver
        self.v_blank_interrupt_flag = interrupt.v_blank
        self.lcd_interrupt_flag     = interrupt.lcd
        self.window                 = Window(self)
        self.background             = Background(self)
        self.status                 = StatusRegister(self)
        self.control                = ControlRegister(self.window, 
                                                      self.background)
        self.memory                 = memory
        self.create_tile_maps()
        self.create_sprites()
        self.reset()
    
    def create_tile_maps(self):
        # create the maxumal possible sprites
        self.tile_map_0 = [None] * 32 * 32
        self.tile_map_1 = [None] * 32 * 32
        self.tile_maps = [self.tile_map_0, self.tile_map_1]
    
    def update_tile(self, address, data):
        # XXX to implement
        pass
    
    def create_sprites(self):
        self.sprites = [None] * 40
        for i in range(40):
            self.sprites[i] = Sprite(self)

    def update_all_sprites(self):
        for i in range(40):
            address = 1 * 4
            self.sprites[i].set_data(self.oam[address + 0],
                                     self.oam[address + 1],
                                     self.oam[address + 2],
                                     self.oam[address + 3])
            
    def update_sprite(self, address, data):
        address -= constants.OAM_ADDR
        # address divided by 4 gives the correct sprite, each sprite has 4
        # bytes of attributes
        sprite_id = int(math.floor(address / 4))
        # XXX why cant I use None here
        attribute = [-1] * 4
        # assign the data to the correct attribute
        attribute[address % 4] = data
        self.sprites[sprite_id].set_data(attribute[0], attribute[1], 
                                         attribute[2], attribute[3])
       
         
    def reset(self):
        self.control.reset()
        self.status.reset()
        self.background.reset()
        self.window.reset()
        self.cycles     = constants.MODE_2_TICKS
        self.line_y     = 0
        self.line_y_compare = 0
        self.dma        = 0xFF
        # window position
        self.background_palette = 0xFC
        self.object_palette_0   = 0xFF 
        self.object_palette_1   = 0xFF

        self.transfer   = True
        self.display    = True
        self.v_blank    = True
        self.dirty      = True

        self.vram       = [0] * constants.VRAM_SIZE
        # Object Attribute Memory
        self.oam        = [0] * constants.OAM_SIZE
        
        self.line       = [0] * (8 + 160 + 8)
        self.objects    = [0] * constants.OBJECTS_PER_LINE
        self.palette    = [0] * 1024
        
        self.frames     = 0
        self.frame_skip = 0
    
    # Read Write shared memory -------------------------------------------------
    
    def write(self, address, data):
        address = int(address)
        # assert data >= 0x00 and data <= 0xFF
        if address == constants.LCDC :
            self.set_control(data)
        elif address == constants.STAT:
            self.set_status(data)
        elif address == constants.SCY:
            self.set_scroll_y(data)
        elif address == constants.SCX:
            self.set_scroll_x(data)
        #elif address == constants.LY:
        #    Read Only: line_y
        #    pass
        elif address == constants.LYC:
            self.set_line_y_compare(data)
        elif address == constants.DMA:
            self.set_dma(data)
        elif address == constants.BGP:
            self.set_background_palette(data)
        elif address == constants.OBP0:
            self.set_object_palette_0(data)
        elif address == constants.OBP1:
            self.set_object_palette_1(data)
        elif address == constants.WY:
            self.set_window_y(data)
        elif address == constants.WX:
            self.set_window_x(data)
        elif constants.OAM_ADDR <= address < \
        constants.OAM_ADDR + constants.OAM_SIZE:
            self.set_oam(address, data)
        elif constants.VRAM_ADDR <= address < \
        constants.VRAM_ADDR + constants.VRAM_SIZE:
            self.set_vram(address, data)
            
    def read(self, address):
        if address == constants.LCDC:
            return self.get_control()
        elif address == constants.STAT:
            return self.get_status()
        elif address == constants.SCY:
            return self.get_scroll_y()
        elif address == constants.SCX:
            return self.get_scroll_x()
        elif address == constants.LY:
            return self.get_line_y()
        elif address == constants.LYC:
            return self.get_line_y_compare()
        elif address == constants.DMA:
            return self.get_dma()
        elif address == constants.BGP:
            return self.get_background_palette()
        elif address == constants.OBP0:
            return self.get_object_palette_0()
        elif address == constants.OBP1:
            return self.get_object_palette_1()
        elif address == constants.WY:
            return self.get_window_y()
        elif address == constants.WX:
            return self.get_window_x()
        elif constants.OAM_ADDR <= address < \
        constants.OAM_ADDR + constants.OAM_SIZE:
            return self.get_oam(address)
        elif constants.VRAM_ADDR <= address < \
        constants.VRAM_ADDR + constants.VRAM_SIZE:
            return self.get_vram(address)
        return 0xFF

    # Getters and Setters ------------------------------------------------------
    
    def get_frame_skip(self):
        return self.frame_skip

    def set_frame_skip(self, frame_skip):
        self.frame_skip = frame_skip
        
    def get_cycles(self):
        return self.cycles

    def get_control(self):
        return self.control.read()

    def set_control(self, data):
        if self.control.lcd_enabled != bool(data & 0x80):
            self.reset_control(data)
        self.window.update_line_y(data)
        self.control.write(data)

    def reset_control(self, data):
        # NOTE: do not reset LY=LYC flag (bit 2) of the STAT register (Mr. Do!)
        self.line_y  = 0
        if (data & 0x80) != 0:
            self.status.set_mode(0x02)
            self.cycles  = constants.MODE_2_TICKS
            self.display = False
        else:
            self.status.set_mode(0)
            self.cycles = constants.MODE_1_TICKS
            self.clear_frame()
                
    def get_status(self):
        return self.status.read(extend=True)

    def set_status(self, data):
        self.status.write(data)
        self.set_status_bug()
        
    def set_status_bug(self) :
        # Gameboy Bug
        if self.control.lcd_enabled and \
           self.status.get_mode() == 1 and \
           self.status.line_y_compare_check():
                self.lcd_interrupt_flag.set_pending()
        
    def get_scroll_x(self):
        """ see set_scroll_x """
        return self.background.scroll_x

    def set_scroll_x(self, data):
        """
        Specifies the position in the 256x256 pixels BG map (32x32 tiles) which 
        is to be displayed at the upper/left LCD display position.
        Values in range from 0-255 may be used for X/Y each, the video 
        controller automatically wraps back to the upper (left) position in BG
        map when drawing exceeds the lower (right) border of the BG map area.
        """
        self.background.scroll_x = data
        
    def get_scroll_y(self):
        """ see set_scroll_x """
        return self.background.scroll_y
                
    def set_scroll_y(self, data):
        """ see set_scroll_x """
        self.background.scroll_y = data
        
    def get_line_y(self):
        """ see set_line_y """
        return self.line_y
    
    def set_line_y(self):
        """
        The LY indicates the vertical line to which the present data is 
        transferred to the LCD Driver. The LY can take on any value between 0 
        through 153. The values between 144 and 153 indicate the V-Blank period.
        Writing will reset the counter.
        """
        pass

    def get_line_y_compare(self):
        """ see set_line_y_compare"""
        return self.line_y_compare

    def set_line_y_compare(self, data):
        """
        The gameboy permanently compares the value of the LYC and LY registers.
        When both values are identical, the coincident bit in the STAT register
        becomes set, and (if enabled) a STAT interrupt is requested.
        """
        self.line_y_compare = data
        if self.control.lcd_enabled:
            self.status.mode0.emulate_hblank_line_y_compare(stat_check=True)
                
    def get_dma(self):
        return self.dma

    def set_dma(self, data):
        """
        Writing to this register launches a DMA transfer from ROM or RAM to OAM
        memory (sprite attribute table). The written value specifies the
        transfer source address divided by 100h, ie. source & destination are:
            Source:      XX00-XX9F   ;XX in range from 00-F1h
            Destination: FE00-FE9F
        It takes 160 microseconds until the transfer has completed, during this
        time the CPU can access only HRAM (memory at FF80-FFFE). For this
        reason, the programmer must copy a short procedure into HRAM, and use
        this procedure to start the transfer from inside HRAM, and wait until
        the transfer has finished:
            ld  (0FF46h),a ;start DMA transfer, a=start address/100h
            ld  a,28h      ;delay...
            wait:          ;total 5x40 cycles, approx 200ms
            dec a          ;1 cycle
            jr  nz,wait    ;4 cycles
        Most programs are executing this procedure from inside of their VBlank
        procedure, but it is possible to execute it during display redraw also,
        allowing to display more than 40 sprites on the screen (ie. for example 
        40 sprites in upper half, and other 40 sprites in lower half of the
        screen).
        """
        self.dma = data
        for index in range(constants.OAM_SIZE):
            self.oam[index] = self.memory.read((self.dma << 8) + index)
        self.update_all_sprites()

    def get_background_palette(self):
        """ see set_background_palette"""
        return self.background_palette

    def set_background_palette(self, data):
        """
        This register assigns gray shades to the color numbers of the BG and 
        Window tiles.
          Bit 7-6 - Shade for Color Number 3
          Bit 5-4 - Shade for Color Number 2
          Bit 3-2 - Shade for Color Number 1
          Bit 1-0 - Shade for Color Number 0
        The four possible gray shades are:
          0  White
          1  Light gray
          2  Dark gray
          3  Black
        """
        if self.background_palette != data:
            self.background_palette = data
            self.dirty              = True

    def get_object_palette_0(self):
        return self.object_palette_0

    def set_object_palette_0(self, data):
        """
        This register assigns gray shades for sprite palette 0. It works exactly
        as BGP (FF47), except that the lower two bits aren't used because sprite
        data 00 is transparent.
        """
        if self.object_palette_0 != data:
            self.object_palette_0 = data
            self.dirty            = True

    def get_object_palette_1(self):
        return self.object_palette_1

    def set_object_palette_1(self, data):
        """
        This register assigns gray shades for sprite palette 1. It works exactly
        as BGP (FF47), except that the lower two bits aren't used because sprite
        data 00 is transparent.
        """
        if self.object_palette_1 != data:
            self.object_palette_1 = data
            self.dirty            = True

    def get_window_y(self):
        """ see set_window.y """
        return self.window.y

    def set_window_y(self, data):
        """
        Specifies the upper/left positions of the Window area. (The window is an
        alternate background area which can be displayed above of the normal
        background. OBJs (sprites) may be still displayed above or behinf the 
        window, just as for normal BG.)
        The window becomes visible (if enabled) when positions are set in range
        WX=0..166, WY=0..143. A postion of WX=7, WY=0 locates the window at
        upper left, it is then completly covering normal background.
        """
        self.window.y = data
        
    def get_window_x(self):
        return self.window.x

    def set_window_x(self, data):
        self.window.x = data

    def set_oam(self, address, data):
        """
        sets one byte of the object attribute memory.
        The object attribute memory stores the position and seme other
        attributes of the sprites
        """
        self.oam[address - constants.OAM_ADDR] = data & 0xFF
        #self.update_sprites(address)
        self.update_sprite(address, data)
        
    def get_oam(self, address):
        return self.oam[address - constants.OAM_ADDR]
        
    def set_vram(self, address, data):
       """
       sets one byte of the video memory.
       The video memroy contains the tiles used to display.
       """
       self.vram[address - constants.VRAM_ADDR] = data & 0xFF
       self.update_tile(address, data)
    
    def get_vram(self, address):
        return self.vram[address - constants.VRAM_ADDR]
    
    # emulation ----------------------------------------------------------------

    def emulate(self, ticks):
        if self.control.lcd_enabled:
            self.cycles -= int(ticks)
            while self.cycles <= 0:
                self.current_mode().emulate()

    def current_mode(self):
        return self.status.current_mode

    
    
    # graphics handling --------------------------------------------------------
    
    def draw_frame(self):
        self.driver.update_display()

    def clear_frame(self):
        self.clear_pixels()
        self.driver.update_display()

    def draw_line(self):
        if self.background.enabled:
            self.background.draw_line(self.line_y)
        else:
            self.background.draw_clean_line(self.line_y)
        if self.window.enabled:
            self.window.draw_line(self.line_y)
        if self.control.sprites_enabled:
            self.draw_sprites_line()
        self.draw_pixels_line()

    def draw_sprites_line_new(self):
        sprites_on_line = self.get_active_sprites_on_line(self.line_y)
        
        last_sprite = sprites_on_line[0]
        last_sprite.draw()
        
        for sprite in sprites_on_line[1:]:
            if sprite.overlaps_on_line(last_sprite, self.line_y):
                sprite.draw_overlapped()
            else:
                sprite.draw()
            
    def get_active_sprites_on_line(self, line_y):
        found = []
        for i in range(len(self.sprites)):
            if self.sprites[i].intersects_line(line_y) and \
            self.sprites[i].enabled:
                found.append(self.sprites[i])
        return found
    
    def draw_sprites_line(self):
        count = self.scan_sprites()
        lastx = 176
        for index in range(176, count):
            data    = self.objects[index]
            x       = (data >> 24) & 0xFF
            flags   = (data >> 12) & 0xFF
            address = data & 0xFFF
            if (x + 8 <= lastx):
                self.draw_object_tile(x, address, flags)
            else:
                self.draw_overlapped_object_tile(x, address, flags)
            lastx = x

    def scan_sprites(self):
        count = 0
        # search active objects
        for offset in range(0, 4*40, 4):
            y = self.oam[offset + 0]
            x = self.oam[offset + 1]
            if (y <= 0 or y >= 144 + 16 or x <= 0 or x >= 168):
                continue
            tile  = self.oam[offset + 2]
            flags = self.oam[offset + 3]
            y     = self.line_y - y + 16
            if self.control.big_sprite_size_selected:
                # 8x16 tile size
                if (y < 0 or y > 15):
                    continue
                # Y flip
                if ((flags & 0x40) != 0):
                    y = 15 - y
                tile &= 0xFE
            else:
                # 8x8 tile size
                if (y < 0 or y > 7):
                    continue
                # Y flip
                if ((flags & 0x40) != 0):
                    y = 7 - y
            self.objects[count] = (x << 24) + (count << 20) + (flags << 12) + \
                                  (tile << 4) + (y << 1)
            count += 1
            if count >= constants.OBJECTS_PER_LINE:
                break
        self.sort_scan_sprite(count)
        return count

    def sort_scan_sprite(self, count):
        # sort objects from lower to higher priority
        for index in range(count):
            rightmost = index
            for number in range(index+1, count):
                if (self.objects[number] >> 20) > \
                   (self.objects[rightmost] >> 20):
                    rightmost = number
            if rightmost != index:
                data                    = self.objects[index]
                self.objects[index]     = self.objects[rightmost]
                self.objects[rightmost] = data

    def draw_tiles(self, x, tile_map, tile_data):
        while x < 168:
            if self.control.background_and_window_lower_tile_data_selected:
                tile = self.vram[tile_map]
            else:
                tile = (self.vram[tile_map] ^ 0x80) & 0xFF
            self.draw_tile(x, tile_data + (tile << 4))
            tile_map = (tile_map & 0x1FE0) + ((tile_map + 1) & 0x001F)
            x += 8
     
    def draw_tile(self, x, address):
        pattern =  self.get_pattern(address)
        for i in range(0, 8):
            self.line[x + i] = (pattern >> (7-i)) & 0x0101
                   
    def get_pattern(self, address):
        return self.vram[address] +(self.vram[address + 1]) << 8


    def draw_object_tile(self, x, address, flags):
        self.draw_object(set_tile_line_call_wrapper(self), x, address, flags)
                      
    def set_tile_line(self, pos, color, mask):
        self.line[pos] |= color | mask

    def draw_overlapped_object_tile(self, x, address, flags):
        self.draw_object(set_overlapped_object_line_call_wrapper(self), 
                         x, address, flags)
        
    def set_overlapped_object_line(self, pos, color, mask):
        self.line[pos] = (self.line[pos] & 0x0101) | color | mask
        
    def draw_object(self, caller, x, address, flags):
        pattern = self.get_pattern(address)
        mask    = 0
        # priority
        if (flags & 0x80) != 0:
            mask |= 0x0008
        # palette
        if (flags & 0x10) != 0:
            mask |= 0x0004
        if (flags & 0x20) != 0:
            self.draw_object_flipped(x, pattern, mask, caller)
        else:
            self.draw_object_normal(x, pattern, mask, caller)
            
    def draw_object_flipped(self, x, pattern, mask, caller):
        color = pattern << 1
        if (color & 0x0202) != 0:
            caller.call(x, color, mask)
        for i in range(0, 7):
            color = pattern >> i
            if (color & 0x0202) != 0:
                caller.call(x + i + 1, color, mask)
                
    def draw_object_normal(self, x, pattern, mask, caller):
        for i in range(0, 7):
            color = pattern >> (6-i)
            if (color & 0x0202) != 0:
                caller.call(x+1, color, mask)
        color = pattern << 1
        if (color & 0x0202) != 0:
            caller.call(x+7, color, mask)

    def draw_pixels_line(self):
        self.update_palette()
        pixels = self.driver.get_pixels()
        offset = self.line_y * self.driver.get_width()
        for x in range(8, 168, 4):
            for i in range(0,4):
                pixels[offset + i] = self.palette[self.line[x + i]]
            offset += 4

    def clear_pixels(self):
        self.driver.clear_pixels()

    def update_palette(self):
        if not self.dirty: return
        # bit 4/0 = BG color, 
        # bit 5/1 = OBJ color, 
        # bit 2   = OBJ palette, 
        # bit 3   = OBJ priority
        for pattern in range(0, 64):
            #color
            if (pattern & 0x22) == 0 or \
               ((pattern & 0x08) != 0 and (pattern & 0x11) != 0):
                # OBJ behind BG color 1-3
                color = (self.background_palette >> ((((pattern >> 3) & 0x02) +\
                        (pattern & 0x01)) << 1)) & 0x03
             # OBJ above BG
            elif ((pattern & 0x04) == 0):
                color = (self.object_palette_0 >> ((((pattern >> 4) & 0x02) + \
                        ((pattern >> 1) & 0x01)) << 1)) & 0x03
            else:
                color = (self.object_palette_1 >> ((((pattern >> 4) & 0x02) +\
                        ((pattern >> 1) & 0x01)) << 1)) & 0x03
            index = ((pattern & 0x30) << 4) + (pattern & 0x0F)
            self.palette[index] = constants.COLOR_MAP[color]
            #self.palette[index] = color
        self.dirty = False

# ------------------------------------------------------------------------------

class VideoDriver(object):
    
    def __init__(self):
        self.width = int(constants.GAMEBOY_SCREEN_WIDTH)
        self.height = int(constants.GAMEBOY_SCREEN_HEIGHT)
        self.clear_pixels()
        
    def clear_pixels(self):
        self.pixels = [0] * self.width * self.height
            
    def get_width(self):
        return self.width
    
    def get_height(self):
        return selg.height
    
    def get_pixels(self):
        return self.pixels
    
    def update_display(self):
        self.clear_pixels()
        
