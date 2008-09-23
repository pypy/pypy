from pypy.lang.gameboy import constants
from pypy.lang.gameboy.ram import RAM


def get_ram():
    return RAM()


def test_ram_reset():
    ram = get_ram();
    assert len(ram.work_ram) == 8192
    assert len(ram.hi_ram)   == 128
    ram.hi_ram   = range(50)
    ram.work_ram = range(50)
    ram.reset()
    
    assert len(ram.work_ram) == 8192
    assert len(ram.hi_ram)   == 128
    assert ram.work_ram      == [0] * 8192
    assert ram.hi_ram        == [0] * 128
    
    

def test_ram_read_write():
    ram = get_ram()
    value = 0x12
    ram.write(0x00, value)
    try:
        ram.read(0x00)
        py.test.fail()
    except Exception:
        pass
        
    assert value not in ram.work_ram
    assert value not in ram.hi_ram
    
    ram.write(0xC000, value)
    assert ram.read(0xC000) == value
    assert value in  ram.work_ram
    assert value not in  ram.hi_ram
    
    value += 1
    ram.write(0xFDFF, value)
    assert ram.read(0xFDFF) == value
    assert value in  ram.work_ram
    assert value not in  ram.hi_ram
    
    
    value += 1
    ram.write(0xFF80, value)
    assert ram.read(0xFF80) == value
    assert value in  ram.hi_ram
    assert value not in  ram.work_ram
    
    value += 1
    ram.write(0xFFFE, value)
    assert ram.read(0xFFFE) == value
    assert value in  ram.hi_ram
    assert value not in  ram.work_ram
    
    value += 1
    ram.write(0xFFFF, value)
    try:
        ram.read(0xFFFF)
        py.test.fail()
    except Exception:
        pass
    assert value not in  ram.hi_ram
    assert value not in  ram.work_ram
    
def test_read_write_work_ram():
    ram = get_ram();
    ram.hi_ram = None
    for i in range(0xC000, 0xFDFF):
        ram.write(i, i)
        assert ram.read(i) == i & 0xFF
        
def test_read_write_hi_ram():
    ram = get_ram();
    ram.work_ram = None
    for i in range(0xFF80, 0xFFFE):
        ram.write(i, i)
        assert ram.read(i) == i & 0xFF