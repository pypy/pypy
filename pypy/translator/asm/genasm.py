import sys, os
from pypy.objspace.flow.model import traverse, Block, Variable, Constant
from pypy.translator.asm import infregmachine
from pypy.rpython.lltype import Signed
from pypy.translator.asm.simulator import Machine, TranslateProgram

# #Available Machine code targets (processor+operating system)
# TARGET_UNKNOWN=0
# TARGET_PPC=1
# TARGET_WIN386=2

# #set one of these
# ASM_TARGET=TARGET_UNKNOWN
# #ASM_TARGET=TARGET_WIN386

# def determine_target():
#     global ASM_TARGET
#     if sys.platform == 'darwin':
#         if os.uname()[-1] == 'Power Macintosh':
#             ASM_TARGET = TARGET_PPC
#     elif sys.platform == 'win32':
#         if 'Intel' in sys.version:
#             ASM_TARGET = TARGET_WIN386

# determine_target()
# if ASM_TARGET == TARGET_UNKNOWN:
#     raise Exception, 'Unknown Machine-code target specified.'

# if ASM_TARGET==TARGET_PPC:
#     from pypy.translator.asm.ppcgen.ppc_assembler import PPCAssembler
#     from pypy.translator.asm.ppcgen.func_builder import make_func
# elif ASM_TARGET==TARGET_WIN386:
#     from pypy.translator.asm.i386gen.i386_assembler import i386Assembler as PPCAssembler  #spoof system for time being
#     from pypy.translator.asm.i386gen.i386_assembler import make_func


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
        def r(*args):
            return Machine.RunProgram(g.assembler.instructions,
                                      args,
                                      tracing=True)

        return r
    elif processor == 'virtfinite':
        insns = TranslateProgram(g.assembler.instructions, 50)
        for i in insns:
            print i
        def r(*args):
            return Machine.RunProgram(insns,
                                      args,
                                      tracing=True)

        return r
    elif processor == 'ppc':
        from pypy.translator.asm.ppc import codegen
        return codegen.make_native_code(graph, g.assembler.instructions)

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
        self.assembler = infregmachine.Assembler()

        for i, var in enumerate(graph.startblock.inputargs):
            self.emit('LIA', self.reg(var), Constant(i))

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
            self.assembler.emit("LOAD", r, var)
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
        A = self.assembler
        for s, t in zip(link.args, link.target.inputargs):
            if isinstance(s, Constant) or s.name != t.name:
                A.emit('MOV', self.reg(t), self.reg(s))
        A.emit('J', self.blocktarget(link.target))

    def genblockcode(self, block):
        A = self.assembler
        A.label(self.blocktarget(block))

        assert len(block.exits) in [0, 1, 2]

        ordinaryops = block.operations[:]
        if len(block.exits) == 2:
            assert block.exitswitch is not None
            assert block.operations[-1].result is block.exitswitch
            del ordinaryops[-1]

        for op in ordinaryops:
            A.emit(op.opname, self.reg(op.result), *map(self.reg, op.args))

        if len(block.exits) == 2:
            assert block.exitswitch is not None
            falselink, truelink = block.exits
            lastop = block.operations[-1]
            assert lastop.opname in ['int_gt', 'int_lt', 'int_ge',
                                     'int_eq', 'int_le', 'int_ne']
            A.emit(lastop.opname, *map(self.reg, lastop.args))
            b = self.blockname()
            A.emit('JT', b)
            self.genlinkcode(falselink)
            A.label(b)
            self.genlinkcode(truelink)
        elif len(block.exits) == 1:
            self.genlinkcode(block.exits[0])
        else:
            assert len(block.inputargs) == 1
            A.emit('RETPYTHON', self.reg(block.inputargs[0]))

    def gencode(self):
        for block in self.allblocks:
            self.genblockcode(block)
