
WORD = 8

# The stack contains the force_index and the, callee saved registers and
# ABI required information
# All the rest of the data is in a GC-managed variable-size "frame".
# This jitframe object's address is always stored in the register FP
# A jitframe is a jit.backend.llsupport.llmodel.jitframe.JITFRAME
# Stack frame fixed area
# Currently only the force_index
JITFRAME_FIXED_SIZE = 16 + 16
# 16 GPR + 16 VFP Regs # 20 if we want to use 4 extra x19..x22
