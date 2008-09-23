import py
from pypy.lang.gameboy.cpu import *
from pypy.lang.gameboy.ram import *
from pypy.lang.gameboy import *
from pypy.lang.gameboy.interrupt import * 

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

# ------------------------------------------------------------------------------
# TEST CPU

def test_reset():
    cpu = get_cpu()
    assert cpu.a.get()  == 0x01
    #assert cpu.flag.get() == 0xB0
    assert cpu.b.get()  == 0x00
    assert cpu.c.get()  == 0x13
    assert cpu.de.get() == 0x00D8
    assert cpu.hl.get() == 0x014D
    #assert cpu.sp.get() == 0xFFE

def test_getters():
    cpu = get_cpu()
    assert_default_registers(cpu)
    assert cpu.af.cpu  == cpu
    assert cpu.a.cpu   == cpu
    assert cpu.flag.cpu   == cpu
    
    assert cpu.bc.cpu  == cpu
    assert cpu.b.cpu   == cpu
    assert cpu.c.cpu   == cpu
    
    assert cpu.de.cpu  == cpu
    assert cpu.d.cpu   == cpu
    assert cpu.e.cpu   == cpu
    
    assert cpu.hl.cpu  == cpu
    assert cpu.hli.cpu == cpu
    assert cpu.h.cpu   == cpu
    assert cpu.l.cpu   == cpu
    
    assert cpu.sp.cpu  == cpu
    assert cpu.pc.cpu  == cpu
    

def test_fetch():
    cpu             = get_cpu()
    address         = 0x3FFF
    value           = 0x12
    # in rom
    cpu.pc.set(address)
    cpu.rom[address] = value
    startCycles      = cpu.cycles
    assert cpu.fetch()            == value
    assert startCycles-cpu.cycles == 1
    # in the memory
    value            = 0x13
    address          = 0xC000
    cpu.pc.set(address)
    cpu.memory.write(address, value)
    assert cpu.fetch() == value
    
    
def test_read_write():
    cpu         = get_cpu()
    address     = 0xC000
    value       = 0x12
    startCycles = cpu.cycles
    cpu.write(address, value)
    assert startCycles-cpu.cycles == 2
    startCycles = cpu.cycles
    assert cpu.read(address)      == value
    assert startCycles-cpu.cycles == 1
    
    address    +=1
    value      += 1
    cpu.write(address, value)
    assert cpu.read(address)      == value
    

def test_relative_conditional_jump():
    cpu         = get_cpu()
    pc          = cpu.pc.get()
    value       = 0x12
    cpu.rom[constants.RESET_PC] = value
    # test jr_nn
    startCycles = cpu.cycles
    cpu.relative_conditional_jump(True)
    assert startCycles-cpu.cycles == 3
    assert_registers(cpu, pc=pc+value+1)
    # test pc.inc
    startCycles = cpu.cycles
    pc          = cpu.pc.get()
    cpu.relative_conditional_jump(False)
    assert startCycles-cpu.cycles == 2
    assert cpu.pc.get()           == pc+1
    
    
def test_flags():
    cpu = get_cpu()
    cpu.flag.set(constants.Z_FLAG)
    assert cpu.is_z()     == True
    assert cpu.is_not_z() == False
    cpu.flag.set(~constants.Z_FLAG)
    assert cpu.is_z()     == False
    assert cpu.is_not_z() == True
    
    cpu.flag.set(constants.C_FLAG)
    assert cpu.is_c()     == True
    assert cpu.is_not_c() == False
    cpu.flag.set(~constants.C_FLAG)
    assert cpu.is_c()     == False
    assert cpu.is_not_c() == True
 
def test_flags_memory_access(): 
    cpu = get_cpu()
    cpu.flag.set(constants.Z_FLAG)
    assert cpu.is_z() == True
    prepare_for_fetch(cpu, 0x12, 0x12)
    cpu.memory.write(0x1234, 0x12)
    assert cpu.is_z() == True
    cpu.rom[0x1234] = 0x12
    assert cpu.is_z() == True
   

def fetch_execute_cycle_test(cpu, opCode, cycles=0):
    prepare_for_fetch(cpu, opCode)
    cycle_test(cpu, 0xCB, cycles)
    
def cycle_test(cpu, opCode, cycles=0, opCodeDisplay=None):
    if opCodeDisplay==None:
        opCodeDisplay = hex(opCode)
    startCycles = cpu.cycles
    try:
        cpu.execute(opCode)
    except Exception, inst:
        assert False, "Opcode %s %s failed to execute: %s" % (opCodeDisplay, OP_CODES[opCode], inst)
    cpuUsedCycles = startCycles-cpu.cycles 
    assert cpuUsedCycles == cycles,\
        "Cycles for opCode %s [CPU.%s] should be %i not %i" %\
         ((opCodeDisplay).ljust(2),\
          OP_CODES[opCode],\
          cycles, cpuUsedCycles)
      
      
def fetch_execute_cycle_test_second_order(cpu, opCode, cycles=0):
    prepare_for_fetch(cpu, opCode)
    cycle_test(cpu, 0xCB, cycles, "[0xCB -> "+hex(opCode)+"]")
    
# TEST HELPERS -----------------------------------------------------------------

def test_create_group_op_codes():
    assert len(GROUPED_REGISTERS) == 8
    start   = 0x12
    step    = 0x03
    func    = CPU.inc
    table   = [(start, step, func)]
    grouped = create_group_op_codes(table)
    assert len(grouped) == len(table)*8
    
    opCode = start
    for entry in grouped:
        assert len(entry) == 2
        assert entry[0] == opCode
        #assert entry[1].func_name == "<lambda>"
        #assert entry[1].func_closure[0].cell_contents == func
        opCode += step
        
        
def test_create_register_op_codes():
    start     = 0x09
    step      = 0x10
    func      = CPU.add_hl
    registers = [CPU.get_bc]*128
    table     = [(start, step, func, registers)]
    list      = create_register_op_codes(table)
    opCode     = start
    assert len(list) == len(registers)
    for entry in list:
        assert len(entry) == 2
        assert entry[0] == opCode
        assert entry[1].func_name == "<lambda>"
        #assert entry[1].func_closure[0].cell_contents == func
        opCode += step
 # HELPERS
 
def assert_default_registers(cpu, a=constants.RESET_A, bc=constants.RESET_BC,\
                             de=constants.RESET_DE, f=constants.RESET_F,\
                             hl=constants.RESET_HL, sp=constants.RESET_SP,\
                             pc=constants.RESET_PC):
    return assert_registers(cpu, a, bc, de, f, hl, sp, pc)

def assert_registers(cpu, a=None, bc=None, de=None, f=None, hl=None, sp=None, pc=None):
    if a is not None:
        assert cpu.a.get() == a, "Register a  is %s but should be %s" % (hex(cpu.a.get()), hex(a))
    if bc is not None:
        assert cpu.bc.get() == bc, "Register bc  is %s but should be %s" % (hex(cpu.bc.get()), hex(bc))
    if de is not None:
        assert cpu.de.get() == de, "Register de is %s but should be %s" % (hex(cpu.de.get()),hex(de))
    if f is not None:
        assert cpu.flag.get() == f, "Register f is %s but should be %s" % (hex(cpu.flag.get()),hex(f))
    if hl is not None:
        assert cpu.hl.get() == hl, "Register hl is %s but should be %s" % (hex(cpu.hl.get()), hex(hl))
    if sp is not None:
        assert cpu.sp.get() == sp, "Register sp is %s but should be %s" % (hex(cpu.sp.get()), hex(sp))
    if pc is not None:
        assert cpu.pc.get() == pc, "Register pc is %s but should be %s" % (hex(cpu.pc.get()), hex(pc))
        

def assert_default_flags(cpu, z_flag=True, n_flag=False, h_flag=False, c_flag=False, p_flag=False, s_flag=False):        
    assert_flags(cpu, z_flag, n_flag, h_flag, c_flag, p_flag, s_flag)

def assert_flags(cpu, z_flag=None, n_flag=None, h_flag=None, c_flag=None, p_flag=None, s_flag=None):
    if z_flag is not None:
        assert cpu.flag.is_zero == z_flag, "Z-Flag is %s but should be %s" % (cpu.flag.is_zero, z_flag)
    if n_flag is not None:
        assert cpu.flag.is_subtraction == n_flag, "N-Flag is %s but should be %s" % (cpu.flag.is_subtraction, n_flag)
    if h_flag is not None:
        assert cpu.flag.is_half_carry == h_flag,  "H-Flag is %s but should be %s" % (cpu.flag.is_half_carry, h_flag)
    if c_flag is not None:
        assert cpu.flag.is_carry == c_flag,  "C-Flag is %s but should be %s" % (cpu.flag.is_carry, c_flag)
    if p_flag is not None:
        assert cpu.flag.p_flag == p_flag,  "P-Flag is %s but should be %s" % (cpu.flag.p_flag, p_flag)
    if s_flag is not None:
        assert cpu.flag.s_flag == s_flag,  "S-Flag is %s but should be %s" % (cpu.flag.s_flag, s_flag)

def prepare_for_fetch(cpu, value, valueLo=None):
    pc = cpu.pc.get()
    if valueLo is not None:
        cpu.rom[pc] = valueLo & 0xFF
        cpu.memory.write(pc, valueLo & 0xFF)
        pc += 1
    cpu.rom[pc] = value & 0xFF
    cpu.memory.write(pc, value & 0xFF)
    
def test_prepare_for_fetch():
    cpu   = get_cpu()
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
    cpu   = get_cpu()
    value = 0x12
    prepare_for_pop(cpu, value+5, value)
    assert cpu.pop() == value
    assert cpu.pop() == value+5
        
def set_registers(registers, value):
    #if registers is not list:
      #  registers = [registers]
    for register in registers:
        register.set(value);
        
        
# test helper methods ----------------------------------------------------------

def test_prepare_for_pop():
    cpu   = get_cpu()
    value = 0x12
    prepare_for_pop(cpu, value, value+1)
    assert cpu.pop() == value+1
    assert cpu.pop() == value
    
def test_prepare_for_fetch():
    cpu   = get_cpu()
    value = 0x12
    prepare_for_fetch(cpu, value, value+1)
    assert cpu.fetch() == value+1
    assert cpu.fetch() == value

# CPU Helper Methods Testing ---------------------------------------------------

def test_fetch():
    cpu = get_cpu()
    cpu.pc.set(100)
    prepare_for_fetch(cpu, 0x12)
    assert cpu.fetch() == 0x12
    assert_default_registers(cpu, pc=100+1)
    
def test_fetch_double_address():
    cpu = get_cpu()
    cpu.pc.set(100)
    prepare_for_fetch(cpu, 0x12, 0x34)
    assert cpu.fetch_double_address() ==  0x1234
    assert_default_registers(cpu, pc=100+2)
    

def test_push_double_register():
    cpu = get_cpu()
    cpu.sp.set(0x03)
    cpu.pc.set(0x1234)
    cpu.push_double_register(cpu.pc)
    assert_default_registers(cpu, sp=1, pc=0x1234)
    assert cpu.pop() == 0x34
    assert cpu.pop() == 0x12
    
    
def test_call():
    cpu = get_cpu()
    cpu.pc.set(0x1234)
    cpu.sp.set(3)
    cpu.call(0x4321)
    assert_default_registers(cpu, sp=1, pc=0x4321)
    assert cpu.pop() == 0x34
    assert cpu.pop() == 0x12
    
# ------------------------------------------------------------------------------
# opCode Testing

#nop
def test_0x00():
    cpu = get_cpu()
    cycle_test(cpu, 0x00, 1)
    assert_default_registers(cpu)

#load_mem_SP
def test_0x08():
    cpu     = get_cpu()
    assert_default_registers(cpu)
    startPC = cpu.pc.get()
    prepare_for_fetch(cpu, 0xCD, 0xEF)
    cpu.sp.set(0x1234)
    cycle_test(cpu, 0x08, 5)
    assert_default_registers(cpu, pc=startPC+2, sp=0x1234)
    assert cpu.memory.read(0xCDEF)   == cpu.sp.get_lo()
    assert cpu.memory.read(0xCDEF+1) == cpu.sp.get_hi()
    
# stop
def test_0x10():
    cpu = get_cpu()
    pc  = cpu.pc.get()
    cycle_test(cpu, 0x10, 0)
    # fetches 1 cycle
    assert_default_registers(cpu, pc=pc+1)
    
# jr_nn
def test_0x18_relative_jump():
    cpu   = get_cpu();
    for jump in range(-128,128):
        cpu.pc.set(0x1234)
        prepare_for_fetch(cpu, jump & 0xFF)
        cycle_test(cpu, 0x18, 3)
        # relative offset + one fetch
        assert cpu.pc.get() == 0x1234 + jump + 1
        assert_default_registers(cpu, f=cpu.flag.get(), pc=0x1234+jump+1)
    
# jr_NZ_nn see test_jr_cc_nn
def test_0x20_to_0x38_relative_conditional_jump():
    cpu    = get_cpu()
    flags  = [~constants.Z_FLAG, constants.Z_FLAG, ~constants.C_FLAG, constants.C_FLAG]
    opCode = 0x20
    value  = 0x12
    for i in range(0, 4):
        for jump in range(-128,128):
            cpu.pc.set(0x1234)
            prepare_for_fetch(cpu, jump & 0xFF)
            cpu.flag.set(flags[i])
            cycle_test(cpu, opCode, 3)
            # relative offset + one fetch
            assert cpu.pc.get() == 0x1234 + jump + 1
            assert_default_registers(cpu, f=cpu.flag.get(), pc=0x1234+jump+1)
        
        pc = cpu.pc.get()
        cpu.flag.set(~flags[i])
        cycle_test(cpu, opCode, 2)
        assert cpu.pc.get() == pc+1
        assert_default_registers(cpu, f=cpu.flag.get(), pc=pc+1)
        value  += 3
        opCode += 0x08
        
# ld_BC_nnnn to ld_SP_nnnn
def test_0x01_0x11_0x21_0x31_load_register_nnnn():
    cpu       = get_cpu()
    registers = [cpu.bc, cpu.de, cpu.hl, cpu.sp]
    value     = 0x12
    opCode    = 0x01
    for index in range(0, len(registers)):
        prepare_for_fetch(cpu, value, value+1)
        cycle_test(cpu, opCode, 3)
        assert registers[index].get_lo() == value+1
        assert registers[index].get_hi() == value
        value  += 3
        opCode += 0x10
        
# add_HL_BC to add_HL_SP
def test_0x09_0x19_0x29_0x39_add_HL():
    cpu       = get_cpu()
    registers = [cpu.bc, cpu.de, cpu.hl, cpu.sp]
    value     = 0x1234
    opCode    = 0x09
    for i in range(0, len(registers)):
        cpu.hl.set(value)
        registers[i].set(value)
        assert  registers[i].get() == value
        cycle_test(cpu, opCode, 2)
        assert cpu.hl.get()        == value+value
        value  += 3
        opCode += 0x10
        
# ld_BCi_A
def test_0x02():
    cpu = get_cpu();
    cpu.bc.set_hi_lo(0xC2, 0x23);
    cpu.a.set(0x12);
    cycle_test(cpu, 0x02, 2);
    assert cpu.read(cpu.bc.get()) == cpu.a.get()
    
# ld_A_BCi
def test_0x0A():
    cpu     = get_cpu()
    value   = 0x12
    address = 0xC020
    cpu.bc.set(address)
    cpu.write(address, value)
    assert cpu.read(address) == value
    cycle_test(cpu, 0x0A, 2)
    assert_default_registers(cpu, a=value, bc=address)
    
        
# ld_DEi_A
def test_0x12():
    cpu = get_cpu();
    cpu.de.set_hi_lo(0xC2, 0x23);
    cpu.a.set(0x12);
    cycle_test(cpu, 0x12, 2);
    assert cpu.read(cpu.de.get()) == cpu.a.get()

# load_a_DEi
def test_0x1A_store_memory_at_de_in_a():
    cpu     = get_cpu()
    value   = 0x12
    address = 0xC020
    cpu.de.set(address)
    cpu.write(address, value)
    assert cpu.read(address) == value
    cycle_test(cpu, 0x1A, 2)
    assert_default_registers(cpu, a=value, de=address)

# ldi_HLi_A
def test_0x22():
    cpu = get_cpu();
    cpu.hl.set_hi_lo(0xCD, 0xEF);
    cpu.a.set(0x12);
    cycle_test(cpu, 0x22, 2);
    assert cpu.read(0xCDEF) == cpu.a.get()
    assert cpu.hl.get()     == 0xCDEF+1

# ldd_HLi_A
def test_0x32():
    cpu = get_cpu();
    cpu.hl.set_hi_lo(0xCD, 0xEF);
    cpu.a.set(0x12);
    cycle_test(cpu, 0x32, 2);
    assert cpu.read(0xCDEF) == cpu.a.get()
    assert cpu.hl.get()     == 0xCDEF-1
    
    
# ldi_A_HLi
def test_0x2A():
    cpu     = get_cpu()
    value   = 0x12
    address = 0xCDEF
    cpu.hl.set(address)
    cpu.write(address, value)
    assert cpu.read(address) == value
    cycle_test(cpu, 0x2A, 2)
    assert_default_registers(cpu, a=value, hl=address+1)

# ldd_A_HLi
def test_0x3A():
    cpu     = get_cpu()
    value   = 0x12
    address = 0xCDEF
    cpu.hl.set(address)
    cpu.write(address, value)
    assert cpu.read(address) == value
    cycle_test(cpu, 0x3A, 2)
    assert_default_registers(cpu, a=value, hl=address-1)
    
# inc_BC DE HL SP
def test_0x03_to_0x33_inc_double_registers():
    cpu       = get_cpu()
    opCode    = 0x03
    registers = [cpu.bc, cpu.de, cpu.hl, cpu.sp]
    value     = 0x12
    for i in range(0,4):
        set_registers(registers, 0)
        registers[i].set(value)
        cycle_test(cpu, opCode, 2);
        assert  registers[i].get() == value + 1
        cpu.reset()
        opCode += 0x10
        value  += 3
 
# dec_BC
def test_0x0B_to_0c38_dec_double_registers():
    cpu       = get_cpu()
    opCode    = 0x0B
    registers = [cpu.bc, cpu.de, cpu.hl, cpu.sp]
    value     = 0x12
    for i in range(0,4):
        set_registers(registers, 0)
        registers[i].set(value)
        cycle_test(cpu, opCode, 2);
        assert  registers[i].get() == value - 1
        cpu.reset()
        cpu.reset()
        opCode += 0x10
        value  += 3
        
def test_inc():
    cpu = get_cpu()
    # cycle testing is done in the other tests
    a = cpu.a
    a.set(0xFF)
    cpu.flag.is_carry = True
    cpu.inc(RegisterCallWrapper(a), RegisterCallWrapper(a))
    assert_default_flags(cpu, z_flag=True, h_flag=True, c_flag=True)
    
    a.set(0x01)
    cpu.inc(RegisterCallWrapper(a), RegisterCallWrapper(a))
    assert_default_flags(cpu, z_flag=False, h_flag=False, c_flag=True)
    
    a.set(0x0F)
    cpu.inc(RegisterCallWrapper(a), RegisterCallWrapper(a))
    assert_default_flags(cpu, z_flag=False, h_flag=True, c_flag=True)

# inc_B C D E H L  A
def test_0x04_to_0x3C_inc_registers():
    cpu       = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    opCode    = 0x04
    value     = 0x12
    for register in registers:
        if register == cpu.hli:
            opCode += 0x08
            continue
        set_registers(registers, 0)
        register.set(value)
        cycle_test(cpu, opCode, 1)
        assert register.get() == value+1
        cpu.reset()
        opCode += 0x08
        value  += 3
        
# inc_HLi
def test_0x34_increment_hli():
    cpu   = get_cpu()
    cpu.hl.set(0xCDEF)
    cpu.write(cpu.hl.get(), 0x12)
    assert cpu.read(cpu.hl.get()) == 0x12
    cycle_test(cpu, 0x34, 3)
    assert cpu.read(cpu.hl.get()) == 0x12 +1
    

def test_dec():
    cpu          = get_cpu()
    # cycle testing is done in the other tests
    a            = cpu.a
    a.set(1)
    cpu.flag.is_carry = True
    cpu.dec(RegisterCallWrapper(a), RegisterCallWrapper(a))
    assert_default_flags(cpu, z_flag=True, h_flag=False, n_flag=True, c_flag=True)
    
    a.set(1)
    cpu.flag.is_carry = False
    cpu.dec(RegisterCallWrapper(a), RegisterCallWrapper(a))
    assert_default_flags(cpu, z_flag=True, h_flag=False, n_flag=True, c_flag=False)
    
    a.set(0x0F+1)
    cpu.flag.is_carry = True
    cpu.dec(RegisterCallWrapper(a), RegisterCallWrapper(a))
    assert_default_flags(cpu, z_flag=False, h_flag=True, n_flag=True, c_flag=True)
    
    a.set(0x0F+1)
    cpu.flag.is_carry = False
    cpu.dec(RegisterCallWrapper(a), RegisterCallWrapper(a))
    assert_default_flags(cpu, z_flag=False, h_flag=True, n_flag=True, c_flag=False)
    

# dec_B C D E H L  A
def test_0x05_to_0x3D_dec_registers():
    cpu       = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    opCode    = 0x05
    value     = 0x12
    for register in registers:
        if register ==  cpu.hli:
            opCode += 0x08
            continue
        cpu.reset()
        set_registers(registers, 0)
        register.set(value)
        cycle_test(cpu, opCode, 1)
        assert register.get() == value-1
        opCode += 0x08
        value  += 3

# dec_HLi
def test_0x35_decrement_hli():
    cpu   = get_cpu()
    cpu.hl.set(0xCDEF)
    cpu.write(cpu.hl.get(), 0x12)
    assert cpu.read(cpu.hl.get()) == 0x12
    cycle_test(cpu, 0x35, 3)
    assert cpu.read(cpu.hl.get()) == 0x12 -1
    
# ld_B_nn C D E H L A )
def test_0x06_to_0x3A():
    cpu       = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    opCode    = 0x06
    value     = 0x12
    for i in range(0, len(registers)):
        if registers[i] ==  cpu.hli:
            opCode += 0x08
            continue
        oldPC = cpu.pc.get()
        set_registers(registers, 0)
        prepare_for_fetch(cpu, value)
        cycle_test(cpu, opCode, 2)
        assert registers[i].get()   == value
        # one fetch
        assert cpu.pc.get() - oldPC == 1
        cpu.reset()
        opCode += 0x08
        value  += 3
        
# ld_HLi_nn
def test_0x36():
    cpu     = get_cpu()
    value   = 0x12
    address = 0xCDEF
    prepare_for_fetch(cpu, value)
    cpu.hl.set(address)
    oldPC   = cpu.pc.get()
    cycle_test(cpu, 0x36, 3)
    assert cpu.read(cpu.hl.get()) == value
    assert_default_registers(cpu, pc=oldPC+1, hl=address)
    
# rlca
def test_0x07():
    cpu   = get_cpu()
    value = 0x80
    cpu.a.set(value)
    cycle_test(cpu, 0x07, 1)   
    assert_default_registers(cpu, a=((value << 1) | (value >> 7)) & 0xFF, f=None);
    
    cpu.reset()
    value = 0x40
    cpu.a.set(value)
    cycle_test(cpu, 0x07, 1)
    assert_default_registers(cpu, a=((value << 1) | (value >> 7)) & 0xFF, f=None);
    
# rrca
def test_0x0F():
    cpu   = get_cpu()
    value = 0x01
    cpu.a.set(value)
    cycle_test(cpu, 0x0F, 1)
    assert_default_registers(cpu, a=((value >> 1) | (value << 7)) & 0xFF, f=None);
    
    cpu.reset()
    value = 0x02
    cpu.a.set(value)
    cycle_test(cpu, 0x0F, 1)
    assert_default_registers(cpu, a=((value >> 1) | (value << 7)) & 0xFF, f=None);

# rla
def test_0x17():
    cpu   = get_cpu()
    value = 0x01
    cpu.flag.set(0x00)
    cpu.a.set(value)
    cycle_test(cpu, 0x17, 1)
    assert_default_registers(cpu, a=(value << 1) & 0xFF, f=None);
    
# rra
def test_0x1F():
    cpu   = get_cpu()
    value = 0x40
    cpu.flag.set(0x00)
    cpu.a.set(value)
    cycle_test(cpu, 0x1F, 1)
    assert_default_registers(cpu, a=(value >> 1) & 0xFF, f=None);
    
    cpu.reset()
    cpu.flag.set(0x00)
    value = 0x40
    cpu.a.set(value)
    cycle_test(cpu, 0x1F, 1)
    assert_default_registers(cpu, a=(value >> 1) & 0xFF, f=None);
    
    cpu.reset()
    cpu.flag.set(0x00)
    value = 0x02
    cpu.a.set(value)
    cycle_test(cpu, 0x1F, 1)
    assert_default_registers(cpu, a=(value >> 1) & 0xFF, f=None);

# daa
def test_0x27():
    cpu = get_cpu()
    cycle_test(cpu, 0x27, 1)

# cpl
def test_0x2F_complement_a():
    cpu          = get_cpu()
    value        = 0x12
    fValue       = cpu.flag.get()
    cpu.flag.is_subtraction = False
    cpu.flag.is_half_carry = False
    cpu.a.set(value)
    cycle_test(cpu, 0x2F, 1)
    assert_default_registers(cpu, a=value^0xFF, f=None)

# scf
def test_0x37():
    cpu = get_cpu()
    cpu.flag.is_carry = False
    cycle_test(cpu, 0x37, 0)
    assert_default_registers(cpu, f=None)
    assert_default_flags(cpu, c_flag=True)
    
    cpu.flag.is_carry = True
    cycle_test(cpu, 0x37, 0)
    assert_default_registers(cpu, f=None)
    assert_default_flags(cpu, c_flag=True)

# ccf
def test_0x3F():
    cpu = get_cpu()
    cpu.flag.is_carry = True
    cycle_test(cpu, 0x3F, 0)
    assert_default_registers(cpu, f=None)
    assert_default_flags(cpu, c_flag=False)
    
    cpu.flag.is_carry = False
    cycle_test(cpu, 0x3F, 0)
    assert_default_registers(cpu, f=None)
    assert_default_flags(cpu, c_flag=True)
    
# halt
def test_0x76():
    cpu        = get_cpu()
    cpu.cycles = 0xFF
    cpu.ime    = True
    assert cpu.halted == False
    cycle_test(cpu, 0x76, cpu.cycles)
    assert cpu.halted == True
    assert_default_registers(cpu)


# ld_B_B to ld_A_A
def test_load_registers():
    cpu    = get_cpu()
    opCode = 0x40
    value  = 0x12
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for store in registers:
         for load in registers:
             if store == cpu.hli and load == cpu.hli:
                 opCode += 0x01
                 continue
             cpu.reset()
             set_registers(registers, 0)
             load.set(value)
             numCycles= 1
             if store == cpu.hli or load == cpu.hli:
                numCycles = 2
             cycle_test(cpu, opCode, numCycles)
             assert store.get() == value
             opCode += 0x01

    
# add_A_B to add_A_A
def test_0x80_to_0x87_add_A():
    cpu    = get_cpu()
    opCode = 0x80
    valueA = 0x11
    value  = 0x12
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(valueA)
        register.set(value)
        if register == cpu.hli:
            numCycles = 2
        else:
            numCycles= 1
        cycle_test(cpu, opCode, numCycles)
        if register == cpu.a:
            assert cpu.a.get() == 2*value
        else:
            assert cpu.a.get() == valueA + value
        value  += 3
        opCode += 0x01

# adc_A_B to adc_A_A
def test_0x88_to_0x8F_add_with_carry_a():
    cpu    = get_cpu()
    opCode = 0x88
    value  = 0x12
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(value)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        assert cpu.a.get() == 2*value
        
        cpu.reset()
        cpu.flag.is_carry = True
        cpu.a.set(value-1)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        if register == cpu.a:
            assert cpu.a.get() == 2*value+1
        else:
            assert cpu.a.get() == 2*value
        value  += 3
        opCode += 0x01

# sub_A_B to sub_A_A
def test_0x90_to_0x98_subtract_a():
    cpu       = get_cpu()
    opCode    = 0x90
    value     = 0x12
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(value)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        assert cpu.a.get() == 0
        value  += 3
        opCode += 0x01
    
# sbc_A_B to sbc_A_A
def test_0x98_0x9F_subtract_with_carry_a():
    cpu       = get_cpu()
    opCode    = 0x98
    value     = 0x12
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(value)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        assert cpu.a.get() == 0
        
        cpu.reset()
        cpu.flag.is_carry = True
        cpu.a.set(value+1)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        if register == cpu.a:
            assert cpu.a.get() == 0xFF
        else:
            assert cpu.a.get() == 0
        
        value  += 3
        opCode += 0x01
    
# and_A_B to and_A_A
def test_0xA0_to_0xA7_and_a():
    cpu       = get_cpu()
    opCode    = 0xA0
    value     = 0x12
    valueA    = 0x11
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(valueA)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        if register == cpu.a:
            assert cpu.a.get() == (value & value)
        else:
            assert cpu.a.get() == (valueA & value)
        value  += 1
        opCode += 0x01
    
# xor_A_B to xor_A_A
def test_0xA8_to_0xAF():
    cpu       = get_cpu()
    opCode    = 0xA8
    value     = 0x12
    valueA    = 0x11
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(valueA)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        if register == cpu.a:
            assert cpu.a.get() == (value ^ value)
        else:
            assert cpu.a.get() == (valueA ^ value)
        value  += 1
        opCode += 0x01

    
# or_A_B to or_A_A
def test_0xB0_to_0xB7():
    cpu       = get_cpu()
    opCode    = 0xB0
    value     = 0x12
    valueA    = 0x11
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(valueA)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        if register == cpu.a:
            assert cpu.a.get() == (value | value)
        else:
            assert cpu.a.get() == (valueA | value)
        value  += 1
        opCode += 0x01

# cp_A_B to cp_A_A
def test_0xB8_to_0xBF_compare_a():
    cpu       = get_cpu()
    opCode    = 0xB8
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(0x12)
        register.set(0x22)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        if register == cpu.a:
            assert cpu.flag.is_zero == True
        else:
            assert cpu.flag.is_zero == False
        
        cpu.a.set(0x12)
        register.set(0x12)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        assert cpu.flag.is_zero == True
            
        opCode += 0x01

# ret_NZ to ret_C
def test_0xC0_to_0xD8_return_on_condition():
    cpu    = get_cpu()
    flags  = [~constants.Z_FLAG, constants.Z_FLAG, ~constants.C_FLAG, constants.C_FLAG]
    opCode = 0xC0
    value  = 0x1234
    for i in range(0, 4):
        cpu.reset()
        prepare_for_pop(cpu, value >> 8, value & 0xFF)
        cpu.flag.set(flags[i])
        cycle_test(cpu, opCode, 5)
        assert cpu.pc.get() == value
        
        cpu.reset()
        prepare_for_pop(cpu, value >> 8, value & 0xFF)
        cpu.flag.set(~flags[i])
        cycle_test(cpu, opCode, 2)
        assert_default_registers(cpu, f=cpu.flag.get())
        value  += 3
        opCode += 0x08

# ldh_mem_A
def test_0xE0():
    cpu    = get_cpu()
    valueA = 0x11
    value  = 0x12
    prepare_for_fetch(cpu, value)
    cpu.a.set(valueA)
    cycle_test(cpu, 0xE0, 3)
    assert cpu.read(0xFF00+value) == valueA
    

# add_SP_nn
def test_0xE8():
    cpu     = get_cpu()
    value   = 0x12
    spValue = 0xCDEF
    prepare_for_fetch(cpu, value)
    cpu.sp.set(spValue)
    cycle_test(cpu, 0xE8, 4)
    assert cpu.sp.get() == spValue+value

# ldh_A_mem
def test_0xF0_store_memory_at_axpanded_fetch_address_in_a():
    cpu     = get_cpu()
    valueA  = 0x11
    value   = 0x12
    address = 0x13
    cpu.a.set(valueA)
    prepare_for_fetch(cpu, address)
    cpu.write(0xFF00+address, value)
    cycle_test(cpu, 0xF0, 3)
    assert cpu.a.get() == value

# ld_A_mem
def test_0xFA_store_fetched_memory_in_a():
    cpu    = get_cpu()
    value  = 0x11
    valueA = 0x12
    cpu.a.set(valueA)
    pc     = cpu.pc.get();
    prepare_for_fetch(cpu, 0x12, 0x34)
    cpu.write(0x1234, value)
    cycle_test(cpu, 0xFA, 4)
    assert_default_registers(cpu, a=value, pc=pc+2)

# ld_mem_A
def test_0xEA_store_a_at_fetched_address():
    cpu    = get_cpu()
    valueA = 0x56
    prepare_for_fetch(cpu, 0x12, 0x34)
    cpu.a.set(valueA)
    cycle_test(cpu, 0xEA, 4)
    assert cpu.read(0x1234) == valueA
    
    
# ld_HL_SP_nn
def test_0xF8():
    cpu     = get_cpu()
    value   = 0x12
    valueSp = 0x1234
    prepare_for_fetch(cpu, value)
    cpu.sp.set(valueSp)
    pc      = cpu.pc.get()
    cycle_test(cpu, 0xF8, 3)
    f       = cpu.flag.get();
    assert_default_registers(cpu, hl=valueSp+value, f=f, sp=valueSp, pc=pc+1)

# pop_BC to pop_AF
def test_0xC1_to_0xF1():
    cpu       = get_cpu()
    registers = [cpu.bc, cpu.de, cpu.hl, cpu.af]
    opCode    = 0xC1
    value     = 0x1234
    for register in registers:
        cpu.reset()
        prepare_for_pop(cpu, value >> 8, value & 0xFF)
        cycle_test(cpu, opCode, 3)
        assert register.get() == value
        value  += 3
        opCode += 0x10

# ret
def test_0xC9():
    cpu     = get_cpu()
    value   = 0x1234
    valueSp = 0x5678
    cpu.sp.set(valueSp)
    prepare_for_pop(cpu, value >> 8, value & 0xFF)
    cycle_test(cpu, 0xC9, 4)
    assert_default_registers(cpu, pc=value, sp=valueSp+2)

# reti
def test_0xD9_return_form_interrupt():
    cpu   = get_cpu()
    cpu.interrupt.reset()
    value = 0x1234
    cpu.sp.set(0)
    prepare_for_pop(cpu, value >> 8, value & 0xFF)
    prepare_for_fetch(cpu, 0x00)
    pc    = cpu.pc.get()
    cycle_test(cpu, 0xD9, 4+1+1) 
    # pc: popped value + 
    assert_default_registers(cpu, pc=value+1, sp=2)
    
def test_handle_interrupt():
    cpu        = get_cpu()
    cpu.interrupt.reset()
    cpu.halted = True
    cpu.cycles = 0xFF
    cpu.handle_pending_interrupts()
    assert cpu.cycles == 0
    
    cpu.reset()
    cpu.interrupt.reset()
    cpu.halted = True
    cpu.cycles = 4
    cpu.interrupt.set_enable_mask(0xFF)
    cpu.interrupt.v_blank.set_pending()
    assert cpu.interrupt.is_pending() == True
    assert cpu.halted                 == True
    cpu.handle_pending_interrupts()
    assert cpu.cycles                 == 0
    assert cpu.halted                 == False
    
    cpu.reset()
    cpu.interrupt.reset()
    cpu.halted = False
    cpu.ime    = True
    cpu.pc.set(0x1234)
    cpu.sp.set(0x02)
    sp = cpu.sp.get()
    cpu.interrupt.set_enable_mask(0xFF)
    cpu.interrupt.v_blank.set_pending()
    cpu.interrupt.lcd.set_pending()
    assert cpu.interrupt.is_pending() == True
    cpu.cycles = 0
    cpu.handle_pending_interrupts()
    assert cpu.cycles == 0
    assert cpu.halted == False 
    assert_default_registers(cpu, pc=cpu.interrupt.v_blank.call_code, sp=sp-2)
    assert cpu.pop()  == 0x34
    assert cpu.pop()  == 0x12

# ld_PC_HL 
def test_0xE9_store_hl_in_pc():
    cpu   = get_cpu()
    value = 0x1234
    cpu.hl.set(value)
    cpu.pc.set(0)
    cycle_test(cpu, 0xE9, 1)
    assert_default_registers(cpu, pc=value, hl=value)

# ld_SP_HL
def test_0xF9_store_hl_in_sp():
    cpu   = get_cpu()
    value = 0x1234
    cpu.hl.set(value)
    cpu.sp.set(0)
    cycle_test(cpu, 0xF9, 2)
    assert_default_registers(cpu, sp=value, hl=value)

# jp_NZ_nnnn to jp_C_nnnn
def test_0xC2_to_0xDA_conditional_jump():
    cpu    = get_cpu()
    flags  = [~constants.Z_FLAG, constants.Z_FLAG, ~constants.C_FLAG, constants.C_FLAG]
    opCode = 0xC2
    value  = 0x1234
    for i in range(0, 4):
        cpu.reset()
        prepare_for_fetch(cpu, value >> 8, value & 0xFF)
        pc = cpu.pc.get()
        cpu.flag.set(flags[i])
        cycle_test(cpu, opCode, 4)
        assert_default_registers(cpu, f=flags[i] & 0xFF, pc=value)
        
        cpu.reset()
        prepare_for_fetch(cpu, value >> 8, value & 0xFF)
        cpu.flag.set(~flags[i])
        pc = cpu.pc.get()
        cycle_test(cpu, opCode, 3)
        assert_default_registers(cpu, f=~flags[i] & 0xFF, pc=pc+2)
        value  += 3
        opCode += 0x08

# ldh_Ci_A
def test_0xE2_write_a_at_expanded_c_address():
    cpu    = get_cpu()
    value  = 0x12
    valueA = value+1
    cpu.c.set(value)
    cpu.a.set(valueA)
    cycle_test(cpu, 0xE2, 2)
    assert cpu.read(0xFF00+value) == valueA

# ldh_A_Ci
def test_0xF2():
    cpu    = get_cpu()
    valueC = 0x12
    valueA = 0x11
    cpu.c.set(valueC)
    cpu.b.set(0);
    cpu.write(0xFF00+valueC, valueA)
    cycle_test(cpu, 0xF2, 2)
    assert_default_registers(cpu, a=valueA, bc=valueC)

# di
def test_0xF3_disable_interrupt():
    cpu = get_cpu()
    cpu.interrupt.reset()
    cpu.ime = True
    cycle_test(cpu, 0xF3, 1)
    assert cpu.ime == False

# ei
def test_0xFB_enable_interrupt():
    cpu        = get_cpu()
    cpu.interrupt.reset()
    cpu.sp.set(0)
    cpu.ime    = False
    cpu.halted = False
    prepare_for_fetch(cpu, 0x00) # nop 1 cycle
    #print  cpu.interrupt.get_enable_mask()
    assert cpu.interrupt.is_pending() == False
    cycle_test(cpu, 0xFB, 1+1)
    assert cpu.interrupt.is_pending() == False
    assert cpu.ime                    == True
    
    cpu.reset()
    cpu.interrupt.reset()
    cpu.sp.set(0)
    cpu.ime    = True
    cpu.halted = False
    prepare_for_fetch(cpu, 0x00)  # nop 1 cycle
    cpu.interrupt.v_blank.set_pending()
    cpu.interrupt.serial.set_pending()
    cpu.interrupt.set_enable_mask(0x1F)
    assert cpu.interrupt.is_pending() == True
    assert cpu.halted                 == False
    assert cpu.ime                    == True  
    cycle_test(cpu, 0xFB, 1+1)
    assert cpu.interrupt.is_pending()        == True
    assert cpu.interrupt.v_blank.is_pending() == False
    assert cpu.interrupt.serial.is_pending() == True
    assert cpu.pc.get()                      == cpu.interrupt.v_blank.call_code
    assert cpu.ime                           == False
    
    cpu.ime    = True
    cycle_test(cpu, 0xFB, 1+1)
    assert cpu.interrupt.v_blank.is_pending() == False
    assert cpu.interrupt.serial.is_pending() == False
    assert cpu.interrupt.is_pending()        == False

# jp_nnnn

# JUMP AND CALL TESTING ========================================================
def test_0xC3_jump():
    cpu = get_cpu()
    prepare_for_fetch(cpu, 0x12, 0x34)
    cycle_test(cpu, 0xC3, 4)
    assert_default_registers(cpu, pc=0x1234)

def conditional_call_test(cpu, opCode, flagSetter):
    # set the condition to false and dont call
    flagSetter(cpu, False)
    cpu.pc.set(0)
    f = cpu.flag.get()
    cycle_test(cpu, opCode, 3)
    assert_default_registers(cpu, pc=2, f=f)
    # set the condition to true: unconditional_call
    cpu.reset()
    fetchValue = 0x4321
    flagSetter(cpu, True)
    cpu.pc.set(0x1234)
    cpu.sp.set(0x03)
    prepare_for_fetch(cpu, fetchValue >> 8, fetchValue & 0xFF)
    assert cpu.sp.get() == 0x03
    f = cpu.flag.get()
    cycle_test(cpu, opCode, 6)
    assert_default_registers(cpu, pc=fetchValue, sp=1, f=f)
    # 2 fetches happen before the pc is pushed on the stack
    assert cpu.pop() == 0x34 + 2
    assert cpu.pop() == 0x12
    
# call_NZ_nnnn
def test_0xC4_conditional_call_NZ():
    cpu = get_cpu()
    conditional_call_test(cpu, 0xC4, set_flag_0xC4)
    
def set_flag_0xC4(cpu, value):
    cpu.flag.is_zero = not value
    
# call_Z_nnnn
def test_0xCC_call_z_nnn():
    cpu = get_cpu()
    conditional_call_test(cpu, 0xCC, set_flag_0xCC)

def set_flag_0xCC(cpu, value):
    cpu.flag.is_zero = value
    
# call_NC_nnnn
def test_0xD4_call_nc_nnn():
    cpu = get_cpu()
    conditional_call_test(cpu, 0xD4, set_flag_0xD4)

def set_flag_0xD4(cpu, value):
    cpu.flag.is_carry = not value
    
# call_C_nnnn
def test_0xDC_call_C_nnnn():
    cpu = get_cpu()
    conditional_call_test(cpu, 0xDC, set_flag_0xDC)

def set_flag_0xDC(cpu, value):
    cpu.flag.is_carry = value

# call_nnnn
def test_unconditional_call():
    cpu        = get_cpu()
    fetchValue = 0x1234
    cpu.pc.set(0x2244)
    cpu.sp.set(3)
    prepare_for_fetch(cpu, 0x12, 0x34)
    cpu.unconditional_call()
    assert_default_registers(cpu, pc=fetchValue, sp=1)
    # two fetches happened in between
    assert cpu.pop() == 0x44+2
    assert cpu.pop() == 0x22
    
def test_0xCD_unconditional_call():
    cpu        = get_cpu(new=True)
    fetchValue = 0x1234
    cpu.pc.set(0x2244)
    cpu.sp.set(3)
    prepare_for_fetch(cpu, 0x12, 0x34)
    cycle_test(cpu, 0xCD, 6)
    assert_default_registers(cpu, pc=fetchValue, sp=1)
    # two fetches happened in between
    assert cpu.pop() == 0x44+2
    assert cpu.pop() == 0x22

# push_BC to push_AF
def test_0xC5_to_0xF5_push_double_register():
    cpu        = get_cpu()
    registers  = [cpu.bc, cpu.de, cpu.hl, cpu.af]
    opCode     = 0xC5
    value      = 0x1234
    for register in registers:
        sp = cpu.sp.get()
        register.set(value)
        cycle_test(cpu, opCode, 4)
        assert cpu.memory.read(cpu.sp.get()+1) == value >> 8
        assert cpu.memory.read(cpu.sp.get())   == value & 0xFF
        assert cpu.sp.get() == sp - 2
        assert cpu.pop() == value & 0xFF
        assert cpu.pop() == value >> 8
        assert cpu.sp.get() == sp 
        opCode += 0x10
        value  += 0x0101
         
         
def a_nn_test(opCode, cycles, opCaller):
    # flags tested already
    cpu      = get_cpu()
    value    = 0x12
    valueAdd = 0x12
    cpu.a.set(value)
    prepare_for_fetch(cpu, valueAdd,)
    pc       = cpu.pc.get()
    
    cycle_test(cpu, opCode, cycles)
    assert_default_registers(cpu, a=opCaller(value,valueAdd, cpu), pc=pc+1, f=cpu.flag.get())
    return cpu

# add_A_nn
def test_0xC6_add_a_fetch():
    a_nn_test(0xC6, 2, lambda a, b, cpu: a+b)

# adc_A_nn
def test_0xCE_add_a_with_carry_fetch():
    a_nn_test(0xCE, 2, lambda a, b, cpu: a+b)

# sub_A_nn
def test_0xD6_subtract_a_fetch():
    a_nn_test(0xD6, 2, lambda a, b, cpu: a-b)

# sbc_A_nn
def test_0xDE_subtract_with_carry_fetch():
    a_nn_test(0xDE, 2, lambda a, b, cpu: a-b)

# and_A_nn
def test_0xE6_and_a_fetch():
    a_nn_test(0xE6, 2, lambda a, b, cpu: a&b)

# xor_A_nn
def test_0xEE():
    a_nn_test(0xEE, 2, lambda a, b, cpu: a^b)

# or_A_nn
def test_0xF6():
    a_nn_test(0xF6, 2, lambda a, b, cpu: a|b)

# cp_A_nn
def test_0xFE():
    # flags tested already
    cpu    = get_cpu()
    value  = 0x12
    valueA = 0x12
    cpu.a.set(valueA)
    pc     = cpu.pc.get()
    
    cycle_test(cpu, 0xFE, 2)
    
    assert_default_registers(cpu, a=valueA, pc=pc+1, f=cpu.flag.get())
    assert cpu.flag.is_zero == True

# rst(0x00) to rst(0x38)
def test_0xC7_to_0xFF_reset():
    cpu      = get_cpu()
    opCode   = 0xC7
    rstValue = 0x00
    for i in range(0,8):
        cpu.reset()
        cpu.pc.set(0x1234)
        cycle_test(cpu, opCode, 4)
        assert cpu.pop()    == 0x34
        assert cpu.pop()    == 0x12
        assert cpu.pc.get() == rstValue
        opCode   += 0x08
        rstValue += 0x08

# switching to other opcode set
def test_0xCB():
    cpu = get_cpu()
    pc  = cpu.pc.get()
    prepare_for_fetch(cpu, 0x80)
    cycle_test(cpu, 0xCB, 2)
    assert_default_registers(cpu, pc=pc+1)
    

    
# SECOND ORDER op_codes ---------------------------------------------------------

def second_order_test(opCode, createFunction):
    cpu       = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    value     = 0xF0
    for register in registers:
        cpu.reset()
        register.set(value)
        cycles = 2
        if register == cpu.hli:
            cycles = 4
        fetch_execute_cycle_test_second_order(cpu, opCode, cycles)
        assert register.get() ==  createFunction(value)
        opCode += 0x01
        value  += 1

# rlc_B to rlc_A
def test_0x00_to_0x07_rotateLeftCircular():
    second_order_test(0x00, lambda value:((value & 0x7F) << 1) + ((value & 0x80) >> 7))

# rrc_B to rrc_F
def test_0x08_to_0x0F_rotateRightCircular():
    second_order_test(0x08, lambda value:(value >> 1) + ((value & 0x01) << 7))

# rl_B to rl_A
def test_0x10_to_0x17_shift_left():
    second_order_test(0x10, lambda value: (value << 1) & 0xFF )

# rr_B to rr_A
def test_0x18_to_0x1F_shift_right():
    second_order_test(0x18, lambda value: value >> 1)

# sla_B to sla_A
def test_0x20_to_0x27_shift_left_arithmetic():
    second_order_test(0x20, lambda value: (value << 1) & 0xFF)

# sra_B to sra_A
def test_0x28_to_0x2F_shift_right_arithmetic():
    second_order_test(0x28, lambda value: (value >> 1) + (value & 0x80))

# swap_B to swap_A
def test_0x30_to_0x37():
    second_order_test(0x30, lambda value: ((value << 4) + (value >> 4)) & 0xFF)

# srl_B to srl_A
def test_0x38_to_0x3F_shift_word_right_logical():
    second_order_test(0x38, lambda value: value >> 1)

# bit_B to bit_A
def test_testBit_op_codes():
    cpu       = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    opCode    = 0x40
    for register in registers:
        registerOpCode = opCode
        for i in range(8):
            cycles = 2
            if register == cpu.hli:
                cycles = 3
                
            cpu.reset()
            register.set(0)
            fetch_execute_cycle_test_second_order(cpu, registerOpCode, cycles)
            assert cpu.flag.is_zero == True
            
            cpu.reset()
            register.set((1<<i))
            fetch_execute_cycle_test_second_order(cpu, registerOpCode, cycles)
            assert cpu.flag.is_zero == False
            
            registerOpCode += 0x08
        opCode += 0x01
    
# set_B to set_C
def test_setBit_op_codes():
    cpu       = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    value     = 0x12
    opCode    = 0xC0
    for register in registers:
        registerOpCode = opCode
        for i in range(8):
            cycles = 2
            if register == cpu.hli:
                cycles = 4
            cpu.reset()
            #if registerOpCode ==0xFF:
            #    print "6544444444444444"
                
            register.set(0)
            fetch_execute_cycle_test_second_order(cpu, registerOpCode, cycles)
            assert (register.get() & (1<<i)) >> i == 1
            fetch_execute_cycle_test_second_order(cpu, registerOpCode, cycles)
            assert (register.get() & (1<<i)) >> i == 1
            registerOpCode += 0x08
        opCode += 0x01

# res_B to res_A
def test_reset_bit_op_codes():
    cpu       = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    value     = 0x12
    opCode    = 0x80
    for register in registers:
        registerOpCode = opCode
        cycles = 2
        if register == cpu.hli:
            cycles = 4
        for i in range(8):
            cpu.reset()
            register.set(0)
            fetch_execute_cycle_test_second_order(cpu, registerOpCode, cycles)
            assert (register.get() & (1<<i)) == 0
            register.set(0xFF)
            fetch_execute_cycle_test_second_order(cpu, registerOpCode, cycles)
            #print register.get(), (register.get() & (1<<i)), hex(registerOpCode) ,i
            #print
            assert (register.get() & (1<<i)) == 0
                  
            registerOpCode += 0x08
        opCode += 1
    

# LOAD TEST -----------------------------------------------------------------
# just for double checking ;)

def load_test(cpu, test_set):
    value = 0
    for test in test_set:
        opCode    = test[0]
        reg_write = test[1]
        reg_read  = test[2]
        value = 1 + (value + 1) & 0xFE
        reg_write.set(0)
        reg_read.set(value)
        cpu.execute(opCode)
        assert reg_write.get() == reg_read.get(), hex(opCode)+" load failed!"
        
        
def test_load_b():
    cpu           = get_cpu()
    read_register = cpu.b
    load_test(cpu, 
              [(0x40, read_register, cpu.b),
               (0x41, read_register, cpu.c),
               (0x42, read_register, cpu.d),
               (0x43, read_register, cpu.e),
               (0x44, read_register, cpu.h),
               (0x45, read_register, cpu.l),
               #(0x46, read_register, cpu.hli),
               (0x47, read_register, cpu.a)])
    
def test_load_c():
    cpu           = get_cpu()
    read_register = cpu.c
    load_test(cpu, 
              [(0x48, read_register, cpu.b),
               (0x49, read_register, cpu.c),
               (0x4A, read_register, cpu.d),
               (0x4B, read_register, cpu.e),
               (0x4C, read_register, cpu.h),
               (0x4D, read_register, cpu.l),
               #(0x4E, read_register, cpu.hli),
               (0x4F, read_register, cpu.a)])
    
    
def test_load_d():
    cpu           = get_cpu()
    read_register = cpu.d
    load_test(cpu, 
              [(0x50, read_register, cpu.b),
               (0x51, read_register, cpu.c),
               (0x52, read_register, cpu.d),
               (0x53, read_register, cpu.e),
               (0x54, read_register, cpu.h),
               (0x55, read_register, cpu.l),
              # (0x56, read_register, cpu.hli),
               (0x57, read_register, cpu.a)])
    
def test_load_e():
    cpu           = get_cpu()
    read_register = cpu.e
    load_test(cpu, 
              [(0x58, read_register, cpu.b),
               (0x59, read_register, cpu.c),
               (0x5A, read_register, cpu.d),
               (0x5B, read_register, cpu.e),
               (0x5C, read_register, cpu.h),
               (0x5D, read_register, cpu.l),
               #(0x5E, read_register, cpu.hli),
               (0x5F, read_register, cpu.a)])
    
def test_load_h():
    cpu           = get_cpu()
    read_register = cpu.h
    load_test(cpu, 
              [(0x60, read_register, cpu.b),
               (0x61, read_register, cpu.c),
               (0x62, read_register, cpu.d),
               (0x63, read_register, cpu.e),
               (0x64, read_register, cpu.h),
               (0x65, read_register, cpu.l),
               #(0x66, read_register, cpu.hli),
               (0x67, read_register, cpu.a)])
    
def test_load_l():
    cpu           = get_cpu()
    read_register = cpu.l
    load_test(cpu, 
              [(0x68, read_register, cpu.b),
               (0x69, read_register, cpu.c),
               (0x6A, read_register, cpu.d),
               (0x6B, read_register, cpu.e),
               (0x6C, read_register, cpu.h),
               (0x6D, read_register, cpu.l),
               #(0x6E, read_register, cpu.hli),
               (0x6F, read_register, cpu.a)])
    
def test_load_hli():
    cpu           = get_cpu()
    read_register = cpu.hli
    load_test(cpu, 
              [(0x70, read_register, cpu.b),
               (0x71, read_register, cpu.c),
               (0x72, read_register, cpu.d),
               (0x73, read_register, cpu.e),
               (0x74, read_register, cpu.h),
               (0x75, read_register, cpu.l),
               (0x77, read_register, cpu.a)])
    
def test_load_a():
    cpu           = get_cpu()
    read_register = cpu.a
    load_test(cpu, 
              [(0x78, read_register, cpu.b),
               (0x79, read_register, cpu.c),
               (0x7A, read_register, cpu.d),
               (0x7B, read_register, cpu.e),
               (0x7C, read_register, cpu.h),
               (0x7D, read_register, cpu.l),
               #(0x7E, read_register, cpu.hli),
               (0x7F, read_register, cpu.a)])
    
    
    

    
