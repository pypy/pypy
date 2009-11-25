from pypy.lang.gameboy import constants
from pypy.lang.gameboy.video_sprite import Sprite
from pypy.lang.gameboy.video import Video
from pypy.lang.gameboy.test.test_video import get_video
from pypy.lang.gameboy.video_mode import Mode0, Mode1, Mode2, Mode3

import py

# ------------------------------------------------------------------------------


class CallChecker(object):
    def __init__(self):
        self.called = False
        
    def __call__(self):
        self.called = True
        
def get_mode0():
    return Mode0(get_video())

def get_mode1():
    return Mode1(get_video())

def get_mode2():
    return Mode2(get_video())

def get_mode3():
    return Mode3(get_video())


# ------------------------------------------------------------------------------

def test_mode_emulate_hblank_line_y_compare():
    mode = get_mode0()
    
    mode.video.status.line_y_compare_flag == True
    mode.video.line_y = 0
    mode.video.line_y_compare = 1
    mode.emulate_hblank_line_y_compare()
    assert mode.video.status.line_y_compare_flag == False
    
    mode.video.line_y = 0
    mode.video.line_y_compare = 0
    mode.video.status.line_y_compare_flag = True
    mode.emulate_hblank_line_y_compare(stat_check=True)
    assert mode.video.status.line_y_compare_flag == True
    
    mode.video.status.line_y_compare_flag = True
    mode.emulate_hblank_line_y_compare(stat_check=False)
    assert mode.video.status.line_y_compare_flag
    
    mode.video.status.line_y_compare_flag = False
    mode.emulate_hblank_line_y_compare(stat_check=False)
    assert mode.video.status.line_y_compare_flag
    
    
def test_mode_line_y_line_y_compare_interrupt_check():
    mode = get_mode0()
    
    mode.video.status.line_y_compare_flag = False
    mode.video.status.line_y_compare_interrupt = False
    mode.line_y_line_y_compare_interrupt_check()
    assert mode.video.status.line_y_compare_flag
    assert mode.video.lcd_interrupt_flag.is_pending() == False
    
    mode.video.status.line_y_compare_flag = False
    mode.video.status.line_y_compare_interrupt = True
    mode.line_y_line_y_compare_interrupt_check()
    assert mode.video.status.line_y_compare_flag
    assert mode.video.lcd_interrupt_flag.is_pending()
    
def test_mode_ids():
    assert get_mode0().id() == 0
    assert get_mode1().id() == 1
    assert get_mode2().id() == 2
    assert get_mode3().id() == 3
    
# ------------------------------------------------------------------------------

def test_mode0_activate():
    mode = get_mode0()
    mode.video.cycles = 0
    mode.activate()
    assert mode.video.cycles == constants.MODE_0_TICKS
    
def test_mode0_h_blank_interrupt_check():
    mode = get_mode0()
    assert not mode.video.lcd_interrupt_flag.is_pending()
    mode.h_blank_interrupt_check();
    assert not mode.video.lcd_interrupt_flag.is_pending()
    
    mode.h_blank_interrupt = True
    mode.video.status.line_y_compare_check = lambda: True;
    mode.h_blank_interrupt_check();
    assert mode.video.lcd_interrupt_flag.is_pending()
    
    mode.h_blank_interrupt = False
    mode.video.lcd_interrupt_flag.set_pending(False)
    mode.video.status.line_y_compare_check = lambda: True;
    mode.h_blank_interrupt_check();
    assert not mode.video.lcd_interrupt_flag.is_pending()
    
    mode.h_blank_interrupt = False
    mode.video.status.line_y_compare_check = lambda: False;
    mode.h_blank_interrupt_check();
    assert not mode.video.lcd_interrupt_flag.is_pending()
    
def test_mode0_emulate_hblank():
    mode = get_mode0()
    mode.video.line_y = 0
    mode.video.status.current_mode = mode
    mode.emulate_hblank()
    assert mode.video.line_y == 1
    assert mode.video.status.get_mode() == 2
    
    mode.video.line_y = constants.GAMEBOY_SCREEN_HEIGHT-1
    mode.video.frames = 0
    mode.video.status.current_mode = mode
    mode.video.frame_skip = 10  
    mode.emulate_hblank()
    assert mode.video.line_y == constants.GAMEBOY_SCREEN_HEIGHT
    assert mode.video.frames == 1
    assert mode.video.v_blank == True
    assert mode.video.display == False
    assert mode.video.status.get_mode() == 1
    
    mode.video.line_y = constants.GAMEBOY_SCREEN_HEIGHT-1
    mode.video.frames = 0
    mode.video.display = True
    mode.video.draw_frame = CallChecker()
    mode.video.status.current_mode = mode
    mode.video.frame_skip = 10
    mode.emulate_hblank()
    assert mode.video.draw_frame.called == True
    assert mode.video.line_y == constants.GAMEBOY_SCREEN_HEIGHT
    assert mode.video.frames == 1
    assert mode.video.v_blank == True
    assert mode.video.display == False
    assert mode.video.status.get_mode() == 1
    