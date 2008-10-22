
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

class DebugRpcXmlMemory(SimpleXMLRPCServer, threading.Thread):
    
    
    def __init__(self, gameboy_debug, debuggerPort, skipExecs):
        threading.Thread.__init__(self)
        SimpleXMLRPCServer.__init__(self, ("localhost", debuggerPort))
        print "python: DEBUGGER PORT:", debuggerPort
        self.skipExecs            = skipExecs;
        self.debuggerPort         = debuggerPort
        self.gameboy_debug        = gameboy_debug
        self.cpu                  = self.gameboy_debug.cpu
        self.pending = False
        self.started = False
        self.rom_checked = False
        self.pending_steps =  0
        self.showed_skip_message_count = 0
        self.logRequests = False
        self.compare_failed = False
        self.is_closed = False
        #self.rpc_paths.append("/pygirl")
        self.register_introspection_functions()
        self.register_functions()
        self.start()
        
    def run(self):
        self.serve_forever()
        
    def register_functions(self):
        for fn in [(self.start_debug,     "start"),
                   (self.check_rom, "check_rom"),
                   (self.close,     "close"),
                   (self.compare,   "compare"),
                   (self.has_next,  "has_next"),
                   (self.next,      "next")]:
            self.register_function(fn[0], fn[1])
            
    # RPC ===================================================================
        
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
        self.compare_memory("ROM", self.cpu.rom, data["rom"])
        self.compare_memory("registeredBitmap", constants.REGISTERED_BITMAP, \
                            data["registeredBitmap"])
        self.compare_cartridge(data)
        self.rom_checked = True
        return "checkedRom"
    
    @printframe("compare elements")
    def compare(self, last_op_code, last_fetch_exec_op_code, instruction_count,
                registers, interrupts, ram, video, timer, cycles):
        self.print_check("instruction count", \
                         self.cpu.instruction_counter, instruction_count)
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
    
    @printframe("checking cartridge data")
    def compare_cartridge(self, data):
        self.print_check("cartridge ROM size", \
                         self.gameboy_debug.cartridge_manager.get_rom_size(), \
                         data["ramSize"])
        self.print_check("cartridge RAM size", 
                         self.gameboy_debug.cartridge_manager.get_ram_size(), \
                         data["romSize"])
        self.print_check("cartridge Memory Bank Type", \
                         self.gameboy_debug.cartridge_manager.get_memory_bank_type(), \
                         data["type"])
        self.print_check("cartridge checksum", \
                         self.gameboy_debug.cartridge_manager.get_checksum(), \
                         data["checksum"])
        self.print_check("cartridge has battery", \
                         self.gameboy_debug.cartridge_manager.has_battery(), \
                         data["hasBattery"])
        
    @printframe("comparing op codes")
    def compare_op_codes(self, last_op_code, last_fetch_exec_op_code):
        self.print_check("last opCode" , self.cpu.last_op_code, last_op_code)
        self.print_check("last opCode" , self.cpu.last_fetch_execute_op_code, \
                        last_fetch_exec_op_code)
        
    @printframe("comparing registers")
    def compare_registers(self, registers):
        for reg in [("a",  self.cpu.a.get()),  ("f",  self.cpu.flag.get()),
                    ("b",  self.cpu.b.get()),  ("c",  self.cpu.c.get()),
                    ("d",  self.cpu.d.get()),  ("e",  self.cpu.e.get()),
                    ("h",  self.cpu.h.get()),  ("l",  self.cpu.l.get()),
                    ("sp", self.cpu.sp.get()), ("pc", self.cpu.pc.get())]:
             self.print_check("register %s" % reg[0], reg[1], registers[reg[0]])
    
    @printframe("comparing interrupts")
    def compare_interrupts(self, interrupt):
        self.print_check("interrupt ime" , \
                            self.cpu.ime, interrupt["ime"])
        self.print_check("interrupt halted" , \
                            self.cpu.halted, interrupt["halted"])
        self.print_check("interrupt enable" , \
                         self.cpu.interrupt.get_enable_mask(), \
                         interrupt["enabled"])
        self.print_check("interrupt flag" , \
                         self.cpu.interrupt.get_interrupt_flag(), \
                         interrupt["flag"])
        
    @printframe("comparing ROM")
    def compare_ram(self, ram):
        self.compare_memory("wram", \
                            self.gameboy_debug.ram.work_ram, ram["wram"])
        self.compare_memory("hram", \
                            self.gameboy_debug.ram.hi_ram, ram["hram"])
        self.compare_memory("catridge external", \
                            self.get_external_cartridge_ram(), ram["ext"])
    
    def get_external_cartridge_ram(self):
        ram = [0xFF] * (0xBFFF-0xA000+1)
        if self.gameboy_debug.cartridge_manager.mbc.ram_enable:
            for i in range(len(ram)):
                ram[i] = self.gameboy_debug.read(0xA000+i)
        return ram
    
    @printframe("comparing video")
    def compare_video(self, video):
        self.compare_video_memory(video)
        self.compare_video_registers(video)
    
    @printframe("comparing memory")  
    def compare_video_memory(self, video):
        self.compare_memory("video vram", self.gameboy_debug.video.vram, \
                            video["vram"])
        self.compare_memory("video object attribute memory oam", \
                            self.gameboy_debug.video.oam, video["oam"])
        self.compare_memory("video line", self.gameboy_debug.video.line, \
                            video["line"])
        self.compare_memory("video objects", self.gameboy_debug.video.objects, \
                            video["objects"])
        self.compare_memory("video palette", self.gameboy_debug.video.palette, \
                            video["palette"])
        
    @printframe("comparing registers")
    def compare_video_registers(self, video):
        self.print_check("video dirty", \
                         self.gameboy_debug.video.dirty, video["dirty"])
        self.print_check("video display", \
                         self.gameboy_debug.video.display, video["display"])
        self.print_check("video bgp", \
                         self.gameboy_debug.video.background_palette, \
                         video["bgp"])
        self.print_check("video dma", \
                         self.gameboy_debug.video.dma, video["dma"])
        self.print_check("video frames", \
                         self.gameboy_debug.video.frames, video["frames"])
        self.print_check("video frameSkip", \
                         self.gameboy_debug.video.frame_skip, \
                         video["frameSkip"])
        self.print_check("video lcdc", \
                         self.gameboy_debug.video.control.read(), video["lcdc"])
        self.print_check("video ly", \
                         self.gameboy_debug.video.line_y, video["ly"])
        self.print_check("video obp0", \
                         self.gameboy_debug.video.object_palette_0, \
                         video["obp0"])
        self.print_check("video obp1", \
                         self.gameboy_debug.video.object_palette_1, \
                         video["obp1"])
        self.print_check("video scx", \
                         self.gameboy_debug.video.background.scroll_x, video["scx"])
        self.print_check("video scy", \
                         self.gameboy_debug.video.background.scroll_y, video["scy"])
        self.print_check("video stat", \
                         self.gameboy_debug.video.status.read(), video["stat"])
        self.print_check("video transfer", \
                           self.gameboy_debug.video.transfer, video["transfer"])
        self.print_check("video vblank", \
                         self.gameboy_debug.video.v_blank, video["vblank"])
        self.print_check("video wly", \
                         self.gameboy_debug.video.window.line_y, video["wly"])
        self.print_check("video wx", \
                         self.gameboy_debug.video.window.x, video["wx"])
        self.print_check("video wy", \
                         self.gameboy_debug.video.window.y, video["wy"])
     
    @printframe("comparing timer")   
    def compare_timer(self, data):
        self.print_check("timer div", \
                         self.gameboy_debug.timer.divider, \
                         data["div"])
        self.print_check("timer dividerCycles", \
                         self.gameboy_debug.timer.divider_cycles, \
                         data["dividerCycles"])
        self.print_check("timer tac", \
                         self.gameboy_debug.timer.timer_control, \
                         data["tac"])
        self.print_check("timer tima", \
                         self.gameboy_debug.timer.timer_counter, \
                         data["tima"])
        self.print_check("timer timerClock", \
                         self.gameboy_debug.timer.timer_clock, \
                         data["timerClock"])
        self.print_check("timer timerCycles", \
                         self.gameboy_debug.timer.timer_cycles, \
                         data["timerCycles"])
        self.print_check("timer tma", \
                         self.gameboy_debug.timer.timer_modulo, \
                         data["tma"])
    
    @printframe("comparing cycles")
    def compare_cycles(self, data):
        self.print_check("cycles video", \
                         self.gameboy_debug.video.cycles, data["video"])
        self.print_check("cycles cpu", \
                         self.gameboy_debug.cpu.cycles, data["cpu"])
        self.print_check("cycles serial", \
                         self.gameboy_debug.serial.cycles, data["serial"])
        self.print_check("cycles joypad", \
                         self.gameboy_debug.joypad.cycles, data["joypad"])
        #sound not yet implemented so no  use for checking cycles here
        #self.print_check("cycles sound", #self.gameboy_debug.sound.cycles, 
        #                    0, data["sound"])
        
    # ==========================================================================    
    
    def compare_memory(self, name, expected, new):
        self.print_check(name+" length", len(expected), len(new))
        if len(expected) != len(new): return
        # only check every 3rd in order to speed things up
        for address in range(0, len(expected), 3):
           self.print_check(name+" value at "+hex(address), \
                            expected[address], new[address])
    
    def print_check(self, msg, expected, got):
        if expected != got:
            self.compare_failed = True
            print "python: !!", msg, "expected:", expected, "got:", got, "!!"
            
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
    
    
    def print_mismatch(self, part, expected, got):
        print "python:", str(part), "expected:", str(expected), "got:", str(got)
