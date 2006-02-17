from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow import model as flowmodel
from pypy.annotation import model as annmodel
from pypy.annotation import listdef, dictdef
from pypy.jit.rtimeshift import STATE, STATE_PTR, REDBOX_PTR, VARLIST
from pypy.jit.rtimeshift import make_types_const
from pypy.rpython import rmodel, rtuple, rlist, rdict, rgenop
from pypy.jit import rtimeshift
from pypy.jit.hintrtyper import HintRTyper, s_JITState, originalconcretetype
from pypy.jit.hintrtyper import GreenRepr, RedRepr, HintLowLevelOpList

# ___________________________________________________________

def define_queue_in_state(rtyper, s_item, fieldname):
    queue_def = listdef.ListDef(None,
                                s_item)
    queue_def.resize()
    queue_def.mutate()

    s_queue = annmodel.SomeList(queue_def)

    r_queue = rtyper.getrepr(s_queue)
    r_queue.setup()
    QUEUE = r_queue.lowleveltype

    def ll_get_queue(questate):
        pass
    def _ll_get_queue(questate):
        return getattr(questate, fieldname)

    llgetq = ll_get_queue

    def ll_get_queue_annotation(queustate_s):
        return s_queue

    llgetq.compute_result_annotation = ll_get_queue_annotation

    def ll_get_queue_specialize(hop):
        return hop.gendirectcall(_ll_get_queue, hop.args_v[0])

    llgetq.specialize = ll_get_queue_specialize

    return s_queue, QUEUE, ll_get_queue
 

class HintTimeshift(object):
    
    def __init__(self, hannotator, rtyper):
        self.hannotator = hannotator
        self.rtyper = rtyper
        self.hrtyper = HintRTyper(hannotator, self)
        self.latestexitindex = -1

        getrepr = self.rtyper.getrepr

        box_list_def = listdef.ListDef(None, annmodel.SomePtr(REDBOX_PTR))
        box_list_def.mutate()
        self.s_box_list = annmodel.SomeList(box_list_def)
        self.r_box_list = getrepr(self.s_box_list)
        self.r_box_list.setup()

        box_accum_def = listdef.ListDef(None, annmodel.SomePtr(REDBOX_PTR))
        box_accum_def.mutate()
        box_accum_def.resize()
        self.s_box_accum = annmodel.SomeList(box_accum_def)
        self.r_box_accum = getrepr(self.s_box_accum)
        self.r_box_accum.setup()

        s_return_info = annmodel.SomeTuple([annmodel.SomePtr(rgenop.LINK),
                                           annmodel.SomePtr(REDBOX_PTR)])

        defs = define_queue_in_state(rtyper, s_return_info, 'return_queue')
        s_return_queue, RETURN_QUEUE, ll_get_return_queue = defs

        s_split_info = annmodel.SomeTuple([annmodel.SomeInteger(),
                                           annmodel.SomePtr(STATE_PTR),
                                           self.s_box_list])

        defs = define_queue_in_state(rtyper, s_split_info, 'split_queue')
        s_split_queue, SPLIT_QUEUE, ll_get_split_queue = defs        


        def ll_newstate():
            questate = lltype.malloc(QUESTATE)
            questate.return_queue = RETURN_QUEUE.TO.ll_newlist(0)
            questate.split_queue = SPLIT_QUEUE.TO.ll_newlist(0)
            return questate

        def ll_copystate(questate):
            newquestate = lltype.malloc(QUESTATE)
            newquestate.return_queue = questate.return_queue
            newquestate.split_queue = questate.split_queue
            basestate = questate.basestate
            newbasestate = newquestate.basestate
            newbasestate.curblock = basestate.curblock
            newbasestate.curoutgoinglink = basestate.curoutgoinglink
            newbasestate.curvalue = basestate.curvalue
            return newquestate
        
        QUESTATE = lltype.GcStruct("quejitstate",
                                   ('basestate', STATE),
                                   ("return_queue", RETURN_QUEUE),
                                   ("split_queue", SPLIT_QUEUE),                                   
                                   adtmeths = {
            'll_get_return_queue': ll_get_return_queue,
            'll_get_split_queue': ll_get_split_queue,
            'll_newstate': ll_newstate,
            'll_copystate': ll_copystate,
            'll_basestate': lambda questate: questate.basestate})

        self.s_return_queue = s_return_queue # for the test
        self.QUESTATE_PTR = lltype.Ptr(QUESTATE)

    def getexitindex(self, link, inputargs, args_r):
        self.latestexitindex += 1
        v_jitstate = flowmodel.Variable('jitstate')
        v_jitstate.concretetype = STATE_PTR
        v_boxes = flowmodel.Variable('boxes')
        v_boxes.concretetype = self.r_box_accum.lowleveltype
      
        reentry_block = flowmodel.Block([v_jitstate, v_boxes])

        llops = HintLowLevelOpList(self, None)

        reenter_vars = [v_jitstate]
        for var in link.args[1:]:
            i = inputargs.index(var)
            r = args_r[i]
            v_box = self.read_out_box(llops, v_boxes, i)
            if isinstance(r, RedRepr):
                reenter_vars.append(v_box)
            else:
                c_TYPE = rmodel.inputconst(lltype.Void,
                                           r.lowleveltype)
                v_value = llops.gendirectcall(REDBOX_PTR.TO.ll_getvalue,
                                              v_box, c_TYPE)
                reenter_vars.append(v_value)

        reenter_link = flowmodel.Link(reenter_vars, link.target)
        reentry_block.operations[:] = llops
        reentry_block.closeblock(reenter_link)

        from_dispatch =flowmodel.Link([None, None], reentry_block)
        self.dispatch_to.append((self.latestexitindex, from_dispatch))        
        return self.latestexitindex

    def timeshift(self):
        for graph in self.hannotator.translator.graphs:
            self.timeshift_graph(graph)
        # RType the helpers found during timeshifting
        self.rtyper.specialize_more_blocks()

    def timeshift_graph(self, graph):
        self.graph = graph
        self.dispatch_to = []
        entering_links = flowmodel.mkentrymap(graph)

        originalblocks = list(graph.iterblocks())
        returnblock = graph.returnblock
        # we need to get the jitstate to the before block of the return block
        self.dispatchblock = flowmodel.Block([])
        self.pre_process_block(self.dispatchblock)
        before_returnblock = self.insert_before_block(returnblock,
                                 entering_links[returnblock],
                                 closeblock=False)
        self.pre_process_block(before_returnblock)
        for block in originalblocks:
            self.pre_process_block(block)            

        for block in originalblocks:
            self.timeshift_block(block)
            if block.operations != ():
                block_entering_links = entering_links.pop(block)
                before_block = self.insert_before_block(block, block_entering_links)              
                self.insert_bookkeeping_enter(block, before_block, len(block_entering_links))
                
                self.insert_bookkeeping_leave_block(block, entering_links)

        # fix its concretetypes
        self.hrtyper.setup_block_entry(before_returnblock)
        self.hrtyper.insert_link_conversions(before_returnblock)
        # add booking logic
        self.insert_return_bookkeeping(before_returnblock)

        # fix its concretetypes
        self.hrtyper.setup_block_entry(self.dispatchblock)
        self.insert_dispatch_logic(returnblock)


    def pre_process_block(self, block):
        # pass 'jitstate' as an extra argument around the whole graph
        if block.operations != ():
            v_jitstate = flowmodel.Variable('jitstate')
            self.hannotator.bindings[v_jitstate] = s_JITState
            block.inputargs.insert(0, v_jitstate)
            for link in block.exits:
                if link.target.operations != ():
                    link.args.insert(0, v_jitstate)
                elif len(link.args) == 1:
                    assert False, "the return block should not be seen"
                    
    def insert_before_block(self, block, entering_links, closeblock=True):
        newinputargs = []
        for var in block.inputargs:
            newvar = flowmodel.Variable(var)
            newvar.concretetype = var.concretetype
            self.hannotator.bindings[newvar] = hs = self.hannotator.bindings[var]
            newinputargs.append(newvar)
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
                                                         
    def read_out_box(self, llops, v_boxes, i):
        c_dum_nocheck = rmodel.inputconst(lltype.Void, rlist.dum_nocheck)
        c_i = rmodel.inputconst(lltype.Signed, i)
        v_box = llops.gendirectcall(rlist.ll_getitem_nonneg,
                                    c_dum_nocheck,
                                    v_boxes,
                                    c_i)
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

        # XXX factor this out too!
        v_boxes = rlist.newlist(llops, self.r_box_list, boxes_v)
        c_TYPES = rmodel.inputconst(VARLIST, make_types_const(TYPES))        


        if nentrylinks > 1:
            enter_block_logic = self.bookkeeping_enter_for_join
        else:
            enter_block_logic = self.bookkeeping_enter_simple


        # fill the block with logic
        enter_block_logic(args_r, newinputargs,
                          before_block,
                          llops,
                          v_boxes,
                          c_TYPES)




    def bookkeeping_enter_simple(self, args_r, newinputargs, before_block, llops, v_boxes,
                                c_TYPES):
        v_newjitstate = llops.genmixlevelhelpercall(rtimeshift.enter_block,
                             [annmodel.SomePtr(STATE_PTR), self.s_box_list,
                              annmodel.SomePtr(VARLIST)],
                             [newinputargs[0], v_boxes, c_TYPES])

        bridge = before_block.exits[0]
        self.insert_read_out_boxes(bridge, llops, v_newjitstate, v_boxes, args_r, newinputargs)
        before_block.operations[:] = llops
        
    # insert before join blocks a block with:
    # key = (<tuple-of-green-values>)
    # boxes = [<rest-of-redboxes>]
    # jitstate = ll_retrieve_jitstate_for_merge({}, # <- constant dict (key->...)
    #                  jitstate, key, boxes)
    # and which passes then to the original block the possibly new jitstate,
    # and possible changed redbox read back again out of the 'boxes' list.
    # ll_retrieve_jitstate_for_merge is supposed to use the "constant" dict as cache
    # mapping green values combinations to frozen states for red boxes values
    # and generated blocks
    def bookkeeping_enter_for_join(self, args_r, newinputargs, before_block, llops, v_boxes,
                                  c_TYPES):
        getrepr = self.rtyper.getrepr        
        items_s = []
        key_v = []
        for r, newvar in zip(args_r, newinputargs):
            if isinstance(r, GreenRepr):
                r_from = getrepr(r.annotation())
                erased_s = r.erased_annotation()
                r_to = getrepr(erased_s)
                items_s.append(erased_s)
                erased_v = llops.convertvar(newvar, r_from, r_to)
                key_v.append(erased_v)


        s_key_tuple = annmodel.SomeTuple(items_s)
  
        s_dict_value = annmodel.SomeTuple([self.s_box_list,
                                           annmodel.SomePtr(rgenop.BLOCK)])
        s_state_dic = annmodel.SomeDict(dictdef.DictDef(None,
                                                        s_key_tuple,
                                                        s_dict_value
                                                        ))
        r_key = getrepr(s_key_tuple)

        r_state_dic = getrepr(s_state_dic)
        r_key.setup()

        r_state_dic.setup()

        c_state_dic = rmodel.inputconst(r_state_dic, {})

        v_key = rtuple.newtuple(llops, r_key, key_v)


        v_oldjitstate = newinputargs[0]

        v_newjitstate = llops.genmixlevelhelpercall(rtimeshift.retrieve_jitstate_for_merge,
                             [s_state_dic, annmodel.SomePtr(STATE_PTR), s_key_tuple, self.s_box_list,
                              annmodel.SomePtr(VARLIST)],
                             [c_state_dic, v_oldjitstate, v_key, v_boxes, c_TYPES])

        v_continue = llops.genop('ptr_nonzero', [v_newjitstate], resulttype=lltype.Bool)

        v_newjitstate2 = flowmodel.Variable(v_newjitstate)
        v_newjitstate2.concretetype = STATE_PTR
        v_boxes2 = flowmodel.Variable(v_boxes)
        v_boxes2.concretetype = self.r_box_list.lowleveltype


        
        read_boxes_block_vars = [v_newjitstate2, v_boxes2]
        for greenvar in key_v:
            greenvar2 = flowmodel.Variable(greenvar)
            greenvar2.concretetype = greenvar.concretetype
            read_boxes_block_vars.append(greenvar2)

        read_boxes_block = flowmodel.Block(read_boxes_block_vars)
        to_read_boxes_block = flowmodel.Link([v_newjitstate, v_boxes] + key_v, read_boxes_block)
        to_read_boxes_block.exitcase = to_read_boxes_block.llexitcase = True
        to_dispatch_block = flowmodel.Link([v_oldjitstate], self.dispatchblock)
        to_dispatch_block.exitcase = to_dispatch_block.llexitcase = False
        
        target = before_block.exits[0].target
        before_block.operations[:] = llops        
        before_block.exitswitch = v_continue
        before_block.recloseblock(to_dispatch_block, to_read_boxes_block)

        llops = HintLowLevelOpList(self, None)

        newinputargs2 = [v_newjitstate2]
        i = 0
        j = 0
        for r in args_r[1:]:
            if isinstance(r, RedRepr):
                newinputargs2.append(self.read_out_box(llops, v_boxes2, i))
                i += 1
            else:
                newinputargs2.append(read_boxes_block_vars[j+2])
                j += 1

        read_boxes_block.operations[:] = llops

        to_target = flowmodel.Link(newinputargs2, target)

        read_boxes_block.closeblock(to_target)

        
    def insert_bookkeeping_leave_block(self, block, entering_links):
        # XXX wrong with exceptions as much else
        
        renamemap = {}
        rename = lambda v: renamemap.get(v, v)
        inargs = []

        def introduce(v):
            if isinstance(v, flowmodel.Variable):
                if v not in renamemap:
                    vprime = renamemap[v] = flowmodel.Variable(v)
                    self.hannotator.bindings[vprime] = self.hannotator.bindings[v]
                    vprime.concretetype = v.concretetype
                    inargs.append(v)

        orig_v_jitstate = block.inputargs[0]
        introduce(orig_v_jitstate)

        newlinks = []

        v_newjitstate = flowmodel.Variable('jitstate')
        self.hannotator.bindings[v_newjitstate] = s_JITState
        v_newjitstate.concretetype = STATE_PTR

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
        if len(newblock.exits) == 1 or isinstance(self.hrtyper.bindingrepr(oldexitswitch), GreenRepr):
            newblock.exitswitch = rename(oldexitswitch)
            v_res = llops.genmixlevelhelpercall(rtimeshift.leave_block,
                                                [annmodel.SomePtr(STATE_PTR)],
                                                [rename(orig_v_jitstate)])     

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
                    boxes_v.append(llops.gendirectcall(rtimeshift.REDBOX.ll_make_from_const, var))
                else:
                    raise RuntimeError('Unsupported boxtype')
            
            getrepr = self.rtyper.getrepr

            v_boxes = rlist.newlist(llops, self.r_box_list, boxes_v)
            false_exit = [exit for exit in newblock.exits if exit.exitcase is False][0]
            exitindex = self.getexitindex(false_exit, inputargs[1:], args_r)
            c_exitindex = rmodel.inputconst(lltype.Signed, exitindex)
            v_jitstate = rename(orig_v_jitstate)
            v_quejitstate = llops.genop('cast_pointer', [v_jitstate],
                                        resulttype=self.QUESTATE_PTR)
            v_res = llops.genmixlevelhelpercall(rtimeshift.leave_block_split,
                                                [annmodel.SomePtr(self.QUESTATE_PTR),
                                                 annmodel.SomePtr(REDBOX_PTR),
                                                 annmodel.SomeInteger(),
                                                 self.s_box_list],
                                                [v_quejitstate,
                                                 rename(oldexitswitch),
                                                 c_exitindex,
                                                 v_boxes])
            llops.append(flowmodel.SpaceOperation('same_as',
                                                  [inputargs[0]],
                                                  v_newjitstate))
            newblock.exitswitch = v_res
        newblock.operations[:] = llops

    def insert_return_bookkeeping(self, before_returnblock):
        v_jitstate, v_value = before_returnblock.inputargs
        r_value = self.hrtyper.bindingrepr(v_value)
        llops = HintLowLevelOpList(self, None)
        if isinstance(r_value, GreenRepr):
            v_value = llops.gendirectcall(rtimeshift.REDBOX.ll_make_from_const,
                                          v_value)

        v_quejitstate = llops.genop('cast_pointer', [v_jitstate],
                                    resulttype=self.QUESTATE_PTR)
            
        llops.genmixlevelhelpercall(rtimeshift.schedule_return,
                                    [annmodel.SomePtr(self.QUESTATE_PTR),
                                     annmodel.SomePtr(REDBOX_PTR)],
                                    [v_quejitstate, v_value])

        before_returnblock.operations[:] = llops
        bridge = flowmodel.Link([v_jitstate], self.dispatchblock)
        before_returnblock.closeblock(bridge)

    def insert_dispatch_logic(self, returnblock):
        dispatchblock = self.dispatchblock
        [v_jitstate] = dispatchblock.inputargs
        llops = HintLowLevelOpList(self, None)


        v_boxes = rlist.newlist(llops, self.r_box_accum, [])

        v_quejitstate = llops.genop('cast_pointer', [v_jitstate],
                                    resulttype=self.QUESTATE_PTR)
        
        v_next = llops.genmixlevelhelpercall(rtimeshift.dispatch_next,
                     [annmodel.SomePtr(self.QUESTATE_PTR), self.s_box_accum],
                     [v_quejitstate, v_boxes])

        dispatchblock.operations[:] = llops

        dispatch_to = self.dispatch_to
        finishedlink = flowmodel.Link([v_jitstate], returnblock)
        dispatch_to.append(('default', finishedlink))

        if len(dispatch_to) == 1:
            dispatchblock.closeblock(finishedlink)
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

        v_returnjitstate = flowmodel.Variable('jitstate')
        returnblock.inputargs = [v_returnjitstate]
        v_returnjitstate.concretetype = STATE_PTR

        
    def timeshift_block(self, block):
        self.hrtyper.specialize_block(block)

    def originalconcretetype(self, var):
        return originalconcretetype(self.hannotator.binding(var))
