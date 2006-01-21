import py
import sys
from pypy.objspace.flow.model import Block, Constant, Variable, Link
from pypy.objspace.flow.model import flatten, mkentrymap, traverse, c_last_exception
from pypy.rpython.lltypesystem import lltype
from pypy.translator.js.node import Node
from pypy.translator.js.opwriter import OpWriter
from pypy.translator.js.log import log 
log = log.funcnode


class FuncNode(Node):
    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.ref   = db.namespace.uniquename(value.graph.name)
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
                    if block.exitswitch != c_last_exception:
                        continue
                    if hasattr(self.graph, 'exceptblock'):
                        from pypy.rpython.rmodel import inputconst
                        e          = self.db.translator.rtyper.getexceptiondata()
                        matchptr   = e.fn_exception_match
                        matchconst = inputconst(lltype.typeOf(matchptr), matchptr)
                        self.db.prepare_arg_value(matchconst) 
                    for link in block.exits[1:]:
                        self.db.prepare_constant(lltype.typeOf(link.llexitcase),
                                                 link.llexitcase)
                                            
        assert self.graph, "cannot traverse"
        traverse(visit, self.graph)

    def write_implementation(self, codewriter):
        graph = self.graph
        log.writeimplemention(graph.name)
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
        if block.exitswitch == c_last_exception:
            return

        if len(block.exits) == 1:
            codewriter.br_uncond(self.blockindex[block.exits[0].target], block.exits[0])
            return

        cond = self.db.repr_arg(block.exitswitch)
        if block.exitswitch.concretetype == lltype.Bool:
            assert len(block.exits) == 2
            codewriter.br(cond,
                          self.blockindex[block.exits[0].target], block.exits[0],
                          self.blockindex[block.exits[1].target], block.exits[1])

        elif block.exitswitch.concretetype in \
            (lltype.Signed, lltype.Unsigned, lltype.SignedLongLong,
             lltype.UnsignedLongLong, lltype.Char, lltype.UniChar):
            defaultlink = None
            mapping = []
            for link in block.exits:
                if link.exitcase is 'default':
                    defaultlink = link
                    continue

                exitcase = link.llexitcase
                if block.exitswitch.concretetype in [lltype.Char, lltype.UniChar]:
                    exitcase = ord(exitcase)
                exitcase = "'%s'" % exitcase

                try:
                    targetvar       = link.target.inputargs[0]
                    targetvar_value = self.db.repr_arg(link.args[0])
                    s = "%s=%s;" % (targetvar, targetvar_value)
                except:
                    s = ''
                targetblock = self.blockindex[link.target]

                code = "'%sblock=%s'" % (s, targetblock)
                mapping.append( (exitcase, code) )

            try:
                default_targetvar       = defaultlink.target.inputargs[0]
                default_targetvar_value = self.db.repr_arg(defaultlink.args[0])
                s = "%s=%s;" % (default_targetvar, default_targetvar_value)
            except:
                s = ''
            default_targetblock     = self.blockindex[defaultlink.target]
            default_code  = "'%sblock=%s'" % (s, default_targetblock)
            if block.exitswitch.concretetype == lltype.Char:
                cond = "%s.charCodeAt(0)" % cond
            codewriter.switch(cond, mapping, default_code)

        else:
           raise BranchException("exitswitch type '%s' not supported" %
                                 block.exitswitch.concretetype)  

    def write_block_operations(self, codewriter, block):
        opwriter = OpWriter(self.db, codewriter, self, block)
        if block.exitswitch == c_last_exception:
            last_op_index = len(block.operations) - 1
        else:
            last_op_index = None
        for op_index, op in enumerate(block.operations):
            if op_index == last_op_index:
                #could raise an exception and should therefor have a function
                #implementation that can be invoked by the outputed code.
                invoke_prefix = 'invoke:'
                assert not op.opname.startswith(invoke_prefix)
                op.opname = invoke_prefix + op.opname
            opwriter.write_operation(op)

    def write_startblock(self, codewriter, block):
        self.write_block_operations(codewriter, block)
        self.write_block_branches(codewriter, block)

    def write_returnblock(self, codewriter, block):
        assert len(block.inputargs) == 1
        codewriter.ret( self.db.repr_arg(block.inputargs[0]) )

    def write_exceptblock(self, codewriter, block):
        assert len(block.inputargs) == 2
        codewriter.throw( str(block.inputargs[1]) )
        codewriter.skip_closeblock()


class ExternalFuncNode(Node):
    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.ref   = value.graph.name #keep the exact name (do not compress)
        self.graph = value.graph
