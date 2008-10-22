"""
PyGirl Emulator
 
Timer and Divider
"""

from pypy.lang.gameboy import constants
from pypy.lang.gameboy.interrupt import *
from math import ceil
from pypy.lang.gameboy.ram import iMemory
import time
import math


class TimerControl(object):
    def __init__(self):
        self.reset()
        
    def reset(self):
        pass

class Timer(iMemory):

    def __init__(self, interrupt):
        assert isinstance(interrupt, Interrupt)
        self.timer_interrupt_flag = interrupt.timer
        self.reset()

    def reset(self):
        self.divider        = 0
        self.divider_cycles = constants.DIV_CLOCK
        self.timer_counter  = 0
        self.timer_modulo   = 0
        self.timer_control  = 0
        self.timer_cycles   = constants.TIMER_CLOCK[0]
        self.timer_clock    = constants.TIMER_CLOCK[0]

    def write(self,  address, data):
        if address == constants.DIV:
            self.set_divider(data)
        elif address == constants.TIMA:
            self.set_timer_counter(data)
        elif address == constants.TMA:
            self.set_timer_modulo(data)
        elif address == constants.TAC:
            self.set_timer_control(data)
    
    def read(self,  address):
        if address == constants.DIV:
            return self.get_divider()
        elif address == constants.TIMA:
            return self.get_timer_counter()
        elif address == constants.TMA:
            return self.get_timer_modulo()
        elif address == constants.TAC:
            return self.get_timer_control()
        return 0xFF

    def get_divider(self):
        return self.divider
    
    def set_divider(self,  data): 
        """ 
        This register is incremented at rate of 16384Hz (~16779Hz on SGB). 
        Writing any value to this register resets it to 00h. 
        """
        self.divider = 0

    def get_timer_counter(self):
        return self.timer_counter
    
    def set_timer_counter(self,  data):
        """
        TIMA
        This timer is incremented by a clock frequency specified by the TAC 
        register ($FF07). When the value overflows (gets bigger than FFh) then
        it will be reset to the value specified in TMA (FF06), and an interrupt
        will be requested, as described below.
        """
        self.timer_counter = data


    def get_timer_modulo(self):
        return self.timer_modulo
    
    def set_timer_modulo(self,  data):
        """
        When the TIMA overflows, this data will be loaded.
        """
        self.timer_modulo = data


    def get_timer_control(self):
        return 0xF8 | self.timer_control

    def set_timer_control(self,  data):
        """
        Bit 2    - Timer Stop  (0=Stop, 1=Start)
        Bits 1-0 - Input Clock Select
             00:   4096 Hz
             01: 262144 Hz
             10:  65536 Hz
             11:  16384 Hz
        """
        if (self.timer_control & 0x03) != (data & 0x03):
            self.timer_clock  = constants.TIMER_CLOCK[data & 0x03]
            self.timer_cycles = constants.TIMER_CLOCK[data & 0x03]
        self.timer_control = data


    def get_cycles(self):
        if (self.timer_control & 0x04) != 0 and \
            self.timer_cycles < self.divider_cycles:
                return self.timer_cycles
        return self.divider_cycles

    def emulate(self,  ticks):
        self.emulate_divider(ticks)
        self.emulate_timer(ticks)

    def emulate_divider(self,  ticks):
        self.divider_cycles -= ticks
        if self.divider_cycles > 0:
            return
        count                = int(math.ceil(-self.divider_cycles / 
                                   constants.DIV_CLOCK)+1)
        self.divider_cycles += count*constants.DIV_CLOCK
        self.divider         = (self.divider + count) % (0xFF+1);
            
    def emulate_timer(self,  ticks):
        if (self.timer_control & 0x04) == 0:
            return
        self.timer_cycles -= ticks
        while self.timer_cycles <= 0:
            self.timer_counter = (self.timer_counter + 1) & 0xFF
            self.timer_cycles += self.timer_clock
            self.timer_interrupt_check()
    
    def timer_interrupt_check(self):
        """
        Each time when the timer overflows (ie. when TIMA gets bigger than FFh),
        then an interrupt is requested by setting Bit 2 in the IF Register 
        (FF0F). When that interrupt is enabled, then the CPU will execute it by
        calling the timer interrupt vector at 0050h.
        """
        if self.timer_counter == 0x00:
            self.timer_counter = self.timer_modulo
            self.timer_interrupt_flag.set_pending()


# CLOCK DRIVER -----------------------------------------------------------------

class Clock(object):
    
    def __init__(self):
        pass
    
    def get_time(self):
        return int(time.time()*1000)
        
