import py
from pypy.objspace.flow.model import Block, Constant, Variable, Link
from pypy.objspace.flow.model import flatten, mkentrymap, traverse
from pypy.rpython import lltype
from pypy.translator.backendoptimization import remove_same_as 
from pypy.translator.unsimplify import remove_double_links                     
from pypy.translator.llvm2.node import LLVMNode, ConstantLLVMNode
from pypy.translator.llvm2.opwriter import OpWriter
from pypy.translator.llvm2.atomic import is_atomic
from pypy.translator.llvm2.log import log 
from pypy.rpython.extfunctable import table as extfunctable
nextnum = py.std.itertools.count().next
log = log.funcnode

class FuncTypeNode(LLVMNode):
    def __init__(self, db, type_):
        self.db = db
        assert isinstance(type_, lltype.FuncType)
        self.type_ = type_
        # XXX Make simplier for now, it is far too hard to read otherwise
        #self.ref = 'ft.%s.%s' % (type_, nextnum())
        self.ref = '%%ft.%s' % (nextnum(),)
        
    def __str__(self):
        return "<FuncTypeNode %r>" % self.ref

    def setup(self):
        self.db.prepare_repr_arg_type(self.type_.RESULT)
        self.db.prepare_repr_arg_type_multi(self.type_._trueargs())

    def writedatatypedecl(self, codewriter):
        returntype = self.db.repr_arg_type(self.type_.RESULT)
        inputargtypes = self.db.repr_arg_type_multi(self.type_._trueargs())
        codewriter.funcdef(self.ref, returntype, inputargtypes)
                
class FuncNode(ConstantLLVMNode):
    _issetup = False 

    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.ref = "%" + value._name
        self.graph = value.graph 
        remove_same_as(self.graph) 
        remove_double_links(self.db._translator, self.graph) 

    def __str__(self):
        return "<FuncNode %r>" %(self.ref,)
    
    def setup(self):
        log("setup", self)
        def visit(node):
            if isinstance(node, Link):
                map(self.db.prepare_arg, node.args)
            elif isinstance(node, Block):
                map(self.db.prepare_arg, node.inputargs)
                for op in node.operations:
                    map(self.db.prepare_arg, op.args)
                    self.db.prepare_arg(op.result)
        assert self.graph, "cannot traverse"
        traverse(visit, self.graph)
        self._issetup = True

    # ______________________________________________________________________
    # main entry points from genllvm 
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

    # ______________________________________________________________________
    # writing helpers for entry points

    def getdecl(self):
        assert self._issetup 
        startblock = self.graph.startblock
        returnblock = self.graph.returnblock
        inputargs = self.db.repr_arg_multi(startblock.inputargs)
        inputargtypes = self.db.repr_arg_type_multi(startblock.inputargs)
        returntype = self.db.repr_arg_type(self.graph.returnblock.inputargs[0])
        result = "%s %s" % (returntype, self.ref)
        args = ["%s %s" % item for item in zip(inputargtypes, inputargs)]
        result += "(%s)" % ", ".join(args)
        return result 

    def write_block(self, codewriter, block):
        self.write_block_phi_nodes(codewriter, block)
        self.write_block_operations(codewriter, block)
        self.write_block_branches(codewriter, block)


    def write_block_phi_nodes(self, codewriter, block):
        entrylinks = mkentrymap(self.graph)[block]
        entrylinks = [x for x in entrylinks if x.prevblock is not None]
        inputargs = self.db.repr_arg_multi(block.inputargs)
        inputargtypes = self.db.repr_arg_type_multi(block.inputargs)
        for i, (arg, type_) in enumerate(zip(inputargs, inputargtypes)):
            names = self.db.repr_arg_multi([link.args[i] for link in entrylinks])
            blocknames = [self.block_to_name[link.prevblock]
                              for link in entrylinks]
            if type_ != "void":
                codewriter.phi(arg, type_, names, blocknames) 

    def write_block_branches(self, codewriter, block):
        if len(block.exits) == 1:
            codewriter.br_uncond(self.block_to_name[block.exits[0].target])
        elif len(block.exits) == 2:
            switch = self.db.repr_arg(block.exitswitch)
            codewriter.br(switch, self.block_to_name[block.exits[0].target],
                          self.block_to_name[block.exits[1].target])

    def write_block_operations(self, codewriter, block):
        opwriter = OpWriter(self.db, codewriter)
        for op in block.operations:
            codewriter.comment(str(op), indent=True)
            opwriter.write_operation(op)
    def write_startblock(self, codewriter, block):
        self.write_block_operations(codewriter, block)
        self.write_block_branches(codewriter, block)

    def write_returnblock(self, codewriter, block):
        assert len(block.inputargs) == 1
        self.write_block_phi_nodes(codewriter, block)
        inputargtype = self.db.repr_arg_type(block.inputargs[0])
        inputarg = self.db.repr_arg(block.inputargs[0])
        if inputargtype != "void":
            codewriter.ret(inputargtype, inputarg)
        else:
            codewriter.ret_void()

    def write_exceptblock(self, codewriter, block):
        codewriter.unwind()
