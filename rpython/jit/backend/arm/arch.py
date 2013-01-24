FUNC_ALIGN = 8
WORD = 4
DOUBLE_WORD = 8

# the number of registers that we need to save around malloc calls
N_REGISTERS_SAVED_BY_MALLOC = 9
# the offset from the FP where the list of the registers mentioned above starts
MY_COPY_OF_REGS = WORD
# The Address in the PC points two words befind the current instruction
PC_OFFSET = 8
FORCE_INDEX_OFS = 0






