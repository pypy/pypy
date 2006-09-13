import py, types
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.objspace.flow import model as flowmodel
from pypy.annotation import model as annmodel
from pypy.annotation import listdef, dictdef
from pypy.jit.timeshifter import rvalue, oop
from pypy.jit.timeshifter.rtimeshift import JITState
from pypy.rpython import rmodel, annlowlevel
from pypy.rpython.lltypesystem import rtuple, rlist, rdict
from pypy.jit.timeshifter import rtimeshift
from pypy.jit.timeshifter.rtyper import HintRTyper, originalconcretetype
from pypy.jit.timeshifter.rtyper import GreenRepr, RedRepr, HintLowLevelOpList
from pypy.translator.unsimplify import varoftype, copyvar, split_block_at_start
from pypy.translator.backendopt import support
from pypy.translator.c import exceptiontransform
from pypy.jit.codegen import model as cgmodel

# ___________________________________________________________

class HintTimeshift(object):
    
    def __init__(self, hannotator, rtyper, RGenOp):
        self.hannotator = hannotator
        self.rtyper = rtyper
        self.RGenOp = RGenOp
        self.hrtyper = HintRTyper(hannotator, self)
        self.annhelper = annlowlevel.MixLevelHelperAnnotator(rtyper)
        self.timeshift_mapping = {}
        self.sigs = {}

        self.s_CodeGenerator, self.r_CodeGenerator = self.s_r_instanceof(
            cgmodel.CodeGenerator)
        self.s_JITState, self.r_JITState = self.s_r_instanceof(JITState)
        self.s_RedBox, self.r_RedBox = self.s_r_instanceof(rvalue.RedBox)
        self.s_OopSpecDesc, self.r_OopSpecDesc = self.s_r_instanceof(
            oop.OopSpecDesc)
        self.s_ConstOrVar, self.r_ConstOrVar = self.s_r_instanceof(
            cgmodel.GenVarOrConst)
        self.s_Block, self.r_Block = self.s_r_instanceof(cgmodel.CodeGenBlock)

        getrepr = self.rtyper.getrepr

        bk = rtyper.annotator.bookkeeper
        box_list_def = listdef.ListDef(None, self.s_RedBox, resized = True)
        self.s_box_list = annmodel.SomeList(box_list_def)
        self.r_box_list = getrepr(self.s_box_list)
        self.r_box_list.setup()

##        box_accum_def = listdef.ListDef(None, self.s_RedBox, resized = True)
##        self.s_box_accum = annmodel.SomeList(box_accum_def)
##        self.r_box_accum = getrepr(self.s_box_accum)
##        self.r_box_accum.setup()

        self.etrafo = hannotator.exceptiontransformer
        self.cexcdata = self.etrafo.cexcdata
        self.exc_data_ptr = self.cexcdata.value
        gv_excdata = RGenOp.constPrebuiltGlobal(self.exc_data_ptr)
        LL_EXC_TYPE  = rtyper.exceptiondata.lltype_of_exception_type
        LL_EXC_VALUE = rtyper.exceptiondata.lltype_of_exception_value
        null_exc_type_box = rvalue.redbox_from_prebuilt_value(RGenOp,
                                         lltype.nullptr(LL_EXC_TYPE.TO))
        null_exc_value_box = rvalue.redbox_from_prebuilt_value(RGenOp,
                                         lltype.nullptr(LL_EXC_VALUE.TO))

        p = self.etrafo.rpyexc_fetch_type_ptr.value
        gv_rpyexc_fetch_type = RGenOp.constPrebuiltGlobal(p)
        tok_fetch_type = RGenOp.sigToken(lltype.typeOf(p).TO)
        kind_etype = RGenOp.kindToken(LL_EXC_TYPE)

        p = self.etrafo.rpyexc_fetch_value_ptr.value
        gv_rpyexc_fetch_value = RGenOp.constPrebuiltGlobal(p)
        tok_fetch_value = RGenOp.sigToken(lltype.typeOf(p).TO)
        kind_evalue = RGenOp.kindToken(LL_EXC_VALUE)

        p = self.etrafo.rpyexc_clear_ptr.value
        gv_rpyexc_clear = RGenOp.constPrebuiltGlobal(p)
        tok_clear = RGenOp.sigToken(lltype.typeOf(p).TO)

        p = self.etrafo.rpyexc_raise_ptr.value
        gv_rpyexc_raise = RGenOp.constPrebuiltGlobal(p)
        tok_raise = RGenOp.sigToken(lltype.typeOf(p).TO)

        def fetch_global_excdata(jitstate):
            builder = jitstate.curbuilder
            gv_etype = builder.genop_call(tok_fetch_type,
                                          gv_rpyexc_fetch_type, [])
            gv_evalue = builder.genop_call(tok_fetch_value,
                                           gv_rpyexc_fetch_value, [])
            builder.genop_call(tok_clear, gv_rpyexc_clear, [])
            etypebox  = rvalue.PtrRedBox(kind_etype,  gv_etype)
            evaluebox = rvalue.PtrRedBox(kind_evalue, gv_evalue)
            rtimeshift.setexctypebox (jitstate, etypebox)
            rtimeshift.setexcvaluebox(jitstate, evaluebox)
        self.fetch_global_excdata = fetch_global_excdata

        def store_global_excdata(jitstate):
            builder = jitstate.curbuilder
            etypebox = jitstate.exc_type_box
            if etypebox.is_constant():
                ll_etype = rvalue.ll_getvalue(etypebox, llmemory.Address)
                if not ll_etype:
                    return       # we known there is no exception set
            evaluebox = jitstate.exc_value_box
            gv_etype  = etypebox .getgenvar(builder)
            gv_evalue = evaluebox.getgenvar(builder)
            builder.genop_call(tok_raise,
                               gv_rpyexc_raise, [gv_etype, gv_evalue])
        self.store_global_excdata = store_global_excdata

        def ll_fresh_jitstate(builder):
            return JITState(builder, None,
                            null_exc_type_box,
                            null_exc_value_box)
        self.ll_fresh_jitstate = ll_fresh_jitstate

        def ll_finish_jitstate(jitstate, graphsigtoken):
            returnbox = rtimeshift.getreturnbox(jitstate)
            gv_ret = returnbox.getgenvar(jitstate.curbuilder)
            store_global_excdata(jitstate)
            jitstate.curbuilder.finish_and_return(graphsigtoken, gv_ret)
        self.ll_finish_jitstate = ll_finish_jitstate


    def s_r_instanceof(self, cls, can_be_None=True):
        # Return a SomeInstance / InstanceRepr pair correspnding to the specified class.
        return self.annhelper.s_r_instanceof(cls, can_be_None=can_be_None)

    def get_sig_hs(self, tsgraph):
        # the signature annotations are cached here because
        # the graph is going to be modified
        try:
            return self.sigs[tsgraph]
        except KeyError:
            ha = self.hannotator
            sig_hs = ([ha.binding(v) for v in tsgraph.getargs()],
                      ha.binding(tsgraph.getreturnvar()))
            self.sigs[tsgraph] = sig_hs
            return sig_hs

    def get_timeshifted_fnptr(self, graph, specialization_key):
        bk = self.hannotator.bookkeeper
        tsgraph = bk.get_graph_by_key(graph, specialization_key)
        args_hs, hs_res = self.get_sig_hs(tsgraph)
        args_r = [self.hrtyper.getrepr(hs_arg) for hs_arg in args_hs]
        ARGS = [self.r_JITState.lowleveltype]
        ARGS += [r.lowleveltype for r in args_r]
        RESULT = self.r_JITState.lowleveltype
        fnptr = lltype.functionptr(lltype.FuncType(ARGS, RESULT),
                                   tsgraph.name,
                                   graph=tsgraph,
                                   _callable = graph.func)
        self.schedule_graph(tsgraph)
        return fnptr, args_r

    def error_value(self, TYPE):
        return exceptiontransform.error_value(TYPE)

    def get_timeshift_mapper(self, FUNC, specialization_key, graphs):
        key = FUNC, specialization_key
        try:
            timeshift_mapper, values, keys = self.timeshift_mapping[key]
        except KeyError:
            values = []
            keys = []
            fnptrmap = {}

            def getter(fnptrmap, fnptr):
                # indirection needed to defeat the flow object space
                return fnptrmap[fnptr]

            def fill_dict(fnptrmap, values, keys):
                for i in range(len(values)):
                    fnptrmap[values[i]] = keys[i]

            def timeshift_mapper(fnptrbox):
                fnptr = rvalue.ll_getvalue(fnptrbox, FUNC)
                try:
                    return getter(fnptrmap, fnptr)
                except KeyError:
                    fill_dict(fnptrmap, values, keys)
                    return getter(fnptrmap, fnptr)   # try again

            self.timeshift_mapping[key] = timeshift_mapper, values, keys

        bk = self.hannotator.bookkeeper
        common_args_r = None
        COMMON_TS_FUNC = None
        tsgraphs = []
        for graph in graphs:
            fnptr = self.rtyper.getcallable(graph)
            ts_fnptr, args_r = self.get_timeshifted_fnptr(graph,
                                   specialization_key)
            tsgraphs.append(ts_fnptr._obj.graph)
            TS_FUNC = lltype.typeOf(ts_fnptr)
            if common_args_r is None:
                common_args_r = args_r
                COMMON_TS_FUNC = TS_FUNC
            else:
                # XXX for now
                assert COMMON_TS_FUNC == TS_FUNC
                assert common_args_r == args_r
            keys.append(fnptr)
            values.append(ts_fnptr)
        return timeshift_mapper, COMMON_TS_FUNC, common_args_r, tsgraphs

    # creates and numbers reentry_block for block reached by link
    # argument:
    #
    # the reentry_block takes a jitstate and a list of boxes
    # and explodes the content of boxes into variables for each
    # link argument;
    # redboxes are preserved, green values are read out of constant
    # boxes
    #
    # then passes the variables to the target of link
    #
    def getexitindex(self, link):
        self.latestexitindex += 1
      
        reentry_block = flowmodel.Block([])

        llops = HintLowLevelOpList(self)
        v_jitstate = llops.getjitstate()

        reenter_vars = []
        i = 0
        for var in link.args:
            if isinstance(var, flowmodel.Constant):
                reenter_vars.append(var)
                continue
            r = self.hrtyper.bindingrepr(var)
            v_box = self.read_out_box(llops, v_jitstate, i)
            i += 1
            if isinstance(r, RedRepr):
                reenter_vars.append(v_box)
            else:
                c_TYPE = rmodel.inputconst(lltype.Void,
                                           r.lowleveltype)
                s_TYPE = self.rtyper.annotator.bookkeeper.immutablevalue(r.lowleveltype)
                v_value = llops.genmixlevelhelpercall(rvalue.ll_getvalue,
                    [self.s_RedBox, s_TYPE],
                    [v_box, c_TYPE],
                    r.annotation())
                                                
                reenter_vars.append(v_value)

        reenter_link = flowmodel.Link(reenter_vars, link.target)
        
        reentry_block.operations[:] = llops
        reentry_block.closeblock(reenter_link)

        from_dispatch = flowmodel.Link([], reentry_block)
        self.dispatch_to.append((self.latestexitindex, from_dispatch))        
        return self.latestexitindex

    def schedule_graph(self, graph):
        if graph not in self.already_scheduled_graphs:
            self.already_scheduled_graphs[graph] = True
            self.graphs_to_timeshift.append(graph)

    def timeshift(self):
        self.already_scheduled_graphs = {}
        self.graphs_to_timeshift = []

        self.schedule_graph(self.hannotator.translator.graphs[0])

        while self.graphs_to_timeshift:
            graph = self.graphs_to_timeshift.pop()
            self.timeshift_graph(graph)
        
        # Annotate and rtype the helpers found during timeshifting
        # XXX XXX XXX -- self.annhelper.finish() -- XXX XXX XXX

    def timeshift_graph(self, graph):
        #print 'timeshift_graph START', graph
        assert graph.startblock in self.hannotator.annotated
        self.graph = graph
        self.dispatch_to = []
        self.statecaches = []
        self.return_cache = None
        self.latestexitindex = -1

        # cache the annotation signature before changing the graph
        args_hs, hs_res = self.get_sig_hs(graph)
        assert (originalconcretetype(hs_res) is lltype.Void
                or not hs_res.is_green())      # XXX not supported yet

        originalblocks = list(graph.iterblocks())
        timeshifted_blocks = []
        for block in originalblocks:
            self.timeshift_block(timeshifted_blocks, block)
        originalblocks = timeshifted_blocks

        entering_links = flowmodel.mkentrymap(graph)

        returnblock = graph.returnblock
        self.r_returnvalue = self.hrtyper.bindingrepr(returnblock.inputargs[0])
        returnblock.operations = []
        graph.returnblock = None

        self.dispatchblock = flowmodel.Block([])

        for block in originalblocks:
            is_returnblock = len(block.exits) == 0
            nentrylinks = len(entering_links[block])
            self.insert_bookkeeping_leave_block(block)
            self.insert_bookkeeping_enter(block, nentrylinks, is_returnblock)

        # fix its concretetypes
        self.insert_dispatch_logic()

        # hack to allow the state caches to be cleared
        # XXX! doesn't work if there are several graphs
        miniglobals = {}
        source = ["def clearcaches():"]
        if self.statecaches:
            for i, cache in enumerate(self.statecaches):
                source.append("    c%d.clear()" % i)
                miniglobals["c%d" % i] = cache
        else:
            source.append("    pass")
        exec py.code.Source('\n'.join(source)).compile() in miniglobals
        clearcaches = miniglobals['clearcaches']
        self.c_ll_clearcaches_ptr = self.annhelper.constfunc(clearcaches, [],
                                                             annmodel.s_None)

        self.insert_start_setup()
        self.insert_v_jitstate_everywhere()

        # and now... the graph is timeshifted, so it is *itself* no longer
        # exception-transformed...
        del graph.exceptiontransformed
        #print 'timeshift_graph END', graph

    def insert_v_jitstate_everywhere(self):
        for block in self.graph.iterblocks():
            v_jitstate = varoftype(self.r_JITState.lowleveltype, 'jitstate')
            block.inputargs = [v_jitstate] + block.inputargs
            for op in block.operations:
                if op.opname == 'getjitstate':
                    op.opname = 'same_as'
                    op.args = [v_jitstate]
                elif op.opname == 'setjitstate':
                    [v_jitstate] = op.args
            for i in range(len(block.operations)-1, -1, -1):
                if block.operations[i].opname == 'setjitstate':
                    del block.operations[i]
            for link in block.exits:
                link.args = [v_jitstate] + link.args

    def insert_start_setup(self):
        newstartblock = self.insert_before_block(self.graph.startblock,
                                                 closeblock=True)
        llops = HintLowLevelOpList(self)
        v_jitstate = llops.getjitstate()

        llops.genop('direct_call', [self.c_ll_clearcaches_ptr])
        llops.genmixlevelhelpercall(rtimeshift.enter_graph,
                                    [self.s_JITState],
                                    [v_jitstate     ],
                                    annmodel.s_None)
        newstartblock.operations = list(llops)
                    
    def insert_before_block(self, block, closeblock=True):
        newinputargs = [copyvar(self.hannotator, var)
                        for var in block.inputargs]

        newblock = flowmodel.Block(newinputargs)
        if block.isstartblock: # xxx
            block.isstartblock = False
            newblock.isstartblock = True
            self.graph.startblock = newblock

        if closeblock:
            bridge = flowmodel.Link(newinputargs, block)
            newblock.closeblock(bridge)
        return newblock

    def make_const_box(self, llops, r_green, v_value, v_jitstate):
        v_box = llops.genmixlevelhelpercall(
            rvalue.ll_fromvalue,
            [self.s_JITState, r_green.annotation()],
            [v_jitstate,      v_value],
            self.s_RedBox)
        return v_box
        

    def build_box_list(self, llops, boxes_v):
        type_erased_v = [llops.convertvar(v_box, self.r_RedBox,
                                          self.r_box_list.item_repr)
                         for v_box in boxes_v]
        v_boxes = rlist.newlist(llops, self.r_box_list, type_erased_v)
        return v_boxes

    def read_out_box(self, llops, v_jitstate, i):
        c_i = rmodel.inputconst(lltype.Signed, i)
        v_box = llops.genmixlevelhelpercall(rtimeshift.getlocalbox,
                    [self.s_JITState, annmodel.SomeInteger(nonneg=True)],
                    [v_jitstate     , c_i                              ],
                    self.s_RedBox)
        return v_box

 
    def insert_bookkeeping_enter(self, block, nentrylinks, is_returnblock):
        if nentrylinks == 1 and not is_returnblock:
            # simple non-merging and non-returning case: nothing to do 
            return

        split_block_at_start(self.hannotator, block)
        before_block = block
        newinputargs = before_block.inputargs
        llops = HintLowLevelOpList(self)
        v_boxes = self.pack_state_into_boxes(llops, newinputargs)

        # fill the block with logic
        cache = self.bookkeeping_enter_for_join(newinputargs,
                                                before_block,
                                                llops,
                                                v_boxes,
                                                is_returnblock)
        if is_returnblock:
            assert self.return_cache is None
            self.return_cache = cache
        

    # insert before join blocks a block with:
    #
    #     finished_flag = merge_point(jitstate, key, boxes)
    #     where
    #         key = (current-green-values)       
    #         boxes = [current-redboxes]
    #         merge_point = (lambda jitstate, key, boxes:
    #                        rtimeshift.retrieve_jitstate_for_merge(
    #                            constant {}, jitstate,
    #                            key, boxes))
    #     if finished_flag then go to dispatch_block
    #     else go to read_boxes_block
    #
    # it also inserts another block 'read_boxes_block' which reads the
    # redboxes back out 'jitstate.local_boxes' and pass them along to
    # the original block, together with the 'jitstate' as usual
    #
    # for the return block case (which is always considered a join block) the
    # 'read_boxes_block' is special:
    #
    #     rtimeshift.save_return(jitstate)
    #     go to dispatch_block
    #
    # retrieve_jitstate_for_merge is supposed to use the "constant" dict as
    # the cache that maps green values combinations to frozen states for red
    # boxes values and generated blocks
    #
    # if finished_flag is True, it means an old state/block could be reused
    # and execution continues to the dispatch_block
    #
    def bookkeeping_enter_for_join(self, newinputargs, before_block,
                                   llops, v_boxes, is_returnblock):
        getrepr = self.rtyper.getrepr        
        items_s = []
        key_v = []
        orig_key_v = []
        for newvar in newinputargs:
            r = self.hrtyper.bindingrepr(newvar)
            if isinstance(r, GreenRepr) and r.lowleveltype is not lltype.Void:
                r_from = getrepr(r.annotation())
                s_erased = r.erased_annotation()
                r_to = getrepr(s_erased)
                items_s.append(s_erased)
                v_erased = llops.convertvar(newvar, r_from, r_to)
                orig_key_v.append(newvar)
                key_v.append(v_erased)

        s_key_tuple = annmodel.SomeTuple(items_s)
        r_key = getrepr(s_key_tuple)
        r_key.setup()
        v_key = rtuple.newtuple(llops, r_key, key_v)

        v_jitstate = llops.getjitstate()

        cache = {}
        self.statecaches.append(cache)

        def merge_point(jitstate, key, boxes):
            return rtimeshift.retrieve_jitstate_for_merge(cache, jitstate,
                                                          key, boxes)

        v_finished_flag = llops.genmixlevelhelpercall(merge_point,
              [self.s_JITState, s_key_tuple, self.s_box_list],
              [v_jitstate, v_key, v_boxes],
              annmodel.SomeBool())

        # now read out the possibly modified red boxes out of v_boxes
        
        read_boxes_block_vars = []
        for greenvar in orig_key_v:
            read_boxes_block_vars.append(copyvar(None, greenvar))

        read_boxes_block = flowmodel.Block(read_boxes_block_vars)
        to_read_boxes_block = flowmodel.Link(orig_key_v, read_boxes_block)
        to_read_boxes_block.exitcase = to_read_boxes_block.llexitcase = False


        to_dispatch_block = flowmodel.Link([], self.dispatchblock)
        to_dispatch_block.exitcase = to_dispatch_block.llexitcase = True
        

        next_block = before_block.exits[0].target

        before_block.operations[:] = llops        
        before_block.exitswitch = v_finished_flag
        before_block.recloseblock(to_read_boxes_block,
                                  to_dispatch_block)

        llops = HintLowLevelOpList(self)
        v_jitstate2 = llops.getjitstate()
        
        linkargs = []
        if not is_returnblock:
            i = 0
            j = 0
            for newvar in newinputargs:
                r = self.hrtyper.bindingrepr(newvar)
                if isinstance(r, RedRepr):
                    linkargs.append(self.read_out_box(llops, v_jitstate2, i))
                    i += 1
                else:
                    linkargs.append(read_boxes_block_vars[j])
                    j += 1
            target = next_block
        else:
            # xxx reorganize
            llops.genmixlevelhelpercall(rtimeshift.save_return,
                                        [self.s_JITState],
                                        [v_jitstate2],
                                        annmodel.s_None)
            target = self.dispatchblock
            
        read_boxes_block.operations[:] = llops
        to_target = flowmodel.Link(linkargs, target)
        read_boxes_block.closeblock(to_target)

        return cache

    # insert at the end  of blocks the following logic:
    # if the block is the returnblock:
    #
    #     go to dispatch_block
    #
    # if the block has just one exit or the exitswitch is green:
    #
    #     <nothing>
    #
    # if the block has more than one exit (split case):
    #
    #     res = rtimeshift.leave_block_split(jitstate,
    #                                        exitswitchredbox, exitindex,
    #                                        true_case_boxes,
    #                                        false_case_boxes)
    #     where
    #         true_case_boxes = [redboxes going into the true case link]
    #         false_case_boxes = [redbox going into the false case link
    #             + green values going into it wrapped into redboxes,
    #               all to be saved for later dispatch]
    #         exitindex = number identifying the false branch of the switch
    #     if res then go to true_exit_block
    #     else go to false_exit_block
    #
    # exitindex is computed by getexitindex, see comment for that method
    #
    # leave_block_split if the exitswitchredbox is constant just
    # returns its value as res otherwise returns True
    # and schedule the false case
    #
    def insert_bookkeeping_leave_block(self, block):
        exits = block.exits
        exitswitch = block.exitswitch

        if len(exits) == 0: # this is the original returnblock
            block.recloseblock(flowmodel.Link([], self.dispatchblock))
        elif (len(exits) == 1 or
              isinstance(self.hrtyper.bindingrepr(exitswitch), GreenRepr)):
            pass # nothing to do
        else:
            llops = HintLowLevelOpList(self)
            v_jitstate = llops.getjitstate()
            assert len(exits) == 2
            false_exit, true_exit = exits
            if true_exit.exitcase is False:
                true_exit, false_exit = false_exit, true_exit
            assert true_exit.exitcase is True
            assert false_exit.exitcase is False
            # sanitize llexitcase
            true_exit.llexitcase = True
            false_exit.llexitcase = False
            v_boxes_true = self.pack_state_into_boxes(llops,
                                                      true_exit.args)
            v_boxes_false = self.pack_state_into_boxes(llops,
                                                       false_exit.args,
                                                       pack_greens_too = True)
            exitindex = self.getexitindex(false_exit)
            c_exitindex = rmodel.inputconst(lltype.Signed, exitindex)
            v_res = llops.genmixlevelhelpercall(rtimeshift.leave_block_split,
                                                [self.s_JITState,
                                                 self.s_RedBox,
                                                 annmodel.SomeInteger(),
                                                 self.s_box_list,
                                                 self.s_box_list],
                                                [v_jitstate,
                                                 exitswitch,
                                                 c_exitindex,
                                                 v_boxes_true,
                                                 v_boxes_false],
                                                annmodel.SomeBool())
            block.exitswitch = v_res
            block.operations.extend(llops)


    def pack_state_into_boxes(self, llops, statevars, pack_greens_too=False):
        v_jitstate = None
        boxes_v = []
        for var in statevars:
            if isinstance(var, flowmodel.Constant):
                continue    # it's correspondingly skipped in getexitindex()
            r = self.hrtyper.bindingrepr(var)
            if isinstance(r, RedRepr):
                boxes_v.append(var)
            elif isinstance(r, GreenRepr):
                if pack_greens_too:
                    if v_jitstate is None:
                        v_jitstate = llops.getjitstate()
                    v_box = self.make_const_box(llops, r, var, v_jitstate)
                    boxes_v.append(v_box)
            else:
                raise RuntimeError('Unsupported boxtype')
        return self.build_box_list(llops, boxes_v)

    # put the following logic in the dispatch block:
    #
    #    nextjitstate = dispatch_next(jitstate)
    #    setjitstate(nextjitstate)
    #    next = getexitindex(nextjitstate)
    #    switch next:
    #    <exitindex>:
    #        go to reentry_block<exitindex>
    #    ...
    #    default:
    #        return nextjitstate
    #
    #     where
    #         dispatch_next = (lambda jitstate:
    #                           rtimeshift.dispatch_next(jitstate,
    #                               return_cache))
    #         where return_cache is a predefined cache
    #
    def insert_dispatch_logic(self):
        dispatchblock = self.dispatchblock

        llops = HintLowLevelOpList(self)

        return_cache = self.return_cache
        assert return_cache is not None
        #RETURN_TYPE = self.r_returnvalue.original_concretetype

        def dispatch_next(jitstate):
            return rtimeshift.dispatch_next(jitstate, return_cache)

        v_nextjitstate = llops.genmixlevelhelpercall(dispatch_next,
                                             [self.s_JITState    ],
                                             [llops.getjitstate()],
                                             self.s_JITState)
        llops.setjitstate(v_nextjitstate)
        v_next = llops.genmixlevelhelpercall(rtimeshift.getexitindex,
                                             [self.s_JITState],
                                             [v_nextjitstate],
                                             annmodel.SomeInteger())
        dispatchblock.operations = list(llops)

        # make a new return block
        returnblock = flowmodel.Block([])
        returnblock.operations = ()
        self.graph.returnblock = returnblock

        # produce the dispatch switch
        dispatch_to = self.dispatch_to
        return_link = flowmodel.Link([], returnblock)
        dispatch_to.append(('default', return_link))

        if len(dispatch_to) == 1:
            dispatchblock.closeblock(return_link)
        else:        
            dispatchblock.exitswitch = v_next
            exitlinks = []
            for case, link in dispatch_to:
                link.exitcase =  case
                if case != 'default':
                    link.llexitcase = case
                else:
                    link.llexitcase = None
                exitlinks.append(link)
            dispatchblock.closeblock(*exitlinks)


    def timeshift_block(self, timeshifted_blocks, block):
        hrtyper = self.hrtyper
        blocks = [block]
        i = 0
        # XXX in-progress, split block at direct_calls for call support 
        while i < len(block.operations):
            op = block.operations[i]
            if (op.opname in ('direct_call', 'indirect_call')
                and hrtyper.guess_call_kind(op) == 'red'):

                link = support.split_block_with_keepalive(block, i+1,
                                         annotator=self.hannotator)

                # the 'save_locals' pseudo-operation is used to save all
                # alive local variables into the current JITState
                vars_to_save = []
                for var in link.args:
                    if isinstance(var, flowmodel.Variable):
                        if var is not op.result:
                            r = hrtyper.bindingrepr(var)
                            if isinstance(r, RedRepr):
                                vars_to_save.append(var)

                assert op is block.operations[i]
                assert len(block.operations) == i+1
                v_dummy = varoftype(lltype.Void)
                self.hannotator.setbinding(v_dummy, annmodel.s_ImpossibleValue)
                extraop = flowmodel.SpaceOperation('save_locals',
                                                   vars_to_save,
                                                   v_dummy)
                block.operations.insert(i, extraop)

                replacement = {}
                for i, var in enumerate(vars_to_save):
                    newvar = copyvar(self.hannotator, var)
                    c_index = flowmodel.Constant(i, concretetype=lltype.Signed)
                    extraop = flowmodel.SpaceOperation('restore_local',
                                                       [c_index],
                                                       newvar)
                    block.operations.append(extraop)
                    replacement[var] = newvar

                if isinstance(hrtyper.bindingrepr(op.result), RedRepr):
                    var = op.result
                    newvar = copyvar(self.hannotator, var)
                    extraop = flowmodel.SpaceOperation('fetch_return',
                                                       [],
                                                       newvar)
                    block.operations.append(extraop)
                    replacement[var] = newvar

                link.args = [replacement.get(var, var) for var in link.args]
                block = link.target
                blocks.append(block)
                self.hannotator.annotated[block] = self.graph
                # for now the call doesn't return its redbox result, but only
                # has the hidden side-effect of putting it in the jitstate
                op.result = varoftype(lltype.Void)
                self.hannotator.setbinding(op.result,
                                           annmodel.s_ImpossibleValue)
                i = 0
                continue
            i += 1
        for block in blocks:
            hrtyper.specialize_block(block)
        timeshifted_blocks.extend(blocks)

    def originalconcretetype(self, var):
        return originalconcretetype(self.hannotator.binding(var))
