============
Gameboy ROM6
============


Specifications
--------------
Filename:     rom6.gb
Description:  This ROM is created to test the implementation of ROM cartridge 
              with an MBC1 controller.
ROM type:     MBC1 + RAM (64kB ROM, 32kB RAM)


Special notes
-------------
This ROM uses call and ret instructions, so this means that the emulator will 
also need to implement and support a stack.

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
call
ret