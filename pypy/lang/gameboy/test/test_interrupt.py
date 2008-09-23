
from pypy.lang.gameboy.interrupt import *
from pypy.lang.gameboy import constants

def get_interrupt():
    return Interrupt()



def test_reset():
    interrupt        = get_interrupt()
    assert interrupt.is_pending()         == False
    assert interrupt.get_enable_mask()    == 0
    assert interrupt.get_interrupt_flag() == 0xE0 | constants.VBLANK
    
    interrupt.enable = 1
    interrupt.flag   = ~constants.VBLANK
    interrupt.reset()
    assert interrupt.get_enable_mask()    == 0
    assert interrupt.get_interrupt_flag() == 0xE0 | constants.VBLANK
    

def test_set_get_enable_mask():
    interrupt = get_interrupt()
    assert interrupt.get_enable_mask() == 0x00
    
    interrupt.set_enable_mask(0x01)
    assert interrupt.v_blank.is_enabled()
    assert interrupt.get_enable_mask() == 0x01
    
    # enable all interrupts 0x01 - 0x10
    interrupt.set_enable_mask(0xFF)
    assert interrupt.v_blank.is_enabled()
    assert interrupt.get_enable_mask() == 0xFF
    
def test_is_pending():
    interrupt = get_interrupt()
    interrupt.v_blank.set_pending()
    assert interrupt.is_pending()     == False
    assert interrupt.is_pending(0x00) == False
    
    interrupt.set_enable_mask(0xFF)
    assert interrupt.is_pending()
    
    interrupt.set_enable_mask(0x00)
    assert interrupt.is_pending()     == False
    
def test_is_pending_common_masks():
    interrupt = get_interrupt()
    for flag in interrupt.interrupt_flags:
        interrupt.reset()
        interrupt.set_enable_mask(0xFF)
        assert interrupt.v_blank.is_pending()
        flag.set_pending(True)
        assert interrupt.is_pending(flag.mask)
    
def test_read_write():
    interrupt = get_interrupt()
    interrupt.write(constants.IE, 0x12)
    assert interrupt.get_enable_mask()  == 0x12
    assert interrupt.read(constants.IE) == 0x12
    
    interrupt.reset()
    interrupt.write(constants.IF, constants.LCD)
    assert interrupt.get_interrupt_flag() == 0xE0 | constants.LCD
    assert interrupt.read(constants.IF)   == 0xE0 | constants.LCD
