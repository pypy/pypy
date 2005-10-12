
class Instruction(object):

    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

    def registers_used(self):
        return [a for a in self.arguments if isinstance(a, int)]

    def renumber(self, regmap):
        def _(a):
            if isinstance(a, int) and a in regmap:
                return regmap[a]
            else:
                return a
        return Instruction(self.name, map(_, self.arguments))

    def __repr__(self):
        if self.name == 'LIA':
            r, a = self.arguments
            args = 'r%s, %s'%tuple(self.arguments)
        elif self.name in ('JT', 'JF', 'J'):
            args = self.arguments[0]
        elif self.name == 'LOAD':
            args = 'r%s, #%s'%tuple(self.arguments)
        else:
            def c(x):
                if isinstance(x, int):
                    return 'r%s'%x
                else:
                    return str(x)
            args = ', '.join(map(c, self.arguments))
        return '%-30s'%('    %-10s %s'%(self.name, args),)

class Program(object):
    # approximately a list of Instructions, but with sprinkles
    # not used yet.

    def __init__(self, insns):
        self.insns = insns

    def iterinsns(self):
        for insn in self.insns:
            if isinstance(ins, str):
                continue
            yield insn

class Assembler(object):
    def __init__(self):
        self.instructions = []

    def emit(self, name, *args):
        self.instructions.append(Instruction(name, args))

    def label(self, lab):
        self.instructions.append(lab)

    def dump(self):
        for i in self.instructions:
            if isinstance(i, str):
                i += ':'
            print i
