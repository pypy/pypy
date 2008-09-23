
import py
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.cartridge import *

# ------------------------------------------------------------------------------

def mapToByte(value):
        return ord(value) & 0xFF

ROM_PATH = str(py.magic.autopath().dirpath().dirpath())+"/rom"
CONTENT = "abcdefghijklmnopqrstuvwxyz1234567890"

MAPPED_CONTENT = map_to_byte(CONTENT)

# ------------------------------------------------------------------------------

def get_cartridge_managers():
    pass

def get_cartridge_file():
    ctrg = CartridgeFile()
    return ctrg

class File(object):
    def __init__(self, data):
        self.data = data
        
    def read(self, size=0):
        if size == 0:
            return self.data
        
    def write(self, data):
        self.data = data
        
    def seek(self, value):
        pass

# ------------------------------------------------------------------------------


# STORE MANAGER TEST -----------------------------------------------------------

def test_cartridge_file_init(): 
    cartridge_file = get_cartridge_file()
    
    assert cartridge_file.cartridge_name is ""
    assert cartridge_file.cartridge_stream is None
    assert cartridge_file.cartridge_file_contents is None
    
    assert cartridge_file.battery_name is ""
    assert cartridge_file.battery_stream is None
    assert cartridge_file.battery_file_contents is None
    

def test_cartridge_file_load():
    cartridge_file = get_cartridge_file()
    romName = "rom1.raw"
    romFilePath = ROM_PATH+"/rom1/"+romName
    
    cartridge_file.load(romFilePath)
    #assert cartridge_file.cartridge_name     == romName
    assert cartridge_file.cartridge_file_path == romFilePath
    
    #assert cartridge_file.battery_name == romFilePath+constants.BATTERY_FILE_EXTENSION
    assert cartridge_file.battery_file_path ==  romFilePath+constants.BATTERY_FILE_EXTENSION
    assert cartridge_file.has_battery() == False
    
    
def test_cartridge_file_hasBattery():
    cartridge_file = get_cartridge_file()
    
    romName = "rom1.raw"
    romFilePath = ROM_PATH+"/rom1/"+romName
    
    cartridge_file.load(romFilePath)
    assert cartridge_file.has_battery() == False
    
    
def test_cartridge_file_read():
    cartridge_file = get_cartridge_file()
    assert cartridge_file.read() is None
    
    
def test_cartridge_file_remove_write_read_Battery():
    cartridge_file = get_cartridge_file()
    
    romName = "rom1.raw"
    romFilePath = ROM_PATH + "/rom1/"+romName
    
    cartridge_file.load(romFilePath)
    cartridge_file.remove_battery()
    assert cartridge_file.has_battery() == False
    
    cartridge_file.write_battery(MAPPED_CONTENT)
    assert cartridge_file.has_battery() == True
    assert cartridge_file.read_battery() == MAPPED_CONTENT
    
    cartridge_file.remove_battery()
    assert cartridge_file.has_battery() == False
    
    
    
    