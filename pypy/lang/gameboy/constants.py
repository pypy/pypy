#___________________________________________________________________________
# GAMEBOY
#___________________________________________________________________________
 
# Gameboy Clock Speed (1048576 Hz)
GAMEBOY_CLOCK = 1 << 20

REGISTERED_BITMAP = [ 0x3C, 0x42, 0xB9, 0xA5, 0xB9, 0xA5, 0x42, 0x3C ]

GAMEBOY_SCREEN_WIDTH  = 160
GAMEBOY_SCREEN_HEIGHT = 144

SPRITE_SIZE = 8

#___________________________________________________________________________
# CATRIGE TYPES
# ___________________________________________________________________________

TYPE_ROM_ONLY                = 0x00

TYPE_MBC1                    = 0x01
TYPE_MBC1_RAM                = 0x02
TYPE_MBC1_RAM_BATTERY        = 0x03

TYPE_MBC2                    = 0x05
TYPE_MBC2_BATTERY            = 0x06

TYPE_MBC3_RTC_BATTERY        = 0x0F
TYPE_MBC3_RTC_RAM_BATTERY    = 0x10
TYPE_MBC3                    = 0x11
TYPE_MBC3_RAM                = 0x12
TYPE_MBC3_RAM_BATTERY        = 0x13

TYPE_MBC5                    = 0x19
TYPE_MBC5_RAM                = 0x1A
TYPE_MBC5_RAM_BATTERY        = 0x1B

TYPE_MBC5_RUMBLE             = 0x1C
TYPE_MBC5_RUMBLE_RAM         = 0x1D
TYPE_MBC5_RUMBLE_RAM_BATTERY = 0x1E

TYPE_HUC3_RTC_RAM            = 0xFE
TYPE_HUC1_RAM_BATTERY        = 0xFF

CARTRIDGE_TYPE_ADDRESS       = 0x0147
CARTRIDGE_ROM_SIZE_ADDRESS   = 0x0148
CARTRIDGE_RAM_SIZE_ADDRESS   = 0x0149
CARTRIDGE_RAM_SIZE_MAPPING   = {0x00:0, 0x01:8192, 0x02:8192, 0x03:32768}
DESTINATION_CODE_ADDRESS     = 0x014A
LICENSEE_ADDRESS             = 0x014B
ROM_VERSION_ADDRESS          = 0x014C
HEADER_CHECKSUM_ADDRESS      = 0x014D
CHECKSUM_A_ADDRESS           = 0x014E
CHECKSUM_B_ADDRESS           = 0x014F

# ROM Bank Size (16KB)
ROM_BANK_SIZE                = 0x4000

# constants.RAM Bank Size (8KB)
RAM_BANK_SIZE                = 0x2000

CARTRIDGE_FILE_EXTENSION       = ".gb"
CARTRIDGE_COLOR_FILE_EXTENSION = ".gbc"
BATTERY_FILE_EXTENSION         = ".sav"
    
# ___________________________________________________________________________
# CPU FLAGS
# ___________________________________________________________________________

Z_FLAG   = 0x80
N_FLAG   = 0x40
H_FLAG   = 0x20
C_FLAG   = 0x10

RESET_A  = 0x01 
#RESET_F = 0xB0 
RESET_F  = 0x80 
RESET_BC = 0x0013
RESET_DE = 0x00D8
RESET_HL = 0x014D
RESET_SP = 0xFFFE
RESET_PC =  0x0100


# ___________________________________________________________________________
#INTERRUPT FLAGS
# ___________________________________________________________________________

# Interrupt Registers
IE     = 0xFFFF # Interrupt Enable
IF     = 0xFF0F # Interrupt Flag

# Interrupt Flags
VBLANK = 0x01 # V-Blank Interrupt (INT 40h)
LCD    = 0x02 # LCD STAT Interrupt (INT 48h)
TIMER  = 0x04 # Timer Interrupt (INT 50h)
SERIAL = 0x08 # Serial Interrupt (INT 58h)
JOYPAD = 0x10 # Joypad Interrupt (INT 60h)


# ___________________________________________________________________________
# VIDEO
# ___________________________________________________________________________

# LCD Register Addresses
LCDC = 0xFF40 # LCD Control
STAT = 0xFF41 # LCD Status
SCY  = 0xFF42 # BG Scroll Y (0-255)
SCX  = 0xFF43 # BG Scroll X (0-255)
LY   = 0xFF44 # LCDC Y-Coordinate (0-153)
LYC  = 0xFF45 # LY Compare
DMA  = 0xFF46 # OAM DMA Transfer
BGP  = 0xFF47 # BG Palette Data
OBP0 = 0xFF48 # Object Palette 0 Data
OBP1 = 0xFF49 # Object Palette 1 Data
WY   = 0xFF4A # Window Y Position (0-143)
WX   = 0xFF4B # Window X Position (0-166)
 
# OAM Register Addresses
OAM_ADDR    = 0xFE00 # OAM Object Attribute Map (FE00..FE9F)
OAM_SIZE    = 0xA0
 
# Video RAM Addresses
VRAM_ADDR   = 0x8000 # 8KB Video RAM (8000..9FFF)
VRAM_SIZE   = 0x2000

# VRAM Tile Data/Maps Addresses
VRAM_DATA_A = 0x0000 # 4KB Tile Data (8000..8FFF)
VRAM_DATA_B = 0x0800 # 4KB Tile Data (8800..97FF)

VRAM_MAP_A  = 0x1800 # 1KB BG Tile Map 0 (9800..9BFF)
VRAM_MAP_B  = 0x1C00 # 1KB BG Tile Map 1 (9C00..9FFF)


#LCD Mode Durations
MODE_0_TICKS       = 50 # H-Blank
MODE_1_TICKS       = 114 # V-Blank
MODE_2_TICKS       = 20 # OAM#/
MODE_3_BEGIN_TICKS = 12 # Display
MODE_3_END_TICKS   = 32 # Display
 
MODE_1_BEGIN_TICKS = 8 # V-Blank Line 144
MODE_1_END_TICKS   = 1 # V-Blank Line 153
 
# Objects per Line
OBJECTS_PER_LINE   = 10
 
# LCD Color Palette
COLOR_MAP =[
 0x9CB916, 0x8CAA14, 0x306430, 0x103F10
 # 0xE0F8D0, 0x88C070, 0x386850, 0x081820
 # 0xFFFFFF, 0xAAAAAA, 0x555555, 0x000000
 ]



# ___________________________________________________________________________
# JOYPAD
# ___________________________________________________________________________

# Joypad Registers P+
JOYP          = 0xFF00
 

# Joypad Poll Speed (64 Hz)
JOYPAD_CLOCK  = GAMEBOY_CLOCK >> 6


BUTTON_DOWN   = 0x08
BUTTON_UP     = 0x04
BUTTON_LEFT   = 0x02
BUTTON_RIGHT  = 0x01
 
BUTTON_START  = 0x08
BUTTON_SELECT = 0x04
BUTTON_B      = 0x02
BUTTON_A      = 0x01



# ___________________________________________________________________________
# SERIAL
# ___________________________________________________________________________
 
# Serial Clock Speed (8 x 1024 bits/sec)
SERIAL_CLOCK      = GAMEBOY_CLOCK >> 16
 
# Serial Idle Speed (128 Hz)
SERIAL_IDLE_CLOCK = GAMEBOY_CLOCK >> 7
 
# Serial Register Addresses
SERIAL_TRANSFER_DATA    = 0xFF01
SERIAL_TRANSFER_CONTROL = 0xFF02
 



# ___________________________________________________________________________
# SOUND
# ___________________________________________________________________________
 
# Sound Clock (256 Hz)
SOUND_CLOCK = 256 
 
# Sound Register Addresses
NR10 = 0xFF10 # AUD1SWEEP
NR11 = 0xFF11 # AUD1LEN
NR12 = 0xFF12 # AUD1ENV
NR13 = 0xFF13 # AUD1LOW
NR14 = 0xFF14 # AUD1HIGH
 
NR21 = 0xFF16 # AUD2LEN
NR22 = 0xFF17 # AUD2ENV
NR23 = 0xFF18 # AUD2LOW
NR24 = 0xFF19 # AUD2HIGH
 
NR30 = 0xFF1A # AUD3ENA
NR31 = 0xFF1B # AUD3LEN
NR32 = 0xFF1C # AUD3LEVEL
NR33 = 0xFF1D # AUD3LOW
NR34 = 0xFF1E # AUD3HIGH
 
NR41 = 0xFF20 # AUD4LEN
NR42 = 0xFF21 # AUD4ENV
NR43 = 0xFF22 # AUD4POLY
NR44 = 0xFF23 # AUD4GO
 
NR50 = 0xFF24 # AUDVOL
NR51 = 0xFF25 # AUDTERM
NR52 = 0xFF26 # AUDENA

AUD3WAVERAM = 0xFF30

BUFFER_LOG_SIZE = 5;


# ___________________________________________________________________________
# TIMER
# ___________________________________________________________________________


# DIV Timer Speed (16384 Hz)
DIV_CLOCK = GAMEBOY_CLOCK >> 14

# Timer Clock Speeds (4096, 262144, 65536 and 16384 Hz)
TIMER_CLOCK = [
 GAMEBOY_CLOCK >> 12,
 GAMEBOY_CLOCK >> 18,
 GAMEBOY_CLOCK >> 16,
 GAMEBOY_CLOCK >> 14
]
 
# Timer Register Addresses
DIV  = 0xFF04 # Divider Register
TIMA = 0xFF05 # Timer Counter
TMA  = 0xFF06 # Timer Modulo
TAC  = 0xFF07 # Timer Control
