
from rpython.jit.backend.aarch64.locations import (RegisterLocation,
    ZeroRegister, VFPRegisterLocation)


registers = [RegisterLocation(i) for i in range(31)]
sp = xzr = ZeroRegister()
[x0, x1, x2, x3, x4, x5, x6, x7, x8, x9, x10,
 x11, x12, x13, x14, x15, x16, x17, x18, x19, x20,
 x21, x22, x23, x24, x25, x26, x27, x28, x29, x30] = registers

vfpregisters = [VFPRegisterLocation(i) for i in range(32)]
all_vfp_regs = vfpregisters[:16]
all_regs = registers[:16] #+ [x19, x20, x21, x22]

lr = x30
fp = x29

# scratch registers that we use internally, but don't save them
# nor we use them for regalloc
ip1 = x17
ip0 = x16

callee_saved_registers = [x19, x20, x21, x22]

argument_regs = caller_resp = [x0, x1, x2, x3, x4, x5, x6, x7]
