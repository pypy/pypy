# Constants that depend on whether we are on 32-bit or 64-bit

# The frame size gives the standard fixed part at the start of
# every assembler frame: the saved value of some registers,
# one word for the force_index, and some extra space used only
# during a malloc that needs to go via its slow path.

import sys
if sys.maxint == (2**31 - 1):
    WORD = 4
    # ebp + ebx + esi + edi + 4 extra words + force_index = 9 words
    FRAME_FIXED_SIZE = 9
    FORCE_INDEX_OFS = -8*WORD
    MY_COPY_OF_REGS = -7*WORD
    IS_X86_32 = True
    IS_X86_64 = False
else:
    WORD = 8
    # rbp + rbx + r12 + r13 + r14 + r15 + 11 extra words + force_index = 18
    FRAME_FIXED_SIZE = 18
    FORCE_INDEX_OFS = -17*WORD
    MY_COPY_OF_REGS = -16*WORD
    IS_X86_32 = False
    IS_X86_64 = True

# The extra space has room for almost all registers, apart from eax and edx
# which are used in the malloc itself.  They are:
#   ecx, ebx, esi, edi               [32 and 64 bits]
#   r8, r9, r10, r12, r13, r14, r15    [64 bits only]
