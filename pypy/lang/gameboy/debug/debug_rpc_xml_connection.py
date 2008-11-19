
from socket import *
from pypy.lang.gameboy import cartridge
from pypy.lang.gameboy import constants
from socket import *
from SimpleXMLRPCServer import *
import sys, threading, time, pdb


# -----------------------------------------------------------------------------

DEBUG = False

class printframe(object):
    open = 0
    def __init__(self, text):
        global DEBUG, open
        printframe.open = 0
        self.text = text
        
    def __call__(self, f):
        def wrapper(*args, **kwargs):
            global DEBUG
            shift =  "    "*printframe.open
            if DEBUG:
                print "python:", shift, self.text, "..."
            printframe.open += 1
            val = f(*args, **kwargs)
            if DEBUG:
                print "python:", shift, self.text, "DONE"
            printframe.open -= 1
            return val
            
        return wrapper
        
# -----------------------------------------------------------------------------        

class DebugRpcXmlConnection(SimpleXMLRPCServer, threading.Thread):
    
    
    def __init__(self, gameboy_debug, debuggerPort, skipExecs):
        threading.Thread.__init__(self)
        SimpleXMLRPCServer.__init__(self, ("localhost", debuggerPort))
        print "python: DEBUGGER PORT:", debuggerPort
        self.skipExecs            = skipExecs;
        self.debuggerPort         = debuggerPort
        self.gameboy_debug        = gameboy_debug
        self.ini_fields()
        #self.rpc_paths.append("/pygirl")
        self.register_introspection_functions()
        self.register_functions()
        self.start()
        
    def ini_fields(self):
        self.pending = False
        self.started = False
        self.rom_checked = False
        self.pending_steps =  0
        self.showed_skip_message_count = 0
        self.logRequests = False
        self.compare_failed = False
        self.is_closed = False
        
    def run(self):
        self.serve_forever()
        
    def register_functions(self):
        for fn in [(self.start_debug,       "start"),
                   (self.compare_rom,       "check_rom"),
                   (self.close,             "close"),
                   (self.compare_system,    "compare"),
                   (self.has_next,          "has_next"),
                   (self.next,              "next")]:
            self.register_function(fn[0], fn[1])
    
    #  ===================================================================
    
    def check_rom(self, data):
        self.gameboy_debug.compare_rom(data)
    
    def compare_system(self, data):
        self.gameboy_debug.compare_system(data)

    #  ===================================================================
        
    def close(self):
    	pdb.set_trace()
        if not self.is_closed:
            print "python: called close"
            self.server_close()
            self.is_closed = True
            raise Exception("CLOSED CONNECTION")
    
    def start_debug(self):
        print "python: called start"
        self.started = True
        return "started"
    
    @printframe("checking rom")
    def check_rom(self, data):
        # XXX
        self.rom_checked = True
        return "checkedRom"
    
    @printframe("compare elements")
    def compare(self, last_op_code, last_fetch_exec_op_code, instruction_count,
                registers, interrupts, ram, video, timer, cycles):
        self.compare_op_codes(last_op_code, last_fetch_exec_op_code)
        self.compare_registers(registers)
        self.compare_interrupts(interrupts)
        self.compare_ram(ram)
        self.compare_video(video)
        self.compare_timer(timer)
        self.compare_cycles(cycles)
        self.pending = False
        return "checked"
    
    @printframe("waiting for next")
    def next(self):
        self.wait_for_next_op_code()
        return "next"
    
    def has_next(self):
        print "python: called has_next"
        return self.pending

    # ==========================================================================

    def wait_for_client_start(self):
        print "python:    waiting for client to start"
        while not self.started:
            self.sleep()
        
    def wait_for_rom_check(self):
        print "python:    waiting for client to send rom"
        while not self.rom_checked:
            self.sleep()
    
    def wait_until_checked(self):
        while self.pending: 
            self.sleep()
        
    def wait_for_next_op_code(self):
        while not self.pending:
            self.sleep()
        
    def sleep(self):
        time.sleep(10/1000)
        
    def wait_for_user_input(self):
        if self.compare_failed:
            self.compare_failed = False
            self.handle_compare_failed()
        if self.pending_steps > 0:
            self.pending_steps -= 1
            return
        self.prompt_for_user_input()
        
    def prompt_for_user_input(self):
        if self.showed_skip_message_count < 2:
            print ">>  enter skip, default is 0:"
            self.showed_skip_message_count += 1
        read = sys.stdin.readline()
        try:
            if int(read) > 0:
                self.pending_steps = int(read)
            if read == "pdb":
            	pdb.set_trace()
        except Exception:
            if ("stop" in read) or ("exit" in read) or (read is "Q"):
                raise Exception("Debug mode Stopped by User")
    
    def handle_compare_failed(self):
        for i in range(3):
            time.sleep(1)
            print '\a'
        self.pending_steps = 0
            
    # ==========================================================================
   
    @printframe("waiting for client to start")
    def start_debug_session(self):
        self.wait_for_client_start()
        self.wait_for_rom_check()
        
    @printframe("handle_executed_op_code")
    def handle_executed_op_code(self, is_fetch_execute=False):
        if self.cpu.instruction_counter > self.skipExecs:
            self.pending = True
        self.wait_for_user_input()
        self.wait_until_checked()
        #if self.cpu.instruction_counter == 6154:
            #pdb.set_trace()
    
