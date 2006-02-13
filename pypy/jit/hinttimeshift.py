from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow import model as flowmodel
from pypy.annotation import model as annmodel
from pypy.annotation import listdef, dictdef
from pypy.jit.rtimeshift import STATE_PTR, REDBOX_PTR
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
        entering_links = flowmodel.mkentrymap(graph)
        
        originalblocks = list(graph.iterblocks())
        for block in originalblocks:
            self.pre_process_block(block)
        for block in originalblocks:
            self.timeshift_block(block)
            self.insert_merge_block(block, entering_links[block])
            

    def pre_process_block(self, block):
        # pass 'jitstate' as an extra argument around the whole graph
        if block.operations != ():
            v_jitstate = flowmodel.Variable('jitstate')
            self.hannotator.bindings[v_jitstate] = s_JITState
            block.inputargs.insert(0, v_jitstate)
            for link in block.exits:
                # not for links going to the return/except block
                if link.target.operations != ():
                    link.args.insert(0, v_jitstate)
            
    def insert_merge_block(self, block, entering_links):
        if len(entering_links) > 1: # join
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
                        
            newinputargs = []
            args_r = []
            for var in block.inputargs:
                newvar = flowmodel.Variable(var)
                newvar.concretetype = var.concretetype
                self.hannotator.bindings[newvar] = hs = self.hannotator.bindings[var]
                args_r.append(self.hrtyper.getrepr(hs))
                newinputargs.append(newvar)
            newblock = flowmodel.Block(newinputargs)
            for link in entering_links:
                link.settarget(newblock)

            getrepr = self.rtyper.getrepr

            items_s = []
            key_v = []
            llops = HintLowLevelOpList(self, None)
            boxes_v = []
            
            for r, newvar in zip(args_r, newinputargs):
                if isinstance(r, GreenRepr):
                    r_from = getrepr(r.annotation())
                    erased_s = r.erased_annotation()
                    r_to = getrepr(erased_s)
                    items_s.append(erased_s)
                    erased_v = llops.convertvar(newvar, r_from, r_to)
                    key_v.append(erased_v)
                elif isinstance(r, RedRepr):
                    boxes_v.append(newvar)
                    
            s_key_tuple = annmodel.SomeTuple(items_s)
            s_box_list = annmodel.SomeList(listdef.ListDef(None,
                                                           annmodel.SomePtr(REDBOX_PTR)))

            s_state_dic = annmodel.SomeDict(dictdef.DictDef(None,
                                                            s_key_tuple,
                                                            s_box_list # XXX
                                                            ))
            r_key = getrepr(s_key_tuple)
            r_box_list = getrepr(s_box_list)
            r_state_dic = getrepr(s_state_dic)
            r_key.setup()
            r_box_list.setup()
            r_state_dic.setup()

            c_state_dic = rmodel.inputconst(r_state_dic, {})
            
            v_key = rtuple.newtuple(llops, r_key, key_v)
            v_boxes = rlist.newlist(llops, r_box_list, boxes_v)


            v_newjiststate = llops.genmixlevelhelpercall(rtimeshift.retrieve_jitstate_for_merge,
                                                         [s_state_dic, annmodel.SomePtr(STATE_PTR), s_key_tuple, s_box_list],
                                                         [c_state_dic, newinputargs[0], v_key, v_boxes])

            newinputargs2 = [v_newjiststate]
            i = 0
            for r, newvar in zip(args_r[1:], newinputargs[1:]):
                if isinstance(r, RedRepr):
                    c_dum_nocheck = rmodel.inputconst(lltype.Void, rlist.dum_nocheck)
                    c_i = rmodel.inputconst(lltype.Signed, i)
                    v_box = llops.gendirectcall(rlist.ll_getitem_nonneg,
                                                c_dum_nocheck,
                                                v_boxes,
                                                c_i)
                    newinputargs2.append(v_box)
                    i += 1
                else:
                    newinputargs2.append(newvar)

            newblock.operations[:] = llops
                            
            bridge = flowmodel.Link(newinputargs2, block)
            newblock.closeblock(bridge)


    def timeshift_block(self, block):
        self.hrtyper.specialize_block(block)

    def originalconcretetype(self, var):
        return originalconcretetype(self.hannotator.binding(var))
