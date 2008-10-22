from pypy.lang.gameboy.debug.gameboy_debug_implementation import *
from pypy.lang.gameboy.debug.debug_rpc_xml_memory import *
import py
import sys
import os
import threading
import pdb

# ------------------------------------------------------------------------------

if sys.platform == 'darwin':
	from AppKit import NSApplication
	NSApplication.sharedApplication()
	
# ------------------------------------------------------------------------------

ROM_PATH    = str(py.magic.autopath().dirpath().dirpath())+"/rom"
filename    = "/Users/cami/Ausbildung/08_UNIBE_FS/bachelor/docs/roms/DieMaus.gb"
filename    = ROM_PATH + "/rom9/rom9.gb"
SOCKET_PORT = 55687
skipExecs   = 22545
skipExecs   = 0

# ------------------------------------------------------------------------------

def parse_file_name():
    global filename
    if len(filename) == 0:
        pos = str(9)
        filename = ROM_PATH+"/rom"+pos+"/rom"+pos+".gb"
    print "loading rom: ", str(filename)
    
# ------------------------------------------------------------------------------
   

def start_python_version():
    global filename, skipExecs
    gameBoy = GameBoyDebugImplementation(SOCKET_PORT, skipExecs, DebugRpcXmlMemory)
    try:
        gameBoy.load_cartridge_file(str(filename))
    except Exception, error:
        gameBoy.load_cartridge_file(str(filename), verify=False)
        print "Cartridge is Corrupted!"
    try:
        gameBoy.mainLoop()
    except Exception, error:
        print "stopped"
        print error
        pdb.set_trace()

# ------------------------------------------------------------------------------ 
    
JMARIO_DIR =  str(py.magic.autopath().dirpath().dirpath()\
                        .dirpath().dirpath()\
                        .dirpath().dirpath()) + "/jmario"

JAVA_CLASSPATH =[ JMARIO_DIR + "/bin/", JMARIO_DIR+"/build/", 
                  JMARIO_DIR + "/lib/xmlrpc-client-3.1.jar",
                  JMARIO_DIR + "/lib/xmlrpc-common-3.1.jar",
                  JMARIO_DIR + "/lib/ws-commons-util-1.0.2.jar",
                  JMARIO_DIR + "/lib/commons-logging-1.1.jar"];
                        
def start_java_version():
    global filename
    command = "java" + \
              " -classpath "+ (':'.join(JAVA_CLASSPATH)) +\
              " gameboy.platform.debug.MainDebug " + \
              filename + " " + \
              str(SOCKET_PORT) + " " + \
              str(skipExecs)
    #command = "java" + \
    #          " -classpath "+ (':'.join(JAVA_CLASSPATH)) +\
    #          " gameboy.platform.j2se.Main " + \
    #          filename + " "
    os.system(command)

    
    
# START ========================================================================
parse_file_name()
threading.Timer(1, start_java_version    ).start()
threading.Timer(0, start_python_version()).start()


