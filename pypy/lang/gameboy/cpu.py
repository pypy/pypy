
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.ram import *
from pypy.lang.gameboy.interrupt import *
from pypy.lang.gameboy.cpu_register import Register, DoubleRegister, \
                                           FlagRegister, ImmediatePseudoRegister
import pdb

# ---------------------------------------------------------------------------

def process_2s_complement(value):
    # check if the left most bit is set
    #if (value >> 7) == 1:
    #    return -((~value) & 0xFF) - 1
    #else :
    #    return value
    return (value ^ 0x80) - 128
     
# # ------------------------------------------------------------------------------


DEBUG_INSTRUCTION_COUNTER = 1

class CPU(object):
    """
    PyGIRL GameBoy (TM) Emulator
    
    Central Unit Processor_a (Sharp LR35902 CPU)
    """
    def __init__(self, interrupt, memory):
        assert isinstance(interrupt, Interrupt)
        self.interrupt = interrupt
        self.memory    = memory
        self.ime       = False
        self.halted    = False
        self.cycles    = 0
        self.ini_registers()
        self.rom       = [0]
        self.reset()

    def ini_registers(self):
        self.b    = Register(self)
        self.c    = Register(self)
        self.bc   = DoubleRegister(self, self.b, self.c, constants.RESET_BC)
        
        self.d    = Register(self)
        self.e    = Register(self)
        self.de   = DoubleRegister(self, self.d, self.e, constants.RESET_DE)

        self.h    = Register(self)
        self.l    = Register(self)
        self.hl   = DoubleRegister(self, self.h, self.l, constants.RESET_HL)
        
        self.hli  = ImmediatePseudoRegister(self, self.hl)
        self.pc   = DoubleRegister(self, Register(self), Register(self), reset_value=constants.RESET_PC)
        self.sp   = DoubleRegister(self, Register(self), Register(self), reset_value=constants.RESET_SP)
        
        self.a    = Register(self, constants.RESET_A)
        self.flag = FlagRegister(self, constants.RESET_F)
        self.af   = DoubleRegister(self, self.a, self.flag)
        

    def reset(self):
        self.reset_registers()
        self.flag.reset()
        self.flag.is_zero = True
        self.ime          = False
        self.halted       = False
        self.cycles       = 0
        self.instruction_counter        = 0
        self.last_op_code               = -1
        self.last_fetch_execute_op_code = -1
        
    def reset_registers(self):
        self.a.reset()
        self.flag.reset()
        self.bc.reset()
        self.de.reset()
        self.hl.reset()
        self.sp.reset()
        self.pc.reset()
    
    # ---------------------------------------------------------------

    def get_af(self):
        return self.af
        
    def get_a(self):
        return self.a
    
    def get_f(self):
        return self.f
        
    def get_bc(self):
        return self.bc
    
    def get_b(self):
        return self.b
    
    def get_c(self):
        return self.c
        
    def get_de(self):
        return self.de
        
    def get_d(self):
        return self.d
        
    def get_e(self):
        return self.e
        
    def get_hl(self):
        return self.hl
        
    def get_hli(self):
        return self.hli
        
    def get_h(self):
        return self.h
        
    def get_l(self):
        return self.l
             
    def get_sp(self):
        return self.sp

    def get_if(self):
        val = 0x00
        if self.ime:
            val = 0x01
        if self.halted:
            val += 0x80
        return val

    def is_z(self):
        """ zero flag"""
        return self.flag.is_zero

    def is_c(self):
        """ carry flag, true if the result did not fit in the register"""
        return self.flag.is_carry

    def is_h(self):
        """ half carry, carry from bit 3 to 4"""
        return self.flag.is_half_carry

    def is_n(self):
        """ subtract flag, true if the last operation was a subtraction"""
        return self.flag.is_subtraction
    
    def isS(self):
        return self.flag.s_flag
    
    def is_p(self):
        return self.flag.p_flag
    
    def is_not_z(self):
        return not self.is_z()

    def is_not_c(self):
        return not self.is_c()
    
    def is_not_h(self):
        return not self.is_h()

    def is_not_n(self):
        return not self.is_n()

    def set_rom(self, banks):
        self.rom = banks       
    
    # ---------------------------------------------------------------
    
    def emulate(self, ticks):
        self.cycles += ticks
        self.handle_pending_interrupts()
        while self.cycles > 0:
            self.execute(self.fetch(use_cycles=False))
            
    def emulate_step(self):
        self.handle_pending_interrupts()
        self.execute(self.fetch(use_cycles=False))
        

    def handle_pending_interrupts(self):
        if self.halted:
            self.update_interrupt_cycles()
        if self.ime and self.interrupt.is_pending():
            self.lower_pending_interrupt()
            
    def update_interrupt_cycles(self):
        if self.interrupt.is_pending():
            self.halted = False
            self.cycles -= 4
        elif self.cycles > 0:
            self.cycles = 0
        
    def lower_pending_interrupt(self):
        for flag in self.interrupt.interrupt_flags:
            if flag.is_pending():
                self.ime = False
                self.call(flag.call_code, use_cycles=False)
                flag.set_pending(False)
                return

    def fetch_execute(self):
        op_code = self.fetch()
        self.last_fetch_execute_op_code = op_code
        FETCH_EXECUTE_OP_CODES[op_code](self)
        
        
    def execute(self, op_code):
        self.instruction_counter += 1
        self.last_op_code = op_code
        OP_CODES[op_code](self)
        
        
    # -------------------------------------------------------------------
        
    def debug(self):
        #print "0xDD called"
        pass
        
    def read(self, hi, lo=None):
        # memory Access, 1 cycle
        address = hi
        if lo is not None:
            address = (hi << 8) + lo
        self.cycles -= 1
        return self.memory.read(address)

    def write(self, address, data):
        # 2 cycles
        self.memory.write(address, data)
        self.cycles -= 2

    def fetch(self, use_cycles=True):
        # Fetching  1 cycle
        if use_cycles:
            self.cycles += 1
        if self.pc.get(use_cycles) <= 0x3FFF:
            data =  self.rom[self.pc.get(use_cycles)]
        else:
            data = self.memory.read(self.pc.get(use_cycles))
        self.pc.inc(use_cycles) # 2 cycles
        return data
    
    def fetch_double_address(self):
        lo = self.fetch() # 1 cycle
        hi = self.fetch() # 1 cycle
        return (hi << 8) + lo
        
    def fetch_double_register(self, register):
        self.double_register_inverse_call(CPUFetchCaller(self), register)

    def push(self, data, use_cycles=True):
        # Stack, 2 cycles
        self.sp.dec(use_cycles) # 2 cycles
        self.memory.write(self.sp.get(use_cycles), data)
        
    def push_double_register(self, register, use_cycles=True):
        # PUSH rr 4 cycles
        self.push(register.get_hi(), use_cycles) # 2 cycles
        self.push(register.get_lo(), use_cycles) # 2 cycles

    def pop(self, use_cycles=True):
        # 1 cycle
        data = self.memory.read(self.sp.get())
        self.sp.inc() # 2 cycles
        self.cycles += 1
        return data
    
    def pop_double_register(self, register):
        # 3 cycles
        self.double_register_inverse_call(CPUPopCaller(self), register)
        
    def double_register_inverse_call(self, getCaller, register):
        b = getCaller.get() # 1 cycle
        a = getCaller.get() # 1 cycle
        register.set_hi_lo(a, b) # 2 cycles
        self.cycles += 1
        
    def call(self, address, use_cycles=True):
        # 4 cycles
        self.push_double_register(self.pc, use_cycles)
        self.pc.set(address, use_cycles=use_cycles)       # 1 cycle
        if use_cycles:
            self.cycles += 1
        
    def load(self, getCaller, setCaller):
        # 1 cycle
        setCaller.set(getCaller.get()) # 1 cycle
        
    def load_fetch_register(self, register):
        self.load(CPUFetchCaller(self), RegisterCallWrapper(register))
        
    def store_hl_in_pc(self):
        # LD PC,HL, 1 cycle
        self.load(DoubleRegisterCallWrapper(self.hl), 
                DoubleRegisterCallWrapper(self.pc))
        
    def fetch_load(self, getCaller, setCaller):
        self.load(CPUFetchCaller(self), setCaller)

    def add_a(self, getCaller, setCaller=None):
        data = getCaller.get()
        # ALU, 1 cycle
        added = (self.a.get() + data) & 0xFF
        self.add_sub_flag_finish(added, data)
        
    def add_hl(self, register):
        # 2 cycles
        data = register.get()
        added = (self.hl.get() + data) # 1 cycle
        self.flag.partial_reset(keep_is_zero=True)
        self.flag.is_half_carry = (((added ^ self.hl.get() ^ data) & 0x1000) != 0) 
        self.flag.is_carry = (added >= 0x10000 or added < 0)
        self.hl.set(added & 0xFFFF)
        self.cycles -= 1
        
    def add_a_with_carry(self, getCaller, setCaller=None):
        # 1 cycle
        data = getCaller.get()
        s = self.a.get() + data + int(self.flag.is_carry)
        self.add_sub_flag_finish(s,data)

    def subtract_with_carry_a(self, getCaller, setCaller=None):
        # 1 cycle
        data = getCaller.get()
        s = self.a.get() - data - int(self.flag.is_carry)
        self.add_sub_flag_finish(s, data)
        self.flag.is_subtraction = True
        
    def add_sub_flag_finish(self, s, data):
        self.flag.reset()
        # set the h flag if the 0x10 bit was affected
        self.flag.is_half_carry = (((s ^ self.a.get() ^ data) & 0x10) != 0)
        self.flag.is_carry = (s >= 0x100 or s < 0)
        self.flag.zero_check(s)
        self.a.set(s & 0xFF)  # 1 cycle
        
    def subtract_a(self, getCaller, setCaller=None):
        # 1 cycle
        data = getCaller.get()
        self.compare_a_simple(data)
        self.a.sub(data, False)
 
    def fetch_subtract_a(self):
        data = self.fetch()
        # 1 cycle
        self.compare_a_simple(data) # 1 cycle
        self.a.sub(data, False)

    def compare_a(self, getCaller, setCaller=None):
        # 1 cycle
        self.compare_a_simple(getCaller.get())
        
    def compare_a_simple(self, s):
        s = (self.a.get() - s) & 0xFF
        self.flag.reset()
        self.flag.is_subtraction = True
        self.flag.zero_check(s)
        self.subtract_his_carry_finish(s)
        self.cycles -= 1
            
    def subtract_his_carry_finish(self, data):
        self.flag.is_carry = (data > self.a.get())
        self.flag.is_half_carry_compare(data, self.a.get())
        
    def and_a(self, getCaller, setCaller=None):
        # 1 cycle
        self.a.set(self.a.get() & getCaller.get())  # 1 cycle
        self.flag.reset()
        self.flag.zero_check(self.a.get())
        self.flag.is_half_carry = True

    def xor_a(self, getCaller, setCaller=None):
        # 1 cycle
        self.a.set( self.a.get() ^ getCaller.get())  # 1 cycle
        self.flag.zero_check(self.a.get(), reset=True)

    def or_a(self, getCaller, setCaller=None):
        # 1 cycle
        self.a.set(self.a.get() | getCaller.get())  # 1 cycle
        self.flag.zero_check(self.a.get(), reset=True)

    def inc_double_register(self, register):
        # INC rr
        register.inc()

    def dec_double_register(self, register):
        # DEC rr
        register.dec()

    def inc(self, getCaller, setCaller):
        # 1 cycle
        data = (getCaller.get() + 1) & 0xFF
        self.dec_inis_carry_finish(data, setCaller, 0x00)
        
    def dec(self, getCaller, setCaller):
        # 1 cycle
        data = (getCaller.get() - 1) & 0xFF
        self.dec_inis_carry_finish(data, setCaller, 0x0F)
        self.flag.is_subtraction = True
     
    def dec_inis_carry_finish(self, data, setCaller, compare):
        self.flag.partial_reset(keep_is_carry=True)
        self.flag.zero_check(data)
        self.flag.is_half_carry = ((data & 0x0F) == compare)
        setCaller.set(data) # 1 cycle

    def rotate_left_circular(self, getCaller, setCaller):
        # RLC 1 cycle
        data = getCaller.get()
        s = ((data << 1) & 0xFF) + ((data & 0x80) >> 7)
        self.flags_and_setter_finish(s, data, setCaller, 0x80)
        #self.cycles -= 1

    def rotate_left_circular_a(self):
        # RLCA rotate_left_circular_a 1 cycle
        self.rotate_left_circular(RegisterCallWrapper(self.a), 
                                  RegisterCallWrapper(self.a))

    def rotate_left(self, getCaller, setCaller):
        # 1 cycle
        data = getCaller.get()
        s = ((data & 0x7F) << 1) + int(self.flag.is_carry)
        self.flags_and_setter_finish(s, data, setCaller, 0x80) # 1 cycle

    def rotate_left_a(self):
        # RLA  1 cycle
        self.rotate_left(RegisterCallWrapper(self.a), 
                         RegisterCallWrapper(self.a))
        
    def rotate_right_circular(self, getCaller, setCaller):
        data = getCaller.get()
        # RRC 1 cycle
        s = (data >> 1) + ((data & 0x01) << 7)
        self.flags_and_setter_finish(s, data, setCaller) # 1 cycle
   
    def rotate_right_circular_a(self):
        # RRCA 1 cycle
        self.rotate_right_circular(RegisterCallWrapper(self.a), 
                                   RegisterCallWrapper(self.a))

    def rotate_right(self, getCaller, setCaller):
        # 1 cycle
        data = getCaller.get()
        s = (data >> 1)
        if self.flag.is_carry:
            s +=  0x80
        self.flags_and_setter_finish(s, data, setCaller) # 1 cycle

    def rotate_right_a(self):
        # RRA 1 cycle
        self.rotate_right(RegisterCallWrapper(self.a), 
                          RegisterCallWrapper(self.a))
   
    def shift_left_arithmetic(self, getCaller, setCaller):
        # 2 cycles
        data = getCaller.get()
        s = (data << 1) & 0xFF
        self.flags_and_setter_finish(s, data, setCaller, 0x80) # 1 cycle

    def shift_right_arithmetic(self, getCaller, setCaller):
        data = getCaller.get()
        # 1 cycle
        s = (data >> 1) + (data & 0x80)
        self.flags_and_setter_finish(s, data, setCaller) # 1 cycle

    def shift_word_right_logical(self, getCaller, setCaller):
        # 2 cycles
        data = getCaller.get()
        s = (data >> 1)
        self.flags_and_setter_finish(s, data, setCaller) # 2 cycles
         
    def flags_and_setter_finish(self, s, data, setCaller, compare_and=0x01):
        # 2 cycles
        s &= 0xFF
        self.flag.reset()
        self.flag.zero_check(s)
        self.flag.is_carry_compare(data, compare_and)
        setCaller.set(s) # 1 cycle

    def swap(self, getCaller, setCaller):
        data = getCaller.get()
        # 1 cycle
        s = ((data << 4) + (data >> 4)) & 0xFF
        self.flag.zero_check(s, reset=True)
        setCaller.set(s)


    def test_bit(self, getCaller, setCaller, n):
        # 2 cycles
        self.flag.partial_reset(keep_is_carry=True)
        self.flag.is_half_carry = True
        self.flag.is_zero = ((getCaller.get() & (1 << n)) == 0)
        self.cycles -= 1

    def set_bit(self, getCaller, setCaller, n):
        # 1 cycle
        setCaller.set(getCaller.get() | (1 << n)) # 1 cycle
        
    def reset_bit(self, getCaller, setCaller, n):
        # 1 cycle
        setCaller.set(getCaller.get() & (~(1 << n))) # 1 cycle
        
    def store_fetched_memory_in_a(self):
        # LD A,(nnnn), 4 cycles
        self.a.set(self.read(self.fetch_double_address()))  # 1+1 + 2 cycles

    def write_a_at_bc_address(self):
        # 2 cycles
        self.write(self.bc.get(), self.a.get())
        
    def write_a_at_de_address(self):
        self.write(self.de.get(), self.a.get())
           
    def store_memory_at_bc_in_a(self):
        self.a.set(self.read(self.bc.get()))

    def store_memory_at_de_in_a(self):
        self.a.set(self.read(self.de.get()))

    def ld_dbRegisteri_A(self, register):
        # LD (rr),A  2 cycles
        self.write(register.get(), self.a.get()) # 2 cycles

    def load_mem_sp(self):
        # LD (nnnn),SP  5 cycles
        address = self.fetch_double_address() # 2 cycles
        self.write(address,       self.sp.get_lo())  # 2 cycles
        self.write((address + 1), self.sp.get_hi()) # 2 cycles
        self.cycles += 1

    def store_a_at_fetched_address(self):
        # LD (nnnn),A  4 cycles
        self.write(self.fetch_double_address(), self.a.get()) # 2 cycles

    def store_memory_at_axpanded_fetch_address_in_a(self):
        # LDH A,(nn) 3 cycles
        self.a.set(self.read(0xFF00 + self.fetch())) # 1+1+1 cycles
        
    def store_expanded_c_in_a(self):
        # LDH A,(C) 2 cycles
        self.a.set(self.read(0xFF00 + self.bc.get_lo())) # 1+2 cycles
        
    def load_and_increment_a_hli(self):
        # loadAndIncrement A,(HL) 2 cycles
        self.a.set(self.read(self.hl.get())) # 2 cycles
        self.hl.inc()# 2 cycles
        self.cycles += 2
        
    def load_and_decrement_a_hli(self):
        # loadAndDecrement A,(HL)  2 cycles
        self.a.set(self.read(self.hl.get())) # 2 cycles
        self.hl.dec() # 2 cycles
        self.cycles += 2
        
    def write_a_at_expanded_fetch_address(self):
        # LDH (nn),A 3 cycles
        self.write(0xFF00 + self.fetch(), self.a.get()) # 2 + 1 cycles

    def write_a_at_expanded_c_address(self):
        # LDH (C),A 2 cycles
        self.write(0xFF00 + self.c.get(), self.a.get()) # 2 cycles
        
    def load_and_increment_hli_a(self):
        # loadAndIncrement (HL),A 2 cycles
        self.write(self.hl.get(), self.a.get()) # 2 cycles
        self.hl.inc() # 2 cycles
        self.cycles += 2

    def load_and_decrement_hli_a(self):
        # loadAndDecrement (HL),A  2 cycles
        self.write(self.hl.get(), self.a.get()) # 2 cycles
        self.hl.dec() # 2 cycles
        self.cycles += 2

    def store_hl_in_sp(self):
        # LD SP,HL 2 cycles
        self.sp.set(self.hl.get()) # 1 cycle
        self.cycles -= 1

    def complement_a(self):
        # CPA
        self.a.set(self.a.get() ^ 0xFF)
        self.flag.is_subtraction = True
        self.flag.is_half_carry = True

    def decimal_adjust_a(self):
        # DAA 1 cycle
        delta = 0
        if self.is_h(): 
            delta |= 0x06
        if self.is_c():
            delta |= 0x60
        if (self.a.get() & 0x0F) > 0x09:
            delta |= 0x06
            if (self.a.get() & 0xF0) > 0x80:
                delta |= 0x60
        if (self.a.get() & 0xF0) > 0x90:
            delta |= 0x60
        if not self.is_n():
            self.a.set((self.a.get() + delta) & 0xFF) # 1 cycle
        else:
            self.a.set((self.a.get() - delta) & 0xFF) # 1 cycle
        self.flag.partial_reset(keep_is_subtraction=True)
        if delta >= 0x60:
            self.flag.is_carry = True
        self.flag.zero_check(self.a.get())

    def increment_sp_by_fetch(self):
        # ADD SP,nn 4 cycles
        self.sp.set(self.get_fetchadded_sp()) # 1+1 cycle
        self.cycles -= 2

    def store_fetch_added_sp_in_hl(self):
        # LD HL,SP+nn   3  cycles
        self.hl.set(self.get_fetchadded_sp()) # 1+1 cycle
        self.cycles -= 1

    def get_fetchadded_sp(self):
        # 1 cycle
        offset = process_2s_complement(self.fetch()) # 1 cycle
        s = (self.sp.get() + offset) & 0xFFFF
        self.flag.reset()
        if (offset >= 0):
            self.flag.is_carry = (s < self.sp.get())
            if (s & 0x0F00) < (self.sp.get() & 0x0F00):
                self.flag.is_half_carry = True
        else:
            self.flag.is_carry = (s > self.sp.get())
            if (s & 0x0F00) > (self.sp.get() & 0x0F00):
                self.flag.is_half_carry = True
        return s
        
    def complement_carry_flag(self):
        # CCF/SCF
        self.flag.partial_reset(keep_is_zero=True, keep_is_carry=True)
        self.flag.is_carry = not self.flag.is_carry

    def set_carry_flag(self):
        self.flag.partial_reset(keep_is_zero=True)
        self.flag.is_carry = True

    def nop(self):
        # NOP 1 cycle
        self.cycles -= 1

    def jump(self):
        # JP nnnn, 4 cycles
        self.pc.set(self.fetch_double_address()) # 1+2 cycles
        self.cycles -= 1

    def conditional_jump(self, cc):
        # JP cc,nnnn 3,4 cycles
        if cc:
            self.jump() # 4 cycles
        else:
            self.pc.add(2) # 3 cycles

    def relative_jump(self):
        # JR +nn, 3 cycles
        self.pc.add(process_2s_complement(self.fetch())) # 3 + 1 cycles
        self.cycles += 1

    def relative_conditional_jump(self, cc):
        # JR cc,+nn, 2,3 cycles
        if cc:
            self.relative_jump() # 3 cycles
        else:
            self.pc.inc() # 2 cycles
    
    def unconditional_call(self):
        # CALL nnnn, 6 cycles
        self.call(self.fetch_double_address())  # 4+2 cycles

    def conditional_call(self, cc):
        # CALL cc,nnnn, 3,6 cycles
        if cc:
            self.unconditional_call() # 6 cycles
        else:
            self.pc.add(2) # 3 cycles

    def ret(self):
        # RET 4 cycles
        lo = self.pop() # 1 cycle
        hi = self.pop() # 1 cycle
        self.pc.set_hi_lo(hi, lo) # 2 cycles

    def conditional_return(self, cc):
        # RET cc 2,5 cycles
        if cc:
            self.ret() # 4 cycles
            # FIXME maybe this should be the same
            self.cycles -= 1
        else:
            self.cycles -= 2

    def return_form_interrupt(self):
        # RETI 4 cycles
        self.ret() # 4 cycles
        self.enable_interrupts() # 1 cycle + others
        #self.cycles += 1

    def restart(self, nn):
        # RST nn 4 cycles
        self.call(nn) # 4 cycles

    def disable_interrupts(self):
        # DI/EI 1 cycle
        self.ime     = False
        self.cycles -= 1

    def enable_interrupts(self):
        # 1 cycle
        self.ime = True
        self.execute(self.fetch()) #  1
        self.handle_pending_interrupts()

    def halt(self):
        # HALT/STOP
        self.halted = True
        # emulate bug when interrupts are pending
        if not self.ime and self.interrupt.is_pending():
            self.execute(self.memory.read(self.pc.get()))
        self.handle_pending_interrupts()

    def stop(self):
        # 0 cycles
        self.cycles += 1
        self.fetch()

# ------------------------------------------------------------------------------

class CallWrapper(object):   
    def get(self, use_cycles=True):
        raise Exception("called CallWrapper.get")
    
    def set(self, value, use_cycles=True):
        raise Exception("called CallWrapper.set")
    
class NumberCallWrapper(CallWrapper):
    def __init__(self, number):
        self.number = number
    
    def get(self, use_cycles=True):
        return self.number
    
    def set(self, value, use_cycles=True):
        raise Exception("called CallWrapper.set")
        
class RegisterCallWrapper(CallWrapper): 
    def __init__(self, register):
        self.register = register
        
    def get(self,  use_cycles=True):
        return self.register.get(use_cycles)
    
    def set(self, value, use_cycles=True):
        return self.register.set(value, use_cycles)


class DoubleRegisterCallWrapper(CallWrapper):
    def __init__(self, register):
        self.register = register
        
    def get(self,  use_cycles=True):
        return self.register.get(use_cycles)
    
    def set(self, value, use_cycles=True):
        return self.register.set(value, use_cycles) 
    
    
class CPUPopCaller(CallWrapper):
    def __init__(self, cpu):
        self.cpu = cpu
        
    def get(self,  use_cycles=True):
        return self.cpu.pop(use_cycles)
    
    
class CPUFetchCaller(CallWrapper):
    def __init__(self, cpu):
        self.cpu = cpu
        
    def get(self,  use_cycles=True):
        return self.cpu.fetch(use_cycles)

# op_code LOOKUP TABLE GENERATION -----------------------------------------------

GROUPED_REGISTERS = [CPU.get_b, CPU.get_c, CPU.get_d,   CPU.get_e,
                     CPU.get_h, CPU.get_l, CPU.get_hli, CPU.get_a]

def create_group_op_codes(table):
    op_codes =[]
    for entry in table:
        op_code   = entry[0]
        step     = entry[1]
        function = entry[2]
        if len(entry) == 4:
            for registerGetter in GROUPED_REGISTERS:
                for n in entry[3]:
                    op_codes.append((op_code, group_lambda(function, registerGetter, n)))
                    op_code += step
        if len(entry) == 5:
            entryStep = entry[4]
            for registerGetter in GROUPED_REGISTERS:
                stepop_code = op_code
                for n in entry[3]:
                    op_codes.append((stepop_code, group_lambda(function, registerGetter, n)))
                    stepop_code += entryStep
                op_code+=step
        else:
            for registerGetter in GROUPED_REGISTERS:
                op_codes.append((op_code,group_lambda(function, registerGetter)))
                op_code += step
    return op_codes

def group_lambda(function, register_getter, value=None):
    if value is None:
        return lambda s: function(s, RegisterCallWrapper(register_getter(s)), 
                                     RegisterCallWrapper(register_getter(s)))
    else:
        return lambda s: function(s, RegisterCallWrapper(register_getter(s)), 
                                     RegisterCallWrapper(register_getter(s)), value)
    
def create_load_group_op_codes():
    op_codes = []
    op_code  = 0x40
    for storeRegister in GROUPED_REGISTERS:
        for loadRegister in GROUPED_REGISTERS:
            if loadRegister != CPU.get_hli or storeRegister != CPU.get_hli:
                op_codes.append((op_code, load_group_lambda(storeRegister, loadRegister)))
            op_code += 1
    return op_codes
            
def load_group_lambda(store_register, load_register):
        return lambda s: CPU.load(s, RegisterCallWrapper(load_register(s)),
                                   RegisterCallWrapper(store_register(s)))
    
def create_register_op_codes(table):
    op_codes = []
    for entry in table:
        op_code  = entry[0]
        step     = entry[1]
        function = entry[2]
        for registerOrGetter in entry[3]:
            op_codes.append((op_code, register_lambda(function, registerOrGetter)))
            op_code += step
    return op_codes

def register_lambda(function, registerOrGetter):
    if callable(registerOrGetter):
        return lambda s: function(s, registerOrGetter(s))
    else:
        return lambda s: function(s, registerOrGetter)
        
        
def initialize_op_code_table(table):
    result = [None] * (0xFF+1)
    for entry in  table:
        if (entry is None) or (len(entry) == 0) or entry[-1] is None:
            continue
        if len(entry) == 2:
            positions = [entry[0]]
        else:
            positions = range(entry[0], entry[1]+1)
        for pos in positions:
            result[pos] = entry[-1]
    return result

# op_code TABLES ---------------------------------------------------------------
# Table with one to one mapping of simple OP Codes                
FIRST_ORDER_OP_CODES = [
    (0x00, CPU.nop),
    (0x08, CPU.load_mem_sp),
    (0x10, CPU.stop),
    (0x18, CPU.relative_jump),
    (0x02, CPU.write_a_at_bc_address),
    (0x12, CPU.write_a_at_de_address),
    (0x22, CPU.load_and_increment_hli_a),
    (0x32, CPU.load_and_decrement_hli_a),
    (0x0A, CPU.store_memory_at_bc_in_a),
    (0x1A, CPU.store_memory_at_de_in_a),
    (0x2A, CPU.load_and_increment_a_hli),
    (0x3A, CPU.load_and_decrement_a_hli),
    (0x07, CPU.rotate_left_circular_a),
    (0x0F, CPU.rotate_right_circular_a),
    (0x17, CPU.rotate_left_a),
    (0x1F, CPU.rotate_right_a),
    (0x27, CPU.decimal_adjust_a),
    (0x2F, CPU.complement_a),
    (0x37, CPU.set_carry_flag),
    (0x3F, CPU.complement_carry_flag),
    (0x76, CPU.halt),
    (0xF3, CPU.disable_interrupts),
    (0xFB, CPU.enable_interrupts),
    (0xE2, CPU.write_a_at_expanded_c_address),
    (0xEA, CPU.store_a_at_fetched_address),
    (0xF2, CPU.store_expanded_c_in_a),
    (0xFA, CPU.store_fetched_memory_in_a),
    (0xC3, CPU.jump),
    (0xC9, CPU.ret),
    (0xD9, CPU.return_form_interrupt),
    (0xDD, CPU.debug),
    (0xE9, CPU.store_hl_in_pc),
    (0xF9, CPU.store_hl_in_sp),
    (0xE0, CPU.write_a_at_expanded_fetch_address),
    (0xE8, CPU.increment_sp_by_fetch),
    (0xF0, CPU.store_memory_at_axpanded_fetch_address_in_a),
    (0xF8, CPU.store_fetch_added_sp_in_hl),
    (0xCB, CPU.fetch_execute),
    (0xCD, CPU.unconditional_call),
    (0xC6, lambda s: CPU.add_a(s,                 CPUFetchCaller(s))),
    (0xCE, lambda s: CPU.add_a_with_carry(s,      CPUFetchCaller(s))),
    (0xD6, CPU.fetch_subtract_a),
    (0xDE, lambda s: CPU.subtract_with_carry_a(s, CPUFetchCaller(s))),
    (0xE6, lambda s: CPU.and_a(s,                 CPUFetchCaller(s))),
    (0xEE, lambda s: CPU.xor_a(s,                 CPUFetchCaller(s))),
    (0xF6, lambda s: CPU.or_a(s,                  CPUFetchCaller(s))),
    (0xFE, lambda s: CPU.compare_a(s,             CPUFetchCaller(s))),
    (0xC7, lambda s: CPU.restart(s, 0x00)),
    (0xCF, lambda s: CPU.restart(s, 0x08)),
    (0xD7, lambda s: CPU.restart(s, 0x10)),
    (0xDF, lambda s: CPU.restart(s, 0x18)),
    (0xE7, lambda s: CPU.restart(s, 0x20)),
    (0xEF, lambda s: CPU.restart(s, 0x28)),
    (0xF7, lambda s: CPU.restart(s, 0x30)),
    (0xFF, lambda s: CPU.restart(s, 0x38))
]

# Table for RegisterGroup OP Codes: (startAddress, delta, method)
REGISTER_GROUP_OP_CODES = [
    (0x04, 0x08, CPU.inc),
    (0x05, 0x08, CPU.dec),    
    (0x06, 0x08, CPU.load_fetch_register),
    (0x80, 0x01, CPU.add_a),    
    (0x88, 0x01, CPU.add_a_with_carry),    
    (0x90, 0x01, CPU.subtract_a),    
    (0x98, 0x01, CPU.subtract_with_carry_a),    
    (0xA0, 0x01, CPU.and_a),    
    (0xA8, 0x01, CPU.xor_a),    
    (0xB0, 0x01, CPU.or_a),
    (0xB8, 0x01, CPU.compare_a),
    (0x06, 0x08, CPU.fetch_load)
]    
        

REGISTER_SET_A    = [CPU.get_bc,   CPU.get_de, CPU.get_hl,   CPU.get_sp]
REGISTER_SET_B    = [CPU.get_bc,   CPU.get_de, CPU.get_hl,   CPU.get_af]
FLAG_REGISTER_SET = [CPU.is_not_z, CPU.is_z,   CPU.is_not_c, CPU.is_c]

# Table for Register OP Codes: (startAddress, delta, method, registers)
REGISTER_OP_CODES = [ 
    (0x01, 0x10, CPU.fetch_double_register,     REGISTER_SET_A),
    (0x09, 0x10, CPU.add_hl,                    REGISTER_SET_A),
    (0x03, 0x10, CPU.inc_double_register,       REGISTER_SET_A),
    (0x0B, 0x10, CPU.dec_double_register,       REGISTER_SET_A),
    (0xC0, 0x08, CPU.conditional_return,        FLAG_REGISTER_SET),
    (0xC2, 0x08, CPU.conditional_jump,          FLAG_REGISTER_SET),
    (0xC4, 0x08, CPU.conditional_call,          FLAG_REGISTER_SET),
    (0x20, 0x08, CPU.relative_conditional_jump, FLAG_REGISTER_SET),
    (0xC1, 0x10, CPU.pop_double_register,       REGISTER_SET_B),
    (0xC5, 0x10, CPU.push_double_register,      REGISTER_SET_B)
]
# Table for Second Order op_codes: (startAddress, delta, method, [args])
SECOND_ORDER_REGISTER_GROUP_OP_CODES = [
    (0x00, 0x01, CPU.rotate_left_circular),    
    (0x08, 0x01, CPU.rotate_right_circular),    
    (0x10, 0x01, CPU.rotate_left),    
    (0x18, 0x01, CPU.rotate_right),    
    (0x20, 0x01, CPU.shift_left_arithmetic),    
    (0x28, 0x01, CPU.shift_right_arithmetic),    
    (0x30, 0x01, CPU.swap),    
    (0x38, 0x01, CPU.shift_word_right_logical),
    (0x40, 0x01, CPU.test_bit,  range(0, 8), 0x08),    
    (0xC0, 0x01, CPU.set_bit,   range(0, 8), 0x08),
    (0x80, 0x01, CPU.reset_bit, range(0, 8), 0x08)         
]

# RAW op_code TABLE INITIALIZATION ----------------------------------------------

FIRST_ORDER_OP_CODES  += create_register_op_codes(REGISTER_OP_CODES)
FIRST_ORDER_OP_CODES  += create_group_op_codes(REGISTER_GROUP_OP_CODES)
FIRST_ORDER_OP_CODES  += create_load_group_op_codes()
SECOND_ORDER_OP_CODES  = create_group_op_codes(SECOND_ORDER_REGISTER_GROUP_OP_CODES)


OP_CODES               = initialize_op_code_table(FIRST_ORDER_OP_CODES)
FETCH_EXECUTE_OP_CODES = initialize_op_code_table(SECOND_ORDER_OP_CODES)

