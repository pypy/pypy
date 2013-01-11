from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow.model import checkgraph, copygraph
from pypy.objspace.flow.model import Block, Link, SpaceOperation, Constant
from pypy.translator.unsimplify import split_block, varoftype
from pypy.translator.stm.stmgcintf import StmOperations
from pypy.translator.backendopt.ssa import SSA_to_SSI
from pypy.annotation.model import lltype_to_annotation, s_Int
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.rlib import rstm


def find_jit_merge_point(graph):
    found = []
    for block in graph.iterblocks():
        for i in range(len(block.operations)):
            op = block.operations[i]
            if (op.opname == 'jit_marker' and
                    op.args[0].value == 'jit_merge_point'):
                found.append((block, i))
    if found:
        assert len(found) == 1, "several jit_merge_point's in %r" % (graph,)
        return found[0]
    else:
        return None

def reorganize_around_jit_driver(stmtransformer, graph):
    location = find_jit_merge_point(graph)
    if location is not None:
        JitDriverSplitter(stmtransformer, graph).split(location)

# ____________________________________________________________


class JitDriverSplitter(object):
    #
    # def graph(..):              |     def graph(..):
    #     stuff_before            |         stuff_before
    #     while 1:               ====>      while 1:
    #         jit_merge_point()   |             if should_break_transaction():
    #         stuff_after         |                 return invoke_stm(..)
    # ----------------------------+             stuff_after
    #
    # def invoke_stm(..):
    #     p = new container object
    #     store (green args, red args) into p
    #     perform_transaction(callback, p)
    #     if p.got_exception: raise p.got_exception
    #     return p.result_value
    #
    # def callback(p):
    #     try:
    #         return run_callback(p)
    #     except e:
    #         p.got_exception = e
    #         return 0         # stop perform_tr() and returns
    #
    # def run_callback(p):
    #     fish (green args, red args) from p
    #     while 1:
    #         stuff_after
    #         if should_break_transaction():
    #             store (green args, red args) into p
    #             return 1     # causes perform_tr() to loop and call us again
    #     p.result_value = result_value
    #     p.got_exception = NULL
    #     return 0         # stop perform_tr() and returns

    def __init__(self, stmtransformer, graph):
        self.stmtransformer = stmtransformer
        self.main_graph = graph
        self.RESTYPE = graph.getreturnvar().concretetype

    def split(self, portal_location):
        self.check_jitdriver(portal_location)
        self.split_after_jit_merge_point(portal_location)
        self.make_container_type()
        #
        rtyper = self.stmtransformer.translator.rtyper
        self.mixlevelannotator = MixLevelHelperAnnotator(rtyper)
        self.make_run_callback_function()
        self.make_callback_function()
        self.make_invoke_stm_function()
        self.rewrite_main_graph()
        self.mixlevelannotator.finish()

    def check_jitdriver(self, (portalblock, portalopindex)):
        op_jitmarker = portalblock.operations[portalopindex]
        assert op_jitmarker.opname == 'jit_marker'
        assert op_jitmarker.args[0].value == 'jit_merge_point'
        jitdriver = op_jitmarker.args[1].value

        assert not jitdriver.greens and not jitdriver.reds   # XXX
        assert not jitdriver.autoreds    # XXX

    def split_after_jit_merge_point(self, (portalblock, portalopindex)):
        split_block(None, portalblock, portalopindex + 1)

    def make_container_type(self):
        self.CONTAINER = lltype.GcStruct('StmArgs',
                                         ('result_value', self.RESTYPE))
        self.CONTAINERP = lltype.Ptr(self.CONTAINER)

    def add_call_should_break_transaction(self, block):
        # add a should_break_transaction() call at the end of the block,
        # turn the following link into an "if False" link, add a new
        # "if True" link going to a fresh new block, and return this new
        # block.
        funcptr = StmOperations.should_break_transaction
        c = Constant(funcptr, lltype.typeOf(funcptr))
        v1 = varoftype(lltype.Signed)
        block.operations.append(SpaceOperation('direct_call', [c], v1))
        v2 = varoftype(lltype.Bool)
        block.operations.append(SpaceOperation('int_is_true', [v1], v2))
        #
        assert block.exitswitch is None
        [link] = block.exits
        block.exitswitch = v2
        link.exitcase = False
        link.llexitcase = False
        newblock = Block([varoftype(v.concretetype) for v in link.args])
        otherlink = Link(link.args[:], newblock)
        otherlink.exitcase = True
        otherlink.llexitcase = True
        block.recloseblock(link, otherlink)
        return newblock

    def rewrite_main_graph(self):
        # add 'should_break_transaction()'
        main_graph = self.main_graph
        block1, i = find_jit_merge_point(main_graph)
        assert i == len(block1.operations) - 1
        del block1.operations[i]
        blockf = self.add_call_should_break_transaction(block1)
        #
        # fill in blockf with a call to invoke_stm()
        v = varoftype(self.RESTYPE)
        op = SpaceOperation('direct_call', [self.c_invoke_stm_func], v)
        blockf.operations.append(op)
        blockf.closeblock(Link([v], main_graph.returnblock))
        #
        checkgraph(main_graph)

    def make_invoke_stm_function(self):
        CONTAINER = self.CONTAINER
        callback = self.callback_function
        #
        def ll_invoke_stm():
            p = lltype.malloc(CONTAINER)
            rstm.perform_transaction(callback, p)
            #if p.got_exception:
            #    raise p.got_exception
            return p.result_value
        #
        mix = self.mixlevelannotator
        c_func = mix.constfunc(ll_invoke_stm, [],
                               lltype_to_annotation(self.RESTYPE))
        self.c_invoke_stm_func = c_func

    def make_callback_function(self):
        run_callback = self.run_callback_function
        #
        def ll_callback(p):
            #try:
                return run_callback(p)
            #except Exception, e:
            #    p.got_exception = e
            #    return 0         # stop perform_tr() and returns
        #
        mix = self.mixlevelannotator
        args_s = [lltype_to_annotation(self.CONTAINERP)]
        self.callback_function = mix.delayedfunction(ll_callback,
                                                     args_s, s_Int)

    def make_run_callback_function(self):
        # make a copy of the 'main_graph'
        run_callback_graph = copygraph(self.main_graph)
        self.run_callback_graph = run_callback_graph
        #
        # make a new startblock
        v_p = varoftype(self.CONTAINERP)
        blockst = Block([v_p])
        #
        # change the startblock of callback_graph to point just after the
        # jit_merge_point
        block1, i = find_jit_merge_point(run_callback_graph)
        assert i == len(block1.operations) - 1
        del block1.operations[i]
        [link] = block1.exits
        run_callback_graph.startblock = blockst
        blockst.closeblock(Link([], link.target))
        #
        # hack at the regular return block, to set the result into
        # 'p.result_value', clear 'p.got_exception', and return 0
        blockr = run_callback_graph.returnblock
        c_result_value = Constant('result_value', lltype.Void)
        blockr.operations = [
            SpaceOperation('setfield',
                           [v_p, c_result_value, blockr.inputargs[0]],
                           varoftype(lltype.Void)),
            #...
            ]
        v = varoftype(self.RESTYPE)
        newblockr = Block([v])
        newblockr.operations = ()
        newblockr.closeblock()
        blockr.recloseblock(Link([Constant(0, lltype.Signed)], newblockr))
        run_callback_graph.returnblock = newblockr
        #
        # add 'should_break_transaction()' at the end of the loop
        blockf = self.add_call_should_break_transaction(block1)
        # ...store stuff...
        blockf.closeblock(Link([Constant(1, lltype.Signed)], newblockr))
        #
        SSA_to_SSI(run_callback_graph)   # to pass 'p' everywhere
        checkgraph(run_callback_graph)
        #
        mix = self.mixlevelannotator
        self.run_callback_function = mix.graph2delayed(run_callback_graph)
