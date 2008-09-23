
from socket import *
from pypy.lang.gameboy import cartridge
import socket
import sys
import threading


def map_binary_to_int(binary):
    return ord(binary)

def map_double_binary_to_int(code):
    #maps a double value to a long
    return ord(code[0]) + ord(code[1]) >> 8

class DebugSocketMemory(object):
    
    
    def __init__(self, gameboy_debug, debuggerPort):
        self.debuggerPort         = debuggerPort
        self.user_wait_skip_count = 0
        self.gameboy_debug        = gameboy_debug
        self.cpu                  = self.gameboy_debug.cpu
        
    def close(self):
        pass
    
    def start_debug_session(self):
        self.compare_rom()
        
    def compare_rom(self):
        pass
            
