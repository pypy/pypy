
from pypy.lang.gameboy.cartridge import *
from pypy.lang.gameboy.timer import Clock
from pypy.lang.gameboy import constants
import py
import pdb

class TestClock(object):
    def __init__(self):
        self.time = 0
    
    def get_time(self):
        return self.time
    

def get_clock_driver():
    return Clock()


RAM_SIZE = 3
ROM_SIZE = 2

def get_ram(size=RAM_SIZE):
    return [0] * int(size * constants.RAM_BANK_SIZE)

def get_rom(size=ROM_SIZE):
    return [0xFF] * int(size * constants.ROM_BANK_SIZE)

def fail_ini_test(caller, ram_size, rom_size):
    try:
        caller(ram_size, rom_size)
        py.test.fail("invalid ram/rom bounds check")
    except:
        pass
 
 
 
def basic_read_write_test(mbc, lower, upper):
    write_bounds_test(mbc, lower, upper)
    read_bounds_test(mbc, lower, upper)
    
def write_bounds_test(mbc, lower, upper):
    value = 0
    try:
        mbc.write(lower-1, value)
        py.test.fail("lower bound check failed")
    except:
        pass
    for address in range(lower, upper):
        mbc.write(address, value % 0xFF)
        value += 1
    try:
        mbc.write(upper+1, value)
        py.test.fail("lower upper check failed")
    except:
        pass
    
def read_bounds_test(mbc, lower, upper):
    value = 0
    try:
        mbc.read(lower-1)
        py.test.fail("lower bound check failed")
    except:
        pass
    for address in range(lower, upper, 1):
        assert mbc.read(address) != None
    try:
        mbc.read(upper+1)
        py.test.fail("lower upper check failed")
    except:
        pass
    
def write_ram_enable_test(mbc):
    value = 0
    for address in range(0x1FFF+1):
        mbc.write(address, 0xFF)
        assert mbc.ram_enable == True
        mbc.write(address, 0x00)
        assert mbc.ram_enable == False
    

# -----------------------------------------------------------------------------

def test_mbc_init():
    try:
        MBC(get_ram(), get_rom(), get_clock_driver())
        py.test.fail("")
    except:
        pass

    try:
        MBC(get_ram(), get_rom(), get_clock_driver(), 0, ROM_SIZE-1, 0,
            RAM_SIZE-1)
        py.test.fail("")
    except:
        pass
    
    try:
        MBC(get_ram(), get_rom(), get_clock_driver(), ROM_SIZE+1, ROM_SIZE+1, 
            RAM_SIZE+1, RAM_SIZE+1)
        py.test.fail("")
    except:
        pass

def test_mbc():
    mbc = MBC(get_rom(2), get_ram(2), get_clock_driver(),1, 0xF3, 2, 0xF1)
    assert mbc.min_rom_bank_size == 1
    assert mbc.max_rom_bank_size == 0xF3
    assert mbc.min_ram_bank_size == 2
    assert mbc.max_ram_bank_size == 0xF1
    assert mbc.rom_bank == constants.ROM_BANK_SIZE
    assert mbc.ram_bank == 0
    assert mbc.ram_enable == False
    assert mbc.rom_size == 2*constants.ROM_BANK_SIZE - 1
    assert mbc.ram_size == 2*constants.RAM_BANK_SIZE - 1 
    assert len(mbc.rom) == constants.ROM_BANK_SIZE * 2
    assert len(mbc.ram) == constants.RAM_BANK_SIZE * 2
    

def test_mbc_read_write():
    mbc = MBC([0]*0xFFFF,[0]*0xFFFF, get_clock_driver(),1, 0xFFFF, 2, 0xFFFF)
    try:
        mbc.write(0, 0)
        py.test.fail(" MBC has an abstract write")
    except:
        pass
    
    try:
        mbc.read(0x1FFFF+1)
        py.test.fail(" write address to high")
    except:
        pass
 
def test_mbc_basic_read_write_test(mbc=None):  
    if mbc==None:
        mbc = MBC([0]*0xFFFF,[0]*0xFFFF, get_clock_driver(),1, 0xFFFF, 2, 0xFFFF)

    value = 0x12
    mbc.rom[0x3FFF] = value
    assert mbc.read(0x3FFF) == value
    
    mbc.rom[mbc.rom_bank] = value
    assert mbc.read(0x4000) == value
    
    
    mbc.ram[mbc.ram_bank] = value
    mbc.ram_enable = False
    try:
        mbc.read(0xA000)
        py.test.fail("ram is not enabled")
    except:
        pass
    mbc.ram_enable = True
    assert mbc.read(0xA000) == value

# -----------------------------------------------------------------------------

def get_default_mbc():
    return DefaultMBC([0]*0xFFFF, [0]*0xFFFF, get_clock_driver()) 

def test_default_mbc_read_write():
    mbc = get_default_mbc()
    mbc.ram_bank = 0
    mbc.ram_enable = True
    for i in range(0xA000, 0xBFFF):
        mbc.write(i, i)
        assert mbc.read(i) == i

# -----------------------------------------------------------------------------

def get_mbc1(rom_size=128, ram_size=4):
    return MBC1(get_rom(rom_size), get_ram(ram_size), get_clock_driver())

def test_mbc1_create(mbc=None):
    if mbc is None:
        mbc = get_mbc1()
    assert mbc.rom_bank == constants.ROM_BANK_SIZE
    assert mbc.memory_model == 0
    assert mbc.ram_enable == False
    assert mbc.ram_bank == 0
    fail_ini_test(mbc, 128, 5)
    fail_ini_test(mbc, 128, -1)
    fail_ini_test(mbc, 1, 4)
    fail_ini_test(mbc, 129, 4)
    
    basic_read_write_test(mbc, 0, 0x7FFF)
    
def test_mbc1_reset(mbc=None):
    if mbc==None:
        mbc = get_mbc1()
    mbc.rom_bank = 0
    mbc.memory_model = 1
    mbc.ram_enable = True
    mbc.ram_bank = 1
    mbc.rom = range(0, 128, 3)
    mbc.ram = range(0, 128, 3)
    mbc.reset()
    assert mbc.rom_bank == constants.ROM_BANK_SIZE
    assert mbc.memory_model == 0
    assert mbc.ram_enable == False
    assert mbc.ram_bank == 0
    assert len(mbc.rom) > 0
    assert len(mbc.ram) > 0
    
    
def test_mbc1_write_ram_enable(mbc=None):
    if mbc is None:
        mbc = get_mbc1()
    write_ram_enable_test(mbc)
        
def test_mbc1_write_rom_bank_test1(mbc=None):
    if mbc is None:
        mbc = get_mbc1()
    value = 1   
    for address in range(0x2000, 0x3FFF+1):
        mbc.memory_model = 0
        rom_bank = mbc.rom_bank
        mbc.write(address, value)
        assert mbc.rom_bank == ((rom_bank & 0x180000) + \
                                ((value & 0x1F) << 14)) & mbc.rom_size
        mbc.memory_model = 10
        mbc.write(address, value)
        assert mbc.rom_bank == ((value & 0x1F) << 14) & mbc.rom_size
        value = (value+1) % (0x1F-1) +1
        
def test_mbc1_write_rom_bank_test2(mbc=None):
    if mbc is None:
        mbc = get_mbc1()
    value = 1   
    for address in range(0x4000, 0x5FFF+1):
        mbc.memory_model = 0
        rom_bank = mbc.rom_bank
        mbc.write(address, value)
        assert mbc.rom_bank == ((mbc.rom_bank & 0x07FFFF) + \
                                ((value & 0x03) << 19))  & mbc.rom_size;
        mbc.memory_model = 10
        mbc.write(address, value)
        assert mbc.ram_bank == ((value & 0x03) << 13) & mbc.ram_size
        value += 1
        value %= 0xFF 
        
def test_mbc1_read_memory_model(mbc=None):
    if mbc is None:
        mbc = get_mbc1()
    value = 1   
    for address in range(0x6000, 0x7FFF+1):
        mbc.write(address, value)
        assert mbc.memory_model == (value & 0x01)
        value += 1
        value %= 0xFF
        
def test_mbc1_read_write_ram(mbc=None):
    if mbc is None:
        mbc = get_mbc1()
    value = 1
    mbc.ram_enable = True
    for address in range(0xA000, 0xBFFF+1):
        mbc.write(address, value)
        #pdb.runcall(mbc.write, address, value)
        assert mbc.ram[mbc.ram_bank + (address & 0x1FFF)] == value
        assert mbc.read(address) == value;
        value += 1
        value %= 0xFF 

# -----------------------------------------------------------------------------

def get_mbc2(rom_size=16, ram_size=1):
    return MBC2(get_rom(rom_size/32.0), get_ram(ram_size), get_clock_driver())

def test_mbc2_create():
    mbc = get_mbc2()
    fail_ini_test(mbc, 2, 0)
    fail_ini_test(mbc, 2, 2)
    fail_ini_test(mbc, 1, 1)
    fail_ini_test(mbc, 17, 1)
    # FIXME read write test missing
    
    
def test_mbc2_write_ram_enable():
    mbc = get_mbc2()
    value = 0
    for address in range(0x1FFF+1):
        mbc.ram_enable = -1
        mbc.write(address, 0x0A)
        if (address & 0x0100) == 0: 
            assert mbc.ram_enable == True
            mbc.write(address, 0x00)
            assert mbc.ram_enable == False
        else:
            assert mbc.ram_enable == -1
        
def test_mbc2_write_rom_bank_test1():
    mbc = get_mbc2()
    value = 1   
    for address in range(0x2000, 0x3FFF+1):
        mbc.rom_bank = -1
        mbc.write(address, value)
        if (address & 0x0100) != 0:
            assert mbc.rom_bank == ((value & 0x0F) << 14) & mbc.rom_size
        else:
            assert mbc.rom_bank == -1
        value = (value + 1) % (0x0F-1) + 1 
        
def test_mbc2_read_write_ram():
    mbc = get_mbc2()        
    value = 1
    mbc.ram_enable = True
    for address in range(0xA000, 0xA1FF+1):
        mbc.write(address, value)
        assert mbc.ram[(address & 0x01FF)] == value & 0x0F
        assert mbc.read(address) == value;
        value += 1
        value %= 0x0F 
    
# -----------------------------------------------------------------------------

def get_mbc3(rom_size=128, ram_size=4):
   return MBC3(get_rom(rom_size), get_ram(ram_size), get_clock_driver())

get_mbc3()

def test_mbc3_create():
    mbc = get_mbc3()
    fail_ini_test(mbc, 128, 0)
    fail_ini_test(mbc, 128, 5)
    fail_ini_test(mbc, 1, 4)
    fail_ini_test(mbc, 129, 4)
    basic_read_write_test(mbc, 0, 0x7FFF)
    
def test_mbc3_write_ram_enable():
    write_ram_enable_test(get_mbc3())
        
def test_mbc3_write_rom_bank():
    mbc= get_mbc3()
    value = 1   
    for address in range(0x2000, 0x3FFF+1):
        mbc.memory_model = 0
        rom_bank = mbc.rom_bank
        mbc.write(address, value)
        if value == 0:
            assert mbc.rom_bank == ((1 & 0x7F) << 14) & mbc.rom_size
        else:
            assert mbc.rom_bank == ((value & 0x7F) << 14) & mbc.rom_size
        value += 1
        value %= 0xFF
        
def test_mbc3_write_ram_bank():
    mbc = get_mbc3()        
    value = 1   
    for address in range(0x4000, 0x5FFF+1):
        mbc.memory_model = 0
        mbc.write(address, value)
        if value >= 0 and value <= 0x03:
            assert mbc.ram_bank == (value << 13) & mbc.ram_size
        else:
           assert mbc.ram_bank == -1;
           assert mbc.clock_register == value
        value += 1
        value %= 0xFF 
        
def test_mbc3_write_clock_latch():
    mbc = get_mbc3()       
    value = 1   
    for address in range(0x6000, 0x7FFF+1):
        mbc.write(address, value)
        if value == 0 or value == 1:    
            assert mbc.clock_latch == value
        if value == 1:
            # clock update check...
            pass
        value += 1
        value %= 0xFF
        
def test_mbc3_read_write_ram():
    mbc = get_mbc3()        
    value = 1
    mbc.ram_enable = True
    for address in range(0xA000, 0xBFFF+1):
        mbc.write(address, value)
        assert mbc.ram[mbc.ram_bank + (address & 0x1FFF)] == value
        assert mbc.read(address) == value;
        value += 1
        value %= 0xFF
        
def test_mbc3_read_write_clock():
    mbc = get_mbc3()        
    value = 1
    mbc.ram_enable = True
    mbc.ram_bank = -1
    old_clock_value = -2
    for address in range(0xA000, 0xBFFF+1):
        mbc.clock_register = 0x08
        mbc.write(address, value)
        assert mbc.clock_seconds == value
        
        mbc.clock_register = 0x09
        mbc.write(address, value)
        assert mbc.clock_minutes == value
        
        mbc.clock_register = 0x0A
        mbc.write(address, value)
        assert mbc.clock_hours == value
        
        mbc.clock_register = 0x0B
        mbc.write(address, value)
        assert mbc.clock_days == value
        
        mbc.clock_register = 0x0C
        clock_control = mbc.clock_control
        mbc.write(address, value)
        assert mbc.clock_control == ((clock_control & 0x80) | value)
        
        value += 1
        value %= 0xFF
        
def test_mbc3_update_clock():
    mbc = get_mbc3()
    mbc.clock         = TestClock()
    mbc.clock.time    = 1 + 2*60 + 3*60*60 + 4*24*60*60
    mbc.clock_days    = 0
    mbc.clock_hours   = 0
    mbc.clock_minutes = 0
    mbc.clock_seconds = 0
    mbc.clock_time    = 0
    mbc.clock_control = 0xFF
    mbc.update_clock()
    assert mbc.clock_days    == 0
    assert mbc.clock_hours   == 0
    assert mbc.clock_minutes == 0
    assert mbc.clock_seconds == 0
    assert mbc.clock_time    == mbc.clock.time 
    
    mbc.clock_time    = 0
    mbc.clock_control = 0x00
    mbc.update_clock()
    assert mbc.clock_days    == 4
    assert mbc.clock_hours   == 3
    assert mbc.clock_minutes == 2
    assert mbc.clock_seconds == 1
    assert mbc.clock_time    == mbc.clock.time 
    
def test_mbc3_update_clock_day_overflow():
    mbc = get_mbc3()
    mbc.clock         = TestClock()
    mbc.clock.time    = 2*512*24*60*60 
    mbc.clock_days    = 0
    mbc.clock_hours   = 0
    mbc.clock_minutes = 0
    mbc.clock_seconds = 0
    mbc.clock_time    = 0
    mbc.clock_control = 0x01
    mbc.update_clock()
    assert mbc.clock_days    == 0
    assert mbc.clock_hours   == 0
    assert mbc.clock_minutes == 0
    assert mbc.clock_seconds == 0
    assert mbc.clock_control == 0x81
    
def test_mbc3_latch_clock():
    mbc = get_mbc3()
    mbc.clock         = TestClock()
    mbc.clock.time    = 1 + 2*60 + 3*60*60 + (0xFF+2)*24*60*60
    mbc.clock_days    = 0
    mbc.clock_hours   = 0
    mbc.clock_minutes = 0
    mbc.clock_seconds = 0
    mbc.clock_time    = 0
    mbc.clock_control = 0x00
    mbc.latch_clock()
    assert mbc.clock_days    == 0xFF+2
    assert mbc.clock_latched_days == (0xFF+2) & 0xFF
    assert mbc.clock_hours   == 3
    assert mbc.clock_latched_hours == 3
    assert mbc.clock_minutes == 2
    assert mbc.clock_latched_minutes == 2
    assert mbc.clock_seconds == 1
    assert mbc.clock_latched_seconds == 1
    assert mbc.clock_latched_control == (mbc.clock_days>>8) & 0x01
    
    
# -----------------------------------------------------------------------------

def get_mbc5(rom_size=512, ram_size=16):
    return MBC5(get_rom(rom_size), get_ram(ram_size), get_clock_driver())

def test_mbc5_create():
    mbc = get_mbc5()
    fail_ini_test(mbc, 512, -1)
    fail_ini_test(mbc, 512, 17)
    fail_ini_test(mbc, 1, 16)
    fail_ini_test(mbc, 513, 16)
    
def test_mbc5_write_ram_enable():
    write_ram_enable_test(get_mbc5())
        
def test_mbc5_write_rom_bank_test1():
    mbc= get_mbc5()
    value = 1   
    for address in range(0x2000, 0x2FFF+1):
        rom_bank = mbc.rom_bank
        mbc.write(address, value)
        assert mbc.rom_bank == ((rom_bank & (0x01 << 22)) + \
                                ((value & 0xFF) << 14)) & mbc.rom_size
        value = (value+1) % (0x1F-1) +1
        
def test_mbc5_write_rom_bank_test2():
    mbc = get_mbc5()        
    value = 1   
    for address in range(0x3000, 0x3FFF+1):
        rom_bank = mbc.rom_bank
        mbc.write(address, value)
        assert mbc.rom_bank == ((rom_bank & (0xFF << 14)) + \
                                ((value & 0x01) << 22)) & mbc.rom_size
        value = (value+1) % (0x1F-1) +1
        
def test_mbc5_write_ram_bank():
    mbc = get_mbc5()        
    value = 1   
    for address in range(0x4000, 0x4FFF+1):
        mbc.rumble = True
        mbc.write(address, value)
        assert mbc.ram_bank == ((value & 0x07) << 13) & mbc.ram_size
        mbc.rumble = False
        mbc.write(address, value)
        assert mbc.ram_bank == ((value & 0x0F) << 13) & mbc.ram_size
        value = (value+1) % (0x1F-1) +1
        
def test_mbc5_read_write_ram():
    mbc = get_mbc5()        
    value = 1
    mbc.ram_enable = True
    for address in range(0xA000, 0xBFFF+1):
        mbc.write(address, value)
        assert mbc.ram[mbc.ram_bank + (address & 0x1FFF)] == value
        assert mbc.read(address) == value;
        value += 1
        value %= 0xFF 

# -----------------------------------------------------------------------------

def get_huc1(rom_size=128, ram_size=4):
    return HuC1(get_rom(rom_size), get_ram(ram_size), get_clock_driver())

def test_huc1_create():
    test_mbc1_create(get_huc1())
    
def test_huc1_write_ram_enable():
    test_mbc1_write_ram_enable(get_huc1())
        
def test_huc1_write_rom_bank_test1():
    test_mbc1_write_rom_bank_test1(get_huc1())
        
def test_huc1_write_rom_bank_test2():
    test_mbc1_write_rom_bank_test2(get_huc1())
        
def test_huc1_read_memory_model():
    test_mbc1_read_memory_model(get_huc1())       
        
def test_huc1_read_write_ram():
    test_mbc1_read_write_ram(get_huc1())    

# -----------------------------------------------------------------------------

def get_huc3(rom_size=128, ram_size=4):
    return HuC3(get_rom(rom_size), get_ram(ram_size), get_clock_driver())

def test_huc3_create():
    mbc = get_huc3()
    fail_ini_test(mbc, 128, 5)
    fail_ini_test(mbc, 128, -1)
    fail_ini_test(mbc, 1, 4)
    fail_ini_test(mbc, 129, 4)

def test_huc3_write_ram_flag():
    mbc= get_huc3()
    value = 1   
    for address in range(0x0000, 0x1FFF+1):
        mbc.write(address, value)
        assert mbc.ram_flag == value
        value = +1
        value %= 0xFF
        
def test_huc3_write_rom_bank():
    mbc= get_huc3()
    value = 1   
    for address in range(0x2000, 0x3FFF+1):
        mbc.write(address, value)
        if (value & 0x7F) == 0:
            assert mbc.rom_bank == ((1 & 0x7F) << 14) & mbc.rom_size
        else:
            assert mbc.rom_bank == ((value & 0x7F) << 14) & mbc.rom_size
        value = +1
        value %= 0xFF
        
def test_huc3_write_ram_bank():
    mbc = get_huc3()        
    value = 1   
    for address in range(0x4000, 0x5FFF+1):
        mbc.write(address, value)
        assert mbc.ram_bank == ((value & 0x0F) << 13) & mbc.rom_size
        value = +1
        value %= 0xFF
        
def test_huc3_write_ram():
    mbc = get_huc3()        
    value = 1
    mbc.ram_flag = 0x0A
    for address in range(0xA000, 0xBFFF+1):
        mbc.write(address, value)
        assert mbc.ram[mbc.ram_bank + (address & 0x1FFF)] == value
        value = +1
        value %= 0xFF
        
def test_huc3_write_ram_value_clock_shift():
    mbc = get_huc3()        
    mbc.ram_flag = 0x0B
    for address in range(0xA000, 0xBFFF+1):
        clock_shift = mbc.clock_shift
        mbc.write(address, 0x10)
        if clock_shift <= 24:
            assert mbc.ram_value == (mbc.clock_register >> clock_shift) & 0x0F
            assert mbc.clock_shift == clock_shift+4
        else:
            assert mbc.clock_shift == clock_shift
            mbc.clock_shift = 0
            
def test_huc3_write_ram_value_clock_shift():
    mbc = get_huc3()       
    value = 1  
    mbc.ram_flag = 0x0B
    for address in range(0xA000, 0xBFFF+1):
        mbc.ram_value == value
        mbc.write(address, 0x60)
        assert mbc.ram_value == 0x01
        value = +1
        value %= 0xFF
        
def test_huc3_write_clock_register_clock_shift():
    mbc = get_huc3()        
    value = 1
    mbc.ram_flag = 0x0B
    for address in range(0xA000, 0xBFFF+1):
        clock_shift = mbc.clock_shift
        clock_register = mbc.clock_register
        mbc.write(address, 0x30+value)
        if clock_shift <= 24:
            assert mbc.clock_shift == clock_shift+4
            assert mbc.clock_register == (clock_register & \
                                           ~(0x0F << clock_shift)) | \
                                         ((value & 0x0F) << clock_shift)
        else:
            assert mbc.clock_shift == clock_shift
            mbc.clock_shift = 0
        value = +1
        value %= 0xF
            
def test_huc3_write_clock_shift():
    mbc = get_huc3()       
    value = 1  
    mbc.ram_flag = 0x0B
    for address in range(0xA000, 0xBFFF+1):
        mbc.ram_value == value
        mbc.clock_shift = 1
        mbc.write(address, 0x40+value)
        if value==0x00 or value==0x03 or value==0x07:
            assert mbc.clock_shift == 0
        else:
            assert mbc.clock_shift == 1
        value = +1
        value %= 0xF
        
    
def test_huc3_update_clock():
    mbc = get_huc3()
    mbc.clock          = TestClock()
    mbc.clock.time     = 1*60 + 2*24*60*60 + 3*365*24*60*60
    mbc.clock_register = 0x00
    mbc.clock_time     = 0
    mbc.update_clock()
    assert mbc.clock_register & 0x00000FFF == 1
    assert mbc.clock_register & 0x00FFF000 == 2 << 12
    assert mbc.clock_register & 0xFF000000 == 3 << 24
    assert mbc.clock_time == mbc.clock.time
# -----------------------------------------------------------------------------

