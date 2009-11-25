import py
from pypy.lang.gameboy.cpu import *
from pypy.lang.gameboy.ram import *
from pypy.lang.gameboy import *
from pypy.lang.gameboy.interrupt import * 

# Helpers ---------------------------------------------------------------------

class Memory(object):
    def __init__(self):
        self.memory = [0xFF]*0xFFFFF
        
    def write(self, address, data):
        self.memory[address] = data
        
    def read(self, address):
        return self.memory[address]
    
global TEST_CPU

TEST_CPU = None
def get_cpu(new=False):
    if new:
        cpu = CPU(Interrupt(), Memory())
        cpu.set_rom([0]*0xFFFF);
        return cpu
    global TEST_CPU
    if TEST_CPU == None:
        TEST_CPU = get_cpu(True)
    TEST_CPU.reset()
    return TEST_CPU

# -----------------------------------------------------------------------------

def assert_default_registers(cpu, a=constants.RESET_A, bc=constants.RESET_BC,\
                             de=constants.RESET_DE, f=constants.RESET_F,\
                             hl=constants.RESET_HL, sp=constants.RESET_SP,\
                             pc=constants.RESET_PC):
    return assert_registers(cpu, a, bc, de, f, hl, sp, pc)

def assert_registers(cpu, a=None, bc=None, de=None, f=None, hl=None, sp=None, pc=None):
    if a is not None:
        assert cpu.a.get() == a, \
        "Register a  is %s but should be %s" % (hex(cpu.a.get()), hex(a))
    if bc is not None:
        assert cpu.bc.get() == bc, \
        "Register bc  is %s but should be %s" % (hex(cpu.bc.get()), hex(bc))
    if de is not None:
        assert cpu.de.get() == de, \
        "Register de is %s but should be %s" % (hex(cpu.de.get()),hex(de))
    if f is not None:
        assert cpu.flag.get() == f, \
        "Register f is %s but should be %s" % (hex(cpu.flag.get()),hex(f))
    if hl is not None:
        assert cpu.hl.get() == hl, \
        "Register hl is %s but should be %s" % (hex(cpu.hl.get()), hex(hl))
    if sp is not None:
        assert cpu.sp.get() == sp, \
        "Register sp is %s but should be %s" % (hex(cpu.sp.get()), hex(sp))
    if pc is not None:
        assert cpu.pc.get() == pc, \
        "Register pc is %s but should be %s" % (hex(cpu.pc.get()), hex(pc))
        

def assert_defaults(cpu, z=True, n=False, h=False, c=False, p=False, s=False):        
    assert_flags(cpu, z, n, h, c, p, s)

def assert_flags(cpu, z=None, n=None, h=None, c=None, p=None, s=None):
    if z is not None:
        assert cpu.flag.is_zero == z, \
        "Z-Flag is %s but should be %s" % (cpu.flag.is_zero, z)
    if n is not None:
        assert cpu.flag.is_subtraction == n, \
        "N-Flag is %s but should be %s" % (cpu.flag.is_subtraction, n)
    if h is not None:
        assert cpu.flag.is_half_carry == h,  \
        "H-Flag is %s but should be %s" % (cpu.flag.is_half_carry, h)
    if c is not None:
        assert cpu.flag.is_carry == c,  \
        "C-Flag is %s but should be %s" % (cpu.flag.is_carry, c)
    if p is not None:
        assert cpu.flag.p_flag == p,  \
        "P-Flag is %s but should be %s" % (cpu.flag.p_flag, p)
    if s is not None:
        assert cpu.flag.s_flag == s,  \
        "S-Flag is %s but should be %s" % (cpu.flag.s_flag, s)

def prepare_for_double_fetch(cpu, value):
    prepare_for_fetch(cpu, (value & 0xFF00) >> 8, value & 0x00FF)
    
def prepare_for_fetch(cpu, value, valueLo=None):
    pc = cpu.pc.get()
    if valueLo is not None:
        cpu.rom[pc] = valueLo & 0xFF
        cpu.memory.write(pc, valueLo & 0xFF)
        pc += 1
    cpu.rom[pc] = value & 0xFF
    cpu.memory.write(pc, value & 0xFF)
    
def test_prepare_for_fetch():
    cpu = get_cpu()
    value = 0x12
    prepare_for_fetch(cpu, value+5, value)
    assert cpu.fetch() == value
    assert cpu.fetch() == value+5
        
def prepare_for_pop(cpu, value, valueLo=None):
    sp = cpu.sp.get()
    if valueLo is not None:
        cpu.memory.write(sp, valueLo & 0xFF)
        sp += 1
    cpu.memory.write(sp, value & 0xFF)
    
def test_prepare_for_pop():
    cpu = get_cpu()
    value = 0x12
    prepare_for_pop(cpu, value+5, value)
    assert cpu.pop() == value
    assert cpu.pop() == value+5
        
def set_registers(registers, value):
    #if registers is not list:
      #  registers = [registers]
    for register in registers:
        register.set(value);
        
        
def method_value_call(cpu, method, number):
    method(cpu, NumberCallWrapper(number))
    
def method_register_call(cpu, method, register):
    method(cpu, RegisterCallWrapper(register), RegisterCallWrapper(register))
    
def method_register_value_call(cpu, method, register, number):
    method(cpu, RegisterCallWrapper(register), RegisterCallWrapper(register),
           number)
    
# Tests -----------------------------------------------------------------------


def test_add_with_carry():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0x00)
    method_value_call(cpu, CPU.add_a_with_carry, 0x00)
    assert cpu.a.get() == 0x01
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    add_flag_test(cpu, CPU.add_a_with_carry)
     
def test_add_a():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0x00)
    method_value_call(cpu, CPU.add_a, 0x00)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=False, h=False, c=False)
    
    add_flag_test(cpu, CPU.add_a)
       
def add_flag_test(cpu, method):
    cpu.flag.set(0x00)
    cpu.a.set(0x00)
    method_value_call(cpu, CPU.add_a_with_carry, 0x00)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x0F)
    method_value_call(cpu, CPU.add_a_with_carry, 0x01)
    assert cpu.a.get() == 0x10
    assert_flags(cpu, z=False, n=False, h=True, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0xFF)
    method_value_call(cpu, CPU.add_a_with_carry, 0xF0)
    assert cpu.a.get() == 0xEF
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu.flag.set(0x00)
    cpu.a.set(0xFF)
    method_value_call(cpu, CPU.add_a_with_carry, 0x01)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=False, h=True, c=True)
    
def test_add_hl():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.hl.set(0x0000)
    method_value_call(cpu, CPU.add_hl, 0x0000)
    assert cpu.hl.get() == 0x0000
    assert_flags(cpu, z=True, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.hl.set(0x0000)
    method_value_call(cpu, CPU.add_hl, 0x0000)
    assert cpu.hl.get() == 0x0000
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.hl.set(0x0000)
    method_value_call(cpu, CPU.add_hl, 0x00)
    assert cpu.hl.get() == 0x0000
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.hl.set(0x0F00)
    method_value_call(cpu, CPU.add_hl, 0x0100)
    assert cpu.hl.get() == 0x1000
    assert_flags(cpu, z=False, n=False, h=True, c=False)
    
    cpu.flag.set(0x00)
    cpu.hl.set(0xFF00)
    method_value_call(cpu, CPU.add_hl, 0xF000)
    assert cpu.hl.get() == 0xEF00
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu.flag.set(0x00)
    cpu.hl.set(0xFF00)
    method_value_call(cpu, CPU.add_hl, 0x0100)
    assert cpu.hl.get() == 0x0000
    assert_flags(cpu, z=False, n=False, h=True, c=True)
    
def test_add_sp():
    cpu = get_cpu()
    cpu.flag.set(0x00)
    for i in range(0, 0x7F):
        cpu.sp.set(0x00)
        prepare_for_fetch(cpu, i);
        cpu.increment_sp_by_fetch()
        assert cpu.sp.get() == i
        assert_flags(cpu, z=False, n=False, h=False, c=False)
        
    for i in range(1, 0x7F):
        cpu.sp.set(0xFF)
        prepare_for_fetch(cpu, 0xFF - i+1);
        cpu.increment_sp_by_fetch()
        assert cpu.sp.get() == 0xFF - i
        assert_flags(cpu, z=False, n=False, h=False, c=False)
        
def test_add_sp_carry():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.sp.set(0xFF)
    prepare_for_fetch(cpu, 0xFF)
    cpu.increment_sp_by_fetch()
    assert cpu.sp.get() == 0xFE
    assert_flags(cpu, z=False, n=False, h=False, c=False)

    cpu.flag.set(0x00)
    cpu.sp.set(0xFF)
    prepare_for_fetch(cpu, 0xFF)
    cpu.increment_sp_by_fetch()
    assert cpu.sp.get() == 0xFE
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.sp.set(0x00)
    prepare_for_fetch(cpu, 0x01)
    cpu.increment_sp_by_fetch()
    assert cpu.sp.get() == 0x01
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0xFF)
    cpu.sp.set(0x00)
    prepare_for_fetch(cpu, 0x01)
    cpu.increment_sp_by_fetch()
    assert cpu.sp.get() == 0x01
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0xFF)
    cpu.sp.set(0x02)
    prepare_for_fetch(cpu, 0xFE)
    cpu.increment_sp_by_fetch()
    assert cpu.sp.get() == 0x00
    assert_flags(cpu, z=False, n=False, h=False, c=False)

def test_add_sp_carry_flags():
    cpu = get_cpu()   
    cpu.flag.set(0xFF)
    cpu.sp.set(0x0FFF)
    prepare_for_fetch(cpu, 0x01)
    cpu.increment_sp_by_fetch()
    assert cpu.sp.get() == 0x1000
    assert_flags(cpu, z=False, n=False, h=True, c=False)
    
    cpu.sp.set(0x1000)
    prepare_for_fetch(cpu, 0xFF)
    cpu.increment_sp_by_fetch()
    assert cpu.sp.get() == 0x0FFF
    assert_flags(cpu, z=False, n=False, h=True, c=False)
    
    cpu.sp.set(0xFFFF)
    prepare_for_fetch(cpu, 0x01)
    cpu.increment_sp_by_fetch()
    assert cpu.sp.get() == 0x0000
    assert_flags(cpu, z=False, n=False, h=True, c=True)
    
    cpu.sp.set(0x0000)
    prepare_for_fetch(cpu, 0xFF)
    cpu.increment_sp_by_fetch()
    assert cpu.sp.get() == 0xFFFF
    assert_flags(cpu, z=False, n=False, h=True, c=True)
    
    
def test_and_a():
    cpu = get_cpu()
    cpu.sp.set(0xFF)
    cpu.flag.set(0xFF)
    method_value_call(cpu, CPU.and_a, 0x00)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=False, h=True, c=False)
    
    cpu.flag.set(0x00)
    method_value_call(cpu, CPU.and_a, 0x00)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=False, h=True, c=False)
    
    cpu.a.set(0xFF)
    method_value_call(cpu, CPU.and_a, 0x12)
    assert cpu.a.get() == 0x12
    assert_flags(cpu, z=False, n=False, h=True, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0xFF)
    method_value_call(cpu, CPU.and_a, 0x12)
    assert cpu.a.get() == 0x12
    assert_flags(cpu, z=False, n=False, h=True, c=False)
      
def test_or_a():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0x00)
    method_value_call(cpu, CPU.or_a, 0xFF)
    assert cpu.a.get() == 0xFF
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x00)
    method_value_call(cpu, CPU.or_a, 0x00)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0xFF)
    method_value_call(cpu, CPU.or_a, 0x00)
    assert cpu.a.get() == 0xFF
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x01)
    method_value_call(cpu, CPU.or_a, 0x00)
    assert cpu.a.get() == 0x01
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x01)
    method_value_call(cpu, CPU.or_a, 0xFF)
    assert cpu.a.get() == 0xFF
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
def test_xor_a():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0x00)
    method_value_call(cpu, CPU.xor_a, 0xFF)
    assert cpu.a.get() == 0xFF
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0xFF)
    cpu.a.set(0xFF)
    method_value_call(cpu, CPU.xor_a, 0xFF)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x01)
    method_value_call(cpu, CPU.xor_a, 0x00)
    assert cpu.a.get() == 0x01
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x01)
    method_value_call(cpu, CPU.xor_a, 0xFF)
    assert cpu.a.get() == 0xFF - 0x01
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x00)
    method_value_call(cpu, CPU.xor_a, 0x00)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=False, h=False, c=False)
      
def test_bit():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0xFF)
    method_register_value_call(cpu, CPU.test_bit, cpu.a, 0x00)
    assert cpu.a.get() == 0xFF
    assert_flags(cpu, z=False, n=False, h=True, c=True)
    
    cpu.flag.set(0x00)
    cpu.a.set(0xFF)
    method_register_value_call(cpu, CPU.test_bit, cpu.a, 0x00)
    assert cpu.a.get() == 0xFF
    assert_flags(cpu, z=False, n=False, h=True, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x40)
    method_register_value_call(cpu, CPU.test_bit, cpu.a, 0x05)
    assert_flags(cpu, z=True, n=False, h=True, c=False)
    
    method_register_value_call(cpu, CPU.test_bit, cpu.a, 0x06)
    assert cpu.a.get() == 0x40
    assert_flags(cpu, z=False, n=False, h=True, c=False)
    
    method_register_value_call(cpu, CPU.test_bit, cpu.a, 0x07)
    assert_flags(cpu, z=True, n=False, h=True, c=False)
    
def test_set_bit():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0x00)
    method_register_value_call(cpu, CPU.set_bit, cpu.a, 0x00)
    assert cpu.a.get() == 0x01
    assert cpu.flag.get() == 0xFF
    
    for i in range(8):
        cpu = get_cpu()
        cpu.flag.set(0x00)
        cpu.a.set(0x00)
        method_register_value_call(cpu, CPU.set_bit, cpu.a, i)
        assert cpu.a.get() == 0x01 << i
        assert cpu.flag.get() == 0x00
        
def test_reset_bit():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0x01)
    method_register_value_call(cpu, CPU.reset_bit, cpu.a, 0x00)
    assert cpu.a.get() == 0x00
    assert cpu.flag.get() == 0xFF
    
    for i in range(8):
        cpu = get_cpu()
        cpu.flag.set(0x00)
        cpu.a.set(0xFF)
        method_register_value_call(cpu, CPU.reset_bit, cpu.a, i)
        assert cpu.a.get() == 0xFF - (0x01 << i)
        assert cpu.flag.get() == 0x00
 
def test_unconditional_call():
    cpu = get_cpu()
    cpu.flag.set(0x12)
    cpu.pc.set(0x1234)
    assert cpu.pc.get_hi() == 0x12
    assert cpu.pc.get_lo() == 0x34
    prepare_for_double_fetch(cpu, 0x5678)
    cpu.unconditional_call()
    assert cpu.flag.get() == 0x12  
    assert cpu.pop() == 0x34+2
    assert cpu.pop() == 0x12
    assert cpu.pc.get() == 0x5678
    
def test_conditional_call():
    cpu = get_cpu()
    cpu.flag.set(0x12)
    cpu.pc.set(0x1234)
    cpu.conditional_call(False)
    assert cpu.pc.get() == 0x1234+2
    assert cpu.flag.get() == 0x12 
    
    cpu.reset()
    cpu.flag.set(0x12)
    cpu.pc.set(0x1234)
    assert cpu.pc.get_hi() == 0x12
    assert cpu.pc.get_lo() == 0x34
    prepare_for_double_fetch(cpu, 0x5678)
    cpu.conditional_call(True)
    assert cpu.flag.get() == 0x12
    assert cpu.pop() == 0x34+2
    assert cpu.pop() == 0x12
    assert cpu.pc.get() == 0x5678
    
def test_complement_carry_flag():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.complement_carry_flag()
    assert_flags(cpu, z=True, n=False, h=False, c=False)
    
    cpu.complement_carry_flag()
    assert_flags(cpu, z=True, n=False, h=False, c=True)
    
    cpu.flag.set(0x00)
    cpu.complement_carry_flag()
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
def test_compare_a():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0x00)
    method_value_call(cpu, CPU.compare_a, 0x00)
    assert_flags(cpu, z=True, n=True, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x00)
    method_value_call(cpu, CPU.compare_a, 0x00)
    assert_flags(cpu, z=True, n=True, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x11)
    method_value_call(cpu, CPU.compare_a, 0x02)
    assert_flags(cpu, z=False, n=True, h=True, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x0F)
    method_value_call(cpu, CPU.compare_a, 0xFF)
    assert_flags(cpu, z=False, n=True, h=False, c=True)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x00)
    method_value_call(cpu, CPU.compare_a, 0x01)
    assert_flags(cpu, z=False, n=True, h=True, c=True)
    
def test_complement_a():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0xF0)
    cpu.complement_a()
    assert cpu.a.get() == 0x0F
    assert_flags(cpu, z=True, n=True, h=True, c=True)
    
    cpu.flag.set(0x00)
    cpu.complement_a()
    assert cpu.a.get() == 0xF0
    assert_flags(cpu, z=False, n=True, h=True, c=False)
    
def test_decimal_adjust_a():
    py.test.skip("not yet implemented")
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0)
    cpu.decimal_adjust_a()
    assert_flags(cpu, z=False, n=True, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0)
    cpu.decimal_adjust_a()
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
def test_decrement_register():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0xFF)
    method_register_call(cpu, CPU.dec, cpu.a)
    assert cpu.a.get() == 0xFE
    assert_flags(cpu, z=False, n=True, h=False, c=True)
    
    cpu.flag.set(0x00)
    method_register_call(cpu, CPU.dec, cpu.a)
    assert cpu.a.get() == 0xFD
    assert_flags(cpu, z=False, n=True, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x01)
    method_register_call(cpu, CPU.dec, cpu.a)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=True, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x10)
    method_register_call(cpu, CPU.dec, cpu.a)
    assert cpu.a.get() == 0x0F
    assert_flags(cpu, z=False, n=True, h=True, c=False)

def test_increment_register():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0xF1)
    method_register_call(cpu, CPU.inc, cpu.a)
    assert cpu.a.get() == 0xF2
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu.flag.set(0x00)
    method_register_call(cpu, CPU.inc, cpu.a)
    assert cpu.a.get() == 0xF3
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x0F)
    method_register_call(cpu, CPU.inc, cpu.a)
    assert cpu.a.get() == 0x10
    assert_flags(cpu, z=False, n=False, h=True, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0xFF)
    method_register_call(cpu, CPU.inc, cpu.a)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=False, h=True, c=False)
  
def test_decrement_double_register():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.bc.set(0xFFFF)
    cpu.dec_double_register(cpu.bc)
    assert cpu.bc.get() == 0xFFFE
    assert cpu.flag.get() == 0xFF
    
    cpu.flag.set(0xFF)
    cpu.dec_double_register(cpu.bc)
    assert cpu.bc.get() == 0xFFFD
    assert cpu.flag.get() == 0xFF
    
    cpu.flag.set(0xFF)
    cpu.bc.set(0x0000)
    cpu.dec_double_register(cpu.bc)
    assert cpu.bc.get() == 0xFFFF
    assert cpu.flag.get() == 0xFF
    
def test_increment_double_register():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.bc.set(0xFFFD)
    cpu.inc_double_register(cpu.bc)
    assert cpu.bc.get() == 0xFFFE
    assert cpu.flag.get() == 0xFF
    
    cpu.flag.set(0xFF)
    cpu.inc_double_register(cpu.bc)
    assert cpu.bc.get() == 0xFFFF
    assert cpu.flag.get() == 0xFF
    
    cpu.flag.set(0xFF)
    cpu.inc_double_register(cpu.bc)
    assert cpu.bc.get() == 0x0000
    assert cpu.flag.get() == 0xFF
    
def test_disable_interrupts():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.disable_interrupts()
    assert cpu.flag.get() == 0xFF
    
    cpu.flag.set(0x00)
    cpu.disable_interrupts()
    assert cpu.flag.get() == 0x00
  
def test_enable_interrupts():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.enable_interrupts()
    assert cpu.flag.get() == 0xFF
    
    cpu.flag.set(0x00)
    cpu.enable_interrupts()
    assert cpu.flag.get() == 0x00
  
def test_jump():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    prepare_for_double_fetch(cpu, 0x1234)
    cpu.jump()
    assert cpu.flag.get()  == 0xFF
    assert cpu.pc.get() == 0x1234

def test_conditional_jump():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    prepare_for_double_fetch(cpu, 0x1234)
    cpu.conditional_jump(True)
    assert cpu.flag.get()  == 0xFF
    assert cpu.pc.get() == 0x1234  
    
    cpu.pc.set(0x1234)
    prepare_for_double_fetch(cpu, 0x1234)
    cpu.conditional_jump(False)
    assert cpu.flag.get()  == 0xFF
    assert cpu.pc.get() == 0x1234+2
    
def test_process_2s_complement():
    assert process_2s_complement(0x00) == 0
    assert process_2s_complement(0xFF) == -1
    
    for i in range(0x7E):
        assert process_2s_complement(i) == i
        
    for i in range(1, 0x7E):
        assert process_2s_complement(0xFF - i+1) == -i
    
def test_relative_jump():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    for i in range(0x7F):
        cpu.pc.set(0x1234)
        prepare_for_fetch(cpu, i)
        cpu.relative_jump()
        assert cpu.flag.get()  == 0xFF
        #+1 for a single fetch
        assert cpu.pc.get() == 0x1234+1 + i
        
    for i in range(1, 0x7F):
        cpu.pc.set(0x1234)
        prepare_for_fetch(cpu, 0xFF - i+1)
        cpu.relative_jump()
        assert cpu.flag.get()  == 0xFF
        #+1 for a single fetch
        assert cpu.pc.get() == 0x1234+1 - i

def test_conditional_relative_jump():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    for i in range(0x7F):
        cpu.pc.set(0x1234)
        prepare_for_fetch(cpu, i)
        cpu.relative_conditional_jump(True)
        assert cpu.flag.get() == 0xFF
        #+1 for a single fetch
        assert cpu.pc.get() == 0x1234+1 + i
    
    cpu.pc.set(0x1234)
    prepare_for_fetch(cpu, 0x12)
    cpu.relative_conditional_jump(False)
    assert cpu.flag.get() == 0xFF
    assert cpu.pc.get() == 0x1234+1
    
def store_fetch_added_sp_in_hl():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.sp.set(0x1234)
    prepare_for_fetch(0x02)
    cpu.store_fetch_added_sp_in_hl()
    assert cpu.hl.get() == 0x1234 + 0x02
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    
    cpu.flag.set(0x00)
    cpu.sp.set(0x1234)
    prepare_for_fetch(0x02)
    cpu.store_fetch_added_sp_in_hl()
    assert cpu.hl.get() == 0x1234 + 0x02
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    
    cpu.flag.set(0xFF)
    cpu.sp.set(0x1234)
    prepare_for_fetch(0xFF)
    cpu.store_fetch_added_sp_in_hl()
    assert cpu.hl.get() == 0x1234 - 1
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
def test_rotate_left():
    cpu = get_cpu()
    cpu.flag.set(0x00)
    cpu.a.set(0xFF)
    method_register_call(cpu, CPU.rotate_left, cpu.a)
    assert cpu.a.get() == 0xFE
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0xFF)
    method_register_call(cpu, CPU.rotate_left, cpu.a)
    assert cpu.a.get() == 0xFE+1
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x01)
    method_register_call(cpu, CPU.rotate_left, cpu.a)
    assert cpu.a.get() == 0x02
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x80)
    method_register_call(cpu, CPU.rotate_left, cpu.a)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=False, h=False, c=True)
    
    cpu.flag.set(0xFF)
    cpu.a.set(0x80)
    method_register_call(cpu, CPU.rotate_left, cpu.a)
    assert cpu.a.get() == 0x01
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x40)
    method_register_call(cpu, CPU.rotate_left, cpu.a)
    assert cpu.a.get() == 0x80
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x7F)
    method_register_call(cpu, CPU.rotate_left, cpu.a)
    assert cpu.a.get() == 0xFE
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
def test_rotate_right():
    cpu = get_cpu()
    cpu.flag.set(0x00)
    cpu.a.set(0xFF)
    method_register_call(cpu, CPU.rotate_right, cpu.a)
    assert cpu.a.get() == 0x7F
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0xFF)
    method_register_call(cpu, CPU.rotate_right, cpu.a)
    assert cpu.a.get() == 0x7F + 0x80
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x01)
    method_register_call(cpu, CPU.rotate_right, cpu.a)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=False, h=False, c=True)
    
    cpu.flag.set(0xFF)
    cpu.a.set(0x01)
    method_register_call(cpu, CPU.rotate_right, cpu.a)
    assert cpu.a.get() == 0x80
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x08)
    method_register_call(cpu, CPU.rotate_right, cpu.a)
    assert cpu.a.get() == 0x04
    assert_flags(cpu, z=False, n=False, h=False, c=False)
   
    for i in range(0, 7):
        cpu.flag.set(0x00)
        cpu.a.set(0x80 >> i)
        method_register_call(cpu, CPU.rotate_right, cpu.a)
        assert cpu.a.get() == 0x80 >> (i+1)
        assert_flags(cpu, z=False, n=False, h=False, c=False)
    
def test_rotate_left_circular():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0xFF)
    method_register_call(cpu, CPU.rotate_left_circular, cpu.a)
    assert cpu.a.get() == 0xFF
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu = get_cpu()
    cpu.flag.set(0x00)
    cpu.a.set(0xFF)
    method_register_call(cpu, CPU.rotate_left_circular, cpu.a)
    assert cpu.a.get() == 0xFF
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x80)
    method_register_call(cpu, CPU.rotate_left_circular, cpu.a)
    assert cpu.a.get() == 0x01
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu.flag.set(0xFF)
    cpu.a.set(0x01)
    method_register_call(cpu, CPU.rotate_left_circular, cpu.a)
    assert cpu.a.get() == 0x02
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
def test_rotate_right_circular():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0xFF)
    method_register_call(cpu, CPU.rotate_right_circular, cpu.a)
    assert cpu.a.get() == 0xFF
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu = get_cpu()
    cpu.flag.set(0x00)
    cpu.a.set(0xFF)
    method_register_call(cpu, CPU.rotate_right_circular, cpu.a)
    assert cpu.a.get() == 0xFF
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x01)
    method_register_call(cpu, CPU.rotate_right_circular, cpu.a)
    assert cpu.a.get() == 0x80
    assert_flags(cpu, z=False, n=False, h=False, c=True)
    
    cpu.flag.set(0xFF)
    cpu.a.set(0x02)
    method_register_call(cpu, CPU.rotate_right_circular, cpu.a)
    assert cpu.a.get() == 0x01
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
def test_subtract_with_carry_a():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0x01)
    method_value_call(cpu, CPU.subtract_with_carry_a, 0x00)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=True, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x01)
    method_value_call(cpu, CPU.subtract_with_carry_a, 0x00)
    assert cpu.a.get() == 0x01
    assert_flags(cpu, z=False, n=True, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x10)
    method_value_call(cpu, CPU.subtract_with_carry_a, 0x01)
    assert cpu.a.get() == 0x0F
    assert_flags(cpu, z=False, n=True, h=True, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x00)
    method_value_call(cpu, CPU.subtract_with_carry_a, 0x01)
    assert cpu.a.get() == 0xFF
    assert_flags(cpu, z=False, n=True, h=True, c=True)
    
    subtract_flag_test(cpu, CPU.subtract_with_carry_a)
    
def test_subtract_a():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0xFF)
    method_value_call(cpu, CPU.subtract_a, 0x01)
    assert cpu.a.get() == 0xFE
    assert_flags(cpu, z=False, n=True, h=False, c=False)
    
    cpu.flag.set(0xFF)
    cpu.a.set(0x01)
    method_value_call(cpu, CPU.subtract_a, 0x01)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=True, h=False, c=False)
    
    subtract_flag_test(cpu, CPU.subtract_a)
    
def subtract_flag_test(cpu, method):
    cpu.flag.set(0x00)
    cpu.a.set(0xFF)
    method_value_call(cpu, CPU.subtract_a, 0x01)
    assert cpu.a.get() == 0xFE
    assert_flags(cpu, z=False, n=True, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x01)
    method_value_call(cpu, CPU.subtract_a, 0x01)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=True, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x10)
    method_value_call(cpu, CPU.subtract_a, 0x01)
    assert cpu.a.get() == 0x0F
    assert_flags(cpu, z=False, n=True, h=True, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x00)
    method_value_call(cpu, CPU.subtract_a, 0x01)
    assert cpu.a.get() == 0xFF
    assert_flags(cpu, z=False, n=True, h=True, c=True)
     
def test_swap():
    cpu = get_cpu()
    cpu.flag.set(0xFF)
    cpu.a.set(0x12)
    method_register_call(cpu, CPU.swap, cpu.a)
    assert cpu.a.get() == 0x21
    assert_flags(cpu, z=False, n=False, h=False, c=False)
    
    cpu.flag.set(0xFF)
    cpu.a.set(0x00)
    method_register_call(cpu, CPU.swap, cpu.a)
    assert cpu.a.get() == 0x00
    assert_flags(cpu, z=True, n=False, h=False, c=False)
    
    cpu.flag.set(0x00)
    cpu.a.set(0x34)
    method_register_call(cpu, CPU.swap, cpu.a)
    assert cpu.a.get() == 0x43
    assert_flags(cpu, z=False, n=False, h=False, c=False)

    