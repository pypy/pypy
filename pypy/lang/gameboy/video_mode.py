
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.constants import SPRITE_SIZE, GAMEBOY_SCREEN_WIDTH, \
                                        GAMEBOY_SCREEN_HEIGHT

# -----------------------------------------------------------------------------
class InvalidModeOrderException(Exception):
    def __init__(self, mode, previous_mode):
        Exception.__init__(self, \
                           "Wrong Mode order! No valid transition %i => %i" \
                           % (previous_mode.id(), mode.id()))
       
class HandleSubclassException(Exception): 
    def __init__(self):
        Exception.__init__(self, "")
        
class Mode(object):
    """
    The two lower STAT bits show the current status of the LCD controller.
    """
    def __init__(self, video):
        self.video = video
        self.reset()
        
    def reset(self):
        raise Exception("unimplemented method")
                        
    def id(self):
        raise Exception("unimplemented method")
    
    def activate(self):
        raise Exception("unimplemented method")
    
    def emulate(self):
        raise Exception("unimplemented method")

    def emulate_hblank_line_y_compare(self, stat_check=False):
        if self.video.line_y == self.video.line_y_compare:
            if not (stat_check and self.video.status.line_y_compare_flag):
                self.line_y_line_y_compare_interrupt_check()
        else:
            self.video.status.line_y_compare_flag = False
            
    def line_y_line_y_compare_interrupt_check(self):
        self.video.status.line_y_compare_flag = True
        if self.video.status.line_y_compare_interrupt:
            self.video.lcd_interrupt_flag.set_pending()

# -----------------------------------------------------------------------------

class Mode0(Mode):
    """
     Mode 0: The LCD controller is in the H-Blank period and
          the CPU can access both the display RAM (8000h-9FFFh)
          and OAM (FE00h-FE9Fh)
    """
    def reset(self):
        self.h_blank_interrupt = False
    
    def id(self):
        return 0
    
    def activate(self):
        self.video.cycles += constants.MODE_0_TICKS
        self.h_blank_interrupt_check()
    
    def h_blank_interrupt_check(self):
        if self.h_blank_interrupt and \
        self.video.status.line_y_compare_check():
            self.video.lcd_interrupt_flag.set_pending()
            
    def emulate(self):
        #self.video.emulate_hblank()
        self.emulate_hblank()
        
    def emulate_hblank(self):
        self.video.line_y += 1
        self.emulate_hblank_line_y_compare()
        if self.video.line_y < GAMEBOY_SCREEN_HEIGHT:
            self.video.status.set_mode(2)
        else:
            self.emulate_hblank_part_2()
            
    def emulate_hblank_part_2(self):
        if self.video.display:
            self.video.draw_frame()
        self.video.frames += 1
        if self.video.frames >= self.video.frame_skip:
            self.video.display = True
            self.video.frames = 0
        else:
            self.video.display = False
        self.video.status.set_mode(1)
        self.video.v_blank  = True
  
# -----------------------------------------------------------------------------
               
class Mode1(Mode):
    """
    Mode 1: The LCD contoller is in the V-Blank period (or the
          display is disabled) and the CPU can access both the
          display RAM (8000h-9FFFh) and OAM (FE00h-FE9Fh)
    """
    def reset(self):
        self.v_blank_interrupt = False
        
    def id(self):
        return 1
    
    def activate(self):
        self.set_begin()

    def set_begin(self):
        self.video.cycles += constants.MODE_1_BEGIN_TICKS
    
    def set_between(self):
        self.video.cycles += constants.MODE_1_TICKS - constants.MODE_1_BEGIN_TICKS
        
    def set_end(self):
        self.video.cycles += constants.MODE_1_END_TICKS
    
    def emulate(self):
        self.emulate_v_blank()
   
    def emulate_v_blank(self):
        if self.video.v_blank:
            self.emulate_v_blank_v_blank()
        elif self.video.line_y == 0:
            self.video.status.set_mode(2)
        else:
            self.emulate_v_blank_other()
 
    def emulate_v_blank_v_blank(self):
        self.video.v_blank  = False
        self.set_between()
        self.v_blank_interrupt_check()
                  
    def v_blank_interrupt_check(self):
        if self.v_blank_interrupt:
            self.video.lcd_interrupt_flag.set_pending()
        self.video.v_blank_interrupt_flag.set_pending()
        
    def emulate_v_blank_other(self):
        if self.video.line_y < 153:
            self.emulate_v_blank_mode_1()
        else:
            self.video.line_y        = 0
            self.video.window.line_y = 0
            self.set_between()
        self.emulate_hblank_line_y_compare() 
                
    def emulate_v_blank_mode_1(self):
        self.video.line_y += 1
        if self.video.line_y != 153:
            self.video.cycles += constants.MODE_1_TICKS
        else:
            self.set_end()

# -----------------------------------------------------------------------------
     
class Mode2(Mode):
    """
    Mode 2: The LCD controller is reading from OAM memory.
          The CPU <cannot> access OAM memory (FE00h-FE9Fh)
          during this period.
    """
    def reset(self):
        self.oam_interrupt = False
        
    def id(self):
        return 2
    
    def activate(self):
        self.video.cycles += constants.MODE_2_TICKS
        self.oam_interrupt_check()
     
    def oam_interrupt_check(self):
        if self.oam_interrupt and \
        self.video.status.line_y_compare_check():
            self.video.lcd_interrupt_flag.set_pending()
            
    def emulate(self):
        self.emulate_oam()
        
    def emulate_oam(self):
        self.video.status.set_mode(3)

# -----------------------------------------------------------------------------

class Mode3(Mode):
    """
       Mode 3: The LCD controller is reading from both OAM and VRAM,
          The CPU <cannot> access OAM and VRAM during this period.
          CGB Mode: Cannot access Palette Data (FF69,FF6B) either.
    """
    def reset(self):
        pass
    
    def id(self):
        return 3
    
    def activate(self):
        self.set_begin()
    
    def set_begin(self):
        self.video.cycles  += constants.MODE_3_BEGIN_TICKS
        self.video.transfer = True
        
    def set_end(self):
        self.video.cycles  += constants.MODE_3_END_TICKS
        self.video.transfer = False
        
    def emulate(self):
        self.emulate_transfer()
        
    def emulate_transfer(self):
        if self.video.transfer:
            if self.video.display:
                self.video.draw_line()
                #print "mode 3 ", self.video.status.get_mode() 
            self.set_end()
        else:
            self.video.status.set_mode(0)
        