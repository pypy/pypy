from pypy.lang.gameboy.profiling.gameboy_profiling_implementation import *
from pypy.lang.gameboy.debug import debug
import py
import sys

from AppKit import NSApplication
NSApplication.sharedApplication()


debug.DEBUG_PRINT_LOGS = False
ROM_PATH = str(py.magic.autopath().dirpath().dirpath())+"/rom"

filename = ""
if len(sys.argv) > 1:
    print sys.argv
    filename = sys.argv[1]
else:
    pos = str(9)
    filename = ROM_PATH+"/rom"+pos+"/rom"+pos+".gb"
    
gameBoy = GameBoyProfilingImplementation(500000)

try:
    gameBoy.load_cartridge_file(str(filename))
except:
    gameBoy.load_cartridge_file(str(filename), verify=False)
    print "Cartridge is Corrupted!"
    
gameBoy.mainLoop()
