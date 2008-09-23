import os
import py
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.gameboy import GameBoy


ROM_PATH = str(py.magic.autopath().dirpath().dirpath().dirpath())+"/lang/gameboy/rom"
EMULATION_CYCLES = 1<<24


def entry_point(argv=None):
    if len(argv) > 1:
        filename = argv[1]
    else:
        filename = ROM_PATH+"/rom4/rom4.gb"
    gameBoy = GameBoy()
    gameBoy.load_cartridge_file(str(filename))
    gameBoy.emulate(EMULATION_CYCLES)
    
    return 0
    

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

def test_target():
    entry_point(["boe", ROM_PATH+"/rom4/rom4.gb"])
