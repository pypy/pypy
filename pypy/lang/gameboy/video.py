"""
 PyGirl Emulator
 LCD Video Display Processor
"""
import math
import operator
from pypy.lang.gameboy.constants import *
from pypy.lang.gameboy.ram import iMemory
from pypy.lang.gameboy.cpu import process_2s_complement
from pypy.lang.gameboy.video_register import ControlRegister, StatusRegister
from pypy.lang.gameboy.video_sprite import Sprite, Tile, Background, Window
from pypy.lang.gameboy.video_mode import Mode0, Mode1, Mode2, Mode3

# -----------------------------------------------------------------------------

class Video(iMemory):

    def __init__(self, video_driver, interrupt, memory):
        assert isinstance(video_driver, VideoDriver)
        self.driver                 = video_driver
        self.v_blank_interrupt_flag = interrupt.v_blank
        self.lcd_interrupt_flag     = interrupt.lcd
        self.create_tile_maps()
        self.window                 = Window(self.tile_maps)
        self.background             = Background(self.tile_maps)
        self.status                 = StatusRegister(self)
        self.control                = ControlRegister(self, self.window, 
                                                      self.background)
        self.memory                 = memory
        self.create_tiles()
        self.create_sprites()
        self.reset()
    
    # -----------------------------------------------------------------------
    
    def create_tile_maps(self):
        # create the maximal possible sprites
        self.tile_map_0 = self.create_tile_map()
        self.tile_map_1 = self.create_tile_map()
        self.tile_maps = [self.tile_map_0, self.tile_map_1]
    
    def create_tile_map(self):
        return [self.create_tile_group() for i in range(TILE_MAP_SIZE)]

    def create_tile_group(self):
        return [0x00 for i in range(TILE_GROUP_SIZE)]

    def create_tiles(self):
        tile_data_overlap = self.create_tile_data()
        self.tile_data_0 = self.create_tile_data() + tile_data_overlap
        self.tile_data_1 = tile_data_overlap + self.create_tile_data()
        self.tile_data = [self.tile_data_0, self.tile_data_1]

    def create_tile_data(self):
        return [Tile() for i in range(TILE_DATA_SIZE / 2)]
        
    def update_tile(self, address, data):
        self.get_tile(address).set_data_at(address, data);

    def get_tile_at(self, tile_index):
        if tile_index < TILE_DATA_SIZE:
            return self.tile_data_0[tile_index]
        else:
            return self.tile_data_1[tile_index - TILE_DATA_SIZE / 2]
    
    def get_tile(self, address):
        tile_index = (address - TILE_DATA_ADDR) >> 4
        return self.get_tile_at(tile_index)

    def select_tile_group_for(self, address):
        tile_map_index = address - TILE_MAP_ADDR #) >> 1
        if tile_map_index < TILE_MAP_SIZE * TILE_GROUP_SIZE:
            map = self.tile_map_0
        else:
            map = self.tile_map_1
            tile_map_index -= TILE_MAP_SIZE * TILE_GROUP_SIZE
        tile_group = map[tile_map_index >> 5]
        return tile_group, tile_map_index & 0x1F

    def get_selected_tile_data_space(self):
        return self.tile_data[not self.control.lower_tile_data_selected]

    def get_tile_map(self, address):
        tile_group, group_index = self.select_tile_group_for(address)
        return tile_group[group_index]

    def update_tile_map(self, address, data):
        tile_group, group_index = self.select_tile_group_for(address)
        tile_group[group_index] = data
    
    # -----------------------------------------------------------------------
    def create_sprites(self):
        self.sprites = [None] * MAX_SPRITES
        for i in range(MAX_SPRITES):
            self.sprites[i] = Sprite(self)

    def update_all_sprites(self):
        # TODO: TEST!
        for i in range(MAX_SPRITES):
            address = i * 4
            self.sprites[i].set_data(self.oam[address + 0],
                                     self.oam[address + 1],
                                     self.oam[address + 2],
                                     self.oam[address + 3])
            
    def update_sprite(self, address, data):
        self.get_sprite(address).set_data_at(address, data)
        
    def update_sprite_size(self):
        for sprite in self.sprites:
            sprite.big_size = self.control.big_sprites 

    def get_sprite_at(self, sprite_index):
        return self.sprites[sprite_index]       

    def get_sprite(self, address):
        address -= OAM_ADDR
        # address divided by 4 gives the correct sprite, each sprite has 4
        # bytes of attributes
        return self.get_sprite_at(address / 4)
        
    # -----------------------------------------------------------------------
         
    def reset(self):
        self.control.reset()
        self.status.reset()
        self.background.reset()
        self.window.reset()
        self.cycles     = MODE_2_TICKS
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

        # self.vram       = [0] * VRAM_SIZE
        # Object Attribute Memory
        self.oam        = [0] * OAM_SIZE
        
        #XXX remove those dumb helper "shown_sprites"
        self.line       = [0] * (SPRITE_SIZE + GAMEBOY_SCREEN_WIDTH + SPRITE_SIZE)
        self.shown_sprites    = [None] * SPRITES_PER_LINE
        self.palette    = [0] * 1024
        
        self.frames     = 0
        self.frame_skip = 0
    
    # Read Write shared memory -------------------------------------------------
    
    def write(self, address, data):
        address = int(address)
        # assert data >= 0x00 and data <= 0xFF
        if address == LCDC :
            self.set_control(data)
        elif address == STAT:
            self.set_status(data)
        elif address == SCY:
            self.set_scroll_y(data)
        elif address == SCX:
            self.set_scroll_x(data)
        #elif address == LY:
        #    Read Only: line_y
        #    pass
        elif address == LYC:
            self.set_line_y_compare(data)
        elif address == DMA:
            self.set_dma(data)
        elif address == BGP:
            self.set_background_palette(data)
        elif address == OBP0:
            self.set_object_palette_0(data)
        elif address == OBP1:
            self.set_object_palette_1(data)
        elif address == WY:
            self.set_window_y(data)
        elif address == WX:
            self.set_window_x(data)
        elif OAM_ADDR <= address < \
        OAM_ADDR + OAM_SIZE:
            self.set_oam(address, data)
        elif VRAM_ADDR <= address < \
        VRAM_ADDR + VRAM_SIZE:
            self.set_vram(address, data)
            
    def read(self, address):
        if address == LCDC:
            return self.get_control()
        elif address == STAT:
            return self.get_status()
        elif address == SCY:
            return self.get_scroll_y()
        elif address == SCX:
            return self.get_scroll_x()
        elif address == LY:
            return self.get_line_y()
        elif address == LYC:
            return self.get_line_y_compare()
        elif address == DMA:
            return self.get_dma()
        elif address == BGP:
            return self.get_background_palette()
        elif address == OBP0:
            return self.get_object_palette_0()
        elif address == OBP1:
            return self.get_object_palette_1()
        elif address == WY:
            return self.get_window_y()
        elif address == WX:
            return self.get_window_x()
        elif OAM_ADDR <= address < \
        OAM_ADDR + OAM_SIZE:
            return self.get_oam(address)
        elif VRAM_ADDR <= address < \
        VRAM_ADDR + VRAM_SIZE:
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
        self.control.write(data)

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
        # copy the memory region
        for index in range(OAM_SIZE):
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
        background. OBJs (sprites) may be still displayed above or behind the 
        window, just as for normal BG.)
        The window becomes visible (if enabled) when positions are set in range
        WX=0..166, WY=0..143. A postion of WX=7, WY=0 locates the window at
        upper left, it is then completely covering normal background.
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
        self.oam[address - OAM_ADDR] = data & 0xFF
        self.update_sprite(address, data)
        
    def get_oam(self, address):
        return self.get_sprite(address).get_data_at(address);
        
    def set_vram(self, address, data):
        """
        sets one byte of the video memory.
        The video memory contains the tiles used to display.
        """
        if address < TILE_MAP_ADDR:
            self.update_tile(address, data)
        else:
            self.update_tile_map(address, data)
    
    def get_vram(self, address):
        if address < TILE_MAP_ADDR:
            return self.get_tile(address).get_data_at(address)
        else:
            return self.get_tile_map(address)
    
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
        self.driver.update_gb_display()

    def clear_frame(self):
        self.driver.clear_gb_pixels()
        self.driver.update_gb_display()

    def tile_index_flip(self):
        if self.control.lower_tile_data_selected:
            return 0
        else:
            return 1 << 7 # First and last 128 tiles are swapped.

    def draw_window(self, window, line_y, line):
        if window.enabled:
            tile_data = self.get_selected_tile_data_space()
            tile_index_flip = self.tile_index_flip()
            window.draw_line(line_y, tile_data, tile_index_flip, line) 
        else:
            window.draw_clean_line(self.line)

    def draw_line(self):
        # XXX We should check if this is necessary for each line.
        self.update_palette()
        self.draw_window(self.background, self.line_y, self.line)
        self.draw_window(self.window, self.line_y, self.line)
        self.draw_sprites(self.line_y, self.line)
        self.send_pixels_line_to_driver()
    
    def draw_sprites(self, line_y, line):
        if not self.control.sprites_enabled: return
        count = self.scan_sprites(line_y)
        lastx = SPRITE_SIZE + GAMEBOY_SCREEN_WIDTH + SPRITE_SIZE
        for index in range(count):
            sprite = self.shown_sprites[index]
            sprite.draw(line, line_y, lastx)
            lastx = sprite.x
            
    def scan_sprites(self, line_y):
        # search active shown_sprites
        count = 0
        for sprite in self.sprites:
            if sprite.is_shown_on_line(line_y):
                self.shown_sprites[count] = sprite
                count += 1
                if count >= SPRITES_PER_LINE:
                    break
        self.sort_scan_sprite(count)
        return count

    def sort_scan_sprite(self, count):
        # TODO: optimize :)
        # sort shown_sprites from high to low priority using the real tile_address
        for index in range(count):
            highest = index
            for right in range(index+1, count):
                if self.shown_sprites[right].x > self.shown_sprites[highest].x:
                    highest = right
            self.shown_sprites[index], self.shown_sprites[highest] = \
                    self.shown_sprites[highest], self.shown_sprites[index]

    def send_pixels_line_to_driver(self):
        for x in range(0, GAMEBOY_SCREEN_WIDTH):
            color = self.palette[self.line[SPRITE_SIZE + x]]
            self.driver.draw_gb_pixel(x, self.line_y, color)

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
            #self.palette[index] = COLOR_MAP[color]
            self.palette[index] = color
        self.dirty = False

# ------------------------------------------------------------------------------

class VideoDriver(object):
    
    def __init__(self):
        self.width  = GAMEBOY_SCREEN_WIDTH
        self.height = GAMEBOY_SCREEN_HEIGHT
        self.create_pixels()

    def clear_gb_pixels(self):
        for y in range(GAMEBOY_SCREEN_HEIGHT):
            for x in range(GAMEBOY_SCREEN_WIDTH):
                self.draw_gb_pixel(x, y, 0)

    def draw_gb_pixel(self, x, y, color):
        old = self.pixels[y][x]
        self.pixels[y][x] = color
        self.changed[y][x] = old != color

    def update_gb_display(self):
        self.update_display()

    def update_display(self):
        # Overwrite this method to actually put the pixels on a screen.
        pass

    def create_pixels(self):
        # any non-valid color is fine
        self.pixels = [[255] * self.width
                        for i in range(self.height)]
        self.changed = [[True] * self.width
                         for i in range(self.height)]
                        
