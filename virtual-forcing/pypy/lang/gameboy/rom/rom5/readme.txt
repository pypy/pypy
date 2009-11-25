============
Gameboy ROM5
============


Specifications
--------------
Filename:     rom5.gb
Description:  This ROM is created to test the conditional jump instructions. It 
              also includes an invalid opcode ($DD) which is used for debugging 
              purposes!
ROM type:     NO MBC (32kB ROM, no RAM)


Special notes
-------------
IMPORTANT: This ROM contains an invalid opcode ($DD) which we use to trigger the 
emulator into a "breakpoint". When executing this ROM, simply treat the $DD 
bytes as NOP ($00) instructions, but also print out the registers and CPU 
status.

This ROM also uses the carry and zero flags, so make sure that the work correctly.


Instructions used
-----------------
ld
jp
jr
inc
dec
nop
di
halt
$DD