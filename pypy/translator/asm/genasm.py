import sys, os
from pypy.objspace.flow.model import Variable, Constant
#from pypy.translator.asm import infregmachine
from pypy.rpython.lltypesystem.lltype import Signed
from pypy.translator.asm.simulator import Machine, TranslateProgram
from pypy.translator.asm.model import *

#Available Machine code targets (processor+operating system)
TARGET_UNKNOWN=0
TARGET_PPC=1
TARGET_WIN386=2

# def determine_target():
#     if sys.platform == 'darwin':
#         if os.uname()[-1] == 'Power Macintosh':
#             return TARGET_PPC
#     elif sys.platform == 'win32':
#         if 'Intel' in sys.version:
#             return TARGET_WIN386
#     else:
#         return TARGET_UNKNOWN
#
# ASM_TARGET = determine_target()


def genasm(translator, processor):

    f = translator.entrypoint

    graph = translator.getflowgraph(f)

    retvar = graph.returnblock.inputargs[0]

    assert retvar.concretetype is Signed

    for v in graph.startblock.inputargs:
        assert v.concretetype is Signed

    g = FuncGenerator(graph)
    g.gencode()

    if processor == 'virt':
        machine = Machine(g.insns)
        def r(*args):
            return machine.execute(*args)

        return r
    elif processor == 'virtfinite':
        insns = TranslateProgram(g.insns, 50)
        for i in insns:
            print i
        def r(*args):
            return Machine.RunProgram(insns,
                                      args)

        return r
    elif processor == 'ppc':
        from pypy.translator.asm.ppc import codegen
        return codegen.make_native_code(graph, g.insns)

class FuncGenerator(object):

    def __init__(self, graph):
        self.graph = graph
        self.allblocks = []
        self.blocknum = {}

        self._var2reg = {}
        self.next_register = 1

        for block in graph.iterblocks():
            self.allblocks.append(block)
            self.blocknum[block] = len(self.blocknum)

        self._block_counter = 0
        self.insns = []

        for i, var in enumerate(graph.startblock.inputargs):
            self.insns.append(LOAD_ARGUMENT(self.reg(var), i))

    def assign_register(self, var):
        assert var not in self._var2reg
        self._var2reg[var.name] = self.next_register
        self.next_register += 1

    def emit(self, *args):
        self.assembler.emit(*args)

    def reg(self, var):
        if isinstance(var, Constant):
            r = self.next_register
            assert isinstance(var.value, int)
            self.insns.append(LOAD_IMMEDIATE(r, var.value))
            self.next_register += 1
            return r
        elif isinstance(var, Variable):
            if var.name not in self._var2reg:
                self.assign_register(var)
            return self._var2reg[var.name]
        else:
            assert False, "reg of non-Variable, non-Constant!?"

    def blockname(self):
        self._block_counter += 1
        return 'anonblock' + str(self._block_counter)

    def blocktarget(self, block):
        return 'block' + str(self.blocknum[block])

    def genlinkcode(self, link):
        for s, t in zip(link.args, link.target.inputargs):
            if isinstance(s, Constant) or s.name != t.name:
                self.insns.append(MOVE(self.reg(t), self.reg(s)))
        self.insns.append(JUMP(self.blocktarget(link.target)))

    def genblockcode(self, block):
        self.insns.append(Label(self.blocktarget(block)))

        assert len(block.exits) in [0, 1, 2]

        for op in block.operations:
            self.insns.append(LLInstruction(
                op.opname, self.reg(op.result), *map(self.reg, op.args)))

        if len(block.exits) == 2:
            assert block.exitswitch is not None
            falselink, truelink = block.exits
            assert truelink.exitcase == True
            assert falselink.exitcase == False

            b = self.blockname()
            self.insns.append(JUMP_IF_TRUE(self.reg(block.exitswitch), b))
            self.genlinkcode(falselink)

            self.insns.append(Label(b))
            self.genlinkcode(truelink)
            
        elif len(block.exits) == 1:
            self.genlinkcode(block.exits[0])
        else:
            assert len(block.inputargs) == 1
            self.insns.append(RETPYTHON(self.reg(block.inputargs[0])))

    def gencode(self):
        for block in self.allblocks:
            self.genblockcode(block)
