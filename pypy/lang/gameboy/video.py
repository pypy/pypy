"""
 PyGirl Emulator
 constants.LCD Video Display Processor
"""
import math
import operator
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.constants import SPRITE_SIZE, GAMEBOY_SCREEN_WIDTH, \
                                        GAMEBOY_SCREEN_HEIGHT
from pypy.lang.gameboy.ram import iMemory
from pypy.lang.gameboy.cpu import process_2s_complement
from pypy.lang.gameboy.video_register import ControlRegister, StatusRegister
from pypy.lang.gameboy.video_sprite import Sprite, Tile, Background, Window
from pypy.lang.gameboy.video_mode import Mode0, Mode1, Mode2, Mode3

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
        #self.get_tile(address).set_data();
        pass
    
    def get_tile(self, address):
        # XXX to implement
        pass
    
    def reset_all_tiles(self):
        #for tile in self.tile_map_0:
        #    tile.reset()
        #for tile in self.tile_map_1:
        #    tile.reset()
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
        # XXX why cant I use None here
        attribute = [-1] * 4
        # assign the data to the correct attribute
        attribute[address % 4] = data
        self.get_sprite(address).set_data(attribute[0], attribute[1], 
                                          attribute[2], attribute[3])
       
    def get_sprite(self, address):
        address -= constants.OAM_ADDR
        # address divided by 4 gives the correct sprite, each sprite has 4
        # bytes of attributes
        return self.sprites[ int(math.floor(address / 4)) ]
        
    def reset_all_sprites(self):
        #for sprite in self.sprites:
        #    sprite.reset()
        pass
         
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
        self.reset_all_tiles()
        # Object Attribute Memory
        self.oam        = [0] * constants.OAM_SIZE
        self.reset_all_sprites()
        
        #XXX remove those dumb helper "objects"
        self.line       = [0] * (SPRITE_SIZE + GAMEBOY_SCREEN_WIDTH + SPRITE_SIZE)
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
        attributes of the sprites, this works only during the v-blank and
        the h-blank period.
        """
        self.oam[address - constants.OAM_ADDR] = data & 0xFF
        self.update_sprite(address, data)
        
    def get_oam(self, address):
        return self.get_sprite(address).get_data_at(address);
        
    def set_vram(self, address, data):
       """
       sets one byte of the video memory.
       The video memory contains the tiles used to display.
       """
       self.vram[address - constants.VRAM_ADDR] = data & 0xFF
       self.update_tile(address, data)
    
    def get_vram(self, address):
        #self.get_tile(address).get_data()[address % 4]
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
            #self.draw_sprites_line_new()
            self.draw_sprites_line()
        self.draw_pixels_line()

    def draw_sprites_line_new(self):
        sprites_on_line = self.get_drawable_sprites_on_line(self.line_y)
        
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
    
    def get_drawable_sprites_on_line(self, line_y):
        sprites_on_line = self.get_active_sprites_on_line(self.line_y)
        sprites_on_line = self.sort_drawable_sprites(sprites_on_line)
        # only 10 sprites per line
        return sprites_on_line[:constants.OBJECTS_PER_LINE]
    
    def sort_drawable_sprites(self, sprites):
        """
        returns an ordered list of selected sprites. 
        The order rules are as following:
        1. order by x -coordinates, lower first
        2. order by id, lower first
        """
        return sprites.sort(key=operator.itemgetter("x"))
    
    
    # -----------------------------------------------
    
    def draw_sprites_line(self):
        count = self.scan_sprites()
        lastx = 176
        for index in range(176, count):
            data    = self.objects[index]
            x       = (data >> 24) & 0xFF
            flags   = (data >> 12) & 0xFF
            address = data & 0xFFF
            if (x + SPRITE_SIZE <= lastx):
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
            if (y <= 0 or y >= SPRITE_SIZE + GAMEBOY_SCREEN_HEIGHT + SPRITE_SIZE
            or x <= 0 or x >= GAMEBOY_SCREEN_WIDTH + SPRITE_SIZE):
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
        while x < GAMEBOY_SCREEN_WIDTH+SPRITE_SIZE:
            if self.control.background_and_window_lower_tile_data_selected:
                tile = self.vram[tile_map]
            else:
                tile = (self.vram[tile_map] ^ 0x80) & 0xFF
            self.draw_tile(x, tile_data + (tile << 4))
            tile_map = (tile_map & 0x1FE0) + ((tile_map + 1) & 0x001F)
            x += SPRITE_SIZE
     
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
        for x in range(SPRITE_SIZE, GAMEBOY_SCREEN_WIDTH+SPRITE_SIZE, 4):
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
        
