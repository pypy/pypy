import py, types
from pypy.rpython.lltypesystem import lltype
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
from pypy.translator.unsimplify import varoftype, copyvar
from pypy.translator.backendopt import support
from pypy.jit.codegen import model as cgmodel

# ___________________________________________________________

class HintTimeshift(object):
    
    def __init__(self, hannotator, rtyper, RGenOp):
        self.hannotator = hannotator
        self.rtyper = rtyper
        self.RGenOp = RGenOp
        self.hrtyper = HintRTyper(hannotator, self)
        self.latestexitindex = -1
        self.annhelper = annlowlevel.MixLevelHelperAnnotator(rtyper)

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
        box_list_def = listdef.ListDef(None, self.s_RedBox, mutated = True)
        self.s_box_list = annmodel.SomeList(box_list_def)
        self.r_box_list = getrepr(self.s_box_list)
        self.r_box_list.setup()

        box_accum_def = listdef.ListDef(None, self.s_RedBox, resized = True)
        self.s_box_accum = annmodel.SomeList(box_accum_def)
        self.r_box_accum = getrepr(self.s_box_accum)
        self.r_box_accum.setup()

    def s_r_instanceof(self, cls, can_be_None=True):
        # Return a SomeInstance / InstanceRepr pair correspnding to the specified class.
        return self.annhelper.s_r_instanceof(cls, can_be_None=can_be_None)

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
    def getexitindex(self, link, entering_links):
        self.latestexitindex += 1
        v_jitstate = varoftype(self.r_JITState.lowleveltype, 'jitstate')
        v_boxes = varoftype(self.r_box_accum.lowleveltype, 'boxes')
      
        reentry_block = flowmodel.Block([v_jitstate, v_boxes])

        llops = HintLowLevelOpList(self, None)

        reenter_vars = [v_jitstate]
        i = 0
        for var in link.args[1:]:
            if isinstance(var, flowmodel.Constant):
                reenter_vars.append(var)
                continue
            r = self.hrtyper.bindingrepr(var)
            v_box = self.read_out_box(llops, v_boxes, i)
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
        if link.target in entering_links: # update entering_links
            entering_links[link.target].append(reenter_link)
        
        reentry_block.operations[:] = llops
        reentry_block.closeblock(reenter_link)

        from_dispatch =flowmodel.Link([None, None], reentry_block)
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
        self.graph = graph
        self.dispatch_to = []
        self.statecaches = []
        self.block2jitstate = {}
        self.return_cache = None
        entering_links = flowmodel.mkentrymap(graph)

        originalblocks = list(graph.iterblocks())
        timeshifted_blocks = []
        for block in originalblocks:
            self.timeshift_block(timeshifted_blocks, entering_links,  block)
        originalblocks = timeshifted_blocks

        inputlinkcounters = {}
        for block in originalblocks:
            inputlinkcounters[block] = len(entering_links[block])

        returnblock = graph.returnblock
        self.r_returnvalue = self.hrtyper.bindingrepr(returnblock.inputargs[0])
        returnblock.operations = []
        graph.returnblock = None
        # we need to get the jitstate to the before block of the return block
        self.dispatchblock = flowmodel.Block([])
        self.insert_jitstate_arg(self.dispatchblock)
#        before_returnblock = self.insert_before_block(returnblock,
#                                 entering_links[returnblock],
#                                 closeblock=False)
        # fix its concretetypes
        #self.hrtyper.setup_block_entry(before_returnblock)
        #self.insert_jitstate_arg(before_returnblock)
        for block in originalblocks:
            self.insert_jitstate_arg(block)            

        for block in originalblocks:
            block_entering_links = entering_links.pop(block)
            before_block = self.insert_before_block(block,
                                                    block_entering_links)
            self.insert_bookkeeping_enter(block, before_block,
                                          inputlinkcounters[block])
            self.insert_bookkeeping_leave_block(block, entering_links)

        #self.hrtyper.insert_link_conversions(before_returnblock)
        # add booking logic
        #self.insert_return_bookkeeping(before_returnblock)

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
        #print 'timeshift_graph END', graph

    def insert_start_setup(self):
        newstartblock = self.insert_before_block(self.graph.startblock, None, closeblock=True)
        v_backstate = varoftype(self.r_JITState.lowleveltype, 'backstate')
        v_jitstate = newstartblock.inputargs[0]
        newstartblock.inputargs[:1] = [v_backstate]
        llops = HintLowLevelOpList(self, None)

        llops.genop('direct_call', [self.c_ll_clearcaches_ptr])
        v_jitstate1 = llops.genmixlevelhelpercall(rtimeshift.enter_graph,
                               [self.s_JITState],
                               [v_backstate],
                               self.s_JITState)
        llops.append(flowmodel.SpaceOperation('same_as', [v_jitstate1], v_jitstate))
        newstartblock.operations = list(llops)
        
    def insert_jitstate_arg(self, block):
        # pass 'jitstate' as an extra argument around the whole graph
        #if block.operations != ():
            v_jitstate = self.getjitstate(block)
            block.inputargs.insert(0, v_jitstate)
            for link in block.exits:
                #if link.target.operations != ():
                link.args.insert(0, v_jitstate)
                #elif len(link.args) == 1:
                #    assert False, "the return block should not be seen"
                    
    def insert_before_block(self, block, block_entering_links, closeblock=True):
        newinputargs = [copyvar(self.hannotator, var) for var in block.inputargs]

        newblock = flowmodel.Block(newinputargs)
        if block.isstartblock: # xxx
            block.isstartblock = False
            newblock.isstartblock = True
            self.graph.startblock = newblock
        else:
            for link in block_entering_links:
                link.settarget(newblock)

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
        
                                                         
    def read_out_box(self, llops, v_boxes, i):
        c_i = rmodel.inputconst(lltype.Signed, i)
        v_box = llops.gendirectcall(rlist.ll_getitem_fast, v_boxes, c_i)

        v_box = llops.convertvar(v_box, self.r_box_list.item_repr, self.r_RedBox)
        return v_box

    def insert_read_out_boxes(self, bridge, llops, v_newjitstate, v_boxes, args_r, newinputargs):
        newinputargs2 = [v_newjitstate]
        if bridge.target.operations == (): # special case the return block
            assert False, "the return block should not be seen"
        else:
            i = 0
            for r, newvar in zip(args_r[1:], newinputargs[1:]):
                if isinstance(r, RedRepr):
                    newinputargs2.append(self.read_out_box(llops, v_boxes, i))
                    i += 1
                else:
                    newinputargs2.append(newvar)

        # patch bridge
        bridge.args = newinputargs2 # patch the link

 
    def insert_bookkeeping_enter(self, block, before_block, nentrylinks):
        newinputargs = before_block.inputargs
        args_r = []
        for var in newinputargs:
            args_r.append(self.hrtyper.bindingrepr(var))
            
        llops = HintLowLevelOpList(self, None)


        TYPES = []
        boxes_v = []
        for r, newvar in zip(args_r, newinputargs):
            if isinstance(r, RedRepr):
                boxes_v.append(newvar)
                TYPES.append(r.original_concretetype)                
        getrepr = self.rtyper.getrepr

        v_boxes = self.build_box_list(llops, boxes_v)

        is_returnblock = len(block.exits) == 0
        if nentrylinks > 1 or is_returnblock:
            enter_block_logic = self.bookkeeping_enter_for_join
        else:
            enter_block_logic = self.bookkeeping_enter_simple


        # fill the block with logic
        cache = enter_block_logic(args_r, newinputargs,
                                  before_block,
                                  llops,
                                  v_boxes,
                                  is_returnblock)
        if is_returnblock:
            assert self.return_cache is None
            self.return_cache = cache

    def build_box_list(self, llops, boxes_v):
        type_erased_v = [llops.convertvar(v_box, self.r_RedBox,
                                          self.r_box_list.item_repr)
                         for v_box in boxes_v]
        v_boxes = rlist.newlist(llops, self.r_box_list, type_erased_v)
        return v_boxes


    def bookkeeping_enter_simple(self, args_r, newinputargs, before_block,
                                 llops, v_boxes, is_returnblock=False):
        return None

    # insert before join blocks a block with:
    #
    #     newjiststate = merge_point(jitstate, key, boxes)
    #     where
    #         key = (current-green-values)       
    #         boxes = [current-redboxes]
    #         merge_point = (lambda jitstate, key, boxes:
    #                        rtimeshift.retrieve_jitstate_for_merge(
    #                            constant {}, jitstate,
    #                            key, boxes))
    #     if newjistate is None then go to dispatch_block(jitstate)
    #     else go to read_boxes_block(newjiststate, boxes)
    #
    # and the other block read_boxes_block which reads the redboxes back out boxes
    # and pass them along to the original block together with the new jitstate
    #
    # for the return block case (which is always considered a join block) the
    # read_boxes_block is special:
    #
    #     rtimeshift.save_return(newjitstate, boxes)
    #     go to dispatch_block(newjitstate)
    #
    # retrieve_jitstate_for_merge is supposed to use the "constant" dict as cache
    # mapping green values combinations to frozen states for red boxes values
    # and generated blocks
    #
    # if the newjitstate is None, it means an old state/block could be reused
    # and execution continues to the dispatch_block
    #
    def bookkeeping_enter_for_join(self, args_r, newinputargs, before_block,
                                   llops, v_boxes, is_returnblock):
        getrepr = self.rtyper.getrepr        
        items_s = []
        key_v = []
        orig_key_v = []
        for r, newvar in zip(args_r, newinputargs):
            if isinstance(r, GreenRepr):
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

        v_oldjitstate = newinputargs[0]

        cache = {}
        self.statecaches.append(cache)

        def merge_point(jitstate, key, boxes):
            return rtimeshift.retrieve_jitstate_for_merge(cache, jitstate,
                                                          key, boxes)

        v_newjitstate = llops.genmixlevelhelpercall(merge_point,
              [self.s_JITState, s_key_tuple, self.s_box_list],
              [v_oldjitstate, v_key, v_boxes],
              self.s_JITState)

        v_continue = llops.genop('ptr_nonzero', [v_newjitstate], resulttype=lltype.Bool)

        # now read out the possibly modified red boxes out of v_boxes

        v_newjitstate2 = varoftype(self.r_JITState.lowleveltype, v_newjitstate)
        v_boxes2 = varoftype(self.r_box_list.lowleveltype, v_boxes)
        
        read_boxes_block_vars = [v_newjitstate2, v_boxes2]
        for greenvar in orig_key_v:
            read_boxes_block_vars.append(copyvar(None, greenvar))

        read_boxes_block = flowmodel.Block(read_boxes_block_vars)
        to_read_boxes_block = flowmodel.Link([v_newjitstate, v_boxes] + orig_key_v, read_boxes_block)
        to_read_boxes_block.exitcase = to_read_boxes_block.llexitcase = True


        to_dispatch_block = flowmodel.Link([v_oldjitstate], self.dispatchblock)
        to_dispatch_block.exitcase = to_dispatch_block.llexitcase = False
        
        target = before_block.exits[0].target
        before_block.operations[:] = llops        
        before_block.exitswitch = v_continue
        before_block.recloseblock(to_dispatch_block, to_read_boxes_block)

        llops = HintLowLevelOpList(self, None)

        newinputargs2 = [v_newjitstate2]
        if not is_returnblock:
            i = 0
            j = 0
            for r in args_r[1:]:
                if isinstance(r, RedRepr):
                    newinputargs2.append(self.read_out_box(llops, v_boxes2, i))
                    i += 1
                else:
                    newinputargs2.append(read_boxes_block_vars[j+2])
                    j += 1
        else:
            # xxx reorganize
            llops.genmixlevelhelpercall(rtimeshift.save_return,
                                        [self.s_JITState, self.s_box_list],
                                        [v_newjitstate2, v_boxes2],
                                        annmodel.s_None)
            target = self.dispatchblock
            
        read_boxes_block.operations[:] = llops

        to_target = flowmodel.Link(newinputargs2, target)

        read_boxes_block.closeblock(to_target)

        return cache

    # insert at the end  of blocks the following logic:
    # if the block is the returnblock:
    #
    #     go to dispatch_block(jitstate)
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
    def insert_bookkeeping_leave_block(self, block, entering_links):
        exits = block.exits
        exitswitch = block.exitswitch

        if len(exits) == 0: # this is the original returnblock
            block.recloseblock(flowmodel.Link(block.inputargs[:1],
                                              self.dispatchblock))
        elif (len(exits) == 1 or
              isinstance(self.hrtyper.bindingrepr(exitswitch), GreenRepr)):
            pass # nothing to do
        else:
            llops = HintLowLevelOpList(self, None)
            v_jitstate = self.getjitstate(block)
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
                                                      true_exit.args[1:],
                                                      v_jitstate,
                                                      pack_greens_too=False)
            v_boxes_false = self.pack_state_into_boxes(llops,
                                                       false_exit.args[1:],
                                                       v_jitstate,
                                                       pack_greens_too=True)
            exitindex = self.getexitindex(false_exit, entering_links)
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


    def pack_state_into_boxes(self, llops, statevars, v_jitstate,
                              pack_greens_too):
        boxes_v = []
        for var in statevars:
            if isinstance(var, flowmodel.Constant):
                continue    # it's correspondingly skipped in getexitindex()
            r = self.hrtyper.bindingrepr(var)
            if isinstance(r, RedRepr):
                boxes_v.append(var)
            elif isinstance(r, GreenRepr):
                if pack_greens_too:
                    v_box = self.make_const_box(llops, r, var, v_jitstate)
                    boxes_v.append(v_box)
            else:
                raise RuntimeError('Unsupported boxtype')
        return self.build_box_list(llops, boxes_v)

    # put the following logic in the dispatch block:
    #
    #    boxes = []
    #    next = rtimeshift.dispatch_next(jitstate, boxes)
    #    switch next:
    #    <exitindex>:
    #        go to reentry_block<exitindex>(jitstate, boxes)
    #    ...
    #    default:
    #        go to prepare_return_block(jitstate)
    #
    # the prepare_return_block does:
    #
    #     returnbox = prepare_return(jitstate)
    #     where
    #         prepare_return = (lambda jitstate:
    #                           rtimeshift.prepare_return(jitstate, return_cache,
    #                                None))) # XXX return type info
    #         where return_cache is a predefined cache
    #     return returnbox
    #
    def insert_dispatch_logic(self):
        dispatchblock = self.dispatchblock
        [v_jitstate] = dispatchblock.inputargs
        llops = HintLowLevelOpList(self, None)


        v_returnbox = varoftype(self.r_RedBox.lowleveltype, 'returnbox')
        returnblock = flowmodel.Block([v_returnbox])
        returnblock.operations = ()
        self.graph.returnblock = returnblock
        
        v_boxes = rlist.newlist(llops, self.r_box_accum, [])
        v_next = llops.genmixlevelhelpercall(rtimeshift.dispatch_next,
                                             [self.s_JITState,
                                              self.s_box_accum],
                                             [v_jitstate, v_boxes],
                                             annmodel.SomeInteger())

        dispatchblock.operations = list(llops)

        dispatch_to = self.dispatch_to
        v_jitstate2 = varoftype(self.r_JITState.lowleveltype, 'jitstate')
        prepare_return_block = flowmodel.Block([v_jitstate2])
        prepare_return_link = flowmodel.Link([v_jitstate], prepare_return_block)
        dispatch_to.append(('default', prepare_return_link))

        if len(dispatch_to) == 1:
            dispatchblock.closeblock(prepare_return_link)
        else:        
            dispatchblock.exitswitch = v_next
            exitlinks = []
            for case, link in dispatch_to:
                link.exitcase =  case
                if case != 'default':
                    link.llexitcase = case
                    link.args = [v_jitstate, v_boxes]
                else:
                    link.llexitcase = None
                exitlinks.append(link)
            dispatchblock.closeblock(*exitlinks)

        return_cache = self.return_cache
        assert return_cache is not None
        RETURN_TYPE = self.r_returnvalue.original_concretetype

        def prepare_return(jitstate):
            return rtimeshift.prepare_return(jitstate, return_cache,
                                             None)
        llops = HintLowLevelOpList(self, None)
        v_return_builder = llops.genmixlevelhelpercall(prepare_return,
                          [self.s_JITState], [v_jitstate2],
                          self.s_RedBox)

        prepare_return_block.operations = list(llops)
        finishedlink = flowmodel.Link([v_return_builder], returnblock)
        prepare_return_block.closeblock(finishedlink)

    def getjitstate(self, block):
        if block not in self.block2jitstate:
            v_jitstate = varoftype(self.r_JITState.lowleveltype, 'jitstate')
            self.block2jitstate[block] = v_jitstate
        return self.block2jitstate[block]

    def timeshift_block(self, timeshifted_blocks, entering_links, block):
        blocks = [block]
        i = 0
        # XXX in-progress, split block at direct_calls for call support 
        while i < len(block.operations):
            op = block.operations[i]
            if op.opname == 'direct_call':
                link = support.split_block_with_keepalive(block, i+1,
                                         annotator=self.hannotator)

                # the 'save_locals' pseudo-operation is used to save all
                # alive local variables into the current JITState
                args = list(link.args)
                while op.result in args:
                    args.remove(op.result)
                assert op is block.operations[i]
                v_dummy = varoftype(lltype.Void)
                self.hannotator.setbinding(v_dummy, annmodel.s_ImpossibleValue)
                extraop = flowmodel.SpaceOperation('save_locals',
                                                   args,
                                                   v_dummy)
                block.operations.insert(i, extraop)

                block = link.target
                entering_links[block] = [link]
                blocks.append(block)
                self.hannotator.annotated[block] = self.graph
                i = 0
                continue
            i += 1
        for block in blocks:
            self.getjitstate(block)   # force this to be precomputed
            self.hrtyper.specialize_block(block)
        timeshifted_blocks.extend(blocks)

    def originalconcretetype(self, var):
        return originalconcretetype(self.hannotator.binding(var))
