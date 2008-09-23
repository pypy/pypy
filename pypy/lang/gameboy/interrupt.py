from pypy.lang.gameboy import constants
from pypy.lang.gameboy.ram import iMemory


class InterruptFlag(object):
    """
    An Interrupt Flag handles a single interrupt channel
    """
    def __init__(self, reset, mask, call_code):
        self._reset    = reset
        self.mask      = mask
        self.call_code = call_code
        self.reset()
        
    def reset(self):
        self._is_pending = self._reset
        self.enabled     = False
        
    def is_pending(self):
        return self._is_pending
    
    def set_pending(self, is_pending=True):
        self._is_pending = is_pending
        
    def is_enabled(self):
        return self.enabled

    def set_enabled(self, enabled):
        self.enabled = enabled
    
# --------------------------------------------------------------------

class Interrupt(iMemory):
    """
    PyGirl Emulator
    Interrupt Controller
    
    V-Blank Interrupt
    The V-Blank interrupt occurs ca. 59.7 times a second on a regular GB and ca.
    61.1 times a second on a Super GB (SGB). This interrupt occurs at the
    beginning of the V-Blank period (LY=144).
    During this period video hardware is not using video ram so it may be freely
    accessed. This period lasts approximately 1.1 milliseconds.
    
    LCDC Status Interrupt
    There are various reasons for this interrupt to occur as described by the STAT
    register ($FF40). One very popular reason is to indicate to the user when the
    video hardware is about to redraw a given LCD line. This can be useful for
    dynamically controlling the SCX/SCY registers ($FF43/$FF42) to perform special
        video effects.
        
    Joypad interrupt is requested when any of the above Input lines changes from
    High to Low. Generally this should happen when a key becomes pressed
    (provided that the button/direction key is enabled by above Bit4/5), 
    however, because of switch bounce, one or more High to Low transitions are 
    usually produced both when pressing or releasing a key.


    """
    
    def __init__(self):
        self.create_interrupt_flags()
        self.create_flag_list()
        self.reset()
        
    def create_interrupt_flags(self):
        self.v_blank  = InterruptFlag(True,  constants.VBLANK, 0x40)
        self.lcd      = InterruptFlag(False, constants.LCD,    0x48)
        self.timer    = InterruptFlag(False, constants.TIMER,  0x50)
        self.serial   = InterruptFlag(False, constants.SERIAL, 0x58)
        self.joypad   = InterruptFlag(False, constants.JOYPAD, 0x60)
        
    def create_flag_list(self):
        self.interrupt_flags = [ self.v_blank,
                                 self.lcd,
                                 self.timer,
                                 self.serial,
                                 self.joypad]

    def reset(self):
        self.set_enable_mask(0x0)
        for flag in self.interrupt_flags:
            flag.reset()
    
    
    def write(self, address, data):
        if  address == constants.IE:
            self.set_enable_mask(data)
        elif address == constants.IF:
            self.set_interrupt_flag(data)

    def read(self, address):
        if  address == constants.IE:
            return self.get_enable_mask()
        elif address == constants.IF:
            return self.get_interrupt_flag()
        return 0xFF
    
    
    def is_pending(self, mask=0xFF):
        return (self.get_enable_mask() & self.get_interrupt_flag() & mask) != 0
    
    def get_enable_mask(self):
        enabled = 0x00
        for interrupt_flag in self.interrupt_flags:
            if interrupt_flag.is_enabled():
                enabled |= interrupt_flag.mask
        return enabled | self.enable_rest_data;

    def set_enable_mask(self, enable_mask):
        for flag in self.interrupt_flags:
            flag.set_enabled(bool(enable_mask & flag.mask))
        self.enable_rest_data = enable_mask & 0xE0;
        
    
    def get_interrupt_flag(self):
        flag = 0x00
        for interrupt_flag in self.interrupt_flags:
            if interrupt_flag.is_pending():
                flag |= interrupt_flag.mask
        return flag | 0xE0

    def set_interrupt_flag(self, data):
        for flag in self.interrupt_flags:
            flag.set_pending((data & flag.mask) != 0)
