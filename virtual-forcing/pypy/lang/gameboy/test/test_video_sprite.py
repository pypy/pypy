from pypy.lang.gameboy.constants import *
from pypy.lang.gameboy.video_sprite import Sprite
from pypy.lang.gameboy.video import Video
from pypy.lang.gameboy.test.test_video import get_video
import py



def get_sprite():
    return Sprite(get_video())


# Sprite Class test ------------------------------------------------------------

def test_standard_values(sprite=None):
    if sprite==None:
        sprite = get_sprite()
    #assert sprite.get_tile_number() == 0
    assert sprite.x == 0
    assert sprite.y == 0
    assert sprite.object_behind_background == False
    assert sprite.x_flipped == False
    assert sprite.y_flipped == False
    assert sprite.tile_number == 0
    
    
def test_reset():
    sprite = get_sprite()
    
   # sprite.set_tile_number(0x12)
   # assert sprite.get_tile_number() == 0x12
    
   # sprite.set_tile_number(0xFFF)
   # assert sprite.get_tile_number() == 0xFF
    
    sprite.x = 10
    assert sprite.x == 10
    
    sprite.y = 11
    assert sprite.y == 11
    
    sprite.object_behind_background = True
    assert sprite.object_behind_background == True
    
    sprite.x_flipped = True
    assert sprite.x_flipped == True
    
    sprite.y_flipped = True
    assert sprite.y_flipped == True
    
    sprite.use_object_pallette_1 = True
    assert sprite.use_object_pallette_1 == True
    
    sprite.reset()
    test_standard_values(sprite)

def test_video_sprite_read_write():
    sprite = get_sprite()
    for i in range(0xFF):
        sprite.set_data_at(0, i)
        assert sprite.get_data_at(0) == i
        
    for i in range(0xFF):
        sprite.set_data_at(1, i)
        assert sprite.get_data_at(1) == i
        
    for i in range(0xFF):
        sprite.set_data_at(2, i)
        assert sprite.get_data_at(2) == i
        
    for i in range(0xFF):
        sprite.set_data_at(3, i)
        assert sprite.get_data_at(3) == i
        
def test_size():
    sprite = get_sprite()
    sprite.big_size = False
    assert sprite.get_width() == 8
    assert sprite.get_height() == 8
    
    sprite.big_size = True
    assert sprite.get_width() == 8
    assert sprite.get_height() == 16

    
def test_hiddden_check():
    sprite = get_sprite()
    assert sprite.hidden
    
    sprite.y = 1
    sprite.x = 0
    sprite.hide_check()
    assert sprite.hidden
    
    sprite.y = 0
    sprite.x = 1
    sprite.hide_check()
    assert sprite.hidden
    
    sprite.y = 1
    sprite.x = 1
    sprite.hide_check()
    assert not sprite.hidden
    
    for y in range(1, 160-1):
        for x in range(1, 168-1):
            sprite.y = y
            sprite.x = x
            sprite.hide_check()
            assert not sprite.hidden
            
    for x in range(1, 168-1):
        sprite.y = 160
        sprite.x = x
        sprite.hide_check()
        assert sprite.hidden
    
    for y in range(1, 160-1):
        sprite.y = y
        sprite.x = 168
        sprite.hide_check()
        assert sprite.hidden
        
    
def test_intersects_line_normal_size():
    sprite = get_sprite()
    sprite.big_size = False
    sprite.y = 2*SPRITE_SIZE+1
    line_intersection_test(sprite)
    
def test_intersects_line_big_size():
    sprite = get_sprite()
    sprite.big_size = True
    sprite.y = 2*SPRITE_SIZE+1
    line_intersection_test(sprite)
    
def line_intersection_test(sprite):
    sprite.video.line_y = 0
    assert not sprite.intersects_current_line(sprite.video.line_y)
    for i in range(sprite.get_height()):
        sprite.video.line_y = i+1
        assert sprite.intersects_current_line(sprite.video.line_y), i
    sprite.video.line_y = sprite.get_height()+1
    assert not sprite.intersects_current_line(sprite.video.line_y)
    
    
# test sprite in video ---------------------------------------------------------
