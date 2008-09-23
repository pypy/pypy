# constants.CATRIGE constants.TYPES
# ___________________________________________________________________________

from pypy.lang.gameboy import constants
from pypy.lang.gameboy.timer import *
from pypy.rlib.streamio import open_file_as_stream

from pypy.lang.gameboy.ram import iMemory

import math

#from pypy.rlib.rstr import str_replace

import os
import pdb

# HELPERS ----------------------------------------------------------------------

def has_cartridge_battery(cartridge_type):    
    return (cartridge_type == constants.TYPE_MBC1_RAM_BATTERY 
                or cartridge_type == constants.TYPE_MBC2_BATTERY 
                or cartridge_type == constants.TYPE_MBC3_RTC_BATTERY 
                or cartridge_type == constants.TYPE_MBC3_RTC_RAM_BATTERY 
                or cartridge_type == constants.TYPE_MBC3_RAM_BATTERY 
                or cartridge_type == constants.TYPE_MBC5_RAM_BATTERY 
                or cartridge_type == constants.TYPE_MBC5_RUMBLE_RAM_BATTERY 
                or cartridge_type == constants.TYPE_HUC1_RAM_BATTERY)


def create_bank_controller(self, cartridge_type, rom, ram, clock):
        if constants.CATRIDGE_TYPE_MAPPING.has_key(cartridge_type) :
            return constants.CATRIDGE_TYPE_MAPPING[cartridge_type](rom, ram, clock)
        else:
            raise InvalidMemoryBankTypeError("Unsupported memory bank controller (0x"+hex(cartridge_type)+")")

def map_to_byte( string):
    mapped = [0]*len(string)
    for i in range(len(string)):
        mapped[i]  = ord(string[i])
    return mapped

def map_to_string(int_array):
    mapped = [0]*len(int_array)
    for i in range(len(int_array)):
        mapped[i]  = chr(int_array[i])
    return ("").join(mapped)

# EXCEPIONS --------------------------------------------------------------------

class InvalidMemoryBankTypeError(Exception):
    pass

class InvalidMemoryAccessException(Exception):
    pass

class InvalidSizeException(Exception):
    pass

class CartridgeHeaderCorruptedException(Exception):
    pass

class CartridgeTruncatedException(Exception):
    pass

        
# ==============================================================================
# CARTRIDGE

class CartridgeManager(object):
    """
        Delegates the loading to the CartridgeFile,
        verifies the Cartridge by calculating the checksums
    """
    def __init__(self, clock):
        assert isinstance(clock, Clock)
        self.clock     = clock
        self.cartridge = None
        self.mbc       = None
        self.rom       = [0]
        self.ram       = [0]
        
    def reset(self):
        if not self.has_battery():
            self.ram = [0xFF]*len(self.ram)
        self.mbc.reset()

    def read(self, address):
        return self.mbc.read(address)
    
    def write(self, address, data):
        self.mbc.write(address, data)
    
    def load(self, cartridge, verify=True):
        assert isinstance(cartridge, CartridgeFile)
        self.cartridge = cartridge
        self.rom       = self.cartridge.read()
        if verify:
            self.check_rom()
        self.create_ram()
        self.load_battery()
        self.mbc = self.create_bank_controller(self.get_memory_bank_type(), 
                                               self.rom, self.ram, self.clock)
        #print self
        
    def check_rom(self):
        if not self.verify_header():
            raise CartridgeHeaderCorruptedException("Cartridge Header is corrupted")
        if self.cartridge.get_size() < self.get_rom_size():
            raise CartridgeTruncatedException("Cartridge is truncated")
        
    def create_ram(self):
        ram_size = self.get_ram_size()
        if self.get_memory_bank_type() >= constants.TYPE_MBC2 \
                and self.get_memory_bank_type() <= constants.TYPE_MBC2_BATTERY:
            ram_size = 512
        self.ram = [0xFF]*ram_size
        
    def load_battery(self):
        if self.cartridge.has_battery():
            self.ram = self.cartridge.read_battery()

    def save(self, cartridge_name):
        if self.cartridge.has_battery():
            self.cartridge.write_battery(self.ram)
            
    def get_memory_bank_type(self):
        return self.rom[constants.CARTRIDGE_TYPE_ADDRESS]
    
    def get_memory_bank(self):
        return self.mbc

    def get_rom(self):
        return self.rom
        
    def get_rom_size(self):
        rom_size = self.rom[constants.CARTRIDGE_ROM_SIZE_ADDRESS]
        if rom_size>=0x00 and rom_size<=0x07:
            return 32768 << rom_size
        return -1
        
    def get_ram_size(self):
        return constants.CARTRIDGE_RAM_SIZE_MAPPING[
                self.rom[constants.CARTRIDGE_RAM_SIZE_ADDRESS]]
    
    def get_destination_code(self):
        return self.rom[constants.DESTINATION_CODE_ADDRESS]
    
    def get_licensee_code():
        return self.rom[constants.LICENSEE_ADDRESS]

    def get_rom_version(self):
        return self.rom[constants.CARTRIDGE_ROM_VERSION_ADDRESS]
    
    def get_header_checksum(self):
        return self.rom[constants.HEADER_CHECKSUM_ADDRESS]
    
    def get_checksum(self):
        return ((self.rom[constants.CHECKSUM_A_ADDRESS]) << 8) \
                + (self.rom[constants.CHECKSUM_B_ADDRESS])

    def has_battery(self):
        return has_cartridge_battery(self.get_memory_bank_type())
    
    def verify(self):
        checksum = 0
        for address in range(len(self.rom)):
            if address is not 0x014E and address is not 0x014F:
                checksum = (checksum + (self.rom[address])) & 0xFF
        return (checksum == self.get_checksum())
    
    def verify_header(self):
        """
        The memory at 0100-014F contains the cartridge header. 
        """
        if len(self.rom) < 0x0150:
            return False
        checksum = 0xE7
        for address in range(0x0134, 0x014C):
            checksum = (checksum - (self.rom[address])) & 0xFF
        return (checksum == self.get_header_checksum())
    
    def create_bank_controller(self, type, rom, ram, clock_driver):
        return MEMORY_BANK_MAPPING[type](rom, ram, clock_driver)

    
    def __repr__(self):
        return "Type=%s, Destination: %s ramSize: %sKB romSize: %sKB" % \
                        (self.get_memory_bank_type(), self.get_destination_code(),
                        self.get_ram_size(), self.get_rom_size()/1024)
        

# ------------------------------------------------------------------------------

    
class CartridgeFile(object):
    """
        File mapping. Holds the file contents and is responsible for reading
        and writing
    """
    def __init__(self, file=None):
        self.reset()
        if file is not None:
            self.load(file)
        
    def reset(self):
        self.cartridge_name          = ""
        self.cartridge_file_path     = ""
        self.cartridge_stream        = None
        self.cartridge_file_contents = None
        self.battery_name            = ""
        self.battery_file_path       = ""
        self.battery_stream          = None
        self.battery_file_contents   = None
        
        
    def load(self, cartridge_path):
        cartridge_path               = str(cartridge_path)
        self.cartridge_file_path     = cartridge_path
        self.cartridge_stream        = open_file_as_stream(cartridge_path)
        self.cartridge_file_contents = map_to_byte(
                                                self.cartridge_stream.readall())
        self.load_battery(cartridge_path)
        
    def load_battery(self, cartridge_file_path):
        self.battery_file_path = self.create_battery_file_path(cartridge_file_path)
        if self.has_battery():
            self.read_battery()
    
    def read_battery(self):
        self.battery_stream = open_file_as_stream(self.battery_file_path)
        self.battery_file_contents = map_to_byte(self.battery_stream.readall())
    
    def create_battery_file_path(self, cartridge_file_path):
        if cartridge_file_path.endswith(constants.CARTRIDGE_FILE_EXTENSION):
            return cartridge_file_path[-len(constants.CARTRIDGE_FILE_EXTENSION)] \
                                    +constants.BATTERY_FILE_EXTENSION
        elif cartridge_file_path.endswith(
                                constants.CARTRIDGE_COLOR_FILE_EXTENSION):
            return cartridge_file_path[-len(constants.CARTRIDGE_COLOR_FILE_EXTENSION)] \
                                    +constants.BATTERY_FILE_EXTENSION
        else:
            return cartridge_file_path + constants.BATTERY_FILE_EXTENSION
    
    def has_battery(self):
        if self.battery_file_path is None:
            return False
        return os.path.exists(self.battery_file_path)
    
    def read(self):
        return self.cartridge_file_contents
    
    def read_battery(self):
        return self.battery_file_contents
    
    def write_battery(self, ram):
        output_stream = open_file_as_stream(self.battery_file_path, "w")
        output_stream.write(map_to_string(ram))
        output_stream.flush()
        self.battery_file_contents = ram
        
    def remove_battery(self):
        if self.has_battery() and self.battery_file_path is not None:
            os.remove(self.battery_file_path)
            
    def get_size(self):
        if self.cartridge_file_path is None:
            return -1
        return os.path.getsize(self.cartridge_file_path)
        
    def get_battery_size(self):
        if self.battery_file_path is None:
            return -1
        return os.path.getsize(self.battery_file_path)
        
# ==============================================================================
# CARTRIDGE TYPES

class MBC(iMemory):
    
    def __init__(self, rom, ram, clock_driver,
                    min_rom_bank_size=0, max_rom_bank_size=0,
                    min_ram_bank_size=0, max_ram_bank_size=0, 
                    rom_bank_size=constants.ROM_BANK_SIZE):
        self.clock             = clock_driver
        self.min_rom_bank_size = min_rom_bank_size
        self.max_rom_bank_size = max_rom_bank_size
        self.min_ram_bank_size = min_ram_bank_size
        self.max_ram_bank_size = max_ram_bank_size
        self.rom_bank_size     = rom_bank_size
        self.rom_bank          = self.rom_bank_size
        self.rom        = []
        self.ram        = []
        self.reset()
        self.set_rom(rom)
        self.set_ram(ram)

    def reset(self):
        self.rom_bank   = self.rom_bank_size
        self.ram_bank   = 0
        self.ram_enable = False
        self.rom_size   = 0
        self.ram_size   = 0
    
    def set_rom(self, buffer):
        banks = int(len(buffer) / self.rom_bank_size)
        if banks < self.min_rom_bank_size or banks > self.max_rom_bank_size:
            raise InvalidSizeException("Invalid ROM size %s, should be in [%s %s]" % 
                            (hex(banks), hex(self.min_rom_bank_size), 
                             hex(self.max_rom_bank_size)))
        self.rom      = buffer
        self.rom_size = self.rom_bank_size * banks - 1


    def set_ram(self, buffer):
        banks = int(len(buffer) / constants.RAM_BANK_SIZE)
        if banks < self.min_ram_bank_size or banks > self.max_ram_bank_size:
            raise InvalidSizeException("Invalid RAM size %s, should be in [%s %s]" % 
                            (hex(banks), hex(self.min_ram_bank_size), 
                             hex(self.max_ram_bank_size)))
        self.ram      = buffer
        self.ram_size = constants.RAM_BANK_SIZE * banks - 1
        
        
    def read(self, address):
        # 0000-3FFF  
        if address <= 0x3FFF:
            return self.rom[address]
        # 4000-7FFF
        elif address <= 0x7FFF:
            return self.rom[self.rom_bank + (address & 0x3FFF)]
        # A000-BFFF
        elif address >= 0xA000 and address <= 0xBFFF:
            if self.ram_enable:
                return self.ram[self.ram_bank + (address & 0x1FFF)]
            else:
                #return 0xFF
                raise Exception("RAM is not Enabled")
        #return 0xFF
        raise InvalidMemoryAccessException("MBC: Invalid address, out of range: %s" 
                                           % hex(address))
    
    def write(self, address, data):
        raise InvalidMemoryAccessException("MBC: Invalid write access")
    
    def write_ram_enable(self, address, data):
        if self.ram_size > 0:
            self.ram_enable = ((data & 0x0A) == 0x0A)
  

#-------------------------------------------------------------------------------

  
class DefaultMBC(MBC):
    
    def __init__(self, rom, ram, clock_driver):
        MBC.__init__(self, rom, ram, clock_driver, 
                        min_rom_bank_size=0,
                        max_rom_bank_size=0xFFFFFF,
                        min_ram_bank_size=0,
                        max_ram_bank_size=0xFFFFFF)
        
    def write(self, address, data):
        self.ram[self.ram_bank + (address & 0x1FFF)] = data
    

#-------------------------------------------------------------------------------
  

class MBC1(MBC):
    """
    PyGirl Emulator
    
    Memory Bank Controller 1 (2MB ROM, 32KB RAM)
     
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-127 (16KB)
    A000-BFFF    RAM Bank 0-3 (8KB)
     """
    def __init__(self, rom, ram, clock_driver):
        MBC.__init__(self, rom, ram, clock_driver, 
                        min_ram_bank_size=0,
                        max_ram_bank_size=4,
                        min_rom_bank_size=2,    
                        max_rom_bank_size=128)
        
    def reset(self):
        MBC.reset(self)
        self.memory_model = 0

    def write(self, address, data):
        # 0000-1FFF
        if address <= 0x1FFF:
            self.write_ram_enable(address, data)
        # 2000-3FFF
        elif address <= 0x3FFF:
            self.write_rom_bank_1(address, data)
        # 4000-5FFF
        elif address <= 0x5FFF:
            self.write_rom_bank_2(address, data)
        # 6000-7FFF
        elif address <= 0x7FFF:
            self.memory_model = data & 0x01
        # A000-BFFF
        elif address >= 0xA000 and address <= 0xBFFF and self.ram_enable:
            self.ram[self.ram_bank + (address & 0x1FFF)] = data
        else:
            return 
            #raise InvalidMemoryAccessException("MBC 1Invalid memory Access address: %s" 
            #                                   % hex(address))

    def write_rom_bank_1(self, address, data):
        if (data & 0x1F) == 0:
            data = 1
        if self.memory_model == 0:
            self.rom_bank = ((self.rom_bank & 0x180000) + 
                             ((data & 0x1F) << 14)) & self.rom_size
        else:
            self.rom_bank = ((data & 0x1F) << 14) & self.rom_size
        
    def write_rom_bank_2(self, address, data):
        if self.memory_model == 0:
            self.rom_bank = ((self.rom_bank & 0x07FFFF) + 
                             ((data & 0x03) << 19)) & self.rom_size
        else:
            self.ram_bank = ((data & 0x03) << 13) & self.ram_size
  

#-------------------------------------------------------------------------------

      
class MBC2(MBC):
    """
    PyGirl GameBoPyGirl 
    Memory Bank Controller 2 (256KB ROM, 512x4bit RAM)
    
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-15 (16KB)
    A000-A1FF    RAM Bank (512x4bit)
     """
     
    def __init__(self, rom, ram, clock_driver):
        MBC.__init__(self, rom, ram, clock_driver,
                    min_ram_bank_size=1, max_ram_bank_size=1,
                    min_rom_bank_size=2, max_rom_bank_size=16,
                    rom_bank_size=512)
        
    def read(self, address):
        if address > 0xA1FF:
            raise InvalidMemoryAccessException("MBC2 out of Bounds: %s" 
                                               % hex(address))
        elif address >= 0xA000:
            return self.ram[address & 0x01FF]
        # A000-BFFF
        elif address >= 0xA000 and address <= 0xA1FF:
            if self.ram_enable:
                return self.ram[self.ram_bank + (address & 0x1FFF)]
            else:
                raise Exception("RAM is not Enabled")
        else:
            return MBC.read(self, address)
        
    def write(self, address, data):
        # 0000-1FFF
        if address <= 0x1FFF:
            self.write_ram_enable(address, data)
        # 2000-3FFF
        elif address <= 0x3FFF:
            self.write_rom_bank(address, data)
        # A000-A1FF
        elif address >= 0xA000 and address <= 0xA1FF:
            self.write_ram(address, data)
            
    def write_rom_bank(self, address, data):
        if (address & 0x0100) == 0:
            return
        if (data & 0x0F) == 0:
            data = 1
        self.rom_bank = ((data & 0x0F) << 14) & self.rom_size
        
    def write_ram(self, address, data):
        if self.ram_enable:
            self.ram[address & 0x01FF] = data & 0x0F
            
    def write_ram_enable(self, address, data):
        if (address & 0x0100) == 0:
            self.ram_enable = ((data & 0x0A) == 0x0A)

#-------------------------------------------------------------------------------


class MBC3(MBC):
    """
    PyGirl GameBoy (TM) EmulatPyGirlBank Controller 3 (2MB ROM, 32KB RAM, Real Time Clock)
    
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-127 (16KB)
    A000-BFFF    RAM Bank 0-3 (8KB)
    """
    
    def __init__(self, rom, ram, clock_driver):
        MBC.__init__(self, rom, ram, clock_driver,
                        min_ram_bank_size=0,
                        max_ram_bank_size=4,
                        min_rom_bank_size=2,  
                        max_rom_bank_size=128)

    def reset(self):
        MBC.reset(self)
        self.clock_latched_daysclock_latched_control = None
        self.clock_time             = self.clock.get_time()
        self.clock_latch            = 0
        self.clock_register         = 0
        self.clock_seconds          = 0
        self.clock_minutes          = 0
        self.clock_hours            = 0
        self.clock_days             = 0
        self.clock_control          = 0
        self.clock_latched_seconds  = 0
        self.clock_latched_minutes  = 0
        self.clock_latched_hours    = 0
        self.clock_latched_days     = 0
        self.clock_latched_control  = 0

    def read(self, address):
        # A000-BFFF
        if address >= 0xA000 and address <= 0xBFFF:
            if self.ram_bank >= 0:
                return self.ram[self.ram_bank + (address & 0x1FFF)]
            else:
                return self.read_clock_data(address)
        else:
            return MBC.read(self, address)
        
    def read_clock_data(self, address):
        if self.clock_register == 0x08:
            return self.clock_latched_seconds
        if self.clock_register == 0x09:
            return self.clock_latched_minutes
        if self.clock_register == 0x0A:
            return self.clock_latched_hours
        if self.clock_register == 0x0B:
            return self.clock_latched_days
        if self.clock_register == 0x0C:
            return self.clock_latched_control
        raise InvalidMemoryAccessException("MBC3.read_clock_data invalid address %i")
    
    def write(self, address, data):
        #print hex(address), hex(data)
        # 0000-1FFF
        if address <= 0x1FFF:
            self.write_ram_enable(address, data)
        # 2000-3FFF
        elif address <= 0x3FFF:
            self.write_rom_bank(address, data)
        # 4000-5FFF
        elif address <= 0x5FFF:
            self.write_ram_bank(address, data)
        # 6000-7FFF
        elif address <= 0x7FFF:
            self.write_clock_latch(address, data)
        # A000-BFFF
        elif address >= 0xA000 and address <= 0xBFFF and self.ram_enable:
            if self.ram_bank >= 0:
                self.ram[self.ram_bank + (address & 0x1FFF)] = data
            else:
                self.write_clock_data(address, data)
    
    def write_rom_bank(self, address, data):
        if data == 0:
            data = 1
        self.rom_bank = ((data & 0x7F) << 14) & self.rom_size
            
    def write_ram_bank(self, address, data):
        if data >= 0x00 and data <= 0x03:
            self.ram_bank = (data << 13) & self.ram_size
        else:
            self.ram_bank = -1
            self.clock_register = data
                
    def write_clock_latch(self, address, data):
        if self.clock_latch == 0 and data == 1:
            self.latch_clock()
        if data == 0 or data == 1:
            self.clock_latch = data
            
    def write_clock_data(self, address, data):
        self.update_clock()
        if self.clock_register == 0x08:
            self.clock_seconds = data
        if self.clock_register == 0x09:
            self.clock_minutes = data
        if self.clock_register == 0x0A:
            self.clock_hours = data
        if self.clock_register == 0x0B:
            self.clock_days = data
        if self.clock_register == 0x0C:
            self.clock_control = (self.clock_control & 0x80) | data
        
    def latch_clock(self):
        self.update_clock()
        self.clock_latched_seconds = self.clock_seconds
        self.clock_latched_minutes = self.clock_minutes
        self.clock_latched_hours   = self.clock_hours
        self.clock_latched_days    = self.clock_days & 0xFF
        self.clock_latched_control = (self.clock_control & 0xFE) | \
                                     ((self.clock_days >> 8) & 0x01)

    def update_clock(self):
        now = self.clock.get_time()
        elapsed = now - self.clock_time
        self.clock_time = now
        if (self.clock_control & 0x40) != 0:
            return
        elapsed += self.clock_days * 24*60*60
        elapsed += self.clock_hours * 60*60
        elapsed += self.clock_minutes * 60
        elapsed += self.clock_seconds
        
        days = int(math.floor(elapsed / (24.0*60*60.0)))
        self.clock_days += days
        elapsed -= days * 24*60*60

        hours = int(math.floor(elapsed / (60*60)))
        self.clock_hours += hours
        elapsed -= hours * 60*60
        
        minutes = int(math.floor(elapsed / 60))
        self.clock_minutes += minutes
        elapsed -= minutes * 60
        
        self.clock_seconds += elapsed
        
        if self.clock_days >= 512:
            self.clock_days %= 512
            self.clock_control |= 0x80


#-------------------------------------------------------------------------------


class MBC5(MBC):
    """
    PyGirl GameBoy (TM) Emulator
    
    MPyGirler 5 (8MB ROM, 128KB RAM)
     *
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-511 (16KB)
    A000-BFFF    RAM Bank 0-15 (8KB)
    """
    def __init__(self, rom, ram, clock_driver):
        MBC.__init__(self, rom, ram, clock_driver, 
                        min_ram_bank_size=0,
                        max_ram_bank_size=16,
                        min_rom_bank_size=2,    
                        max_rom_bank_size=512)

    def reset(self):
        MBC.reset(self)
        self.rumble = True
        
    def write(self, address, data):
        address = int(address)
        # 0000-1FFF
        if address <= 0x1FFF:  
            self.write_ram_enable(address, data)
        # 2000-2FFF
        elif address <= 0x2FFF:
            self.rom_bank = ((self.rom_bank & (0x01 << 22)) + 
                             ((data) << 14)) & self.rom_size
        # 3000-3FFF
        elif address <= 0x3FFF:
            self.rom_bank = ((self.rom_bank & (0xFF << 14)) + 
                             ((data & 0x01) << 22)) & self.rom_size
        # 4000-4FFF
        elif address <= 0x4FFF:
            self.write_ram_bank(address, data)
        # A000-BFFF
        elif address >= 0xA000 and address <= 0xBFFF and self.ram_enable:
            self.ram[self.ram_bank + (address & 0x1FFF)] = data

    def write_ram_bank(self, address, data):
        if self.rumble:
            self.ram_bank = ((data & 0x07) << 13) & self.ram_size
        else:
            self.ram_bank = ((data & 0x0F) << 13) & self.ram_size


#-------------------------------------------------------------------------------


class HuC1(MBC1):
    def __init__(self, rom, ram, clock_driver):
        MBC1.__init__(self, rom, ram, clock_driver)



#-------------------------------------------------------------------------------



class HuC3(MBC):
    """
    PyGirl GameBoy (TM) Emulator
    
    Hudson Memory PyGirl2MB ROM, 128KB RAM, RTC)
    
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-127 (16KB)
    A000-BFFF    RAM Bank 0-15 (8KB)
    """
    def __init__(self, rom, ram, clock_driver):
        MBC.__init__(self, rom, ram, clock_driver, 
                        min_ram_bank_size=0,
                        max_ram_bank_size=4,
                        min_rom_bank_size=2,    
                        max_rom_bank_size=128)

    def reset(self):
        MBC.reset(self)
        self.ram_flag       = 0
        self.ram_value      = 0
        self.clock_register = 0
        self.clock_shift    = 0
        self.clock_time     = self.clock.get_time()

    def read(self, address):
        # A000-BFFF
        if address >= 0xA000 and address <= 0xBFFF:
            return self.read_ram_or_flag(address)
        else:
            return MBC.read(self, address)
        
    def read_ram_or_flag(self, address):
        if self.ram_flag == 0x0C:
            return self.ram_value
        elif self.ram_flag == 0x0D:
            return 0x01
        elif self.ram_flag == 0x0A or self.ram_flag == 0x00 and \
                self.ram_size > 0:
            return self.ram[self.ram_bank + (address & 0x1FFF)]
        raise InvalidMemoryAccessException("Huc3 read error")
    
    def write(self, address, data):
        # 0000-1FFF
        if address <= 0x1FFF:
            self.ram_flag = data
        # 2000-3FFF
        elif address <= 0x3FFF:
            self.write_rom_bank(address, data)
        # 4000-5FFF
        elif address <= 0x5FFF:
            self.ram_bank = ((data & 0x0F) << 13) & self.ram_size
        # A000-BFFF
        elif address >= 0xA000 and address <= 0xBFFF:
            self.write_ram_flag(address, data)
         
    def write_rom_bank(self, address, data):
        if (data & 0x7F) == 0:
            data = 1
        self.rom_bank = ((data & 0x7F) << 14) & self.rom_size
        
    def write_ram_flag(self, address, data):
        if self.ram_flag == 0x0B:
            self.write_with_ram_flag_0x0B(address, data)
        elif self.ram_flag >= 0x0C and self.ram_flag <= 0x0E:
            pass
        elif self.ram_flag == 0x0A and self.ram_size > 0:
            self.ram[self.ram_bank + (address & 0x1FFF)] = data
                        
    def write_with_ram_flag_0x0B(self, address, data):
        compare = data & 0xF0
        if self.clock_shift > 24 and data != 0x60:
            return
        if compare == 0x10:
            self.write_ram_value_clock_shift(address, data)
        elif compare == 0x30:
            self.write_clock_register_clock_shift(address, data)
        elif compare == 0x40:
            self.write_clock_shift(address, data)
        elif compare == 0x50:
            pass
        elif compare == 0x60:
            self.ram_value = 0x01
         
    def write_ram_value_clock_shift(self, address, data):
        self.ram_value = (self.clock_register >> self.clock_shift) & 0x0F
        self.clock_shift += 4
            
    def write_clock_register_clock_shift(self, address, data):
        self.clock_register &= ~(0x0F << self.clock_shift)
        self.clock_register |= ((data & 0x0F) << self.clock_shift)
        self.clock_shift += 4
                    
    def write_clock_shift(self, address, data):
        switch = data & 0x0F
        self.update_clock()
        if switch == 0:
            self.clock_shift = 0
        elif switch == 3:
            self.clock_shift = 0
        elif switch == 7:
            self.clock_shift = 0
            
    def update_clock(self):
        now = self.clock.get_time()
        elapsed = now - self.clock_time
        # years (4 bits)
        years = int(math.floor(elapsed / (365*24*60*60)))
        elapsed -= years*365*24*60*60
        # days (12 bits)
        days = int(math.floor(elapsed / (24*60*60)))
        elapsed -= days*24*60*60
        # minutes (12 bits)
        minutes = int(math.floor(elapsed / 60))
        elapsed -= minutes*60
        
        self.clock_register |= years << 24
        self.clock_register |= days << 12
        self.clock_register |= minutes
        
        self.clock_time = now - elapsed


# MEMORY BANK MAPPING ----------------------------------------------------------


MEMORY_BANK_TYPE_RANGES = [
    (constants.TYPE_MBC1,             constants.TYPE_MBC1_RAM_BATTERY,        MBC1),
    (constants.TYPE_MBC2,             constants.TYPE_MBC2_BATTERY,            MBC2),
    (constants.TYPE_MBC3_RTC_BATTERY, constants.TYPE_MBC3_RAM_BATTERY,        MBC3),
    (constants.TYPE_MBC5,             constants.TYPE_MBC5_RUMBLE_RAM_BATTERY, MBC5),
    (constants.TYPE_HUC3_RTC_RAM,     constants.TYPE_HUC3_RTC_RAM,            HuC3),
    (constants.TYPE_HUC1_RAM_BATTERY, constants.TYPE_HUC1_RAM_BATTERY,        HuC1)
]


def initialize_mapping_table():
    result = [DefaultMBC] * 256
    for entry in MEMORY_BANK_TYPE_RANGES:
        if len(entry) == 2:
            positions = [entry[0]]
        else:
            positions = range(entry[0], entry[1]+1)
        for pos in positions:
            result[pos] = entry[-1]
    return result

MEMORY_BANK_MAPPING = initialize_mapping_table()
