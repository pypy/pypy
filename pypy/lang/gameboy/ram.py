"""
PyGirl Emulator

Work and High RAM
"""

from pypy.lang.gameboy import constants


class iMemory(object):
     def write(self, address, data):
         pass
     
     def read(self, address):
         return 0xFF

class RAM(iMemory):

    def __init__(self):
        self.work_ram =  [0]*8192
        self.hi_ram =  [0]*128
        self.reset()

    def reset(self):
        self.work_ram =  [0]*8192
        self.hi_ram   =  [0]*128

    def write(self, address, data):
        # C000-DFFF Work RAM (8KB)
        # E000-FDFF Echo RAM
        if address >= 0xC000 and address <= 0xFDFF:
            self.work_ram[address & 0x1FFF] = data & 0xFF
        # FF80-FFFE
        elif address >= 0xFF80 and address <= 0xFFFE:
            self.hi_ram[address & 0x7F] = data & 0xFF

    def read(self, address):
        # C000-DFFF Work RAM
        # E000-FDFF Echo RAM
        if address >= 0xC000 and address <= 0xFDFF:
            return self.work_ram[address & 0x1FFF]
        # FF80-FFFE
        elif address >= 0xFF80 and address <= 0xFFFE:
            return self.hi_ram[address & 0x7F]
        raise Exception("Invalid Memory access, address out of range")