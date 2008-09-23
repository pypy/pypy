============
Gameboy ROM1
============


Description
-----------
This is a raw ROM, meaning it contains no valid Gameboy header, just 
instructions. Addressing is relative, so the ROM can be loaded anywhere in 
memory.


Disassembly
-----------
3E 01       LD  A, 1
06 01       LD  B, 1
80          ADD A, B