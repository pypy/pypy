import py
from pypy.lang.gameboy.timer import *
from pypy.lang.gameboy.interrupt import *
from pypy.lang.gameboy import constants


def get_timer():
    return Timer(Interrupt())

    
# ------------------------------------------------------------------------------


def test_reset(timer=None):
    if timer is None:
        timer = get_timer()
    assert timer.divider == 0
    assert timer.divider_cycles == constants.DIV_CLOCK
    assert timer.timer_counter  == 0
    assert timer.timer_modulo   == 0
    assert timer.timer_control  == 0
    assert timer.timer_cycles   == constants.TIMER_CLOCK[0]
    assert timer.timer_clock    == constants.TIMER_CLOCK[0]
    
    
def test_read_write():
    timer         = get_timer()
    timer.divider = 10
    value         = 0x11
    timer.write(constants.DIV, value)
    assert timer.get_divider()       == 0
    assert timer.read(constants.DIV) == 0
    
    timer.reset()
    timer.write(constants.TIMA, value)
    assert timer.get_timer_counter()  == value
    assert timer.read(constants.TIMA) == value
    timer.reset()
    
    timer.write(constants.TMA, value)
    assert timer.get_timer_modulo()  == value
    assert timer.read(constants.TMA) == value
    timer.reset()
    
    
def test_get_timer_control():
    timer = get_timer()
    value = 0x12
    timer.write(constants.TAC, value)
    assert timer.get_timer_control() == 0xF8 | value 
    assert timer.read(constants.TAC) == 0xF8 |value

def test_set_timer_control():
    timer = get_timer()
    value = 0x12
    timer.set_timer_control(value)
    assert timer.timer_control == value
    assert timer.timer_cycles  == constants.TIMER_CLOCK[value & 0x03]
    assert timer.timer_clock   == constants.TIMER_CLOCK[value & 0x03]
    timer.reset()
    timer.timer_control = value+1
    timer.timer_clock   = 0
    timer.timer_cycles  = 0
    timer.set_timer_control(value+1)
    assert timer.timer_control == value+1
    assert timer.timer_clock   == 0
    assert timer.timer_clock   == 0
    
def test_read_write_divider():
    timer         = get_timer()
    value         = 0x12
    timer.divider = value
    assert timer.get_divider() == timer.divider
    # divider resets on write
    timer.set_divider(value)
    assert timer.get_divider() == 0
    
def test_cycles():
    timer                = get_timer()
    value                = 10
    timer.divider_cycles = value
    assert timer.get_cycles() == timer.divider_cycles
    timer.timer_control = 0x04
    timer.timer_cycles  = value-1
    timer.timer_cycles  = value
    assert timer.get_cycles() == timer.timer_cycles
    
def test_emulate_divider():
    timer                = get_timer()
    timer.divider_cycles = 10
    timer.divider        = 1
    timer.emulate_divider(2)
    assert timer.divider        == 1
    assert timer.divider_cycles == 8
    
def test_test_emulate_divider_below_zero():
    timer                = get_timer()
    timer.divider_cycles = 0
    timer.divider        = 1
    timer.emulate_divider(2)
    assert timer.divider_cycles == constants.DIV_CLOCK - 2
    assert timer.divider        == 2
    
    timer.divider_cycles = 0
    timer.divider        = 1
    timer.emulate_divider(0)
    assert timer.divider_cycles == constants.DIV_CLOCK
    assert timer.divider        == 2
    
    timer.divider_cycles = 0
    timer.divider        = 0xFF
    timer.emulate_divider(2)
    assert timer.divider_cycles == constants.DIV_CLOCK - 2
    assert timer.divider        == 0
    
    timer.divider_cycles = 0
    timer.divider        = 0
    timer.emulate_divider(2*constants.DIV_CLOCK)
    assert timer.divider_cycles == constants.DIV_CLOCK
    assert timer.divider        == 3
    
def test_emulate_timer_timer_control_return():
    timer = get_timer()
    timer.timer_control = 0
    timer.timer_cycles  = -10
    timer.timer_counter = 3
    timer.emulate_timer(10)
    assert timer.timer_cycles  == -10
    assert timer.timer_counter == 3
    
def test_emulate_timer_timer_cycles_return():
    timer = get_timer()
    timer.timer_control = 0x04
    timer.timer_cycles  = 11
    cycles              = timer.timer_cycles
    timer.emulate_timer(10)
    assert timer.timer_cycles == 1
    
def test_emulate_timer_timer_cycles_timer_counter():
    timer = get_timer()
    timer.timer_control = 0x04
    timer.timer_counter = 0
    timer.timer_cycles  = 0
    timer.timer_clock   = 5
    timer.emulate_timer(10)
    assert timer.timer_counter == 3
    assert timer.timer_cycles  == 5
    timer.timer_control = 0x04
    timer.timer_counter = 0xFF
    timer.timer_modulo  = 5
    timer.timer_cycles  = 0
    timer.timer_clock   = 5
    timer.emulate_timer(10)
    assert timer.timer_counter == 2+5
    assert timer.timer_cycles  == 5
    
def test_emulate_timer_timer_cycles_timer_counter_single_0_pass():
    timer = get_timer()
    timer.timer_control = 0x04
    timer.timer_counter = 0xFF
    timer.timer_modulo  = 0
    timer.timer_cycles  = 0
    timer.timer_clock   = 5
    timer.emulate_timer(10)
    assert timer.timer_counter == 2
    assert timer.timer_cycles  == 5
    
    timer.timer_control = 0x04
    timer.timer_counter = 0xFF
    timer.timer_modulo  = 1
    timer.timer_cycles  = 0
    timer.timer_clock   = 5
    timer.emulate_timer(10)
    assert timer.timer_counter == 2+1
    assert timer.timer_cycles  == 5
    
    
def test_emulate_timer_timer_cycles_timer_counter_mutli_0_pass():
    timer = get_timer()
    timer.timer_control = 0x04
    timer.timer_counter = 0xFF
    timer.timer_modulo  = 0
    timer.timer_cycles  = 0
    timer.timer_clock   = 1
    # emulate 0xFF + 1+1 times => 2 zero passes
    timer.emulate_timer(0xFF+1)
    assert timer.timer_counter == 0
    assert timer.timer_cycles  == 1
    
    timer.timer_control = 0x04
    timer.timer_counter = 0xFF
    timer.timer_modulo  = 1
    timer.timer_cycles  = 0
    timer.timer_clock   = 1
    # emulate 0xFF + 1+1 times => 2 zero passes
    timer.emulate_timer(0xFF+1)
    assert timer.timer_counter == 2*1
    assert timer.timer_cycles  == 1
    
    # emulate n zero passes
    for i in range(1,10):
        timer.timer_control = 0x04
        timer.timer_counter = 0xFF
        timer.timer_modulo  = i
        timer.timer_cycles  = 0
        timer.timer_clock   = 1
        timer.emulate_timer((0xFF+1)*(i-1))
        assert timer.timer_counter == i*i
        assert timer.timer_cycles  == 1
    
    
    
def test_emulate_timer_interrupt():
    timer               = get_timer()
    ticks               = 0
    timer.timer_control = 0x04
    timer.timer_counter = -1
    # raise an interupt as we pass 0
    assert not timer.timer_interrupt_flag.is_pending()
    timer.timer_cycles = -timer.timer_clock+1
    timer.emulate_timer(ticks)
    assert timer.timer_cycles  == 1
    assert timer.timer_counter == timer.timer_modulo
    assert timer.timer_interrupt_flag.is_pending()
    
    
