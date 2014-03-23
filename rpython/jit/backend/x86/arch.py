# Constants that depend on whether we are on 32-bit or 64-bit
# the frame is absolutely standard. Stores callee-saved registers,
# return address and some scratch space for arguments.

import sys
if sys.maxint == (2**31 - 1):
    WORD = 4
    IS_X86_32 = True
    IS_X86_64 = False
else:
    WORD = 8
    IS_X86_32 = False
    IS_X86_64 = True

#
#        +--------------------+    <== aligned to 16 bytes
#        |   return address   |
#        +--------------------+           ----------------------.
#        |    saved regs      |                FRAME_FIXED_SIZE |
#        +--------------------+       --------------------.     |
#        |   scratch          |          PASS_ON_MY_FRAME |     |
#        |      space         |                           |     |
#        +--------------------+    <== aligned to 16 -----' ----'

# All the rest of the data is in a GC-managed variable-size "frame".
# This frame object's address is always stored in the register EBP/RBP.
# A frame is a jit.backend.llsupport.llmodel.JITFRAME = GcArray(Signed).

# The frame's fixed size gives the standard fixed part at the
# start of every frame: the saved value of some registers

if WORD == 4:
    # ebp + ebx + esi + edi + 15 extra words = 19 words
    FRAME_FIXED_SIZE = 19
    PASS_ON_MY_FRAME = 15
    JITFRAME_FIXED_SIZE = 6 + 8 * 2 # 6 GPR + 8 XMM * 2 WORDS/float
else:
    # rbp + rbx + r12 + r13 + r14 + r15 + 13 extra words = 19
    FRAME_FIXED_SIZE = 19
    PASS_ON_MY_FRAME = 13
    JITFRAME_FIXED_SIZE = 28 # 13 GPR + 15 XMM

assert PASS_ON_MY_FRAME >= 12       # asmgcc needs at least JIT_USE_WORDS + 3
