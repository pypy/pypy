from pypy.objspace.flow.model import traverse, Block, Variable, Constant
from pypy.translator.asm.ppcgen.ppc_assembler import PPCAssembler
from pypy.translator.asm.ppcgen.func_builder import make_func

def genlinkcode(link):
    for s, t in zip(link.args, link.target.inputargs):
        print '    ', 'mr', t, s
    

def genasm(translator):

    f = translator.entrypoint

    graph = translator.getflowgraph(f)

    g = FuncGenerator(graph)
    g.gencode()
    return make_func(g.assembler, 'i', 'ii')
    

class FuncGenerator(object):

    def __init__(self, graph):
        self.graph = graph
        self.allblocks = []
        self.blocknum = {}
        def visit(block):
            if isinstance(block, Block):
                self.allblocks.append(block)
                self.blocknum[block] = len(self.blocknum)
        traverse(visit, graph)
        self._var2reg = {}
        self.next_register = 3
        for var in graph.startblock.inputargs:
            self.assign_register(var)
        self._block_counter = 0
        self.assembler = PPCAssembler()

    def assign_register(self, var):
        assert var not in self._var2reg
        self._var2reg[var] = self.next_register
        self.next_register += 1

    def reg(self, var):
        assert isinstance(var, Variable)
        if var not in self._var2reg:
            self.assign_register(var)
        return self._var2reg[var]

    def blockname(self):
        self._block_counter += 1
        return 'anonblock' + str(self._block_counter)

    def genlinkcode(self, link):
        for s, t in zip(link.args, link.target.inputargs):
            self.assembler.mr(self.reg(t), self.reg(s))
        self.assembler.b('block' + str(self.blocknum[link.target]))

    def genblockcode(self, block):
        self.assembler.label('block'+str(self.blocknum[block]))
        for op in block.operations:
            print self.reg(op.result), op, op.args
            getattr(self, op.opname)(op.result, *op.args)
        assert len(block.exits) in [0, 1, 2]
        if len(block.exits) == 2:
            assert block.exitswitch is not None
            truelink, falselink = block.exits
            b = self.blockname()
            self.assembler.cmpwi(0, self.reg(block.exitswitch), 1)
            self.assembler.bne(b)
            self.genlinkcode(truelink)
            self.assembler.label(b)
            self.genlinkcode(falselink)
        elif len(block.exits) == 1:
            self.genlinkcode(block.exits[0])
        else:
            self.assembler.mr(3, self.reg(block.inputargs[0]))
            self.assembler.blr()

    def gencode(self):
        #print map(self.reg, self.graph.startblock.inputargs)
        for block in self.allblocks:
            self.genblockcode(block)

    def int_add(self, dest, v1, v2):
        if isinstance(v1, Constant):
            self.assembler.addi(self.reg(dest), self.reg(v2), v1.value)
        elif isinstance(v2, Constant):
            self.assembler.addi(self.reg(dest), self.reg(v1), v2.value)
        else:
            self.assembler.add(self.reg(dest), self.reg(v1), self.reg(v2))

    def int_sub(self, dest, v1, v2):
        if isinstance(v1, Constant):
            self.assembler.subfi(self.reg(dest), self.reg(v2), v1.value)
        elif isinstance(v2, Constant):
            self.assembler.addi(self.reg(dest), self.reg(v1), -v2.value)
        else:
            self.assembler.sub(self.reg(dest), self.reg(v1), self.reg(v2))

    def int_gt(self, dest, v1, v2):
        conditional = 'bgt'
        if isinstance(v1, Constant):
            conditional = 'ble'
            self.assembler.cmpwi(0, self.reg(v2), v1.value)
        elif isinstance(v2, Constant):
            self.assembler.cmpwi(0, self.reg(v1), v2.value)
        else:
            self.assembler.cmpw(0, self.reg(v2), self.reg(v1))
        b = self.blockname()
        self.assembler.xor(self.reg(dest), self.reg(dest), self.reg(dest))
        getattr(self.assembler, conditional)(b)
        self.assembler.addi(self.reg(dest), self.reg(dest), 1)
        self.assembler.label(b)

    def same_as(self, dest, v1):
        self.assembler.mr(self.reg(dest), self.reg(v1))

        
