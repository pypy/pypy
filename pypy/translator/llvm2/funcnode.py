import py
from pypy.objspace.flow.model import Block, Constant, Variable, flatten, mkentrymap
from pypy.translator.llvm2.log import log 
log = log.funcnode

class FuncNode(object):
    _issetup = False 

    def __init__(self, db, func):
        self.db = db
        self.func = func
        self.ref = self.func.func_name

    def setup(self): 
        self.graph = self.db.getgraph(self.func)
        self._issetup = True

    def getdecl(self):
        assert self._issetup 
        startblock = self.graph.startblock
        returnblock = self.graph.returnblock
        inputargs = self.db.multi_getref(startblock.inputargs)
        inputargtypes = self.db.multi_gettyperef(startblock.inputargs)
        returntype = self.db.gettyperef(self.graph.returnblock.inputargs[0])
        result = "%s %%%s" % (returntype, self.ref)
        args = ["%s %s" % item for item in zip(inputargtypes, inputargs)]
        result += "(%s)" % ", ".join(args)
        return result 

    def writedecl(self, codewriter): 
        codewriter.declare(self.getdecl())

    def writeimpl(self, codewriter):
        assert self._issetup 
        graph = self.graph
        log.writeimpl(graph.name)
        codewriter.openfunc(self.getdecl())
        nextblock = graph.startblock
        args = graph.startblock.inputargs 
        l = [x for x in flatten(graph) if isinstance(x, Block)]
        self.block_to_name = {}
        for i, block in enumerate(l):
            self.block_to_name[block] = "block%s" % i
        for block in l:
            codewriter.label(self.block_to_name[block])
            for name in 'startblock returnblock exceptblock'.split():
                if block is getattr(graph, name):
                    getattr(self, 'write_' + name)(codewriter, block)
                    break
            else:
                self.write_block(codewriter, block)
        codewriter.closefunc()

    def write_block(self, codewriter, block):
        self.write_block_phi_nodes(codewriter, block)
        self.write_block_operations(codewriter, block)
        self.write_block_branches(codewriter, block)


    def write_block_phi_nodes(self, codewriter, block):
        entrylinks = mkentrymap(self.graph)[block]
        entrylinks = [x for x in entrylinks if x.prevblock is not None]
        inputargs = self.db.multi_getref(block.inputargs)
        inputargtypes = self.db.multi_gettyperef(block.inputargs)
        for i, (arg, type_) in enumerate(zip(inputargs, inputargtypes)):
            names = self.db.multi_getref([link.args[i] for link in entrylinks])
            blocknames = [self.block_to_name[link.prevblock]
                              for link in entrylinks]
            codewriter.phi(arg, type_, names, blocknames) 

    def write_block_branches(self, codewriter, block):
        if len(block.exits) == 1:
            codewriter.br_uncond(self.block_to_name[block.exits[0].target])
        elif len(block.exits) == 2:
            switch = self.db.getref(block.exitswitch)
            codewriter.br(switch, self.block_to_name[block.exits[0].target],
                          self.block_to_name[block.exits[1].target])

    def write_block_operations(self, codewriter, block):
        opwriter = OpWriter(self.db, codewriter)
        for op in block.operations:
            meth = getattr(opwriter, op.opname, None)
            assert meth is not None, "operation %r not found" %(op.opname,)
            meth(op)
                

    def write_startblock(self, codewriter, block):
        self.write_block_operations(codewriter, block)
        self.write_block_branches(codewriter, block)

    def write_returnblock(self, codewriter, block):
        assert len(block.inputargs) == 1
        self.write_block_phi_nodes(codewriter, block)
        inputargtype = self.db.gettyperef(block.inputargs[0])
        inputarg = self.db.getref(block.inputargs[0])
        codewriter.ret(inputargtype, inputarg)

class OpWriter(object):
    def __init__(self, db, codewriter):
        self.db = db
        self.codewriter = codewriter

    def binaryop(self, name, op):
        assert len(op.args) == 2
        self.codewriter.binaryop(name,
                                 self.db.getref(op.result),
                                 self.db.gettyperef(op.result),
                                 self.db.getref(op.args[0]),
                                 self.db.getref(op.args[1]))
    def int_mul(self, op):
        self.binaryop('mul', op)

    def int_floordiv(self, op):
        self.binaryop('div', op)

    def int_add(self, op):
        self.binaryop('add', op)

    def int_sub(self, op):
        self.binaryop('sub', op)
        
