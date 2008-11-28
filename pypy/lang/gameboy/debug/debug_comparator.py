
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

class Comparator:

    def __init__(self, debug_connection):
        self.debug_connection = debug_connection
        
    
    def compare(self, data):
        pass
    
    def compare_memory(self, name, expected, new):
        self.print_compare(name+" length", len(expected), len(new))
        if len(expected) != len(new): return
        for address in range(0, len(expected), 1):
            self.print_compare(name+" value at "+hex(address), \
                    expected[address], new[address])
    
    def print_compare(self, msg, expected, got, output=False):
        if expected != got:
            self.compare_failed = True
            print "python: !!", msg, "expected:", expected, "got:", got, "!!"
            
    
    def print_mismatch(self, part, expected, got):
        print "python:", str(part), "expected:", str(expected), "got:", str(got)
        
        
    def compare_set(self, set, data, label=""):
        for compare_value in set:
            self.print_check(label+": "+compare_value[0], 
                             compare_value[1], 
                             data[compare_value[2]]);
            
    def compare_memory_set(self, set, data, label=""):
        for compare_value in set:
            self.compare_memory(label+": "++compare_value[0], 
                                compare_value[1], 
                                data[compare_value[2]]);
        
        
# -----------------------------------------------------------------------------

class GameboyComparator(Comparator):
    
    def __init__(self, debug_connection, gameboy):
        Comparator.__init__(self, debug_connection)
        self.gameboy = gameboy
        self.create_part_comparators(debug_connection)
        
    def create_part_comparators(self, debug_connection):
        self.cpu_comparator       = CPUComparator(debug_connection, 
                                                  self.gameboy.cpu)
        self.timer_comparator     = TimerComparator(debug_connection,       
                                                    self.gameboy.timer)
        self.interrupt_comparator = InterruptComparator(debug_connection, 
                                                        self.gameboy)
        self.video_comparator     = VideoComparator(debug_connection, 
                                                    self.gameboy.video)
        self.ram_comparator       = RAMComparator(debug_connection, self.gameboy)
    
    def compare(self, data):
        self.cpu_comparator.compare(data["cpu"])
        self.video_comparator.compare(data["video"])
        self.compare_cycles(data["cycles"])
        self.timer_comparator.compare(data["timer"])
        self.interrupt_comparator.compare(data["interrupt"])
        self.ram_comparator.compare(data["ram"])
    
    @printframe("comparing cycles")        
    def compare_cycles(self, data):
        cmp = [
                ("video",  self.video.cycles,                "data"),
                ("cpu",    self.gameboy_debug.cpu.cycles,    "cpu"),
                ("serial", self.gameboy_debug.serial.cycles, "serial"),
                ("joypad", self.gameboy_debug.joypad.cycles, "joypad")
        ]
        self.compare_set(cmp, data, label="cycles")  
        #sound not yet implemented so no  use for checking cycles here
        #self.print_check("cycles sound", #self.gameboy_debug.sound.cycles, 
        #                    0, data["sound"])   

class ROMComparator(Comparator):
    def __init__(self, debug_connection, gameboy):
        Comparator.__init__(self, debug_connection)
        self.gameboy = gameboy
        self.cartridgeComparator = CartridgeComparator(debug_connection, 
                                        self.gameboy.cartridge_manager)
   
    @printframe("checking ROM")     
    def compare(self, data):
        cmp = [
            ("ROM", self.rom, "rom"),
            ("Registered Bitmap", constants.REGISTERED_BITMAP, "registeredBitmap")
        ]
        self.compare_set(cmp, data)
        self.compare_cartridge(data)
        

class CartridgeComparator(Comparator):
    def __init__(self, debug_connection, cartridge_manager):
        Comparator.__init__(self, debug_connection)
        self.cartridge_manager = cartridge_manager
        
    @printframe("checking cartridge data")           
    def compare(self, data):
        cmp = [
            ("ROM size",
                    self.cartridge_manager.get_rom_size(), "ramSize"),
            ("RAM size", 
                    self.cartridge_manager.get_ram_size(), "romSize"),
            ("Memory Bank Type", 
                    self.cartridge_manager.get_memory_bank_type(), "type"),
            ("checksum", 
                    self.cartridge_manager.get_checksum(), "checksum"),
            ("has battery", 
                    self.cartridge_manager.has_battery(), "hasBattery")
        ]
        self.compare_set(cmp, data, label="cartridge")
        

class InterruptComparator(Comparator):
    def __init__(self, debug_connection, gameboy):
        Comparator.__init__(self, debug_connection)
        self.cpu = gameboy.cpu
        self.interrupt = gameboy.interrupt
        
    @printframe("comparing interrupts")
    def compare(self, data):
        cmp = [
            ("ime",    self.cpu.ime,                        "ime"),
            ("halted", self.cpu.halted,                     "halted"),
            ("enable", self.interrupt.get_enable_mask(),    "enabled"),
            ("flag",   self.interrupt.get_interrupt_flag(), "flag")
        ]
        self.compare_set(cmp, data, label="interrupt")
        
class CPUComparator(Comparator):
    def __init__(self, debug_connection, cpu):
        Comparator.__init__(self, debug_connection);
        self.cpu = cpu
        
    @printframe("comparing CPU")    
    def compare(self, data):
        self.print_check("instruction count",
                         self.cpu.instruction_counter, 
                         data["instruction_count"])
        self.compare_opcodes(data)
        self.compare_registers(data["registers"])
   
    @printframe("comparing op codes")     
    def compare_opcodes(self, data):
        cmp = [
            ("last opCode" , self.cpu.last_op_code, "last_op_code"),
            ("last opCode" , self.cpu.last_fetch_execute_op_code, 
                    "last_fetch_exec_op_code")
        ]
        self.compare_set(cmp, data)
        
    @printframe("comparing registers")
    def compare_registers(self, data):
        display_results = []
        mapping =  [
            ("a",  self.cpu.a.get()),  ("f",  self.cpu.flag.get()),
            ("b",  self.cpu.b.get()),  ("c",  self.cpu.c.get()),
            ("d",  self.cpu.d.get()),  ("e",  self.cpu.e.get()),
            ("h",  self.cpu.h.get()),  ("l",  self.cpu.l.get()),
            ("sp", self.cpu.sp.get()), ("pc", self.cpu.pc.get())
        ];
        for reg in mapping:
            display_results.append((reg[1], registers[reg[0]]))
            self.print_check("register %s" % reg[0], reg[1], registers[reg[0]], output=True)
        self.print_register(mapping, display_results)
            
    def print_registers(self, mapping, display_results):
	    for i in range(len(display_results)):
	        line = ""
	        line += mapping[i][0].rjust(2) + ": "
	        line += str(display_results[i][0]).rjust(3) + " | "
	        print line
	        line =""
	        for i in range(len(display_results)):
	            line += "    " + str(display_results[i][0]).rjust(3) + " | "
	        print line
	        self.print_cpu_fetch()
        
    def print_cpu_fetch(self):
        pc = self.cpu.pc.get(use_cycles=False)
        print "fetch:", self.cpu.fetch(use_cycles=False)
        self.cpu.pc.set(pc, use_cycles=False)
                
      
class TimerComparator(Comparator):
    def __init__(self, debug_connection, timer):
        Comparator.__init__(self, debug_connection)
        self.timer = timer
    
    @printframe("comparing timer")      
    def compare(self, data):
        cmp = [
            ("div",           self.timer.divider,        "div"),
            ("dividerCycles", self.timer.divider_cycles, "dividerCycles"),
            ("tac",           self.timer.timer_control,  "tac"),
            ("tima",          self.timer.timer_counter,  "tima"),
            ("timerClock",    self.timer.timer_clock,    "timerClock"),
            ("timerCycles",   self.timer.timer_cycles,   "timerCycles"),
            ("tma",           self.timer.timer_modulo,   "tma")
        ]
        self.compare_set(cmp, data, label="timer")
           
        
class RAMComparator(Comparator):
    def __init__(self, debug_connection, gameboy_debug):
        Comparator.__init__(self, debug_connection)
        self.gameboy_debug = gameboy_debug
    
    @printframe("comparing RAM")   
    def compare(self, data):
        cpm = [
            ("wram",              self.gameboy_debug.ram.work_ram,   "wram"),
            ("hram",              self.gameboy_debug.ram.hi_ram,     "hram"),
            ("catridge external", self.get_external_cartridge_ram(), "ext")
        ]
        self.compare_memory_set(cmp, data)
    
    def get_external_cartridge_ram(self):
        ram = [0xFF] * (0xBFFF-0xA000+1)
        if self.gameboy_debug.cartridge_manager.mbc.ram_enable:
            for i in range(len(ram)):
                ram[i] = self.gameboy_debug.read(0xA000+i)
        return ram
            

class VideoComparator(Comparator):
    def __init__(self, debug_connection, video):
        Comparator.__init__(self, debug_connection)
        self.video = video
     
    @printframe("comparing video")   
    def compare(self, data):
        self.compare_memory(data)
        self.compare_registers(data)
        self.compare_other(data)
       
    @printframe("comparing memory")  
    def compare_memory(self, data):
        cmp = [
            (" vram",   self.video.vram,    "vram"),
            ("oam",     self.video.oam,     "oam"),
            ("line",    self.video.line,    "line"),
            ("objects", self.video.objects, "objects"),
            ("palette", self.video.palette, "palette")
        ]
        self.compare_memory_set(cmp, data, label="video");
    
    @printframe("comparing registers") 
    def compare_registers(self, data):
        cmp = [
            ("dirty",     self.video.dirty, "dirty"),
            ("display",   self.video.display, "display"),
            ("bgp",       self.video.background_palette, "bgp"),
            ("dma",       self.video.dma, "dma"),
            ("frames",    self.video.frames, "frames"),
            ("frameSkip", self.video.frame_skip, "frameSkip"),
            ("lcdc",      self.video.control.read(), "lcdc"),
            ("ly",        self.video.line_y, "ly"),
            ("obp0",      self.video.object_palette_0, "obp0"),
            ("obp1",      self.video.object_palette_1, "obp1"),
            ("scx",       self.video.background.scroll_x, "scx"),
            ("scy",       self.video.background.scroll_y, "scy"),
            ("stat",      self.video.status.read(), "stat"),
            ("transfer",  self.video.transfer, "transfer"),
            ("vblank",    self.video.v_blank, "vblank"),
            ("wly",       self.video.window.line_y, "wly"),
            ("wx",        self.video.window.x, "wx"),
            ("wy",        self.video.window.y, "wy")
        ]
        self.compare_set(cmp, data, label="video")
        
    @printframe("comparing additional tracked variables") 
    def compare_other(self, data):
        cmp = [
            ("Last Read Address",
                    self.video.lastReadAddress, "lastReadAddress"),
            ("Last Write Address", 
                    self.video.lastWriteAddress, "lastWriteAddress"),
            ("Last eritten Data", 
                    self.video.lastWriteData, "lastWriteData"),
            ("Check wether emulated HBlank", 
                    self.video.emulateHBlank, "emulateHBlank"),
            ("Check wether emulated OAM", 
                    self.video.emulateOAM, "emulateOAM"),
            ("Check wether emulated Transfer", 
                    self.video.emulateTransfer, "emulateTransfer"),
            ("Check wether emulated VBLank", 
                    self.video.emulateVBlank, "emulateVBlank"),
        ]
        self.compare_set(cmp, data, label="video")
         