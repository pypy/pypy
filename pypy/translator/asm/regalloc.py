
def regalloc(insns, nregisters):
#    from pypy.translator.asm.infregmachine import Instruction

    maxregs = 0
    
    for insn in insns:
        if isinstance(insn, str):
            continue
        maxregs = max(insn.registers_used() + [0])

    if maxregs < 30:
        return insns[:]
    
