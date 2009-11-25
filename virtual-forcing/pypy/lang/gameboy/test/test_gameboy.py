
import py
from pypy.lang.gameboy.gameboy import *



def get_gameboy():
    gameboy = GameBoy()
    return gameboy



def test_init():
    gameboy = get_gameboy()
    gameboy.read(0xFF05) == 0x00   # TIMA
    gameboy.read(0xFF06) == 0x00   # TMA
    gameboy.read(0xFF07) == 0x00   # TAC
    gameboy.read(0xFF10) == 0x80   # NR10 a.k.a. rAUD1SWEEP
    gameboy.read(0xFF11) == 0xBF   # NR11 a.k.a. rAUD1LEN
    gameboy.read(0xFF12) == 0xF3   # NR12 a.k.a. rAUD1ENV
    gameboy.read(0xFF14) == 0xBF   # NR14 a.k.a. rAUD1HIGH
    gameboy.read(0xFF16) == 0x3F   # NR21 a.k.a. rAUD2LEN
    gameboy.read(0xFF17) == 0x00   # NR22 a.k.a. rAUD2ENV
    gameboy.read(0xFF19) == 0xBF   # NR24 a.k.a. rAUD2HIGH
    gameboy.read(0xFF1A) == 0x7F   # NR30 a.k.a. rAUD3ENA
    gameboy.read(0xFF1B) == 0xFF   # NR31 a.k.a. rAUD3LEN
    gameboy.read(0xFF1C) == 0x9F   # NR32 a.k.a. rAUD3LEVEL
    gameboy.read(0xFF1E) == 0xBF   # NR33 a.k.a. rAUD3LOW
    gameboy.read(0xFF20) == 0xFF   # NR41 a.k.a. rAUD4LEN
    gameboy.read(0xFF21) == 0x00   # NR42 a.k.a. rAUD4ENV
    gameboy.read(0xFF22) == 0x00   # NR43 a.k.a. rAUD4POLY
    gameboy.read(0xFF23) == 0xBF   # NR44 a.k.a. rAUD4GO
    gameboy.read(0xFF24) == 0x77   # NR50 a.k.a. rAUDVOL
    gameboy.read(0xFF25) == 0xF3   # NR51 a.k.a. rAUDTERM
    gameboy.read(0xFF26) == 0xF1   # NR52
    gameboy.read(0xFF40) == 0x91   # LCDC
    gameboy.read(0xFF42) == 0x00   # SCY
    gameboy.read(0xFF43) == 0x00   # SCX
    gameboy.read(0xFF45) == 0x00   # LYC
    gameboy.read(0xFF47) == 0xFC   # BGP
    gameboy.read(0xFF48) == 0xFF   # OBP0
    gameboy.read(0xFF49) == 0xFF   # OBP1
    gameboy.read(0xFF4A) == 0x00   # WY
    gameboy.read(0xFF4B) == 0x00   # WX
    gameboy.read(0xFFFF) == 0x00   # IE