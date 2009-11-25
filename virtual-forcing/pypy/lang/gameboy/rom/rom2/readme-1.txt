============
Gameboy ROM2
============


Description
-----------
This is a raw ROM, meaning it contains no valid Gameboy header, just 
instructions. Addressing is relative, so the ROM can be loaded anywhere in 
memory.


Disassembly
-----------
3E 00       LD  A, 0
06 00       LD  B, 0
80          ADD A, B