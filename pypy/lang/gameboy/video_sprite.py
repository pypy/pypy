
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.constants import SPRITE_SIZE, GAMEBOY_SCREEN_WIDTH, \
                                        GAMEBOY_SCREEN_HEIGHT

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
        self.tile_number    = 0
        self.hidden         = True
        self.rest_attributes_and_flags = 0
        
    def get_data_at(self, address):
        return self.get_data()[address % 4]
    
    def get_data(self):
        return [self.y, self.x, self.tile_number, self.get_attributes_and_flags()]
    
    def set_data(self, byte0=-1, byte1=-1, byte2=-1, byte3=-1):
        """
        extracts the sprite data from an oam entry
        """
        if byte0 is not -1:
            self.extract_y_position(byte0)
        if byte1 is not -1:
            self.extract_x_position(byte1)
        if byte2 is not -1:
            self.extract_tile_number(byte2)
        if byte3 is not -1:
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
        self.tile_number                = bool(data  & (1 << 4)) 
        self.rest_attributes_and_flags  = data  & (1+2+4+8)
        
    def get_attributes_and_flags(self):
        value = 0
        value += int(self.object_behind_background) << 7
        value += int(self.x_flipped)                << 6
        value += int(self.y_flipped)                << 5
        value += int(self.tile_number)              << 4
        value += self.rest_attributes_and_flags
        return value
        
    def hide_check(self):
        if self.y <= 0  or self.y >= GAMEBOY_SCREEN_WIDTH:
            self.hidden = True
        elif self.x <= 0  or self.x >= GAMEBOY_SCREEN_WIDTH+SPRITE_SIZE:
            self.hidden = True
        else:
            self.hidden = False
        
    def get_tile_number(self):
        return self.tile.id
    
    def get_width(self):
        return SPRITE_SIZE
    
    def get_height(self):
        if self.big_size:
            return 2*SPRITE_SIZE
        else:
            return SPRITE_SIZE
         
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
        self.reset()
        
    def reset(self):
        pass
    
    def set_tile_data(self, data):
        pass

    def get_pixel_data(self):
        return self.pixel_data
    
    def get_selected_tile_map_space(self):
        pass
    
    def get_data_at(self, address):
        return self.get_data()[address % self.byte_size()]
    
    def get_data():
        return []
    
    def byte_size(self):
        return 0
    
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
            self.line_y = GAMEBOY_SCREEN_HEIGHT    
    
    def get_tile_map_space(self):
        #if (self.control.read() & mask) != 0:
        if self.upper_tile_map_selected:
            return constants.VRAM_MAP_B
        else:
            return constants.VRAM_MAP_A
        
    def draw_line(self, line_y):
        if line_y  < self.y or self.x >= 167 or \
           self.line_y >= GAMEBOY_SCREEN_HEIGHT:
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
        for x in range(8+GAMEBOY_SCREEN_WIDTH+8):
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
    
      