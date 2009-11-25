============
Gameboy ROM4
============


Specifications
--------------
Filename:     rom4.gb
Description:  This ROM is created to test the DI and HALT instructions. It also 
              uses the LCDC register to turn off the screen.
ROM type:     NO MBC (32kB ROM, no RAM)


Instructions used
-----------------
ld
jp
nop
res
di
halt


Memory registers used
---------------------
$ff40 (LCDC register, used to turn of screen)


Short information
-----------------
HALT stops the CPU until an interrupt occurs. Nintendo recommends using this 
command in your main game loop in order to save battery power while the CPU has 
nothing else to do.

When an interrupt occurs while in HALT, the CPU starts back up and pushes the 
Program Counter onto the stack before servicing the interrupt(s). Except it 
doesn't push the address after HALT as one might expect but rather the address 
of HALT itself.

Nintendo also recommends that you put a NOP after HALT commands. The reason for 
this is that the Program Counter will not increment properly (CPU bug) if you 
try to do a HALT while IME = 0 and an interrupt is pending. A single-byte 
instruction immediately following HALT will get executed twice if IME = 0 and an 
interrupt is pending. If the instruction following HALT is a multi-byte 
instruction then the game could hang or registers could get scrambled.
