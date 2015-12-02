WORD = 8 # well, we only support 64 bit
DOUBLE_WORD = 8

#
#                                         OFF SP |
#     +------------------------------+       160 + SP | towards 0xff
#     |  thread local addr           |                |
#     +------------------------------+       160 + SP |
#     |          ....                |                |
#     |  gpr save area (16x int,     |                |
#     |  4x float, f0, f2, f4, f6)   |                |
#     |          ....                |                |
#     +------------------------------+ <- SP   0 + SP | towards 0x0
#
#

REGISTER_AREA_BYTES = 160
THREADLOCAL_BYTES = 8
SP_BACK_CHAIN_BYTES = 8
PARAM_SAVE_AREA_BYTES = 64

# in reverse order to SP
offset = 0
REGISTER_AREA_OFFSET = offset
offset += REGISTER_AREA_BYTES
THREADLOCAL_ADDR_OFFSET = offset
offset += THREADLOCAL_BYTES
PARAM_SAVE_AREA_OFFSET = offset
offset += 0

assert offset == 168

STD_FRAME_SIZE_IN_BYTES = offset
assert offset >= 160 # at least 160 bytes!
del offset



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
