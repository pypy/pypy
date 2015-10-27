WORD = 8 # well, we only support 64 bit
DOUBLE_WORD = 8

#
#                                                 OFFSET
#     +------------------------------+            0
#     |  gpr save are (int+float)    |
#     +------------------------------+            8
#     |  local vars                  |
#     +------------------------------+            0
#     |                              |
#     +------------------------------+
#     |                              |
#     +------------------------------+ <- SP      0         (r15)
#

GPR_STACK_SAVE_IN_BYTES = 120
STD_FRAME_SIZE_IN_BYTES = 140
THREADLOCAL_ADDR_OFFSET = 8

assert STD_FRAME_SIZE_IN_BYTES % 2 == 0
