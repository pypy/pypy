import py
import sys
from pypy.objspace.flow.model import Block, Constant, Variable, Link
from pypy.objspace.flow.model import flatten, mkentrymap, traverse, last_exception
from pypy.rpython import lltype
from pypy.translator.js.node import LLVMNode, ConstantLLVMNode
from pypy.translator.js.opwriter import OpWriter
from pypy.translator.js.log import log 
log = log.funcnode


class FuncNode(ConstantLLVMNode):
    __slots__ = "db value ref graph blockindex".split()

    def __init__(self, db, value):
        self.db = db
        self.value = value
        pypy_prefix     = '' #pypy_
        self.ref   = self.make_ref(pypy_prefix, value.graph.name)
        self.graph = value.graph

    def __str__(self):
        return "<FuncNode %r>" %(self.ref,)
    
    def setup(self):
        #log("setup", self)
        def visit(node):
            if isinstance(node, Link):
                map(self.db.prepare_arg, node.args)
            elif isinstance(node, Block):
                block = node
                map(self.db.prepare_arg, block.inputargs)
                for op in block.operations:
                    map(self.db.prepare_arg, op.args)
                    self.db.prepare_arg(op.result)
                    if block.exitswitch != Constant(last_exception):
                        continue
                    for link in block.exits[1:]:
                        self.db.prepare_constant(lltype.typeOf(link.llexitcase),
                                                 link.llexitcase)
                                            
        assert self.graph, "cannot traverse"
        traverse(visit, self.graph)

    def writeimpl(self, codewriter):
        graph = self.graph
        log.writeimpl(graph.name)
        nextblock = graph.startblock
        args = graph.startblock.inputargs 
        blocks = [x for x in flatten(graph) if isinstance(x, Block)]
        self.blockindex= {}
        for i, block in enumerate(blocks):
            self.blockindex[block] = i
        codewriter.openfunc(self.getdecl(), self, blocks)
        for block in blocks:
            codewriter.openblock(self.blockindex[block])
            for name in 'startblock returnblock exceptblock'.split():
                if block is getattr(graph, name):
                    getattr(self, 'write_' + name)(codewriter, block)
                    break
            else:
                self.write_block(codewriter, block)
            codewriter.closeblock()
        codewriter.closefunc()

    # ______________________________________________________________________
    # writing helpers for entry points

    def getdecl(self):
        startblock = self.graph.startblock
        returnblock = self.graph.returnblock
        startblock_inputargs = [a for a in startblock.inputargs
                                if a.concretetype is not lltype.Void]

        inputargs = self.db.repr_arg_multi(startblock_inputargs)
        return self.ref + "(%s)" % ", ".join(inputargs)

    def write_block(self, codewriter, block):
        self.write_block_operations(codewriter, block)
        self.write_block_branches(codewriter, block)

    def write_block_branches(self, codewriter, block):
        if block.exitswitch == Constant(last_exception):
            #codewriter.comment('FuncNode(ConstantLLVMNode) *last_exception* write_block_branches @%s@' % str(block.exits))
            return
        if len(block.exits) == 1:
            codewriter.br_uncond(self.blockindex[block.exits[0].target], block.exits[0])
        elif len(block.exits) == 2:
            cond = self.db.repr_arg(block.exitswitch)
            codewriter.br(cond,
                          self.blockindex[block.exits[0].target], block.exits[0],
                          self.blockindex[block.exits[1].target], block.exits[1])

    def write_block_operations(self, codewriter, block):
        opwriter = OpWriter(self.db, codewriter, self, block)
        if block.exitswitch == Constant(last_exception):
            last_op_index = len(block.operations) - 1
        else:
            last_op_index = None
        for op_index, op in enumerate(block.operations):
            if op_index == last_op_index:
                #could raise an exception and should therefor have a function
                #implementation that can be invoked by the llvm-code.
                invoke_prefix = 'invoke:'
                assert not op.opname.startswith(invoke_prefix)
                op.opname = invoke_prefix + op.opname
            opwriter.write_operation(op)

    def write_startblock(self, codewriter, block):
        self.write_block_operations(codewriter, block)
        self.write_block_branches(codewriter, block)

    def write_returnblock(self, codewriter, block):
        assert len(block.inputargs) == 1
        # #self.write_block_phi_nodes(codewriter, block)
        # inputargtype = self.db.repr_arg_type(block.inputargs[0])
        # inputarg = self.db.repr_arg(block.inputargs[0])
        # codewriter.ret(inputargtype, inputarg)
        codewriter.ret( self.db.repr_arg(block.inputargs[0]) )

    def write_exceptblock(self, codewriter, block):
        #self.db.genllvm.exceptionpolicy.write_exceptblock(self, codewriter, block)
        codewriter.comment('XXX TODO write_exceptblock')
        codewriter.append('throw "Pypy exception"')
        codewriter.skip_closeblock()
