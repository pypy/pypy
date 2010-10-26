from pypy.jit.backend.arm.locations import RegisterLocation

registers = [RegisterLocation(i) for i in range(16)]
r0, r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12, r13, r14, r15 = registers

# aliases for registers
fp = r11
ip = r12
sp = r13
lr = r14
pc = r15

all_regs = registers[:12]

callee_resp = [r4, r5, r6, r7, r8, r9, r10, r11]
callee_saved_registers = callee_resp+[lr]
callee_restored_registers = callee_resp+[pc]
