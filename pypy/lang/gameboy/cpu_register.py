# ---------------------------------------------------------------------------

class AbstractRegister(object):
    def __init__(self):
        self.invalid = False
        
    def get(self, use_cycles=True):
        self.check_sync()
        return self._get(use_cycles)   
         
    def set(self, value, use_cycles=True):
        self.check_sync()
        self.invalidate_other()
        self._set(value, use_cycles)
        
    def sub(self, value, use_cycles=True):
        self.check_sync()
        self.invalidate_other()
        return self._sub(value, use_cycles)
        
    def add(self, value, use_cycles=True):
        self.check_sync()
        self.invalidate_other()
        return self._add(value, use_cycles)
        
    def _get(self, use_cycles):
        raise Exception("not implemented")
    
    def _set(self, value, use_cycles):
        raise Exception("not implemented")
        
    def _sub(self, value, use_cycles):
        raise Exception("not implemented")
        
    def _add(self, value, use_cycles):
        raise Exception("not implemented")
        
    def check_sync(self):
        if self.invalid:
            self.sync()
    
    def invalidate_other(self):
        raise Exception("not implemented")
            
    def sync(self):
        raise Exception("not implemented")
        

class Register(AbstractRegister):
    
    def __init__(self, cpu, value=0x00):
        AbstractRegister.__init__(self)
       # assert isinstance(cpu, CPU)
        self.reset_value = self.value = value
        self.double_register = None
        self.cpu = cpu
        if value != 0:
            self._set(value)
        
    def reset(self):
        self.value = self.reset_value
        
    def sync(self):
        if self.double_register is not None:
            self.double_register.sync_registers()
    
    def invalidate_other(self):
        if self.double_register is not None:
            self.double_register.invalid = True
    
    def _set(self, value, use_cycles=True):
        self.value = value & 0xFF
        if use_cycles:
            self.cpu.cycles -= 1
        
    def _get(self, use_cycles=True):
        return self.value
    
    def _add(self, value, use_cycles=True):
        self._set(self._get(use_cycles) + value, use_cycles)
        
    def _sub(self, value, use_cycles=True):
        self._set(self._get(use_cycles) - value, use_cycles)
    
#------------------------------------------------------------------------------

class DoubleRegister(AbstractRegister):
    
    def __init__(self, cpu, hi, lo, reset_value=0x0000):
        AbstractRegister.__init__(self)
        self.cpu = cpu
        self.invalid = True
        self.reset_value = reset_value
        self.hi = hi
        self.lo = lo
        self.hi.double_register = self
        self.lo.double_register = self
        self.value = 0x0000
    
    def reset(self):
        self.set(self.reset_value, use_cycles=False)
            
    def sync_registers(self):
        self.hi._set(self.value >> 8, use_cycles=False)            
        self.hi.invalid = False
        self.lo._set(self.value & 0xFF, use_cycles=False)          
        self.lo.invalid = False
        
    def sync(self):
        self.value = (self.hi._get(use_cycles=False)<<8) + \
                      self.lo._get(use_cycles=False)
        self.invalid = False

    def invalidate_other(self):
        self.hi.invalid = True
        self.lo.invalid = True
        
    def _set(self, value, use_cycles=True):
        self.value  = value & 0xFFFF
        if use_cycles:
            self.cpu.cycles -= 1
            
    def set_hi(self, hi=0, use_cycles=True):
        self.hi.set(hi, use_cycles)
    
    def set_lo(self, lo=0, use_cycles=True):
        self.lo.set(lo, use_cycles)
        
    def _get(self, use_cycles=True):
        return self.value
    
    def get_hi(self, use_cycles=True):
        return self.hi.get(use_cycles)
        
    def get_lo(self, use_cycles=True):
        return self.lo.get(use_cycles)

    def inc(self, use_cycles=True):
        self.add(1, use_cycles=False)
        if use_cycles:
            self.cpu.cycles -= 2

    def dec(self, use_cycles=True):
        self.add(-1, use_cycles=False)
        if use_cycles:
            self.cpu.cycles -= 2

    def _add(self, value, use_cycles=True):
        self.value += value
        self.value &= 0xFFFF
        if use_cycles:
            self.cpu.cycles -= 3

#------------------------------------------------------------------------------

class ReservedDoubleRegister(AbstractRegister):
    
    def __init__(self, cpu, reset_value=0x0000):
        AbstractRegister.__init__(self)
        self.cpu = cpu
        self.reset_value = reset_value
        self.value = 0x0000
    
    def reset(self):
        self.set(self.reset_value, use_cycles=False)
            
    def set(self, value, use_cycles=True):
        self.value  = value & 0xFFFF
        if use_cycles:
            self.cpu.cycles -= 1
            
    def set_hi(self, hi=0, use_cycles=True):
        self.set((hi << 8) + (self.value & 0xFF))
    
    def set_lo(self, lo=0, use_cycles=True):
        self.set((self.value & 0xFF00) + (lo & 0xFF))
        
    def get(self, use_cycles=True):
        return self.value
    
    def get_hi(self, use_cycles=True):
        return (self.value >> 8) & 0xFF
        
    def get_lo(self, use_cycles=True):
        return self.value & 0xFF

    def inc(self, use_cycles=True):
        self.add(1, use_cycles=False)
        if use_cycles:
            self.cpu.cycles -= 2

    def dec(self, use_cycles=True):
        self.add(-1, use_cycles=False)
        if use_cycles:
            self.cpu.cycles -= 2

    def add(self, value, use_cycles=True):
        self.value += value
        self.value &= 0xFFFF
        if use_cycles:
            self.cpu.cycles -= 3


# ------------------------------------------------------------------------------

class ImmediatePseudoRegister(Register):
    
    def __init__(self, cpu, hl):
        #assert isinstance(cpu, CPU)
        self.cpu = cpu
        self.hl = hl
        
    def set(self, value, use_cycles=True):
        self.cpu.write(self.hl.get(use_cycles=use_cycles), value) # 2 + 0
        if not use_cycles:
            self.cpu.cycles += 2
    
    def get(self, use_cycles=True):
        if not use_cycles:
            self.cpu.cycles += 1
        result = self.cpu.read(self.hl.get(use_cycles=use_cycles)) # 1
        return result
    
# ------------------------------------------------------------------------------
  
class FlagRegister(Register):
    """
    The Flag Register (lower 8bit of AF register)
      Bit  Name  Set Clr  Expl.
      7    zf    Z   NZ   Zero Flag
      6    n     -   -    Add/Sub-Flag (BCD)
      5    h     -   -    Half Carry Flag (BCD)
      4    cy    C   NC   Carry Flag
      3-0  -     -   -    Not used (always zero)
    Contains the result from the recent instruction which has affected flags.
    
    The Zero Flag (Z)
    This bit becomes set (1) if the result of an operation has been zero (0). 
    Used  for conditional jumps.
    
    The Carry Flag (C, or Cy)
    Becomes set when the result of an addition became bigger than FFh (8bit) or
    FFFFh (16bit). Or when the result of a subtraction or comparision became 
    less than zero (much as for Z80 and 80x86 CPUs, but unlike as for 65XX and 
    ARM  CPUs). Also the flag becomes set when a rotate/shift operation has 
    shifted-out a "1"-bit.
    Used for conditional jumps, and for instructions such like ADC, SBC, RL, 
    RLA, etc.
    
    The BCD Flags (N, H)
    These flags are (rarely) used for the DAA instruction only, N Indicates
    whether the previous instruction has been an addition or subtraction, and H
    indicates carry for lower 4bits of the result, also for DAA, the C flag must
    indicate carry for upper 8bits.
    After adding/subtracting two BCD numbers, DAA is intended to convert the
    result into BCD format; BCD numbers are ranged from 00h to 99h rather than 
    00h to FFh.
    Because C and H flags must contain carry-outs for each digit, DAA cannot be
    used for 16bit operations (which have 4 digits), or for INC/DEC operations
    (which do not affect C-flag).    
    """
    def __init__(self, cpu, reset_value):
        Register.__init__(self, cpu)
        #assert isinstance(cpu, CPU)
        self.reset_value = reset_value
        self.reset()
         
    def reset(self):
        self.is_zero        = False
        self.is_subtraction = False
        self.is_half_carry  = False
        self.is_carry       = False
        self.p_flag         = False
        self.s_flag         = False
        self.lower          = 0x00

    def partial_reset(self, keep_is_zero=False, keep_is_subtraction=False, 
                      keep_is_half_carry=False, keep_is_carry=False,\
                keep_p=False, keep_s=False):
        if not keep_is_zero:
            self.is_zero = False
        if not keep_is_subtraction:
            self.is_subtraction = False
        if not keep_is_half_carry:
            self.is_half_carry = False
        if not keep_is_carry:
            self.is_carry = False
        if not keep_p:
            self.p_flag = False
        if not keep_s:
            self.s_flag = False
        self.lower = 0x00
            
    def _get(self, use_cycles=True):
        value  = 0
        value += (int(self.is_carry)        << 4)
        value += (int(self.is_half_carry)   << 5)
        value += (int(self.is_subtraction)  << 6)
        value += (int(self.is_zero)         << 7)
        return value + self.lower
            
    def _set(self, value, use_cycles=True):
        self.is_carry       = bool(value & (1 << 4))
        self.is_half_carry  = bool(value & (1 << 5))
        self.is_subtraction = bool(value & (1 << 6))
        self.is_zero        = bool(value & (1 << 7))
        self.lower          = value & 0x0F
        if use_cycles:
            self.cpu.cycles -= 1
        
    def zero_check(self, value):
        self.is_zero = ((value & 0xFF) == 0)
            
    def is_carry_compare(self, value, compare_and=0x01, reset=False):
        if reset:
             self.reset()
        self.is_carry = ((value & compare_and) != 0)

    def is_half_carry_compare(self, new, old):
        self.is_half_carry = (old & 0x0F) < (new & 0x0F)
