import sys
from pypy.objspace.flow.model import traverse, Block, Variable, Constant


#Available Machine code targets (processor+operating system)
TARGET_PPC=1
TARGET_WIN386=2

#set one of these
ASM_TARGET=TARGET_PPC
#ASM_TARGET=TARGET_WIN386


if ASM_TARGET==TARGET_PPC:
    from pypy.translator.asm.ppcgen.ppc_assembler import PPCAssembler
    from pypy.translator.asm.ppcgen.func_builder import make_func
elif ASM_TARGET==TARGET_WIN386:
    from pypy.translator.asm.i386gen.i386_assembler import i386Assembler as PPCAssembler  #spoof system for time being
    from pypy.translator.asm.i386gen.i386_assembler import make_func
else:
    raise Exception,'Unknown Machine-code target specified.  Set ASM_TARGET=TARGET_XXXX  '


def genlinkcode(link):
    for s, t in zip(link.args, link.target.inputargs):
        print '    ', 'mr', t, s


def genasm(translator):

    f = translator.entrypoint

    graph = translator.getflowgraph(f)

    g = FuncGenerator(graph)
    g.gencode()
    if ASM_TARGET==TARGET_WIN386:
        g.assembler.dump()
    return make_func(g.assembler, 'i', 'ii')


class FuncGenerator(object):

    def __init__(self, graph):
        self.graph = graph
        self.allblocks = []
        self.blocknum = {}

##         origins = {}
##         lastuse = {}

##         opindex = 0

        for block in graph.iterblocks():
            self.allblocks.append(block)
            self.blocknum[block] = len(self.blocknum)


##             for arg in block.inputargs:
##                 if op.result.name not in origins:
##                     origins[op.result.name] = opindex

##             for op in blocks:
##                 origins[op.result.name] = opindex
##                 for arg in op.args:
##                     if isinstance(arg, Variable):
##                         lastuse[arg.name] = opindex
##                 opindex += 1

##         liveranges = []

##         for n in origins:
##             if n not in lastuse:
##                 continue
##             liveranges.append((lastuse[n], origins[n], n))

        self._var2reg = {}
        self.next_register = 3
        for var in graph.startblock.inputargs:
            self.assign_register(var)

        self._block_counter = 0
        self.assembler = PPCAssembler()

    def assign_register(self, var):
        assert var not in self._var2reg
        self._var2reg[var.name] = self.next_register
        self.next_register += 1

    def reg(self, var):
        assert isinstance(var, Variable)
        if var.name not in self._var2reg:
            self.assign_register(var)
        return self._var2reg[var.name]

    def blockname(self):
        self._block_counter += 1
        return 'anonblock' + str(self._block_counter)

    def genlinkcode(self, link):
        A = self.assembler
        for s, t in zip(link.args, link.target.inputargs):
            if s.name != t.name:
                A.mr(self.reg(t), self.reg(s))
        A.b('block' + str(self.blocknum[link.target]))

    def genblockcode(self, block):
        A = self.assembler
        A.label('block'+str(self.blocknum[block]))
        for op in block.operations:
            getattr(self, op.opname)(op.result, *op.args)
        assert len(block.exits) in [0, 1, 2]
        if len(block.exits) == 2:
            assert block.exitswitch is not None
            truelink, falselink = block.exits
            b = self.blockname()
            A.cmpwi(0, self.reg(block.exitswitch), 1)
            A.bne(b)
            self.genlinkcode(truelink)
            A.label(b)
            self.genlinkcode(falselink)
        elif len(block.exits) == 1:
            self.genlinkcode(block.exits[0])
        else:
            A.mr(3, self.reg(block.inputargs[0]))
            A.blr()

    def gencode(self):
        #print map(self.reg, self.graph.startblock.inputargs)
        for block in self.allblocks:
            self.genblockcode(block)


    def int_add(self, dest, v1, v2):
        A = self.assembler
        if isinstance(v1, Constant):
            A.addi(self.reg(dest), self.reg(v2), v1.value)
        elif isinstance(v2, Constant):
            A.addi(self.reg(dest), self.reg(v1), v2.value)
        else:
            A.add(self.reg(dest), self.reg(v1), self.reg(v2))

    def int_sub(self, dest, v1, v2):
        A = self.assembler
        if isinstance(v1, Constant):
            A.subfi(self.reg(dest), self.reg(v2), v1.value)
        elif isinstance(v2, Constant):
            A.addi(self.reg(dest), self.reg(v1), -v2.value)
        else:
            A.sub(self.reg(dest), self.reg(v1), self.reg(v2))

    def int_gt(self, dest, v1, v2):
        A = self.assembler
        conditional = 'bgt'
        if isinstance(v1, Constant):
            conditional = 'ble'
            A.cmpwi(0, self.reg(v2), v1.value)
        elif isinstance(v2, Constant):
            A.cmpwi(0, self.reg(v1), v2.value)
        else:
            A.cmpw(0, self.reg(v2), self.reg(v1))
        b = self.blockname()
        A.xor(self.reg(dest), self.reg(dest), self.reg(dest))
        getattr(self.assembler, conditional)(b)
        A.addi(self.reg(dest), self.reg(dest), 1)
        A.label(b)

    def same_as(self, dest, v1):
        self.assembler.mr(self.reg(dest), self.reg(v1))


