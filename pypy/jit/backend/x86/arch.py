# Constants that depend on whether we are on 32-bit or 64-bit

# The frame size gives the standard fixed part at the start of
# every assembler frame: the saved value of some registers,
# one word for the force_index, and some extra space used only
# during a malloc that needs to go via its slow path.

import sys
if sys.maxint == (2**31 - 1):
    WORD = 4
    IS_X86_32 = True
    IS_X86_64 = False
else:
    WORD = 8
    IS_X86_32 = False
    IS_X86_64 = True

# The stack for a JIT call is fixed, but it contains only scratch space
# used e.g. for storing arguments to further calls:
#
#        +--------------------+    <== aligned to 16 bytes
#        |   return address   |
#        +--------------------+
#        |   scratch          |
#        |      space         |
#        +--------------------+    <== aligned to 16 bytes

if WORD == 4:
    SCRATCH_SIZE = 7     # total size: 32 bytes
else:
    SCRATCH_SIZE = 3     # total size: 32 bytes

# All the rest of the data is in a GC-managed variable-size "frame".
# This frame object's address is always stored in the register EBP/RBP.
# A frame is a jit.backend.llsupport.llmodel.JITFRAME = GcArray(Signed).
# The following locations are indices in this array.

# The frame's fixed size gives the standard fixed part at the
# start of every frame: the saved value of some registers,
# one word for the force_index, and some extra space used only
# during a malloc that needs to go via its slow path.

if WORD == 4:
    # XXX rethink the fixed size
    # ebp + ebx + esi + edi + 4 extra words + force_index = 9 words
    FRAME_FIXED_SIZE = 6
    SAVED_REGISTERS = 1    # range(1, 5)
    MY_COPY_OF_REGS = 5    # range(5, 9)
    XXX
    JITFRAME_FIXED_SIZE = 29 # 13 GPR + 16 XMM
                             # reg, we don't save it
else:
    # rbp + rbx + r12 + r13 + r14 + r15 + 11 extra words + force_index = 18
    FRAME_FIXED_SIZE = 6
    SAVED_REGISTERS = 1    # range(1, 7)
    MY_COPY_OF_REGS = 7    # range(7, 18)
    JITFRAME_FIXED_SIZE = 29 # 13 GPR + 16 XMM
                             # reg, we don't save it
    
# "My copy of regs" has room for almost all registers, apart from eax and edx
# which are used in the malloc itself.  They are:
#   ecx, ebx, esi, edi               [32 and 64 bits]
#   r8, r9, r10, r12, r13, r14, r15    [64 bits only]
#
# Note that with asmgcc, the locations corresponding to callee-save registers
# are never used.
