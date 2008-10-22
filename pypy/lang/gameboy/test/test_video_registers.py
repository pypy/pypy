from pypy.lang.gameboy import constants
from pypy.lang.gameboy.video_register import ControlRegister
from pypy.lang.gameboy.video_register import StatusRegister
from pypy.lang.gameboy.video_sprite import Window
from pypy.lang.gameboy.video_sprite import Background
from pypy.lang.gameboy.test.test_video import get_video
import py


def get_control_register():
    video = get_video()
    return ControlRegister(Window(video), Background(video))

def get_status_register():
    return StatusRegister(get_video())

# ControlRegister --------------------------------------------------------------

def test_video_control_reset():
    control = get_control_register()
    assert control.read() == 0x91
    control.write(0xFF)
    assert control.read() == 0xFF
    control.reset()
    assert control.read() == 0x91
    
    
def test_video_control_read_write_properties():
    control   = get_control_register()
    for i in range(0xFF):
        control.write(i)
        assert control.read() == i
        
def test_video_control_get_selected_tile_data_space():
    control = get_control_register()
    
    control.window.upper_tile_map_selected = True
    assert control.get_selected_tile_data_space() == constants.VRAM_DATA_A
    
    control.window.upper_tile_map_selected = False
    assert control.get_selected_tile_data_space() == constants.VRAM_DATA_B
    
# StatusRegister ---------------------------------------------------------------

def test_video_status_reset():
    status = get_status_register()
    assert status.read(extend=True) == 0x02 + 0x80
    
    status.write(0x00, write_all=True)
    assert status.read(extend=True) == 0x00
    status.reset()
    assert status.read(extend=True) == 0x02 + 0x80
    
    status.write(0xFF, write_all=True)
    assert status.read(extend=True) == 0xFF
    status.reset()
    assert status.read(extend=True) == 0x02 + 0x80
    
def test_video_status_mode():
    status = get_status_register()
    assert status.get_mode() == 2
    for i in range(3):
        status.set_mode(i)
        assert status.get_mode() == i
        
    status.set_mode(4)
    assert status.get_mode()  == 0
    
def test_video_status_mode_properties():
    status = get_status_register()
    status.write(0x00, write_all=True)
    
    assert status.read(extend=True) == 0x00
    
    status.mode0.h_blank_interrupt = True
    assert status.read(extend=True) == (1 << 3)
    status.mode0.h_blank_interrupt = False
    
    status.mode1.v_blank_interrupt = True
    assert status.read(extend=True) == (1 << 4)
    status.mode1.v_blank_interrupt = False
    
    status.mode2.oam_interrupt = True
    assert status.read(extend=True) == (1 << 5)
    status.mode2.oam_interrupt = False
    
def test_video_status_get_mode():
    status = get_status_register()
    status.current_mode = status.mode0
    assert status.get_mode() == 0
    
    for i in range(0,4):
        status.current_mode = status.modes[i]
        assert status.get_mode() == status.modes[i].id()

def test_video_status_set_mode():
    status = get_status_register()
    for i in range(0,4):
        status.set_mode(i)
        assert status.current_mode == status.modes[i]
        
def test_video_status_line_y_compare_check():
    status = get_status_register()
    
    status.line_y_compare_flag = False
    status.line_y_compare_interrupt = False
    assert status.line_y_compare_check()
    
    status.line_y_compare_flag = True
    status.line_y_compare_interrupt = False
    assert status.line_y_compare_check()
    
    status.line_y_compare_flag = False
    status.line_y_compare_interrupt = True
    assert status.line_y_compare_check()
    
    status.line_y_compare_flag = True
    status.line_y_compare_interrupt = True
    assert not status.line_y_compare_check()