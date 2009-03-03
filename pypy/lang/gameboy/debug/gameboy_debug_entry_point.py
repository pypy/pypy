#!/usr/bin/env python
import py, sys, os, threading
from pypy.lang.gameboy.debug.gameboy_debug_implementation import *
from pypy.lang.gameboy.debug.debug_rpc_xml_connection import *

# ------------------------------------------------------------------------------

#if sys.platform == 'darwin':
    #from AppKit import NSApplication
    #NSApplication.sharedApplication()

# ------------------------------------------------------------------------------

ROM_PATH    = str(py.magic.autopath().dirpath().dirpath())+"/rom"
# filename    = ROM_PATH + "/rom9/rom9.gb"
filename = "/home/tverwaes/roms/SuperMarioLand.gb"
SOCKET_PORT = 55682

skip_count   = 22545
skip_count   = 2700
skip_count   = 0

skip_count = 0
first_skip = 0
in_between_skip = 0


if len(sys.argv) > 1:
    skip_count       = sys.argv[1]
    first_skip       = sys.argv[2] 
    in_between_skip = sys.argv[3]

# ------------------------------------------------------------------------------

def parse_file_name():
    global filename
    if len(filename) == 0:
        pos = str(9)
        filename = ROM_PATH+"/rom"+pos+"/rom"+pos+".gb"
    print "loading rom: ", str(filename)
    
def ask_for_skip_count():
    global skip_count
    if len(sys.argv) > 1: return
    print ">> enter initial skip amount: ",
    read = sys.stdin.readline()
    try:
        if int(read) > 0:
            skip_count = int(read)
    except Exception:
        skip_count = 0
        
def ask_for_in_between_skip():
    global in_between_skip
    if len(sys.argv) > 1: return
    print ">> enter initial in_between_skip amount: ",
    read = sys.stdin.readline()
    try:
        if int(read) > 0:
            in_between_skip = int(read)
    except Exception:
        in_between_skip = 1000
        
# ------------------------------------------------------------------------------
   

def start_python_version():
    global filename, skip_count, in_between_skip
    gameBoy = GameBoyDebugImplementation(SOCKET_PORT, DebugRpcXmlConnection, 
                                         skip_count, in_between_skip)
    try:
        gameBoy.load_cartridge_file(str(filename))
    except Exception, error:
        gameBoy.load_cartridge_file(str(filename), verify=False)
        print "Cartridge is Corrupted!"
    gameBoy.mainLoop()
    #try:
    #    gameBoy.mainLoop()
    #except Exception, error:
    #    print "stopped"
    #    print error
    #    pdb.set_trace()

# ------------------------------------------------------------------------------ 
    
MARIO_DIR =  str(py.magic.autopath().dirpath().dirpath()\
                        .dirpath().dirpath()\
                        .dirpath().dirpath()) + "/mario"

JAVA_CLASSPATH =[ MARIO_DIR+"/build/", 
                  MARIO_DIR + "/lib/xmlrpc-client-3.1.jar",
                  MARIO_DIR + "/lib/xmlrpc-common-3.1.jar",
                  MARIO_DIR + "/lib/ws-commons-util-1.0.2.jar",
                  MARIO_DIR + "/lib/commons-logging-1.1.jar"];
                        
def start_java_version():
    global filename
    command = "java" + \
              " -classpath "+ (':'.join(JAVA_CLASSPATH)) +\
              " gameboy.platform.debug.MainDebug " + \
              filename + " " + \
              str(SOCKET_PORT) + " " + \
              str(skip_count)
    print command
    # command = "java" + \
    #           " -classpath "+ (':'.join(JAVA_CLASSPATH)) +\
    #           " gameboy.platform.j2se.Main " + \
    #           filename + " "
    os.system(command)

#try:
#    import psyco
#    psyco.full()
#except:
#    pass
    
# START ========================================================================
parse_file_name()

ask_for_skip_count()
ask_for_in_between_skip()

threading.Timer(1, start_java_version    ).start()
threading.Timer(0, start_python_version()).start()


