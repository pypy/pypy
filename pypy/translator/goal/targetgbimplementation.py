#!/usr/bin/env python
import os, py, pdb, sys
from pypy.lang.gameboy.gameboy_implementation import GameBoyImplementation


ROM_PATH = str(py.magic.autopath().dirpath().dirpath().dirpath())+"/lang/gameboy/rom"

print ROM_PATH

def entry_point(argv=None):
    if argv is not None and len(argv) > 1:
        filename = argv[1]
    else:
        pos = str(9)
        filename = ROM_PATH+"/rom"+pos+"/rom"+pos+".gb"
    print "loading rom: ", str(filename)
    gameBoy = GameBoyImplementation()
    try:
        gameBoy.load_cartridge_file(str(filename))
    except:
        print "Corrupt Cartridge"
        gameBoy.load_cartridge_file(str(filename), verify=False)

    gameBoy.open_window()
    gameBoy.mainLoop()

    return 0
    

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

def test_target():
    entry_point(sys.argv)
    
    
# STARTPOINT ===================================================================

if __name__ == '__main__':
    use_rsdl = False
    if use_rsdl and sys.platform == 'darwin':
        from AppKit import NSApplication
        NSApplication.sharedApplication()
    try:
        import psyco
        psyco.full()
    except:
        pass
    
    test_target()
