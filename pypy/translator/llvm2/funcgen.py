import py
from pypy.translator.llvm2 import llvmbc
from pypy.rpython import lltype
from pypy.objspace.flow.model import Block, Constant, Variable, flatten, mkentrymap


PRIMITIVES_TO_LLVM = {lltype.Signed: "int"}
PRIMITIVES_TO_C = {lltype.Signed: "int"}

log = py.log.Producer('genllvm') 

class FunctionCodeGenerator(object):
    def __init__(self, graph, func):
        self.graph = graph
        self.func = func
        self.funcname = self.func.func_name

    def declaration(self):
        startblock = self.graph.startblock
        returnblock = self.graph.returnblock
        inputargs = self.getllvmnames(startblock.inputargs)
        inputargtypes = self.getllvmtypes(startblock.inputargs)
        returntype = self.getllvmtype(self.graph.returnblock.inputargs[0])
        result = "%s %%%s" % (returntype, self.funcname)
        args = ["%s %s" % item for item in zip(inputargs, inputargtypes)]
        result += "(%s)" % ", ".join(args)
        return result

    def c_declaration(self):
        returntype = PRIMITIVES_TO_C[
            self.graph.returnblock.inputargs[0].concretetype]
        inputargtypes = [PRIMITIVES_TO_C[arg.concretetype]
                             for arg in self.graph.startblock.inputargs]
        result = "%s %s(%s)" % (returntype, self.funcname,
                                ", ".join(inputargtypes))
        return result

    def pyrex_wrapper(self):
        inputargs = self.getllvmnames(self.graph.startblock.inputargs)
        yield "cdef extern " + self.c_declaration()
        yield "def %s_wrapper(%s):" % (self.funcname, ", ".join(inputargs))
        yield "    return %s(%s)" % (self.funcname, ", ".join(inputargs))

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

