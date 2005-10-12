from pypy.objspace.flow.model import Constant

def regalloc(insns, nregisters):
    from pypy.translator.asm.infregmachine import Instruction

    output = []
    
    for insn in insns:
        if isinstance(insn, str):
            output.append(insn)
            continue
        thismap = {}
        for i, r in enumerate(insn.registers_used()):
            if r not in thismap:
                if insn.name != 'LIA':
                    output.append(Instruction('LOADSTACK', (i+1, Constant(r))))
                    thismap[r] = i+1
                else:
                    thismap[r] = r
        output.append(insn.renumber(thismap))
        for r, i in thismap.items():
            output.append(Instruction('STORESTACK', (Constant(r), i)))
            
    return output
