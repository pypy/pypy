import py
from pypy.translator.llvm2 import llvmbc
from pypy.rpython import lltype
from pypy.objspace.flow.model import Block, Constant, Variable, flatten, mkentrymap


PRIMITIVES_TO_LLVM = {lltype.Signed: "int"}

log = py.log.Producer('genllvm') 

class FunctionCodeGenerator(object):
    def __init__(self, graph, func):
        self.graph = graph
        self.func = func

    def declaration(self):
        returntype = self.getllvmname(self.graph.returnblock.inputargs[0])
        argtypes = self.getllvmtypes(self.graph.startblock.inputargs)
        funcname = "%" + self.func.func_name
   # XXX varnames
        result = "%s %s(%s)" % (returntype, funcname,
                                ", ".join(argtypes))
        return result

    def implementation(self):
        graph = self.graph
        log.gen("starting", graph.name)
        nextblock = graph.startblock
        args = graph.startblock.inputargs 
        l = [x for x in flatten(graph) if isinstance(x, Block)]
        self.block_to_name = {}
        for i, block in enumerate(l):
            self.block_to_name[block] = "block%s" % i
        for block in l: 
            for line in self.gen_block(block): 
                yield line 

    def gen_block(self, block):
        inputargs = self.getllvmnames(block.inputargs)
        inputargtypes = self.getllvmtypes(block.inputargs)
        yield self.block_to_name[block] + ":"
        entrylinks = mkentrymap(self.graph)[block]
        for i, (arg, type_) in enumerate(zip(inputargs, inputargtypes)):
            line = [arg, " = phi ", type_]
            for link in entrylinks:
                line.append(" [%s, %%%s]" % (self.getllvmname(link.args[i]),
                                            self.block_to_name[link.prevblock]))
            yield "".join(line)
        if block is self.graph.returnblock: 
            assert len(inputargs) == 1
            yield "ret %s %s" % (inputargtypes[0], inputargs[0])
        else:
            #operations
            #branches
            assert len(block.exits) == 1
            yield "br label %%%s" % self.block_to_name[block.exits[0].target] 

    def getllvmname(self, arg):
        if isinstance(arg, Constant):
            return str(arg.value).lower() #False --> false
        elif isinstance(arg, Variable):
            return "%" + str(arg)
        else:
            raise TypeError, arg

    def getllvmtype(self, arg):
        log.type(arg)
        return PRIMITIVES_TO_LLVM[arg.concretetype]

    def getllvmnames(self, args):
        return [self.getllvmname(arg) for arg in args]

    def getllvmtypes(self, args):
        return [self.getllvmtype(arg) for arg in args]

py.log.setconsumer('genllvm', None)

