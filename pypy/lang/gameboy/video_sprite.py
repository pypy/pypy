
from pypy.lang.gameboy.constants import *

# -----------------------------------------------------------------------------

class Sprite(object):
    """   
           8px
       +--------+
       |        |      Normal Sprite size: 8 x 8px
       | upper  | 8px
       |        |
     (x,y)------+
       |        |      Big Sprite size:    8 x 16px
       | lower  | 8px
       |        |
       +--------+
            8x
    
    """
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
        self.palette_number = 0
        self.hidden         = True
        self.rest_attributes_and_flags = 0
        
    def get_data_at(self, address):
        address %= 4
        if address == 0:
            return self.y
        if address == 1:
            return self.x
        if address == 2:
            return self.tile_number
        if address == 3:
            return self.get_attributes_and_flags()

        # Making PyPy happy...
        raise Exception(("Cannot happen: ", address))
    
    def set_data(self, y, x, tile_number, flags):
        """
        extracts the sprite data from an oam entry
        """
        self.extract_y_position(y)
        self.extract_x_position(x)
        self.extract_tile_number(tile_number)
        self.extract_attributes_and_flags(flags)

    def set_data_at(self, address, data):
        """
        extracts the sprite data from an oam entry
        """
        address %= 4
        if address == 0:
            self.extract_y_position(data)
        if address == 1:
            self.extract_x_position(data)
        if address == 2:
            self.extract_tile_number(data)
        if address == 3:
            self.extract_attributes_and_flags(data)
        
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
        Bit6   X flip          (0=Normal, 1=Vertically mirrored)
        Bit5   Y flip          (0=Normal, 1=Horizontally mirrored)
        Bit4   Palette number  **Non CGB Mode Only** (0=OBP0, 1=OBP1)
        """
        self.object_behind_background   = bool(data & (1 << 7))
        self.y_flipped                  = bool(data & (1 << 6))
        self.x_flipped                  = bool(data & (1 << 5))
        self.palette_number             = bool(data & (1 << 4))
        self.rest_attributes_and_flags  = data & ((1<<3) +
                                                  (1<<2) +
                                                  (1<<1) +
                                                  (1<<0))
        
    def get_attributes_and_flags(self):
        value = 0
        value += int(self.object_behind_background) << 7
        value += int(self.y_flipped)                << 6
        value += int(self.x_flipped)                << 5
        value += int(self.palette_number)           << 4
        value += self.rest_attributes_and_flags
        return value
    
    # For testing purposes only
    def get_width(self):
        return SPRITE_SIZE
    
    def get_height(self):
        if self.big_size:
            return 2*SPRITE_SIZE
        else:
            return SPRITE_SIZE
        
    def get_tile_number(self):
        return self.tile_number
    
    def get_tile_address(self):
        address = self.get_tile_number()
        if self.big_size:
             address &= 0xFE
        return address
                            
    def get_tile_for_current_line(self, y):
        return self.get_tile_for_relative_line(self.current_line_y(y))

    def get_tile_for_relative_line(self, y):
        if (y < SPRITE_SIZE) ^ (self.big_size and self.y_flipped):
            return self.get_tile()
        else:
            return self.get_lower_tile() 
            
    def get_tile(self):
        return self.video.get_tile_at(self.get_tile_address())

    def get_lower_tile(self):
        return self.video.get_tile_at(self.get_tile_address() + 1)
                
    def hide_check(self):
        """returns and caches the general visibility of a Sprite.
        Updates the hidden property. See also intersects_current_line.""" 
        if self.y <= 0 or self.y >= GAMEBOY_SCREEN_WIDTH:
            self.hidden = True
        elif self.x <= 0 or self.x >= GAMEBOY_SCREEN_WIDTH+SPRITE_SIZE:
            self.hidden = True
        else:
            self.hidden = False
        return self.hidden
         
    def intersects_current_line(self, line_y):
        y = self.current_line_y(line_y)
        return y >= 0 and y < self.get_height()
    
    def is_shown_on_line(self, line_y):
        return not self.hidden and self.intersects_current_line(line_y)
         
    def current_line_y(self, y):
        return (y - self.y) + 2 * SPRITE_SIZE  
        
    def get_draw_y(self, line_y):
        y = self.current_line_y(line_y)
        if self.y_flipped:
            y = self.get_height() - 1 - y
        return y                          

    def draw(self, line, line_y, lastx):
        tile = self.get_tile_for_current_line(line_y)
        draw_y = self.get_draw_y(line_y)
        tile.draw_for_sprite(self, line, draw_y, lastx)

    def tile_mask(self):
        return (self.palette_number << 2) +\
               (self.object_behind_background << 3)

# -----------------------------------------------------------------------------

class Tile(object):
    
    def __init__(self):
        self.data = [0x00 for i in range(2*SPRITE_SIZE)]
       
    def set_tile_data(self, data):
        self.data = data

    def get_data_at(self, address):
        return self.data[address % (2*SPRITE_SIZE)]
    
    def set_data_at(self, address, data):
        self.data[address % (2*SPRITE_SIZE)] = data
    
    def get_data(self):
        return self.data

    def get_pattern_at(self, address):
        return self.get_data_at(address) +\
               (self.get_data_at(address + 1) << 8)

    def draw(self, line, x, y):
        pattern = self.get_pattern_at(y << 1)
        for i in range(SPRITE_SIZE):
            color = (pattern >> (SPRITE_SIZE - 1 - i)) & 0x0101
            line[x + i] = color
 
    def draw_for_sprite(self, sprite, line, y, lastx):
        if sprite.x_flipped:
            convert, offset =  1, 0           # 0-7
        else:
            convert, offset = -1, SPRITE_SIZE # 7-0

        pattern = self.get_pattern_at(y << 1)
        mask    = sprite.tile_mask()

        for i in range(SPRITE_SIZE):
            color = (pattern >> i) & 0x0101
            x = sprite.x + offset + i*convert
            if color:
                if sprite.x + SPRITE_SIZE > lastx:
                    # Overlapped.
                    line[x] &= 0x0101
                line[x] |= (color << 1) | mask

# -----------------------------------------------------------------------------

class Drawable(object):
    def __init__(self, tile_maps):
        self.tile_maps               = tile_maps
        self.enabled                 = False
        self.upper_tile_map_selected = False
        self.reset()

    def get_tile_map_space(self):
        return self.tile_maps[self.upper_tile_map_selected]

    def reset(self):
        raise Exception("Not implemented")

    def draw_tiles(self, x_start, tile_group, y, tile_data, index_flip, line, group_index=0):
        x = x_start
        while x < GAMEBOY_SCREEN_WIDTH+SPRITE_SIZE:
            tile_index = tile_group[group_index % TILE_GROUP_SIZE]
            tile_index ^= index_flip
            tile = tile_data[tile_index]
            tile.draw(line, x, y)
            group_index += 1
            x += SPRITE_SIZE

    def draw_line(self, line_y, tile_data, tile_index_flip, line):
        raise Exception("Not implemented")

    def draw_clean_line(self, line):
        raise Exception("Not implemented")      

# -----------------------------------------------------------------------------

class Window(Drawable):
    
    def reset(self):
        self.x       = 0
        self.y       = 0

    def draw_clean_line(self, line):
        pass
       
    def draw_line(self, line_y, tile_data, tile_index_flip, line):
        relative_y = line_y - self.y
        if relative_y >= 0 and relative_y < GAMEBOY_SCREEN_HEIGHT:

            tile_map   = self.get_tile_map_space()
            tile_group = tile_map[relative_y >> 3]

            self.draw_tiles(self.x + 1, tile_group,
                            relative_y, tile_data,
                            tile_index_flip, line)

# -----------------------------------------------------------------------------

class Background(Drawable):
    
    def reset(self):
        # SCROLLX and SCROLLY hold the coordinates of background to
        # be displayed in the left upper corner of the screen.
        self.scroll_x   = 0
        self.scroll_y   = 0
      
    def draw_clean_line(self, line):
        for x in range(len(line)):
            line[x] = 0x00
    
    def draw_line(self, line_y, tile_data, tile_index_flip, line):
        relative_y = (self.scroll_y + line_y) & 0xFF
        x = self.scroll_x

        tile_map = self.get_tile_map_space()
        tile_group = tile_map[relative_y >> 3]
        self.draw_tiles(8 - (x % 8), tile_group,
                        relative_y, tile_data,
                        tile_index_flip, line, x >> 3)
