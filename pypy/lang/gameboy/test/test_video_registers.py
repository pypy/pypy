from pypy.lang.gameboy import constants
from pypy.lang.gameboy.video import ControlRegister
from pypy.lang.gameboy.video import StatusRegister
from pypy.lang.gameboy.video import Window
from pypy.lang.gameboy.video import Background
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
