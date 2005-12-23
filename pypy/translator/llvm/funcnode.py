from pypy.objspace.flow.model import Block, Constant, Link
from pypy.objspace.flow.model import mkentrymap, traverse, c_last_exception
from pypy.rpython.lltypesystem import lltype
from pypy.translator.llvm.node import LLVMNode, ConstantLLVMNode
from pypy.translator.llvm.opwriter import OpWriter
from pypy.translator.llvm.log import log 
from pypy.translator.llvm.backendopt.removeexcmallocs import remove_exception_mallocs
from pypy.translator.unsimplify import remove_double_links
log = log.funcnode

class FuncTypeNode(LLVMNode):
    __slots__ = "db type_ ref".split()
    
    def __init__(self, db, type_):
        self.db = db
        assert isinstance(type_, lltype.FuncType)
        self.type_ = type_
        self.ref = self.make_ref('%functiontype', '')

    def __str__(self):
        return "<FuncTypeNode %r>" % self.ref

    def setup(self):
        self.db.prepare_type(self.type_.RESULT)
        self.db.prepare_type_multi(self.type_._trueargs())

    def writedatatypedecl(self, codewriter):
        returntype = self.db.repr_type(self.type_.RESULT)
        inputargtypes = [self.db.repr_type(a) for a in self.type_._trueargs()]
        codewriter.funcdef(self.ref, returntype, inputargtypes)

class BranchException(Exception):
    pass

class FuncNode(ConstantLLVMNode):
    __slots__ = "db value ref graph block_to_name".split()

    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.ref   = self.make_ref('%pypy_', value.graph.name)
        self.graph = value.graph

        self.db.exceptionpolicy.transform(self.db.translator,
                                          self.graph)

        remove_exception_mallocs(self.db.translator, self.graph, self.ref)

        #XXX experimental
        #from pypy.translator.llvm.backendopt.mergemallocs import merge_mallocs
        #merge_mallocs(self.db.translator, self.graph, self.ref)

        remove_double_links(self.db.translator, self.graph)

    def __str__(self):
        return "<FuncNode %r>" %(self.ref,)
    
    def setup(self):
        def visit(node):
            if isinstance(node, Link):
                map(self.db.prepare_arg, node.args)
            elif isinstance(node, Block):
                block = node
                map(self.db.prepare_arg, block.inputargs)
                for op in block.operations:
                    map(self.db.prepare_arg, op.args)
                    self.db.prepare_arg(op.result)
                    if block.exitswitch != c_last_exception:
                        continue
                    for link in block.exits[1:]:
                        type_ = lltype.typeOf(link.llexitcase)
                        self.db.prepare_constant(type_, link.llexitcase)
                                            
        assert self.graph, "cannot traverse"
        traverse(visit, self.graph)

    # ______________________________________________________________________
    # main entry points from genllvm 
    def writedecl(self, codewriter): 
        codewriter.declare(self.getdecl())

    def writeimpl(self, codewriter):
        graph = self.graph
        log.writeimpl(graph.name)
        codewriter.openfunc(self.getdecl())
        nextblock = graph.startblock
        args = graph.startblock.inputargs 
        self.block_to_name = {}
        for i, block in enumerate(graph.iterblocks()):
            self.block_to_name[block] = "block%s" % i
        for block in graph.iterblocks():
            codewriter.label(self.block_to_name[block])
            for name in 'startblock returnblock exceptblock'.split():
                if block is getattr(graph, name):
                    getattr(self, 'write_' + name)(codewriter, block)
                    break
            else:
                self.write_block(codewriter, block)
        codewriter.closefunc()

    def writeglobalconstants(self, codewriter):
        pass
    
    # ______________________________________________________________________
    # writing helpers for entry points
    def getdecl_parts(self):
        startblock = self.graph.startblock
        returnblock = self.graph.returnblock
        startblock_inputargs = [a for a in startblock.inputargs
                                if a.concretetype is not lltype.Void]

        inputargs = self.db.repr_arg_multi(startblock_inputargs)
        inputargtypes = self.db.repr_arg_type_multi(startblock_inputargs)
        returntype = self.db.repr_arg_type(self.graph.returnblock.inputargs[0])
        args = ["%s %s" % item for item in zip(inputargtypes, inputargs)]
        return returntype, self.ref, args

    def getdecl(self):
        returntype, ref, args = self.getdecl_parts()
        return "%s %s(%s)" % (returntype, ref, ", ".join(args))

    # ______________________________________________________________________
    # helpers for block writers
    
    def get_phi_data(self, block):
        exceptionpolicy = self.db.exceptionpolicy
        data = []
        
        entrylinks = mkentrymap(self.graph)[block]
        entrylinks = [x for x in entrylinks if x.prevblock is not None]

        inputargs = self.db.repr_arg_multi(block.inputargs)
        inputargtypes = self.db.repr_arg_type_multi(block.inputargs)

        # for each argument in block, return a 4 tuple of
        # arg_name, arg_type, [list of names from previous blocks,
        # [corresponding list of block names]
        for ii, (arg, type_) in enumerate(zip(inputargs, inputargtypes)):

            names = self.db.repr_arg_multi([link.args[ii]
                                            for link in entrylinks])

            blocknames = [self.block_to_name[link.prevblock]
                          for link in entrylinks]

            assert len(names) == len(blocknames)

            # some exception policies will add new blocks...
            exceptionpolicy.update_phi_data(self, entrylinks, block, blocknames)
            data.append((arg, type_, names, blocknames))

        return data

    def write_block_phi_nodes(self, codewriter, block):
        for arg, type_, names, blocknames in self.get_phi_data(block):
            if type_ != "void":
                codewriter.phi(arg, type_, names, blocknames)

    def write_block_branches(self, codewriter, block):
        if block.exitswitch == c_last_exception:
            # special case - handled by exception policy
            return
        
        if len(block.exits) == 1:
            codewriter.br_uncond(self.block_to_name[block.exits[0].target])
            return

        cond, condtype = self.db.repr_argwithtype(block.exitswitch)
        if block.exitswitch.concretetype == lltype.Bool:
            assert len(block.exits) == 2
            codewriter.br(cond,
                          self.block_to_name[block.exits[0].target],
                          self.block_to_name[block.exits[1].target])

        elif block.exitswitch.concretetype in \
            (lltype.Signed, lltype.Unsigned, lltype.SignedLongLong,
             lltype.UnsignedLongLong, lltype.Char, lltype.UniChar):
            defaultlink = None
            value_labels = []
            for link in block.exits:
                if link.exitcase is 'default':
                    defaultlink = link
                    continue 
                value_labels.append( (link.llexitcase, self.block_to_name[link.target]) )
            codewriter.switch(condtype, cond, self.block_to_name[defaultlink.target], value_labels)

        else:
            raise BranchException("exitswitch type '%s' not supported" % block.exitswitch.concretetype)

    def write_block_operations(self, codewriter, block):
        opwriter = OpWriter(self.db, codewriter, self, block)
        
        if block.exitswitch == c_last_exception:
            invoke_prefix = 'invoke:'
            # could raise an exception and should therefor have a function
            # implementation that can be invoked by the llvm-code.
            op = block.operations[len(block.operations) - 1]
            assert not op.opname.startswith(invoke_prefix)
            op.opname = invoke_prefix + op.opname

        # emit operations
        for op in block.operations:
            opwriter.write_operation(op)

    # ______________________________________________________________________
    # actual block writers
    
    def write_startblock(self, codewriter, block):
        self.write_block_operations(codewriter, block)
        self.write_block_branches(codewriter, block)

    def write_block(self, codewriter, block):
        self.write_block_phi_nodes(codewriter, block)
        self.write_block_operations(codewriter, block)
        self.write_block_branches(codewriter, block)

    def write_returnblock(self, codewriter, block):
        assert len(block.inputargs) == 1
        self.write_block_phi_nodes(codewriter, block)
        inputarg, inputargtype = self.db.repr_argwithtype(block.inputargs[0])
        codewriter.ret(inputargtype, inputarg)

    def write_exceptblock(self, codewriter, block):
        self.db.exceptionpolicy.write_exceptblock(self,
                                                  codewriter,
                                                  block)
