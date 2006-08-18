import py
from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow import model as flowmodel
from pypy.annotation import model as annmodel
from pypy.annotation import listdef, dictdef
from pypy.jit.timeshifter import rvalue, oop
from pypy.jit.timeshifter.rtimeshift import JITState, ResidualGraphBuilder
from pypy.rpython import rmodel, rgenop, annlowlevel
from pypy.rpython.lltypesystem import rtuple, rlist, rdict
from pypy.jit.timeshifter import rtimeshift
from pypy.jit.timeshifter.rtyper import HintRTyper, originalconcretetype
from pypy.jit.timeshifter.rtyper import GreenRepr, RedRepr, HintLowLevelOpList
from pypy.translator.unsimplify import varoftype, copyvar
from pypy.translator.backendopt import support

# ___________________________________________________________

class HintTimeshift(object):
    
    def __init__(self, hannotator, rtyper):
        self.hannotator = hannotator
        self.rtyper = rtyper
        self.hrtyper = HintRTyper(hannotator, self)
        self.latestexitindex = -1
        self.block2jitstate = {}
        self.return_cache = None
        self.annhelper = annlowlevel.MixLevelHelperAnnotator(rtyper)

        self.s_ResidualGraphBuilder, self.r_ResidualGraphBuilder = self.s_r_instanceof(ResidualGraphBuilder)
        self.s_JITState, self.r_JITState = self.s_r_instanceof(JITState)
        self.s_RedBox, self.r_RedBox = self.s_r_instanceof(rvalue.RedBox)
        self.s_OopSpecDesc, self.r_OopSpecDesc = self.s_r_instanceof(
            oop.OopSpecDesc)

        getrepr = self.rtyper.getrepr

        bk = rtyper.annotator.bookkeeper
        box_list_def = listdef.ListDef(None, self.s_RedBox)
        box_list_def.mutate()
        self.s_box_list = annmodel.SomeList(box_list_def)
        self.r_box_list = getrepr(self.s_box_list)
        self.r_box_list.setup()

        box_accum_def = listdef.ListDef(None, self.s_RedBox)
        box_accum_def.mutate()
        box_accum_def.resize()
        self.s_box_accum = annmodel.SomeList(box_accum_def)
        self.r_box_accum = getrepr(self.s_box_accum)
        self.r_box_accum.setup()

        self.ll_make_builder_graph = self.annhelper.getgraph(
            rtimeshift.ll_make_builder,
            [], self.s_ResidualGraphBuilder)
        self.ll_int_box_graph = self.annhelper.getgraph(
            rtimeshift.ll_int_box,
            [rgenop.s_ConstOrVar, rgenop.s_ConstOrVar],
            self.s_RedBox)
        self.ll_addr_box_graph = self.annhelper.getgraph(
            rtimeshift.ll_addr_box,
            [rgenop.s_ConstOrVar, rgenop.s_ConstOrVar],
            self.s_RedBox)
        self.ll_double_box_graph = self.annhelper.getgraph(
            rtimeshift.ll_int_box,
            [rgenop.s_ConstOrVar, rgenop.s_ConstOrVar],
            self.s_RedBox)
        self.ll_geninputarg_graph = self.annhelper.getgraph(
            rtimeshift.ll_geninputarg,
            [self.s_ResidualGraphBuilder, annmodel.SomePtr(rgenop.CONSTORVAR)],
            rgenop.s_ConstOrVar)
        self.ll_end_setup_builder_graph = self.annhelper.getgraph(
            rtimeshift.ll_end_setup_builder,
            [self.s_ResidualGraphBuilder],
            annmodel.SomePtr(rgenop.BLOCK))

##         self.ll_close_jitstate_graph = self.annhelper.getgraph(
##             rtimeshift.ll_close_jitstate,
##             [self.s_JITState],
##             annmodel.s_None)

        self.ll_close_builder_graph = self.annhelper.getgraph(
            rtimeshift.ll_close_builder,
            [self.s_ResidualGraphBuilder],
            annmodel.s_None)

    def s_r_instanceof(self, cls, can_be_None=True):
        # Return a SomeInstance / InstanceRepr pair correspnding to the specified class.
        classdesc = self.rtyper.annotator.bookkeeper.getdesc(cls)
        classdef = classdesc.getuniqueclassdef()
        s_instance = annmodel.SomeInstance(classdef, can_be_None)
        r_instance = self.annhelper.getdelayedrepr(s_instance)
        return s_instance, r_instance

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
    def getexitindex(self, link, inputargs, args_r, entering_links):
        self.latestexitindex += 1
        v_jitstate = varoftype(self.r_JITState.lowleveltype, 'jitstate')
        v_boxes = varoftype(self.r_box_accum.lowleveltype, 'boxes')
      
        reentry_block = flowmodel.Block([v_jitstate, v_boxes])

        llops = HintLowLevelOpList(self, None)

        reenter_vars = [v_jitstate]
        for var in link.args[1:]:
            if isinstance(var, flowmodel.Constant):
                reenter_vars.append(var)
                continue
            i = inputargs.index(var)
            r = args_r[i]
            v_box = self.read_out_box(llops, v_boxes, i)
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
        self.annhelper.finish()

    def timeshift_graph(self, graph):
        self.graph = graph
        self.dispatch_to = []
        self.statecaches = []
        entering_links = flowmodel.mkentrymap(graph)

        originalblocks = list(graph.iterblocks())
        timeshifted_blocks = []
        for block in originalblocks:
            self.timeshift_block(timeshifted_blocks, entering_links,  block)
        originalblocks = timeshifted_blocks

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
                                          len(block_entering_links))
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

    def insert_start_setup(self):
        newstartblock = self.insert_before_block(self.graph.startblock, None, closeblock=True)
        v_builder = varoftype(self.r_ResidualGraphBuilder.lowleveltype, 'builder')
        v_jitstate = newstartblock.inputargs[0]
        newstartblock.inputargs[0] = v_builder
        llops = HintLowLevelOpList(self, None)

        llops.genop('direct_call', [self.c_ll_clearcaches_ptr])
        v_jitstate1 = llops.genmixlevelhelpercall(rtimeshift.enter_graph,
                                                  [self.s_ResidualGraphBuilder],
                                                  [v_builder],
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
                    
    def insert_before_block(self, block, entering_links, closeblock=True):
        newinputargs = [copyvar(self.hannotator, var) for var in block.inputargs]

        newblock = flowmodel.Block(newinputargs)
        if block.isstartblock: # xxx
            block.isstartblock = False
            newblock.isstartblock = True
            self.graph.startblock = newblock
        else:
            for link in entering_links:
                link.settarget(newblock)

        if closeblock:
            bridge = flowmodel.Link(newinputargs, block)
            newblock.closeblock(bridge)
        return newblock

    def make_const_box(self, llops, r_green, v_value):
        v_box = llops.genmixlevelhelpercall(
            rvalue.ll_fromvalue,
            [r_green.annotation()], [v_value], self.s_RedBox)
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

    # insert before non-join blocks a block with:
    #
    #     newjitstate = rtimeshift.enter_block(jitstate, boxes)
    #     where boxes = [current-redboxes]
    #
    # then pass the newjitstate (XXX modified?) and boxes
    # to the block original; boxes are modified in place
    #
    def bookkeeping_enter_simple(self, args_r, newinputargs, before_block,
                                 llops, v_boxes, is_returnblock=False):
        v_newjitstate = llops.genmixlevelhelpercall(rtimeshift.enter_block,
                             [self.s_JITState, self.s_box_list],
                             [newinputargs[0], v_boxes],
                             self.s_JITState)

        bridge = before_block.exits[0]
        # not used any more: v_boxes is not modified by enter_block() nowadays
        #self.insert_read_out_boxes(bridge, llops, v_newjitstate, v_boxes, args_r, newinputargs)
        before_block.operations[:] = llops

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
                erased_s = r.erased_annotation()
                r_to = getrepr(erased_s)
                items_s.append(erased_s)
                erased_v = llops.convertvar(newvar, r_from, r_to)
                orig_key_v.append(newvar)
                key_v.append(erased_v)

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

    # insert after blocks the following logic:
    # if the original block is the returnblock:
    #
    #     go to dispatch_block(jitstate)
    #
    # if the original block has just one exit or the exitswitch is green:
    #
    #     newjitstate = rtimeshift.leave_block(jitstate)
    #
    # if the original block has more than one exit (split case):
    #
    #     res = rtimeshift.leave_block_split(jitstate, exitswitchredbox, exitindex, boxes)
    #     where
    #         boxes =[boxes-for-all-current-red-and-green-values]
    #         exitindex = number identifying the false branch of the switch
    #     if res then go to true_exit_block
    #     else go to false_exit_block
    #
    # exitindex is computed by getexitindex, see comment for that method
    #
    # leave_block_split if the exitswitchredbox is constant just returns its value as res
    # otherwise returns True and schedule the false case
    #
    def insert_bookkeeping_leave_block(self, block, entering_links):
        # XXX wrong with exceptions as much else
        
        renamemap = {}
        rename = lambda v: renamemap.get(v, v)
        inargs = []

        def introduce(v):
            if isinstance(v, flowmodel.Variable):
                if v not in renamemap:
                    vprime = renamemap[v] = copyvar(self.hannotator, v)
                    inargs.append(v)

        orig_v_jitstate = block.inputargs[0]
        introduce(orig_v_jitstate)

        newlinks = []

        v_newjitstate = varoftype(self.r_JITState.lowleveltype, 'jitstate')
        self.hannotator.bindings[v_newjitstate] = self.s_JITState

        def rename_on_link(v):
            if v is orig_v_jitstate:
                return v_newjitstate
            else:
                return rename(v)

        for link in block.exits:
            for v in link.args:
                introduce(v)
            newlink =  link.copy(rename_on_link)
            newlink.llexitcase = newlink.exitcase # sanitize the link llexitcase
            newlinks.append(newlink)
            target = link.target
            # update entering_links as necessary
            if target in entering_links:
                target_entering_links = entering_links[target]
                target_entering_links.remove(link)
                target_entering_links.append(newlink)
        introduce(block.exitswitch)

        inputargs = [rename(v) for v in inargs]
        newblock = flowmodel.Block(inputargs)
        newblock.closeblock(*newlinks)
            
        inlink = flowmodel.Link(inargs, newblock)
        oldexitswitch = block.exitswitch
        block.exitswitch = None
        block.recloseblock(inlink)

        llops = HintLowLevelOpList(self, None)
        if len(newblock.exits) == 0: # this is the original returnblock
            newblock.recloseblock(flowmodel.Link(newblock.inputargs, self.dispatchblock))
        elif len(newblock.exits) == 1 or isinstance(self.hrtyper.bindingrepr(oldexitswitch), GreenRepr):
            newblock.exitswitch = rename(oldexitswitch)
            v_res = llops.genmixlevelhelpercall(rtimeshift.leave_block,
                                                [self.s_JITState],
                                                [rename(orig_v_jitstate)],
                                                self.s_JITState)     

            llops.append(flowmodel.SpaceOperation('same_as',
                                   [v_res],
                                   v_newjitstate))
        else:
            args_r = []
            boxes_v = []
            for var in inputargs[1:]:
                r = self.hrtyper.bindingrepr(var)
                args_r.append(r)
                if isinstance(r, RedRepr):
                    boxes_v.append(var)
                elif isinstance(r, GreenRepr):
                    v_box = self.make_const_box(llops, r, var)
                    boxes_v.append(v_box)
                else:
                    raise RuntimeError('Unsupported boxtype')
            
            v_boxes = self.build_box_list(llops, boxes_v)
            false_exit = [exit for exit in newblock.exits if exit.exitcase is False][0]
            exitindex = self.getexitindex(false_exit, inputargs[1:], args_r, entering_links)
            c_exitindex = rmodel.inputconst(lltype.Signed, exitindex)
            v_jitstate = rename(orig_v_jitstate)
            v_res = llops.genmixlevelhelpercall(rtimeshift.leave_block_split,
                                                [self.s_JITState,
                                                 self.s_RedBox,
                                                 annmodel.SomeInteger(),
                                                 self.s_box_list],
                                                [v_jitstate,
                                                 rename(oldexitswitch),
                                                 c_exitindex,
                                                 v_boxes],
                                                annmodel.SomeBool())
            llops.append(flowmodel.SpaceOperation('same_as',
                                                  [inputargs[0]],
                                                  v_newjitstate))
            newblock.exitswitch = v_res
        newblock.operations[:] = llops

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
    #     builder = prepare_return(jitstate)
    #     where
    #         prepare_return = (lambda jitstate:
    #                           rtimeshift.prepare_return(jitstate, return_cache,
    #                                constTYPE(RETURN_TYPE)))
    #         where return_cache is a predefined cache
    #     return builder 
    #
    def insert_dispatch_logic(self):
        dispatchblock = self.dispatchblock
        [v_jitstate] = dispatchblock.inputargs
        llops = HintLowLevelOpList(self, None)


        v_returnbuilder = varoftype(self.r_ResidualGraphBuilder.lowleveltype, 'builder')
        returnblock = flowmodel.Block([v_returnbuilder])
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
                                             rgenop.constTYPE(RETURN_TYPE))
        llops = HintLowLevelOpList(self, None)
        v_return_builder = llops.genmixlevelhelpercall(prepare_return,
                          [self.s_JITState], [v_jitstate2],
                          self.s_ResidualGraphBuilder)

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
