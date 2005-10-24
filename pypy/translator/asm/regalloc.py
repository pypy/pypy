from pypy.translator.asm.model import *

def regalloc(insns, nregisters):
    output = []

    for insn in insns:
        thismap = {}
        i = 1
        target = insn.target_register()
        if target is not None:
            if not isinstance(insn, LOAD_ARGUMENT):
                thismap[target] = i
                i += 1
            else:
                thismap[target] = target

        for r in insn.source_registers():
            if r not in thismap:
                output.append(LOAD_STACK(i+1, r))
                thismap[r] = i+1
                i += 1

        output.append(insn.renumber(thismap))

        if target is not None:
            output.append(STORE_STACK(target, thismap[target]))

    return output
