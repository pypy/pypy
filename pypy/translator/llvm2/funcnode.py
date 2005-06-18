import py
from pypy.rpython import lltype
from pypy.objspace.flow.model import Block, Constant, Variable, flatten, mkentrymap
from pypy.translator.llvm2.log import log 
log = log.funcnode

PRIMITIVES_TO_LLVM = {lltype.Signed: "int"}

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
        inputargs = self.getllvmnames(startblock.inputargs)
        inputargtypes = self.getllvmtypes(startblock.inputargs)
        returntype = self.getllvmtype(self.graph.returnblock.inputargs[0])
        result = "%s %%%s" % (returntype, self.ref)
        args = ["%s %s" % item for item in zip(inputargs, inputargtypes)]
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
            self.write_block(codewriter, block)
        codewriter.closefunc() 

    def write_block(self, codewriter, block):
        inputargs = self.getllvmnames(block.inputargs)
        inputargtypes = self.getllvmtypes(block.inputargs)
        codewriter.label(self.block_to_name[block]) 
        entrylinks = mkentrymap(self.graph)[block]
        for i, (arg, type_) in enumerate(zip(inputargs, inputargtypes)):
            names = self.getllvmnames([link.args[i] for link in entrylinks])
            blocknames = [self.block_to_name[link.prevblock] for link in entrylinks]
            codewriter.phi(arg, type_, names, blocknames) 
        if block is self.graph.returnblock: 
            assert len(inputargs) == 1
            codewriter.ret(inputargtypes[0], inputargs[0])
        else:
            #operations
            #branches
            assert len(block.exits) == 1
            codewriter.br_uncond(self.block_to_name[block.exits[0].target])

    def getllvmname(self, arg):
        if isinstance(arg, Constant):
            return str(arg.value).lower() #False --> false
        elif isinstance(arg, Variable):
            return "%" + str(arg)
        else:
            raise TypeError, arg

    def getllvmtype(self, arg):
        return PRIMITIVES_TO_LLVM[arg.concretetype]

    def getllvmnames(self, args):
        return [self.getllvmname(arg) for arg in args]

    def getllvmtypes(self, args):
        return [self.getllvmtype(arg) for arg in args]
