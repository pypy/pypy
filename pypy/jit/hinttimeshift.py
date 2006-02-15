from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow import model as flowmodel
from pypy.annotation import model as annmodel
from pypy.annotation import listdef, dictdef
from pypy.jit.rtimeshift import STATE_PTR, REDBOX_PTR, VARLIST
from pypy.jit.rtimeshift import make_types_const
from pypy.rpython import rmodel, rtuple, rlist, rdict
from pypy.jit import rtimeshift
from pypy.jit.hintrtyper import HintRTyper, s_JITState, originalconcretetype
from pypy.jit.hintrtyper import GreenRepr, RedRepr, HintLowLevelOpList

# ___________________________________________________________

class HintTimeshift(object):
    
    def __init__(self, hannotator, rtyper):
        self.hannotator = hannotator
        self.rtyper = rtyper
        self.hrtyper = HintRTyper(hannotator, self)

    def timeshift(self):
        for graph in self.hannotator.translator.graphs:
            self.timeshift_graph(graph)
        # RType the helpers found during timeshifting
        self.rtyper.specialize_more_blocks()

    def timeshift_graph(self, graph):
        self.graph = graph
        entering_links = flowmodel.mkentrymap(graph)

        originalblocks = list(graph.iterblocks())
        returnblock = graph.returnblock
        # we need to get the jitstate to the before block of the return block
        before_returnblock = self.insert_before_block(returnblock, entering_links[returnblock])
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
        self.insert_bookkeeping_enter(returnblock, before_returnblock,
                                      len(entering_links[returnblock]))

    def pre_process_block(self, block):
        # pass 'jitstate' as an extra argument around the whole graph
        if block.operations != ():
            v_jitstate = flowmodel.Variable('jitstate')
            self.hannotator.bindings[v_jitstate] = s_JITState
            block.inputargs.insert(0, v_jitstate)
            for link in block.exits:
                if link.target.operations != ():
                    link.args.insert(0, v_jitstate)
                elif len(link.args) == 1: # pass the jitstate instead of the return value
                                          # to the return block!
                    link.args[0] = v_jitstate
                    v_returnjitstate = flowmodel.Variable('jitstate')                    
                    self.hannotator.bindings[v_returnjitstate] = s_JITState
                    link.target.inputargs = [v_returnjitstate]
                    
    def insert_before_block(self, block, entering_links):
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
            
        bridge = flowmodel.Link(newinputargs, block)
        newblock.closeblock(bridge)
        return newblock
                                                         
    def insert_bookkeeping_enter(self, block, before_block, nentrylinks):
        newinputargs = before_block.inputargs
        args_r = []
        for var in newinputargs:
            hs = self.hannotator.bindings[var]
            args_r.append(self.hrtyper.getrepr(hs))
            
        llops = HintLowLevelOpList(self, None)

        s_box_list = annmodel.SomeList(listdef.ListDef(None,
                                                       annmodel.SomePtr(REDBOX_PTR)))
        TYPES = []
        boxes_v = []
        for r, newvar in zip(args_r, newinputargs):
            if isinstance(r, RedRepr):
                boxes_v.append(newvar)
                TYPES.append(r.original_concretetype)                
        getrepr = self.rtyper.getrepr

        r_box_list = getrepr(s_box_list)
        r_box_list.setup()        
        v_boxes = rlist.newlist(llops, r_box_list, boxes_v)
        c_TYPES = rmodel.inputconst(VARLIST, make_types_const(TYPES))        


        if nentrylinks > 1:
            enter_block_logic = self.bookkeeping_enter_for_join
        else:
            enter_block_logic = self.bookkeeping_enter_simple


        # fill the block with logic
        v_newjitstate = enter_block_logic(args_r, newinputargs,
                                          llops,
                                          s_box_list, v_boxes,
                                          c_TYPES)

        def read_out_box(i):
            c_dum_nocheck = rmodel.inputconst(lltype.Void, rlist.dum_nocheck)
            c_i = rmodel.inputconst(lltype.Signed, i)
            v_box = llops.gendirectcall(rlist.ll_getitem_nonneg,
                                        c_dum_nocheck,
                                        v_boxes,
                                        c_i)
            return v_box
            

        bridge = before_block.exits[0]
        newinputargs2 = [v_newjitstate]
        if bridge.target.operations == (): # special case the return block
            # XXX maybe better to return a tuple (state, value)?
            c_curvalue = rmodel.inputconst(lltype.Void, "curvalue")
            if isinstance(args_r[1], GreenRepr):
                v_value = llops.gendirectcall(rtimeshift.REDBOX.ll_make_from_const,
                                              newinputargs[1])
            else:
                v_value = read_out_box(0)
            llops.genop('setfield', [v_newjitstate, c_curvalue, v_value])
        else:
            i = 0
            for r, newvar in zip(args_r[1:], newinputargs[1:]):
                if isinstance(r, RedRepr):
                    newinputargs2.append(read_out_box(i))
                    i += 1
                else:
                    newinputargs2.append(newvar)

        # patch before block and bridge
        before_block.operations[:] = llops
        bridge.args = newinputargs2 # patch the link

    def bookkeeping_enter_simple(self, args_r, newinputargs, llops, s_box_list, v_boxes,
                                c_TYPES):
        v_newjiststate = llops.genmixlevelhelpercall(rtimeshift.enter_block,
                             [annmodel.SomePtr(STATE_PTR), s_box_list,
                              annmodel.SomePtr(VARLIST)],
                             [newinputargs[0], v_boxes, c_TYPES])
        return v_newjiststate
        


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
    def bookkeeping_enter_for_join(self, args_r, newinputargs, llops, s_box_list, v_boxes,
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
  

        s_state_dic = annmodel.SomeDict(dictdef.DictDef(None,
                                                        s_key_tuple,
                                                        s_box_list # XXX
                                                        ))
        r_key = getrepr(s_key_tuple)

        r_state_dic = getrepr(s_state_dic)
        r_key.setup()

        r_state_dic.setup()

        c_state_dic = rmodel.inputconst(r_state_dic, {})

        v_key = rtuple.newtuple(llops, r_key, key_v)



        v_newjiststate = llops.genmixlevelhelpercall(rtimeshift.retrieve_jitstate_for_merge,
                             [s_state_dic, annmodel.SomePtr(STATE_PTR), s_key_tuple, s_box_list,
                              annmodel.SomePtr(VARLIST)],
                             [c_state_dic, newinputargs[0], v_key, v_boxes, c_TYPES])
        return v_newjiststate
        
        
    def insert_bookkeeping_leave_block(self, block, entering_links):
        # XXX wrong with exceptions as much else
        
        renamemap = {}
        rename = lambda v: renamemap.get(v, v)
        inargs = []

        def introduce(v):
            if isinstance(v, flowmodel.Variable):
                if v not in renamemap:
                    vprime = renamemap[v] = flowmodel.Variable(v)
                    vprime.concretetype = v.concretetype
                    inargs.append(v)

        orig_v_jitstate = block.inputargs[0]
        introduce(orig_v_jitstate)

        newlinks = []

        v_newjitstate = flowmodel.Variable('jitstate')
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
        newblock.exitswitch = rename(block.exitswitch)
        newblock.closeblock(*newlinks)
            
        inlink = flowmodel.Link(inargs, newblock)

        block.exitswitch = None
        block.recloseblock(inlink)

        llops = HintLowLevelOpList(self, None)

        v_res = llops.genmixlevelhelpercall(rtimeshift.leave_block,
                                            [annmodel.SomePtr(STATE_PTR)],
                                            [rename(orig_v_jitstate)])     

        llops.append(flowmodel.SpaceOperation('same_as',
                               [v_res],
                               v_newjitstate))

        newblock.operations[:] = llops

    def timeshift_block(self, block):
        self.hrtyper.specialize_block(block)

    def originalconcretetype(self, var):
        return originalconcretetype(self.hannotator.binding(var))
