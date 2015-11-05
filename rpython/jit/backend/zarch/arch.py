WORD = 8 # well, we only support 64 bit
DOUBLE_WORD = 8

#
#                                                 OFFSET
#     +------------------------------+            0
#     |  gpr save are (int+float)    |
#     +------------------------------+            GPR_STACK_SAVE_IN_BYTES | 120
#     |  last base pointer           |
#     +------------------------------+            BSP_STACK_OFFSET        | 128
#     |                              |
#     +------------------------------+
#     |                              |
#     +------------------------------+                                    | 140
#
#

GPR_STACK_SAVE_IN_BYTES = 120
STD_FRAME_SIZE_IN_BYTES = 140
THREADLOCAL_ADDR_OFFSET = 8

assert STD_FRAME_SIZE_IN_BYTES % 2 == 0



#
#     +------------------------------+ <- assembler begin
#     |  SAVE CONTEXT                |
#     +------------------------------+
# +--+|  BRANCH (saves addr of pool  |
# |   |  in r13)                     |
# |   +------------------------------+
# |   |  ...                         |
# |   |  LITERAL POOL                | <---+
# |   |  ...                         | <-+ |
# +-->+------------------------------+   | |
#     |  ...                         | +-|-+
#     |  CODE                        |   |
#     |  ...                         |   |
# +--+|  Guard X                     |   |
# |   |  ...                         |   |
# |   +------------------------------+   |
# |   |  ...                         | +-+
# |   |  RECOVERY                    |
# +-->|  ...                         |
#     +------------------------------+
#
#     A recovery entry looks like this:
#
#     +------------------------------+
#     | LOAD POOL (r0, guard_offset +|
#     | RECOVERY_TARGET_OFFSET)      |
#     +------------------------------+
#     | LOAD POOL (r2, guard_offset +|  parameter 0
#     | RECOVERY_GCMAP_OFFSET)       |
#     +------------------------------+
#     | LOAD IMM (r3, fail_descr)    |  parameter 1
#     +------------------------------+
#     | BRANCH TO r0                 |
#     +------------------------------+
#    

RECOVERY_TARGET_POOL_OFFSET = 0
RECOVERY_GCMAP_POOL_OFFSET = 8

JUMPABS_TARGET_ADDR__POOL_OFFSET = 0
JUMPABS_POOL_ADDR_POOL_OFFSET = 8
