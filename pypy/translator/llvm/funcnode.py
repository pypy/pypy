from pypy.objspace.flow.model import Block, Constant, Link, copygraph, Variable
from pypy.objspace.flow.model import mkentrymap, c_last_exception
from pypy.rpython.lltypesystem import lltype
from pypy.translator.llvm.node import FuncNode
from pypy.translator.llvm.opwriter import OpWriter
from pypy.translator.llvm.log import log 
from pypy.translator.unsimplify import remove_double_links, no_links_to_startblock
log = log.funcnode

class BranchException(Exception):
    pass

class FuncImplNode(FuncNode):
    prefix = '@pypy_'
    __slots__ = "db value graph block_to_name bad_switch_block".split()

    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.graph = value.graph
        self.bad_switch_block = False

        self.make_name(value.graph.name)

    def setup(self):
        assert self.graph, "cannot traverse"
        prepare_arg = self.db.prepare_arg
        for block in self.graph.iterblocks():
            for arg in block.inputargs:
                prepare_arg(arg)
            for op in block.operations:
                for arg in op.args:
                    prepare_arg(arg)
                prepare_arg(op.result)
            assert block.exitswitch != c_last_exception
            for link in block.exits:
                for arg in link.args:
                    prepare_arg(arg)

    # ______________________________________________________________________
    # main entry points from genllvm 

    def patch_graph(self):
        graph = self.graph
        self.gcrootscount = 0
        if self.db.gctransformer:
            # inline the GC helpers (malloc, write_barrier) into
            # a copy of the graph
            graph = copygraph(graph, shallow=True)
            self.db.gctransformer.inline_helpers(graph)
            # the 'gc_reload_possibly_moved' operations make the graph not
            # really SSA.  Fix them now.
            for block in graph.iterblocks():
                rename = {}
                for op in block.operations:
                    if rename:
                        op.args = [rename.get(v, v) for v in op.args]
                    if op.opname == 'gc_reload_possibly_moved':
                        v_newaddr, v_targetvar = op.args
                        assert isinstance(v_targetvar.concretetype, lltype.Ptr)
                        v_newptr = Variable()
                        v_newptr.concretetype = v_targetvar.concretetype
                        op.opname = 'cast_adr_to_ptr'
                        op.args = [v_newaddr]
                        op.result = v_newptr
                        rename[v_targetvar] = v_newptr
                    elif op.opname == 'llvm_store_gcroot':
                        index = op.args[0].value
                        self.gcrootscount = max(self.gcrootscount, index+1)
                if rename:
                    block.exitswitch = rename.get(block.exitswitch,
                                                  block.exitswitch)
                    for link in block.exits:
                        link.args = [rename.get(v, v) for v in link.args]
        # fix special cases that llvm can't handle
        remove_double_links(self.db.translator.annotator, graph)
        no_links_to_startblock(graph)
        return graph

    def writedecl(self, codewriter): 
        codewriter.declare(self.getdecl())

    def writeimpl(self, codewriter):
        self.oldgraph = self.graph
        self.graph = self.patch_graph()
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
            for name in 'startblock returnblock'.split():
                if block is getattr(graph, name):
                    getattr(self, 'write_' + name)(codewriter, block)
                    break
            else:
                self.write_block(codewriter, block)
        if self.bad_switch_block:
            codewriter.label('badswitch')
            codewriter._indent('call void @abort()')
            codewriter._indent('unreachable')
        codewriter.closefunc()
        self.graph = self.oldgraph
        del self.oldgraph
    
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
        annotations = ''
        if self.db.genllvm.config.translation.gcrootfinder == "llvmgc":
            annotations += ' gc "gcrootsingle"'
        return '%s %s(%s)%s' % (returntype, ref, ", ".join(args), annotations)

    # ______________________________________________________________________
    # helpers for block writers
    
    def get_phi_data(self, block):
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
            data.append((arg, type_, names, blocknames))

        return data

    def write_block_phi_nodes(self, codewriter, block):
        for arg, type_, names, blocknames in self.get_phi_data(block):
            if type_ != "void":
                codewriter.phi(arg, type_, names, blocknames)

    def write_block_branches(self, codewriter, block):        
        assert block.exitswitch != c_last_exception

        if len(block.exits) == 1:
            codewriter.br_uncond(self.block_to_name[block.exits[0].target])
            return

        cond, condtype = self.db.repr_argwithtype(block.exitswitch)
        if block.exitswitch.concretetype == lltype.Bool:
            assert len(block.exits) == 2
            if block.exits[0].llexitcase == False:
                assert block.exits[1].llexitcase == True
                false_case = block.exits[0].target
                true_case = block.exits[1].target
            else:
                assert block.exits[0].llexitcase == True
                assert block.exits[1].llexitcase == False
                false_case = block.exits[1].target
                true_case = block.exits[0].target
            codewriter.br(cond,
                          self.block_to_name[false_case],
                          self.block_to_name[true_case])

        elif block.exitswitch.concretetype in \
            (lltype.Signed, lltype.Unsigned, lltype.SignedLongLong,
             lltype.UnsignedLongLong, lltype.Char, lltype.UniChar):
            defaultlink = None
            value_labels = []
            for link in block.exits:
                if link.exitcase == 'default':
                    defaultlink = link
                    continue

                exitcase = link.llexitcase
                if block.exitswitch.concretetype in [lltype.Char, lltype.UniChar]:
                    exitcase = ord(exitcase)
                value_labels.append( (exitcase,
                                      self.block_to_name[link.target]) )

            if defaultlink:
                defaultblockname = self.block_to_name[defaultlink.target]
            else:
                defaultblockname = 'badswitch'
                self.bad_switch_block = True

            codewriter.switch(condtype, cond, defaultblockname, value_labels)

        else:
            raise BranchException("exitswitch type '%s' not supported" %
                                  block.exitswitch.concretetype)

    def write_block_operations(self, codewriter, block):
        # XXX We dont need multiple of these
        opwriter = OpWriter(self.db, codewriter)

        assert block.exitswitch != c_last_exception

        # emit operations
        for op in block.operations:
            opwriter.write_operation(op)

    # ______________________________________________________________________
    # actual block writers
    
    def write_startblock(self, codewriter, block):
        if self.gcrootscount > 0:
            codewriter.declare_gcroots(self.gcrootscount)
        self.write_block_operations(codewriter, block)
        # a start block may return also
        if block.exitswitch is None and len(block.exits) == 0:
            inputarg, inputargtype = self.db.repr_argwithtype(block.inputargs[0])
            codewriter.ret(inputargtype, inputarg)
        else:
            self.write_block_branches(codewriter, block)

    def write_block(self, codewriter, block):
        self.write_block_phi_nodes(codewriter, block)
        self.write_block_operations(codewriter, block)
        self.write_block_branches(codewriter, block)

    def write_returnblock(self, codewriter, block):
        block.exitswitch is None and len(block.exits) == 0
        assert len(block.inputargs) == 1
        self.write_block_phi_nodes(codewriter, block)
        inputarg, inputargtype = self.db.repr_argwithtype(block.inputargs[0])
        codewriter.ret(inputargtype, inputarg)
