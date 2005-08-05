import py
from pypy.objspace.flow.model import Block, Constant, Variable, Link
from pypy.objspace.flow.model import flatten, mkentrymap, traverse, last_exception
from pypy.rpython import lltype
from pypy.translator.backendoptimization import remove_same_as 
from pypy.translator.unsimplify import remove_double_links                     
from pypy.translator.llvm2.node import LLVMNode, ConstantLLVMNode
from pypy.translator.llvm2.opwriter import OpWriter
from pypy.translator.llvm2.log import log 
log = log.funcnode

class FuncTypeNode(LLVMNode):
    def __init__(self, db, type_):
        self.db = db
        assert isinstance(type_, lltype.FuncType)
        self.type_ = type_
        self.ref = self.make_ref('%functiontype', '')
        
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
    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.ref = "%" + value.graph.name
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

    def writecomments(self, codewriter):
        """ write operations strings for debugging purposes. """ 
        blocks = [x for x in flatten(self.graph) if isinstance(x, Block)]
        for block in blocks:
            for op in block.operations:
                strop = str(op)
                l = (len(strop) + 2) # new line & null
                tempname = self.db.add_op2comment(l, op)
                typeandata = '[%s x sbyte] c"%s\\0A\\00"' % (l, strop)
                codewriter.globalinstance(tempname, typeandata)

    def writeglobalconstants(self, codewriter):
        pass
    
    # ______________________________________________________________________
    # writing helpers for entry points

    def getdecl(self):
        startblock = self.graph.startblock
        returnblock = self.graph.returnblock
        # XXX hack as per remove_voids()
        startblock_inputargs = [a for a in startblock.inputargs
                                if a.concretetype is not lltype.Void]

        inputargs = self.db.repr_arg_multi(startblock_inputargs)
        inputargtypes = self.db.repr_arg_type_multi(startblock_inputargs)
        returntype = self.db.repr_arg_type(self.graph.returnblock.inputargs[0])
        result = "%s %s" % (returntype, self.ref)
        args = ["%s %s" % item for item in zip(inputargtypes, inputargs)]
        result += "(%s)" % ", ".join(args)
        return result 

    def write_block(self, codewriter, block):
        self.write_block_phi_nodes(codewriter, block)
        self.write_block_operations(codewriter, block)
        self.write_block_branches(codewriter, block)

    def get_phi_data(self, block):
        data = []
        entrylinks = mkentrymap(self.graph)[block]
        entrylinks = [x for x in entrylinks if x.prevblock is not None]
        inputargs = self.db.repr_arg_multi(block.inputargs)
        inputargtypes = self.db.repr_arg_type_multi(block.inputargs)
        for i, (arg, type_) in enumerate(zip(inputargs, inputargtypes)):
            names = self.db.repr_arg_multi([link.args[i] for link in entrylinks])
            blocknames = [self.block_to_name[link.prevblock]
                              for link in entrylinks]
            for i, link in enumerate(entrylinks):   #XXX refactor into a transformation
                if link.prevblock.exitswitch == Constant(last_exception) and \
                   link.prevblock.exits[0].target != block:
                    blocknames[i] += '_exception_found_branchto_' + self.block_to_name[block]
            data.append( (arg, type_, names, blocknames) )
        return data

    def write_block_phi_nodes(self, codewriter, block):
        for arg, type_, names, blocknames in self.get_phi_data(block):
            if type_ != "void":
                codewriter.phi(arg, type_, names, blocknames)

    def write_block_branches(self, codewriter, block):
        #assert len(block.exits) <= 2    #more exits are possible (esp. in combination with exceptions)
        if block.exitswitch == Constant(last_exception):
            #codewriter.comment('FuncNode(ConstantLLVMNode) *last_exception* write_block_branches @%s@' % str(block.exits))
            return
        if len(block.exits) == 1:
            codewriter.br_uncond(self.block_to_name[block.exits[0].target])
        elif len(block.exits) == 2:
            cond = self.db.repr_arg(block.exitswitch)
            codewriter.br(cond, self.block_to_name[block.exits[0].target],
                          self.block_to_name[block.exits[1].target])

    def write_block_operations(self, codewriter, block):
        opwriter = OpWriter(self.db, codewriter, self, block)
        if block.exitswitch == Constant(last_exception):
            last_op_index = len(block.operations) - 1
        else:
            last_op_index = None
        for op_index, op in enumerate(block.operations):
            if False:   # print out debug string
                codewriter.newline()
                codewriter.comment("** %s **" % str(op))
                info = self.db.get_op2comment(op)
                if info is not None:
                    lenofopstr, opstrname = info
                    codewriter.debugcomment(self.db.repr_tmpvar(),
                                            lenofopstr,
                                            opstrname)
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
        self.write_block_phi_nodes(codewriter, block)
        inputargtype = self.db.repr_arg_type(block.inputargs[0])
        inputarg = self.db.repr_arg(block.inputargs[0])
        if inputargtype != "void":
            codewriter.ret(inputargtype, inputarg)
        else:
            codewriter.ret_void()

    def _is_raise_new_exception(self, block):
        is_raise_new = False
        entrylinks = mkentrymap(self.graph)[block]
        entrylinks = [x for x in entrylinks if x.prevblock is not None]
        inputargs = self.db.repr_arg_multi(block.inputargs)
        for i, arg in enumerate(inputargs):
            names = self.db.repr_arg_multi([link.args[i] for link in entrylinks])
            for name in names:  #These tests-by-name are a bit yikes, but I don't see a better way right now
                if not name.startswith('%last_exception_') and not name.startswith('%last_exc_value_'):
                    is_raise_new = True
        return is_raise_new

    def write_exceptblock(self, codewriter, block):
        assert len(block.inputargs) == 2

        if self._is_raise_new_exception(block):
            self.write_block_phi_nodes(codewriter, block)

            inputargs = self.db.repr_arg_multi(block.inputargs)
            inputargtypes = self.db.repr_arg_type_multi(block.inputargs)

            codewriter.store(inputargtypes[0], inputargs[0], '%last_exception_type')
            codewriter.store(inputargtypes[1], inputargs[1], '%last_exception_value')
        else:
            codewriter.comment('reraise last exception')
            #Reraising last_exception.
            #Which is already stored in the global variables.
            #So nothing needs to happen here!

        codewriter.unwind()
