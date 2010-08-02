# Constants that depend on whether we are on 32-bit or 64-bit

import sys
if sys.maxint == (2**31 - 1):
    WORD = 4
    # ebp + ebx + esi + edi + force_index = 5 words
    FRAME_FIXED_SIZE = 5
    IS_X86_32 = True
    IS_X86_64 = False
else:
    WORD = 8
    # rbp + rbx + r12 + r13 + r14 + r15 + force_index = 7 words
    FRAME_FIXED_SIZE = 7
    IS_X86_32 = False
    IS_X86_64 = True

FORCE_INDEX_OFS = -(FRAME_FIXED_SIZE-1)*WORD
