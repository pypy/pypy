
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
        
        
          
# -----------------------------------------------------------------------------

class GameboyComparator(Comparator):
    
    def __init__(self, debug_connection, gameboy):
        Comparator.__init__(self, debug_connection)
        self.gameboy = gameboy
        self.create_part_comparators(debug_connection)
        
    def create_part_comparators(self, debug_connection):
        self.cpu_comparator = CPUComparator(debug_connection, self.gameboy.cpu)
        self.timer_comparator = TimerComparator(debug_connection, self.gameboy.timer)
        self.interrupt_comparator = InterruptComparator(debug_connection, self.gameboy)
        self.video_comparator = VideoComparator(debug_connection, self.gameboy.video)
        self.ram_comparator = RAMComparator(debug_connection, self.gameboy)
    
    def compare(self, data):
        self.compare_cycles(data["cycles"])
        self.cpu_comparator.compare(data["cpu"])
        self.timer_comparator.compare(data["timer"])
        self.interrupt_comparator.compare(data["interrupt"])
        self.video_comparator.compare(data["video"])
        self.ram_comparator.compare(data["ram"])
    
    @printframe("comparing cycles")        
    def compare_cycles(self, data):
        self.print_check("cycles video", self.video.cycles, data["video"])
        self.print_check("cycles cpu", 
                self.gameboy_debug.cpu.cycles, data["cpu"])
        self.print_check("cycles serial",
                self.gameboy_debug.serial.cycles, data["serial"])
        self.print_check("cycles joypad",
                self.gameboy_debug.joypad.cycles, data["joypad"])   
        #sound not yet implemented so no  use for checking cycles here
        #self.print_check("cycles sound", #self.gameboy_debug.sound.cycles, 
        #                    0, data["sound"])   

class ROMComparator(Comparator):
    
    def __init__(self, debug_connection, gameboy):
        Comparator.__init__(self, debug_connection)
        self.gameboy = gameboy
        self.cartridgeComparator = CartridgeComparator(debug_connection, 
                                        self.gameboy_debug.cartridge_manager)
   
    @printframe("checking ROM")     
    def compare(self, data):
        self.compare_memory("ROM", self.rom, data["rom"])
        self.compare_memory("registeredBitmap", constants.REGISTERED_BITMAP, \
                            data["registeredBitmap"])
        self.compare_cartridge(data)
        

class CartridgeComparator(Comparator):
    
    def __init__(self, debug_connection, catridge_manager):
        Comparator.__init__(self, debug_connection)
        self.cartridge_manager = cartridge_manager
        
    @printframe("checking cartridge data")           
    def compare(self, data):
        self.print_compare("cartridge ROM size",
                self.cartridge_manager.get_rom_size(),
                data["ramSize"])
        self.print_compare("cartridge RAM size", 
                self.cartridge_manager.get_ram_size(),
                data["romSize"])
        self.print_compare("cartridge Memory Bank Type",
                self.cartridge_manager.get_memory_bank_type(),
                data["type"])
        self.print_compare("cartridge checksum",
                self.cartridge_manager.get_checksum(),
                data["checksum"])
        self.print_compare("cartridge has battery",
                self.cartridge_manager.has_battery(),
                data["hasBattery"])
        

class InterruptComparator(Comparator):
    
    def __init__(self, debug_connection, gameboy):
        Comparator.__init__(self, debug_connection)
        self.cpu = gameboy.cpu
        self.interrupt = gameboy.interrupt
        
    @printframe("comparing interrupts")
    def compare(self, data):
        self.print_check("interrupt ime", self.cpu.ime,  data["ime"])
        self.print_check("interrupt halted" , self.cpu.halted, data["halted"])
        self.print_check("interrupt enable" ,
                self.interrupt.get_enable_mask(), data["enabled"])
        self.print_check("interrupt flag" ,
                self.interrupt.get_interrupt_flag(), data["flag"])
                       
        
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
        self.compare_registers(data)
   
    @printframe("comparing op codes")     
    def compare_opcodes(self, data):
        self.print_check("last opCode" , self.cpu.last_op_code, 
                         data["last_op_code"])
        self.print_check("last opCode" , self.cpu.last_fetch_execute_op_code,
                         data["last_fetch_exec_op_code"])
        
    @printframe("comparing registers")
    def compare_registers(self, data):
        registers = data["registers"]
        display_results = []
        mapping =  [("a",  self.cpu.a.get()),  ("f",  self.cpu.flag.get()),
        ("b",  self.cpu.b.get()),  ("c",  self.cpu.c.get()),
        ("d",  self.cpu.d.get()),  ("e",  self.cpu.e.get()),
        ("h",  self.cpu.h.get()),  ("l",  self.cpu.l.get()),
        ("sp", self.cpu.sp.get()), ("pc", self.cpu.pc.get())];
        
        for reg in mapping:
            display_results.append(( reg[1], registers[reg[0]]))
            self.print_check("register %s" % reg[0], reg[1], registers[reg[0]], output=True)
            
            line = ""
            for i in range(len(display_results)):
                line += mapping[i][0].rjust(2) + ": "
                line += str(display_results[i][0]).rjust(3) + " | "
                print line
               
                line =""
                for i in range(len(display_results)):
                    line += "    " + str(display_results[i][0]).rjust(3) + " | "
                print line
                
                pc = self.cpu.pc.get(use_cycles=False)
                print "fetch:", self.cpu.fetch(use_cycles=False)
                self.cpu.pc.set(pc, use_cycles=False)
                
      
class TimerComparator(Comparator):
    
    def __init__(self, debug_connection, timer):
        Comparator.__init__(self, debug_connection)
        self.timer = timer
    
    @printframe("comparing timer")      
    def compare(self, data):
        self.print_check("timer div", \
                self.timer.divider, \
                data["div"])
        self.print_check("timer dividerCycles", \
                self.timer.divider_cycles, \
                data["dividerCycles"])
        self.print_check("timer tac", \
                self.timer.timer_control, \
                data["tac"])
        self.print_check("timer tima", \
                self.timer.timer_counter, \
                data["tima"])
        self.print_check("timer timerClock", \
                self.timer.timer_clock, \
                data["timerClock"])
        self.print_check("timer timerCycles", \
                self.timer.timer_cycles, \
                data["timerCycles"])
        self.print_check("timer tma", \
                self.timer.timer_modulo, \
                data["tma"])             
           
        
class RAMComparator(Comparator):
    
    def __init__(self, debug_connection, gameboy_debug):
        Comparator.__init__(self, debug_connection)
        self.gameboy_debug = gameboy_debug
    
    @printframe("comparing RAM")   
    def compare(self, data):
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
            
        

class VideoComparator(Comparator):
    
    def __init__(self, debug_connection, video):
        Comparator.__init__(self, debug_connection)
        self.video = video
     
    @printframe("comparing video")   
    def compare(self, data):
        self.compare_memory(video)
        self.compare_registers(video)
       
    @printframe("comparing memory")  
    def compare_memory(self, data):
        self.compare_memory("video vram", self.video.vram,
                            data["vram"])
        self.compare_memory("video object attribute memory oam",
                            self.video.oam, data["oam"])
        self.compare_memory("video line", self.video.line,
                            data["line"])
        self.compare_memory("video objects", self.video.objects,
                            data["objects"])
        self.compare_memory("video palette", self.video.palette,
                            data["palette"])        
    
    @printframe("comparing registers")    
    def compare_registers(self, data):
        self.print_check("video dirty", \
                self.video.dirty, data["dirty"])
        self.print_check("video display", \
                self.video.display, data["display"])
        self.print_check("video bgp", \
                self.video.background_palette, \
                data["bgp"])
        self.print_check("video dma", \
                self.video.dma, data["dma"])
        self.print_check("video frames", \
                self.video.frames, data["frames"])
        self.print_check("video frameSkip", \
                self.video.frame_skip, \
                data["frameSkip"])
        self.print_check("video lcdc", \
                self.video.control.read(), data["lcdc"])
        self.print_check("video ly", \
                self.video.line_y, data["ly"])
        self.print_check("video obp0", \
                self.video.object_palette_0, \
                data["obp0"])
        self.print_check("video obp1", \
                self.video.object_palette_1, \
                data["obp1"])
        self.print_check("video scx", \
                self.video.background.scroll_x, data["scx"])
        self.print_check("video scy", \
                self.video.background.scroll_y, data["scy"])
        self.print_check("video stat", \
                self.video.status.read(), data["stat"])
        self.print_check("video transfer", \
                self.video.transfer, data["transfer"])
        self.print_check("video vblank", \
                self.video.v_blank, data["vblank"])
        self.print_check("video wly", \
                self.video.window.line_y, data["wly"])
        self.print_check("video wx", \
                self.video.window.x, data["wx"])
        self.print_check("video wy", \
                self.video.window.y, data["wy"])        