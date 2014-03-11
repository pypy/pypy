from rpython.rtyper.lltypesystem import lltype, rclass
from rpython.flowspace.model import checkgraph, copygraph
from rpython.flowspace.model import Block, Link, SpaceOperation, Constant
from rpython.translator.unsimplify import split_block, varoftype
from rpython.annotator.model import s_Int
from rpython.rtyper.llannotation import lltype_to_annotation
from rpython.rtyper.annlowlevel import (MixLevelHelperAnnotator,
                                      cast_base_ptr_to_instance)
from rpython.rlib import rstm
from rpython.tool.sourcetools import compile2
from rpython.translator.c.support import log

def find_jit_merge_point(graph, relaxed=False):
    found = []
    for block in graph.iterblocks():
        for i in range(len(block.operations)):
            op = block.operations[i]
            if (op.opname == 'jit_marker'
                and op.args[0].value == 'jit_merge_point'):
                jitdriver = op.args[1].value
                if not jitdriver.autoreds:
                    if jitdriver.stm_do_transaction_breaks:
                        found.append((block, i))
                    else:
                        log.WARNING("ignoring non-stm jitdriver in  %r" % (
                            graph,))
                else:
                    log.WARNING("ignoring jitdriver with autoreds in %r" % (
                        graph,))        # XXX XXX!

    assert len(found) <= 1, "several jit_merge_point's in %r" % (graph,)
    if found:
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
    #                             |             stuff_after
    # ----------------------------+             
    #
    # def invoke_stm(..):
    #     p = new container object
    #     store (green args, red args) into p
    #     perform_transaction(callback, p)
    #     if p.got_exception: raise p.got_exception
    #     return p.result_value
    #
    # (note that perform_transaction() itself will fill p.got_exception)
    #
    # def callback(p, retry_counter):
    #     fish (green args, red args) from p
    #     while 1:
    #         stuff_after
    #         if should_break_transaction():
    #             store (green args, red args) into p
    #             return 1     # causes perform_tr() to loop and call us again
    #     p.result_value = result_value
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
        self.make_callback_function()
        self.make_invoke_stm_function()
        self.rewrite_main_graph()
        self.mixlevelannotator.finish()

    def check_jitdriver(self, (portalblock, portalopindex)):
        op_jitmarker = portalblock.operations[portalopindex]
        assert op_jitmarker.opname == 'jit_marker'
        assert op_jitmarker.args[0].value == 'jit_merge_point'
        jitdriver = op_jitmarker.args[1].value
        assert not jitdriver.autoreds    # fix me

    def split_after_jit_merge_point(self, (portalblock, portalopindex)):
        link = split_block(None, portalblock, portalopindex + 1)
        self.TYPES = [v.concretetype for v in link.args]

    def make_container_type(self):
        args = [('a%d' % i, self.TYPES[i]) for i in range(len(self.TYPES))]
        self.CONTAINER = lltype.GcStruct('StmArgs',
                                         ('result_value', self.RESTYPE),
                                         ('got_exception', rclass.OBJECTPTR),
                                         *args)
        self.CONTAINERP = lltype.Ptr(self.CONTAINER)

    def add_call_should_break_transaction(self, block):
        # add a should_break_transaction() call at the end of the block,
        # turn the following link into an "if False" link, add a new
        # "if True" link going to a fresh new block, and return this new
        # block.
        v2 = varoftype(lltype.Bool)
        block.operations.append(
            SpaceOperation('stm_should_break_transaction', [], v2))
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
        block1, i = find_jit_merge_point(main_graph, relaxed=True)
        assert i == len(block1.operations) - 1
        del block1.operations[i]
        blockf = self.add_call_should_break_transaction(block1)
        #
        # fill in blockf with a call to invoke_stm()
        v = varoftype(self.RESTYPE, 'result')
        op = SpaceOperation('direct_call',
                            [self.c_invoke_stm_func] + blockf.inputargs, v)
        blockf.operations.append(op)
        blockf.closeblock(Link([v], main_graph.returnblock))
        #
        checkgraph(main_graph)

    def make_invoke_stm_function(self):
        CONTAINER = self.CONTAINER
        callback = self.callback_function
        XXX
        perform_transaction = rstm.make_perform_transaction(callback,
                                                            self.CONTAINERP)
        irange = range(len(self.TYPES))
        source = """if 1:
        def ll_invoke_stm(%s):
            p = lltype.malloc(CONTAINER)
            %s
            perform_transaction(p)
            if p.got_exception:
                raise cast_base_ptr_to_instance(Exception, p.got_exception)
            return p.result_value
"""     % (', '.join(['a%d' % i for i in irange]),
           '; '.join(['p.a%d = a%d' % (i, i) for i in irange]))
        d = {'CONTAINER': CONTAINER,
             'lltype': lltype,
             'perform_transaction': perform_transaction,
             'cast_base_ptr_to_instance': cast_base_ptr_to_instance,
             }
        exec compile2(source) in d
        ll_invoke_stm = d['ll_invoke_stm']
        #
        mix = self.mixlevelannotator
        c_func = mix.constfunc(ll_invoke_stm,
                               map(lltype_to_annotation, self.TYPES),
                               lltype_to_annotation(self.RESTYPE))
        self.c_invoke_stm_func = c_func

    def container_var(self):
        return varoftype(self.CONTAINERP, 'stmargs')

    def make_callback_function(self):
        # make a copy of the 'main_graph'
        callback_graph = copygraph(self.main_graph)
        callback_graph.name += '_stm'
        self.callback_graph = callback_graph
        self.stmtransformer.translator.graphs.append(callback_graph)
        #for v1, v2 in zip(
        #    self.main_graph.getargs() + [self.main_graph.getreturnvar()],
        #    callback_graph.getargs() + [callback_graph.getreturnvar()]):
        #    self.stmtransformer.translator.annotator.transfer_binding(v2, v1)
        #
        # make a new startblock
        v_p = self.container_var()
        v_retry_counter = varoftype(lltype.Signed, 'retry_counter')
        blockst = Block([v_retry_counter])   # 'v_p' inserted below
        renamed_p = {blockst: v_p}
        annotator = self.stmtransformer.translator.annotator
        annotator.setbinding(v_p, lltype_to_annotation(self.CONTAINERP))
        annotator.setbinding(v_retry_counter, s_Int)
        #
        # change the startblock of callback_graph to point just after the
        # jit_merge_point
        block1, i = find_jit_merge_point(callback_graph, relaxed=True)
        assert i == len(block1.operations) - 1
        del block1.operations[i]
        [link] = block1.exits
        callback_graph.startblock = blockst
        #
        # fill in the operations of blockst: getfields reading all live vars
        a_vars = []
        for i in range(len(self.TYPES)):
            c_a_i = Constant('a%d' % i, lltype.Void)
            v_a_i = varoftype(self.TYPES[i])
            blockst.operations.append(
                SpaceOperation('getfield', [v_p, c_a_i], v_a_i))
            a_vars.append(v_a_i)
        blockst.closeblock(Link(a_vars, link.target))
        #
        # hack at the regular return block, to set the result into
        # 'p.result_value' and return 0.  Note that 'p.got_exception'
        # is already cleared.
        blockr = callback_graph.returnblock
        c_result_value = Constant('result_value', lltype.Void)
        v_p = self.container_var()
        renamed_p[blockr] = v_p
        blockr.operations = [
            SpaceOperation('setfield',
                           [v_p, c_result_value, blockr.inputargs[0]],
                           varoftype(lltype.Void)),
            ]
        v = varoftype(lltype.Signed)
        annotator.setbinding(v, s_Int)
        newblockr = Block([v])
        newblockr.operations = ()
        newblockr.closeblock()
        blockr.recloseblock(Link([Constant(0, lltype.Signed)], newblockr))
        callback_graph.returnblock = newblockr
        #
        # add 'should_break_transaction()' at the end of the loop
        blockf = self.add_call_should_break_transaction(block1)
        # store the variables again into v_p
        v_p = self.container_var()
        renamed_p[blockf] = v_p
        for i in range(len(self.TYPES)):
            c_a_i = Constant('a%d' % i, lltype.Void)
            v_a_i = blockf.inputargs[i]
            assert v_a_i.concretetype == self.TYPES[i]
            blockf.operations.append(
                SpaceOperation('setfield', [v_p, c_a_i, v_a_i],
                               varoftype(lltype.Void)))
        blockf.closeblock(Link([Constant(1, lltype.Signed)], newblockr))
        #
        # now pass the original 'v_p' everywhere
        for block in callback_graph.iterblocks():
            if block.operations == ():    # skip return and except blocks
                continue
            v_p = renamed_p.get(block, self.container_var())
            block.inputargs = [v_p] + block.inputargs
            for link in block.exits:
                if link.target.operations != ():   # to return or except block
                    link.args = [v_p] + link.args
        #
        checkgraph(callback_graph)
        #
        FUNCTYPE = lltype.FuncType([self.CONTAINERP, lltype.Signed],
                                   lltype.Signed)
        mix = self.mixlevelannotator
        self.callback_function = mix.graph2delayed(callback_graph,
                                                   FUNCTYPE=FUNCTYPE)
