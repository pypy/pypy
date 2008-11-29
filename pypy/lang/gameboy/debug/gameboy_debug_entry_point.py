#!/usr/bin/env python
import py, sys, os, threading
from pypy.lang.gameboy.debug.gameboy_debug_implementation import *
from pypy.lang.gameboy.debug.debug_rpc_xml_connection import *

# ------------------------------------------------------------------------------

if sys.platform == 'darwin':
    from AppKit import NSApplication
    NSApplication.sharedApplication()

# ------------------------------------------------------------------------------

ROM_PATH    = str(py.magic.autopath().dirpath().dirpath())+"/rom"
filename    = ROM_PATH + "/rom9/rom9.gb"
SOCKET_PORT = 55682
skip_count   = 6150
#skip_count   = 22545
#skip_count   = 2700
# skip_count   = 0

# ------------------------------------------------------------------------------

def parse_file_name():
    global filename
    if len(filename) == 0:
        pos = str(9)
        filename = ROM_PATH+"/rom"+pos+"/rom"+pos+".gb"
    print "loading rom: ", str(filename)
    
def ask_for_skip_count():
    print ">> enter initial skip amount:"
    read = sys.stdin.readline()
    try:
        if int(read) > 0:
            skip_count = int(read)
    except Exception:
        skip_count = 0
        
# ------------------------------------------------------------------------------
   

def start_python_version():
    global filename, skip_count
    gameBoy = GameBoyDebugImplementation(SOCKET_PORT, skip_count, DebugRpcXmlConnection)
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

JAVA_CLASSPATH =[ JMARIO_DIR+"/build/", 
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
              str(skip_count)
    print command
    # command = "java" + \
    #           " -classpath "+ (':'.join(JAVA_CLASSPATH)) +\
    #           " gameboy.platform.j2se.Main " + \
    #           filename + " "
    os.system(command)

    
    
# START ========================================================================
parse_file_name()
ask_for_skip_count()
threading.Timer(1, start_java_version    ).start()
threading.Timer(0, start_python_version()).start()


