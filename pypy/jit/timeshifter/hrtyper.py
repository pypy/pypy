import types
import py
from pypy.tool.ansi_print import ansi_log
from pypy.objspace.flow import model as flowmodel
from pypy.translator.unsimplify import varoftype
from pypy.translator.backendopt.ssa import SSA_to_SSI
from pypy.annotation import model as annmodel
from pypy.annotation import listdef
from pypy.annotation.pairtype import pair, pairtype
from pypy.rpython.annlowlevel import PseudoHighLevelCallable
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython import annlowlevel
from pypy.rpython.rtyper import RPythonTyper, LowLevelOpList, TyperError
from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.lltypesystem.rstr import string_repr
from pypy.rpython.typesystem import LowLevelTypeSystem
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.hintannotator import model as hintmodel
from pypy.jit.hintannotator import container as hintcontainer
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.timeshifter import rtimeshift, rvalue, rcontainer, oop
from pypy.jit.timeshifter.exception import ExceptionDesc
from pypy.jit.codegen import model as cgmodel

class HintTypeSystem(LowLevelTypeSystem):
    name = "hinttypesystem"

    offers_exceptiondata = False
    
    def perform_normalizations(self, hrtyper):
        from pypy.rpython import normalizecalls
        hannotator = hrtyper.annotator
        call_families = hannotator.bookkeeper.tsgraph_maximal_call_families
        while True:
            progress = False
            for callfamily in call_families.infos():
                graphs = callfamily.tsgraphs.keys()
                progress |= normalizecalls.normalize_calltable_row_annotation(
                    hannotator,
                    graphs)
            if not progress:
                break   # done

HintTypeSystem.instance = HintTypeSystem()

# ___________________________________________________________


class HintRTyper(RPythonTyper):
    log = py.log.Producer("timeshifter")
    py.log.setconsumer("timeshifter", ansi_log)

    def __init__(self, hannotator, rtyper, RGenOp):
        RPythonTyper.__init__(self, hannotator, 
                              type_system=HintTypeSystem.instance)
        self.rtyper = rtyper
        self.RGenOp = RGenOp
        self.green_reprs = PRECOMPUTED_GREEN_REPRS.copy()
        self.red_reprs = {}
        #self.color_cache = {}

        self.annhelper = annlowlevel.MixLevelHelperAnnotator(rtyper)
        self.timeshift_mapping = {}
        self.sigs = {}
        self.dispatchsubclasses = {}
        self.old_percentage = 0

        (self.s_JITState,
         self.r_JITState)      = self.s_r_instanceof(rtimeshift.JITState)
        (self.s_RedBox,
         self.r_RedBox)        = self.s_r_instanceof(rvalue.RedBox)
        (self.s_PtrRedBox,
         self.r_PtrRedBox)     = self.s_r_instanceof(rvalue.PtrRedBox)
        (self.s_ConstOrVar,
         self.r_ConstOrVar)    = self.s_r_instanceof(cgmodel.GenVarOrConst)
        (self.s_Queue,
         self.r_Queue)       = self.s_r_instanceof(rtimeshift.BaseDispatchQueue)

        def ll_fresh_jitstate(builder, exceptiondesc):
            return rtimeshift.JITState(builder, None,
                                       exceptiondesc.null_exc_type_box,
                                       exceptiondesc.null_exc_value_box)
        self.ll_fresh_jitstate = ll_fresh_jitstate

        def ll_finish_jitstate(jitstate, exceptiondesc, graphsigtoken):
            returnbox = rtimeshift.getreturnbox(jitstate)
            gv_ret = returnbox.getgenvar(jitstate)
            builder = jitstate.curbuilder
            for virtualizable_box in jitstate.virtualizables:
                assert isinstance(virtualizable_box, rvalue.PtrRedBox)
                content = virtualizable_box.content
                assert isinstance(content, rcontainer.VirtualizableStruct)
                content.store_back(jitstate)        
            exceptiondesc.store_global_excdata(jitstate)
            jitstate.curbuilder.finish_and_return(graphsigtoken, gv_ret)
        self.ll_finish_jitstate = ll_finish_jitstate

        self.v_queue = varoftype(self.r_Queue.lowleveltype, 'queue')
        #self.void_red_repr = VoidRedRepr(self)

        # global state for the portal corresponding to this timeshifted world
        class PortalState(object):
            pass
        def compile_more_functions():
            "Empty by default; overridden in rewire_portal()"
        self.portalstate = PortalState()
        self.portalstate.compile_more_functions = compile_more_functions

    def specialize(self, origportalgraph=None, view=False,
                   dont_simplify_again=False):
        """
        Driver for running the timeshifter.
        """
        if not dont_simplify_again:
            self.annotator.simplify()
##        self.type_system.perform_normalizations(self)
        bk = self.annotator.bookkeeper
##        bk.compute_after_normalization()
        entrygraph = self.annotator.translator.graphs[0]
        self.origportalgraph = origportalgraph
        if origportalgraph:
            self.portalgraph = bk.get_graph_by_key(origportalgraph, None)
            leaveportalgraph = self.portalgraph
        else:
            self.portalgraph = None
            # in the case of tests not specifying a portal
            # we still need to force merges when entry
            # returns
            leaveportalgraph = entrygraph
            
        self.contains_promotion = False
        self.portal_contains_global_mp = False
        pending = [entrygraph]
        seen = {entrygraph: True}
        while pending:
            graph = pending.pop()
            for nextgraph in self.timeshift_cflow(graph,
                                is_portal=graph is leaveportalgraph):
                if nextgraph not in seen:
                    pending.append(nextgraph)
                    seen[nextgraph] = True
        if self.contains_promotion:
            assert self.portal_contains_global_mp, (
                "No global merge point found.  "
                "Forgot 'hint(None, global_merge_point=True)'?")
        self.log.event("Timeshifted control flow of %d graphs." % (len(seen),))

        self.exceptiondesc = ExceptionDesc(self,
                                           self.portal_contains_global_mp)

        #import pdb; pdb.set_trace()
        # only keep the hint-annotated graphs that are really useful
        self.annotator.translator.graphs = [graph
            for graph in self.annotator.translator.graphs
            if graph in seen]
        if view:
            self.annotator.translator.view()     # in the middle
        self.blockcount = 0
        self.graphcount = 0
        self.ngraphs = len(seen)
        for graph in seen:
            self.timeshift_ops(graph)

        self.log.event("Completed timeshifting of %d graphs." % (len(seen),))
        if origportalgraph:
            n = len(list(self.portalgraph.iterblocks()))
            self.log.event("portal has now %d blocks" % n)
            self.rewire_portal()

        # move the timeshifted graphs into the original translator
        base_translator = self.annotator.base_translator
        for graph in self.annotator.translator.graphs:
            flowmodel.checkgraph(graph)
            base_translator.graphs.append(graph)

    # remember a shared pointer for the portal graph,
    # so that it can be later patched by rewire_portal.
    # this pointer is going to be used by the resuming logic
    # and portal (re)entry.
    def naked_tsfnptr(self, tsgraph):
        if tsgraph is self.portalgraph:
            try:
                return self.portal_tsfnptr
            except AttributeError:
                self.portal_tsfnptr = self.gettscallable(tsgraph)
                return self.portal_tsfnptr
        return self.gettscallable(tsgraph)
        
    def rewire_portal(self):
        origportalgraph = self.origportalgraph
        portalgraph = self.portalgraph
        annhelper = self.annhelper
        rgenop = self.RGenOp()

        args_specification = []
        portal_args_s = []
        for v in portalgraph.getargs()[1:]:
            r = self.bindingrepr(v)
            if isinstance(r, GreenRepr):
                arg_spec = "green", None, None
                portal_args_s.append(annmodel.lltype_to_annotation(
                    r.lowleveltype))
            else:
                arg_spec = "red", r.residual_args_collector(), r.arg_redbox_maker()
                portal_args_s.append(self.s_RedBox)
            args_specification.append(arg_spec)

        tsportalgraph = portalgraph
        # patch the shared portal pointer
        portalgraph = flowmodel.copygraph(tsportalgraph, shallow=True)
        portalgraph.tag = 'portal'
        self.annotator.translator.graphs.append(portalgraph)

        portal_fnptr = self.naked_tsfnptr(self.portalgraph)
        portal_fnptr._obj.graph = portalgraph
        
        portal_fn = PseudoHighLevelCallable(
            portal_fnptr,
            [self.s_JITState] + portal_args_s,
            self.s_JITState)
        FUNC = self.get_residual_functype(portalgraph)
        RESTYPE = FUNC.RESULT
        reskind = rgenop.kindToken(RESTYPE)
        boxbuilder = rvalue.ll_redboxbuilder(RESTYPE)
        args_specification = unrolling_iterable(args_specification)
        fresh_jitstate = self.ll_fresh_jitstate
        finish_jitstate = self.ll_finish_jitstate
        exceptiondesc = self.exceptiondesc
        sigtoken = rgenop.sigToken(FUNC)

        # debug helper
        def readportal(*args):
            i = 0
            key = ()
            for color, _, _ in args_specification:
                if color == "green":
                    x = args[i]
                    if isinstance(lltype.typeOf(x), lltype.Ptr): 
                        x = llmemory.cast_ptr_to_adr(x)
                    key = key + (x,)
                i = i + 1
            cache = state.cache
            try:
                gv_generated = cache[key]
            except KeyError:
                return lltype.nullptr(FUNC)
            fn = gv_generated.revealconst(lltype.Ptr(FUNC))
            return fn
            
        def readallportals():
            return [gv_gen.revealconst(lltype.Ptr(FUNC))
                    for gv_gen in state.cache.values()]
        
        def portalentry(*args):
            i = 0
            key = ()
            residualargs = ()
            for color, collect_residual_args, _ in args_specification:
                if color == "green":
                    x = args[i]
                    if isinstance(lltype.typeOf(x), lltype.Ptr): 
                        x = llmemory.cast_ptr_to_adr(x)
                    key = key + (x,)
                else:
                    residualargs = residualargs + collect_residual_args(args[i])
                i = i + 1
            cache = state.cache
            try:
                gv_generated = cache[key]
            except KeyError:
                portal_ts_args = ()
                builder, gv_generated, inputargs_gv = rgenop.newgraph(sigtoken,
                                                             "generated")
                cache[key] = gv_generated
                top_jitstate = fresh_jitstate(builder, exceptiondesc)
                i = 0
                for color, _, make_arg_redbox in args_specification:
                    if color == "green":
                        llvalue = args[0]
                        args = args[1:]
                        portal_ts_args += (llvalue,)
                    else:
                        llvalue = args[0]
                        args = args[1:]
                        box = make_arg_redbox(top_jitstate, inputargs_gv, i)
                        i += make_arg_redbox.consumes                        
                        portal_ts_args += (box,)

                state.graph_compilation_queue.append((top_jitstate, portal_ts_args))
                compile_more_functions()

            fn = gv_generated.revealconst(lltype.Ptr(FUNC))
            return fn(*residualargs)

        def compile_more_functions():
            while state.graph_compilation_queue:
                top_jitstate, portal_ts_args = state.graph_compilation_queue.pop()
                builder = top_jitstate.curbuilder
                builder.start_writing()
                top_jitstate = portal_fn(top_jitstate, *portal_ts_args)
                if top_jitstate is not None:
                    finish_jitstate(top_jitstate, exceptiondesc, sigtoken)
                builder.end()
                builder.show_incremental_progress()

        state = self.portalstate
        state.cache = {}
        state.graph_compilation_queue = []
        state.compile_more_functions = compile_more_functions

        args_s = [annmodel.lltype_to_annotation(v.concretetype) for
                  v in origportalgraph.getargs()]
        s_result = annmodel.lltype_to_annotation(
                    origportalgraph.getreturnvar().concretetype)
        portalentrygraph = annhelper.getgraph(portalentry, args_s, s_result)
        x = self.annotator.base_translator.graphs.pop()
        assert portalentrygraph is x

        s_funcptr = annmodel.SomePtr(lltype.Ptr(FUNC))
        self.readportalgraph = annhelper.getgraph(readportal, args_s,
                                   s_funcptr)

        s_funcptrlist = annmodel.SomeList(listdef.ListDef(None, s_funcptr,
                                                          resized=True))
        self.readallportalsgraph = annhelper.getgraph(readallportals, [],
                                                      s_funcptrlist)

        TYPES = [v.concretetype for v in origportalgraph.getargs()]
        argspecandtypes = unrolling_iterable(zip(args_specification,
                                                  TYPES))
        fetch_global_excdata = self.exceptiondesc.fetch_global_excdata

        def portalreentry(jitstate, *args): # xxx virtualizables?
            i = 0
            key = ()
            curbuilder = jitstate.curbuilder
            args_gv = []
            for color, _, _ in args_specification:
                if color == "green":
                    x = args[i]
                    if isinstance(lltype.typeOf(x), lltype.Ptr): 
                        x = llmemory.cast_ptr_to_adr(x)
                    key = key + (x,)
                else:
                    box = args[i]
                    args_gv.append(box.getgenvar(jitstate))
                i = i + 1
            cache = state.cache
            try:
                gv_generated = cache[key]
            except KeyError:
                portal_ts_args = ()
                builder, gv_generated, inputargs_gv = rgenop.newgraph(sigtoken,
                                                                "generated")
                cache[key] = gv_generated
                i = 0
                for (color, _, _), T in argspecandtypes:
                    if color == "green":
                        llvalue = args[0]
                        args = args[1:]
                        portal_ts_args += (llvalue,)
                    else:
                        args = args[1:]
                        kind = rgenop.kindToken(T)
                        boxcls = rvalue.ll_redboxcls(T)
                        gv_arg = inputargs_gv[i]
                        box = boxcls(kind, gv_arg)
                        i += 1
                        portal_ts_args += (box,)

                top_jitstate = fresh_jitstate(builder, exceptiondesc)
                state.graph_compilation_queue.append((top_jitstate, portal_ts_args))

            gv_res = curbuilder.genop_call(sigtoken, gv_generated, args_gv)
            fetch_global_excdata(jitstate)

            if RESTYPE == lltype.Void:
                retbox = None
            else:
                retbox = boxbuilder(reskind, gv_res)
            jitstate.returnbox = retbox
            assert jitstate.next is None
            return jitstate

        portalreentrygraph = annhelper.getgraph(portalreentry,
                [self.s_JITState] + portal_args_s, self.s_JITState)
        x = self.annotator.base_translator.graphs.pop()
        assert portalreentrygraph is x

        annhelper.finish()

        origportalgraph.startblock = portalentrygraph.startblock
        origportalgraph.returnblock = portalentrygraph.returnblock
        origportalgraph.exceptblock = portalentrygraph.exceptblock
        origportalgraph.tag = "PortalEntry"
        origportalgraph.name += '_portal_entry'

        tsportalgraph.startblock = portalreentrygraph.startblock
        tsportalgraph.returnblock = portalreentrygraph.returnblock
        tsportalgraph.exceptblock = portalreentrygraph.exceptblock
        tsportalgraph.tag = "PortalReentry"
        tsportalgraph.name += '_portal_reentry'        
        

    def timeshift_cflow(self, graph, is_portal=False):
        # prepare the graphs by inserting all bookkeeping/dispatching logic
        # as special operations
        from pypy.jit.timeshifter.transform import HintGraphTransformer
        assert graph.startblock in self.annotator.annotated
        transformer = HintGraphTransformer(self.annotator, graph,
                                           is_portal=is_portal)
        transformer.transform()
        flowmodel.checkgraph(graph)    # for now
        self.contains_promotion |= transformer.contains_promotion
        if is_portal:
            self.portal_contains_global_mp = (
                transformer.mergepointfamily.has_global_mergepoints())
        return transformer.tsgraphs_seen

    def timeshift_ops(self, graph):
        # specialize all blocks of this graph
        for block in list(graph.iterblocks()):
            self.annotator.annotated[block] = graph
            self.specialize_block(block)
            self.blockcount += 1
            if self.blockcount % 100 == 0:
                percentage = 100 * self.graphcount / self.ngraphs
                if percentage >= self.old_percentage + 5:
                    self.old_percentage = percentage
                    self.log.event("Timeshifted ops in %d blocks, %d/%d graphs (%d %%)" %
                                   (self.blockcount, self.graphcount,
                                    self.ngraphs, percentage))
        self.graphcount += 1                
        # "normalize" the graphs by putting an explicit v_jitstate variable
        # everywhere
        self.insert_v_jitstate_everywhere(graph)
        SSA_to_SSI(graph, annotator=self.annotator)
        # the graph is now timeshifted, so it is *itself* no longer
        # exception-transformed...
        del graph.exceptiontransformed

    # ____________________________________________________________

    def s_r_instanceof(self, cls, can_be_None=True):
        # Return a SomeInstance / InstanceRepr pair correspnding to the specified class.
        return self.annhelper.s_r_instanceof(cls, can_be_None=can_be_None)

    def get_sig_hs(self, tsgraph):
        # the signature annotations are cached on the HintBookkeeper because
        # the graph is transformed already
        return self.annotator.bookkeeper.tsgraphsigs[tsgraph]

    def get_residual_functype(self, tsgraph):
        ha = self.annotator
        args_hs, hs_res = self.get_sig_hs(ha.translator.graphs[0])
        RESTYPE = originalconcretetype(hs_res)
        args_r = [self.getrepr(hs_arg) for hs_arg in args_hs
                                       if not hs_arg.is_green()]
        ARGS = []
        for r_arg in args_r:
            ARGS += r_arg.residual_argtypes()
        return lltype.FuncType(ARGS, RESTYPE)

    def make_new_lloplist(self, block):
        return HintLowLevelOpList(self)

    def translate_no_return_value(self, hop):
        op = hop.spaceop
        if op.result.concretetype is not lltype.Void:
            raise TyperError("the hint-annotator doesn't agree that '%s' "
                             "returns a Void" % op.opname)
        # try to avoid a same_as in common cases
        if (len(hop.llops) > 0
            and hop.llops[-1].result.concretetype is lltype.Void):
            hop.llops[-1].result = op.result
        else:
            hop.llops.append(flowmodel.SpaceOperation('same_as',
                                                      [c_void],
                                                      op.result))

    def getgreenrepr(self, lowleveltype):
        try:
            return self.green_reprs[lowleveltype]
        except KeyError:
            r = GreenRepr(lowleveltype)
            self.green_reprs[lowleveltype] = r
            return r

    def getredrepr(self, lowleveltype):
        try:
            return self.red_reprs[lowleveltype]
        except KeyError:
            assert not isinstance(lowleveltype, lltype.ContainerType)
            redreprcls = RedRepr
            if isinstance(lowleveltype, lltype.Ptr):
                if isinstance(lowleveltype.TO, lltype.Struct):
                    if lowleveltype.TO._hints.get('virtualizable', False):
                        redreprcls = RedVirtualizableStructRepr
                    else:
                        redreprcls = RedStructRepr
            r = redreprcls(lowleveltype, self)
            self.red_reprs[lowleveltype] = r
            return r

##    def getredrepr_or_none(self, lowleveltype):
##        if lowleveltype is lltype.Void:
##            return self.void_red_repr
##        else:
##            return self.getredrepr(lowleveltype)

##    def gethscolor(self, hs):
##        try:
##            return self.color_cache[id(hs)]
##        except KeyError:
##            if hs.is_green():
##                color = "green"
##            else:
##                color = "red"
##            self.color_cache[id(hs)] = color
##            return color

    def get_dispatch_subclass(self, mergepointfamily):
        try:
            return self.dispatchsubclasses[mergepointfamily]
        except KeyError:
            attrnames = mergepointfamily.getlocalattrnames()
            subclass = rtimeshift.build_dispatch_subclass(attrnames)
            self.dispatchsubclasses[mergepointfamily] = subclass
            return subclass

    def get_args_r(self, tsgraph):
        args_hs, hs_res = self.get_sig_hs(tsgraph)
        return [self.getrepr(hs_arg) for hs_arg in args_hs]

    def gettscallable(self, tsgraph):
        args_r = self.get_args_r(tsgraph)
        ARGS = [self.r_JITState.lowleveltype]
        ARGS += [r.lowleveltype for r in args_r]
        RESULT = self.r_JITState.lowleveltype
        return lltype.functionptr(lltype.FuncType(ARGS, RESULT),
                                  tsgraph.name,
                                  graph=tsgraph)

    def get_timeshift_mapper(self, graph2ts):
        # XXX try to share the results between "similar enough" graph2ts'es
        key = graph2ts.items()
        key.sort()
        key = tuple(key)
        try:
            return self.timeshift_mapping[key]
        except KeyError:
            pass

        bk = self.annotator.bookkeeper
        keys = []
        values = []
        common_args_r = None
        COMMON_TS_FUNC = None
        for graph, tsgraph in graph2ts.items():
            fnptr    = self.rtyper.getcallable(graph)
            ts_fnptr = self.gettscallable(tsgraph)
            args_r   = self.get_args_r(tsgraph)
            TS_FUNC  = lltype.typeOf(ts_fnptr)
            if common_args_r is None:
                common_args_r = args_r
                COMMON_TS_FUNC = TS_FUNC
            else:
                # should be ensured by normalization
                assert COMMON_TS_FUNC == TS_FUNC
                assert common_args_r == args_r
            keys.append(fnptr)
            values.append(ts_fnptr)

        fnptrmap = {}

        def getter(fnptrmap, fnptr):
            # indirection needed to defeat the flow object space
            return fnptrmap[llmemory.cast_ptr_to_adr(fnptr)]

        def fill_dict(fnptrmap, values, keys):
            for i in range(len(values)):
                fnptrmap[llmemory.cast_ptr_to_adr(keys[i])] = values[i]

        def timeshift_mapper(fnptr):
            try:
                return getter(fnptrmap, fnptr)
            except KeyError:
                fill_dict(fnptrmap, values, keys)
                return getter(fnptrmap, fnptr)   # try again

        result = timeshift_mapper, COMMON_TS_FUNC, common_args_r
        self.timeshift_mapping[key] = result
        return result

    def insert_v_jitstate_everywhere(self, graph):
        for block in graph.iterblocks():
            v_jitstate = varoftype(self.r_JITState.lowleveltype, 'jitstate')
            if block is graph.returnblock:
                assert block.inputargs[0].concretetype is lltype.Void
                del block.inputargs[0]
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
                if link.target is graph.returnblock:
                    del link.args[0]    # Void
                link.args = [v_jitstate] + link.args

    def generic_translate_operation(self, hop):
        # detect constant-foldable all-green operations
        if hop.spaceop.opname not in rtimeshift.FOLDABLE_GREEN_OPS:
            return None
        green = True
        for r_arg in hop.args_r:
            green = green and isinstance(r_arg, GreenRepr)
        if green and isinstance(hop.r_result, GreenRepr):
            # Just generate the same operation in the timeshifted graph.
            hop.llops.append(hop.spaceop)
            return hop.spaceop.result
        else:
            #print "RED op", hop.spaceop
            return None

    def default_translate_operation(self, hop):
        # by default, a red operation converts all its arguments to
        # genop variables, and emits a call to a helper that will generate
        # the same operation at run-time
        opdesc = rtimeshift.make_opdesc(hop)
        if opdesc.nb_args == 1:
            ll_generate = rtimeshift.ll_gen1
        elif opdesc.nb_args == 2:
            ll_generate = rtimeshift.ll_gen2
        ts = self
        c_opdesc = inputconst(lltype.Void, opdesc)
        s_opdesc = ts.rtyper.annotator.bookkeeper.immutablevalue(opdesc)
        v_jitstate = hop.llops.getjitstate()
        args_v = hop.inputargs(*[self.getredrepr(originalconcretetype(hs))
                                for hs in hop.args_s])
        args_s = [ts.s_RedBox] * len(args_v)
        return hop.llops.genmixlevelhelpercall(ll_generate,
                                               [s_opdesc, ts.s_JITState] + args_s,
                                               [c_opdesc, v_jitstate]    + args_v,
                                               ts.s_RedBox)

    def translate_op_debug_assert(self, hop):
        pass

    def translate_op_debug_assert_ptr_nonzero(self, hop, nonzeroness=True):
        hs = hop.args_s[0]
        if hs.is_green():
            return
        v_box = hop.inputarg(self.getredrepr(originalconcretetype(hs)), arg=0)
        v_box = hop.llops.as_ptrredbox(v_box)
        c_nonzeroness = hop.inputconst(lltype.Bool, nonzeroness)
        v_jitstate = hop.llops.getjitstate()
        hop.llops.genmixlevelhelpercall(rtimeshift.ll_learn_nonzeroness,
                          [self.s_JITState, self.s_PtrRedBox, annmodel.s_Bool],
                          [v_jitstate,      v_box           , c_nonzeroness  ],
                          annmodel.s_None)

    def translate_op_debug_assert_ptr_iszero(self, hop):
        self.translate_op_debug_assert_ptr_nonzero(hop, nonzeroness=False)

    def translate_op_resume_point(self, hop):
        pass

    def translate_op_keepalive(self,hop):
        pass

    def translate_op_same_as(self, hop):
        [v] = hop.inputargs(hop.r_result)
        return v

    def translate_op_ts_metacall(self, hop):
        # note that if the ts_metacall operation is pure and green, then
        # we don't even get there because the original graph in which
        # it is will just be green_call'ed by the caller.
        nb_args = hop.nb_args - 2
        def normalize(hs):
            T = originalconcretetype(hs)
            if T is lltype.Void:
                return lltype.Void
            else:
                return self.getredrepr(T)
        args_r = [normalize(hs) for hs in hop.args_s[2:]]
        vlist = hop.inputargs(lltype.Void, lltype.Void, *args_r)
        metadesccls = vlist[1].value
        metadesc = metadesccls(self)
        metafunc = metadesc.metafunc
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(metafunc,
                            [self.s_JITState] + [self.s_RedBox] * nb_args,
                            [v_jitstate]      + vlist[2:],
                            self.s_RedBox)

    def translate_op_getfield(self, hop):
        if isinstance(hop.args_r[0], BlueRepr):
            return hop.args_r[0].timeshift_getfield(hop)
        ts = self
        if hop.args_v[0] == ts.exceptiondesc.cexcdata:
            # reading one of the exception boxes (exc_type or exc_value)
            fieldname = hop.args_v[1].value
            if fieldname == 'exc_type':
                reader = rtimeshift.getexctypebox
            elif fieldname == 'exc_value':
                reader = rtimeshift.getexcvaluebox
            else:
                raise Exception("getfield(exc_data, %r)" % (fieldname,))
            v_jitstate = hop.llops.getjitstate()
            return hop.llops.genmixlevelhelpercall(reader,
                                                   [ts.s_JITState],
                                                   [v_jitstate   ],
                                                   ts.s_RedBox)
        # virtualizable access read
        PTRTYPE = originalconcretetype(hop.args_s[0])
        if PTRTYPE.TO._hints.get('virtualizable', False):
            assert hop.args_v[1].value != 'vable_access'

        # non virtual case                
        v_argbox, c_fieldname = hop.inputargs(self.getredrepr(PTRTYPE),
                                              green_void_repr)
        v_argbox = hop.llops.as_ptrredbox(v_argbox)
        c_deepfrozen = inputconst(lltype.Bool, hop.args_s[0].deepfrozen)
        structdesc = rcontainer.StructTypeDesc(self, PTRTYPE.TO)
        fielddesc = structdesc.getfielddesc(c_fieldname.value)
        if fielddesc is None:   # Void field
            return
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_gengetfield,
            [ts.s_JITState, annmodel.s_Bool, s_fielddesc, ts.s_PtrRedBox],
            [v_jitstate   , c_deepfrozen   , c_fielddesc, v_argbox      ],
            ts.s_RedBox)

    def translate_op_getarrayitem(self, hop):
        PTRTYPE = originalconcretetype(hop.args_s[0])
        if PTRTYPE.TO.OF is lltype.Void:
            return
        ts = self
        v_argbox, v_index = hop.inputargs(self.getredrepr(PTRTYPE),
                                          self.getredrepr(lltype.Signed))
        c_deepfrozen = inputconst(lltype.Bool, hop.args_s[0].deepfrozen)
        fielddesc = rcontainer.ArrayFieldDesc(self, PTRTYPE.TO)
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(
            rtimeshift.ll_gengetarrayitem,
            [ts.s_JITState, annmodel.s_Bool, s_fielddesc,
                                ts.s_RedBox, ts.s_RedBox],
            [v_jitstate,       c_deepfrozen, c_fielddesc,
                                   v_argbox,    v_index ],
            ts.s_RedBox)

    def translate_op_getarraysize(self, hop):
        PTRTYPE = originalconcretetype(hop.args_s[0])
        ts = self
        [v_argbox] = hop.inputargs(self.getredrepr(PTRTYPE))
        
        fielddesc = rcontainer.ArrayFieldDesc(self, PTRTYPE.TO)
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(
            rtimeshift.ll_gengetarraysize,
            [ts.s_JITState, s_fielddesc, ts.s_RedBox],
            [v_jitstate,    c_fielddesc, v_argbox   ],
            ts.s_RedBox)


    def translate_op_setfield(self, hop):
        if isinstance(hop.args_r[0], BlueRepr):
            return hop.args_r[0].timeshift_setfield(hop)
        ts = self
        PTRTYPE = originalconcretetype(hop.args_s[0])
        VALUETYPE = originalconcretetype(hop.args_s[2])
        if VALUETYPE is lltype.Void:
            return
        if hop.args_v[0] == ts.exceptiondesc.cexcdata:
            # reading one of the exception boxes (exc_type or exc_value)
            fieldname = hop.args_v[1].value
            if fieldname == 'exc_type':
                writer = rtimeshift.setexctypebox
            elif fieldname == 'exc_value':
                writer = rtimeshift.setexcvaluebox
            else:
                raise Exception("setfield(exc_data, %r)" % (fieldname,))
            v_valuebox = hop.inputarg(self.getredrepr(VALUETYPE), arg=2)
            v_jitstate = hop.llops.getjitstate()
            hop.llops.genmixlevelhelpercall(writer,
                                            [ts.s_JITState, ts.s_RedBox],
                                            [v_jitstate,    v_valuebox ],
                                            annmodel.s_None)
            return
        # non virtual case ...
        v_destbox, c_fieldname, v_valuebox = hop.inputargs(self.getredrepr(PTRTYPE),
                                                           green_void_repr,
                                                           self.getredrepr(VALUETYPE)
                                                           )
        v_destbox = hop.llops.as_ptrredbox(v_destbox)
        structdesc = rcontainer.StructTypeDesc(self, PTRTYPE.TO)
        fielddesc = structdesc.getfielddesc(c_fieldname.value)
        assert fielddesc is not None   # skipped above
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_gensetfield,
            [ts.s_JITState, s_fielddesc, ts.s_PtrRedBox, ts.s_RedBox],
            [v_jitstate,    c_fielddesc, v_destbox,      v_valuebox],
            annmodel.s_None)

    def translate_op_setarrayitem(self, hop):
        PTRTYPE = originalconcretetype(hop.args_s[0])
        VALUETYPE = PTRTYPE.TO.OF
        if VALUETYPE is lltype.Void:
            return
        ts = self
        v_argbox, v_index, v_valuebox= hop.inputargs(self.getredrepr(PTRTYPE),
                                                     self.getredrepr(lltype.Signed),
                                                     self.getredrepr(VALUETYPE))
        fielddesc = rcontainer.ArrayFieldDesc(self, PTRTYPE.TO)
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        hop.llops.genmixlevelhelpercall(rtimeshift.ll_gensetarrayitem,
            [ts.s_JITState, s_fielddesc, ts.s_RedBox, ts.s_RedBox, ts.s_RedBox],
            [v_jitstate,    c_fielddesc, v_argbox,    v_index    , v_valuebox ],
            ts.s_RedBox)

    def translate_op_getsubstruct(self, hop):
        ##if isinstance(hop.args_r[0], BlueRepr):
        ##    return hop.args_r[0].timeshift_getsubstruct(hop)
        ts = self
        PTRTYPE = originalconcretetype(hop.args_s[0])
        v_argbox, c_fieldname = hop.inputargs(self.getredrepr(PTRTYPE),
                                              green_void_repr)
        v_argbox = hop.llops.as_ptrredbox(v_argbox)
        fielddesc = rcontainer.NamedFieldDesc(self, PTRTYPE, c_fieldname.value)
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_gengetsubstruct,
            [ts.s_JITState, s_fielddesc, ts.s_PtrRedBox],
            [v_jitstate,    c_fielddesc, v_argbox      ],
            ts.s_RedBox)

    def translate_op_getarraysubstruct(self, hop):
        PTRTYPE = originalconcretetype(hop.args_s[0])
        ts = self
        v_argbox, v_index = hop.inputargs(self.getredrepr(PTRTYPE),
                                          self.getredrepr(lltype.Signed))
        fielddesc = rcontainer.ArrayFieldDesc(self, PTRTYPE.TO)
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(
            rtimeshift.ll_gengetarraysubstruct,
            [ts.s_JITState, s_fielddesc, ts.s_RedBox, ts.s_RedBox],
            [v_jitstate,    c_fielddesc, v_argbox,    v_index    ],
            ts.s_RedBox)


    def translate_op_cast_pointer(self, hop):
        FROM_TYPE = originalconcretetype(hop.args_s[0])
        [v_argbox] = hop.inputargs(self.getredrepr(FROM_TYPE))
        return v_argbox

    def translate_op_malloc(self, hop):
        r_result = hop.r_result
        return r_result.create(hop)

    def translate_op_malloc_varsize(self, hop):
        ts = self
        assert isinstance(hop.r_result, RedRepr)
        PTRTYPE = originalconcretetype(hop.s_result)
        TYPE = PTRTYPE.TO
        v_size = hop.inputarg(self.getredrepr(lltype.Signed), arg=1)
        if isinstance(TYPE, lltype.Struct):
            return hop.r_result.create_varsize(hop, v_size)
        
        contdesc = rcontainer.ArrayFieldDesc(self, TYPE)
        c_contdesc = inputconst(lltype.Void, contdesc)
        s_contdesc = ts.rtyper.annotator.bookkeeper.immutablevalue(contdesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_genmalloc_varsize,
                   [ts.s_JITState, s_contdesc, ts.s_RedBox],
                   [v_jitstate,    c_contdesc, v_size     ], ts.s_RedBox)
        
    def translate_op_zero_gc_pointers_inside(self, hop):
        pass

    def translate_op_ptr_nonzero(self, hop, reverse=False):
        ts = self
        PTRTYPE = originalconcretetype(hop.args_s[0])
        v_argbox, = hop.inputargs(self.getredrepr(PTRTYPE))
        v_argbox = hop.llops.as_ptrredbox(v_argbox)
        v_jitstate = hop.llops.getjitstate()
        c_reverse = hop.inputconst(lltype.Bool, reverse)
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_genptrnonzero,
            [ts.s_JITState, ts.s_PtrRedBox, annmodel.s_Bool],
            [v_jitstate   , v_argbox      , c_reverse      ],
            ts.s_RedBox)

    def translate_op_ptr_iszero(self, hop):
        return self.translate_op_ptr_nonzero(hop, reverse=True)

    def translate_op_ptr_eq(self, hop, reverse=False):
        ts = self
        PTRTYPE = originalconcretetype(hop.args_s[0])
        r_ptr = self.getredrepr(PTRTYPE)
        v_argbox0, v_argbox1 = hop.inputargs(r_ptr, r_ptr)
        v_argbox0 = hop.llops.as_ptrredbox(v_argbox0)
        v_argbox1 = hop.llops.as_ptrredbox(v_argbox1)
        v_jitstate = hop.llops.getjitstate()
        c_reverse = hop.inputconst(lltype.Bool, reverse)
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_genptreq,
            [ts.s_JITState, ts.s_PtrRedBox, ts.s_PtrRedBox, annmodel.s_Bool],
            [v_jitstate   , v_argbox0     , v_argbox1     , c_reverse      ],
            ts.s_RedBox)

    def translate_op_ptr_ne(self, hop):
        return self.translate_op_ptr_eq(hop, reverse=True)


    # special operations inserted by the HintGraphTransformer

    def translate_op_ensure_queue(self, hop, prefix=''):
        mpfamily = hop.args_v[0].value
        subclass = self.get_dispatch_subclass(mpfamily)
        s_subclass = self.rtyper.annotator.bookkeeper.immutablevalue(subclass)
        c_subclass = inputconst(lltype.Void, subclass)
        v_jitstate = hop.llops.getjitstate()
        ensure_queue = getattr(rtimeshift, prefix+'ensure_queue')
        v_queue =  hop.llops.genmixlevelhelpercall(ensure_queue,
                             [self.s_JITState, s_subclass],
                             [v_jitstate     , c_subclass],
                             self.s_Queue)
        hop.llops.append(flowmodel.SpaceOperation('same_as', [v_queue],
                                                  self.v_queue))


    def translate_op_replayable_ensure_queue(self, hop):
        return self.translate_op_ensure_queue(hop, prefix='replayable_')

        
    def translate_op_enter_frame(self, hop):
        v_jitstate = hop.llops.getjitstate()
        hop.llops.genmixlevelhelpercall(rtimeshift.enter_frame,
                                        [self.s_JITState, self.s_Queue],
                                        [v_jitstate     , self.v_queue],
                                        annmodel.s_None)

    def translate_op_leave_graph_red(self, hop, is_portal=False):
        c_is_portal = inputconst(lltype.Bool, is_portal)
        v_newjs = hop.llops.genmixlevelhelpercall(rtimeshift.leave_graph_red,
                            [self.s_Queue, annmodel.s_Bool],
                            [self.v_queue, c_is_portal],
                            self.s_JITState)
        hop.llops.setjitstate(v_newjs)

    def translate_op_leave_graph_portal(self, hop):
        self.translate_op_leave_graph_red(hop, is_portal=True)

    def translate_op_leave_graph_gray(self, hop):
        v_newjs = hop.llops.genmixlevelhelpercall(rtimeshift.leave_graph_gray,
                            [self.s_Queue],
                            [self.v_queue],
                            self.s_JITState)
        hop.llops.setjitstate(v_newjs)

    def translate_op_leave_graph_yellow(self, hop):
        v_newjs = hop.llops.genmixlevelhelpercall(
                            rtimeshift.leave_graph_yellow,
                            [self.s_Queue],
                            [self.v_queue],
                            self.s_JITState)
        hop.llops.setjitstate(v_newjs)

    def translate_op_save_locals(self, hop):
        v_jitstate = hop.llops.getjitstate()
        boxes_r = [self.getredrepr(originalconcretetype(hs))
                   for hs in hop.args_s]
        boxes_v = hop.inputargs(*boxes_r)
        boxes_s = [self.s_RedBox] * len(hop.args_v)
        hop.llops.genmixlevelhelpercall(rtimeshift.save_locals,
                                        [self.s_JITState] + boxes_s,
                                        [v_jitstate     ] + boxes_v,
                                        annmodel.s_None)

    def translate_op_save_greens(self, hop):
        v_jitstate = hop.llops.getjitstate()
        greens_v = list(self.wrap_green_vars(hop.llops, hop.args_v))
        greens_s = [self.s_ConstOrVar] * len(greens_v)
        return hop.llops.genmixlevelhelpercall(rtimeshift.save_greens,
                                               [self.s_JITState] + greens_s,
                                               [v_jitstate     ] + greens_v,
                                               annmodel.s_None)

    def translate_op_enter_block(self, hop):
        v_jitstate = hop.llops.getjitstate()
        hop.llops.genmixlevelhelpercall(rtimeshift.enter_block,
                                        [self.s_JITState],
                                        [v_jitstate     ],
                                        annmodel.s_None)

    def translate_op_restore_local(self, hop):
        assert isinstance(hop.args_v[0], flowmodel.Constant)
        index = hop.args_v[0].value
        c_index = hop.inputconst(lltype.Signed, index)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.getlocalbox,
                    [self.s_JITState, annmodel.SomeInteger(nonneg=True)],
                    [v_jitstate     , c_index                          ],
                    self.s_RedBox)

    def translate_op_restore_green(self, hop):
        assert isinstance(hop.args_v[0], flowmodel.Constant)
        index = hop.args_v[0].value
        c_index = hop.inputconst(lltype.Signed, index)
        TYPE = originalconcretetype(hop.s_result)
        s_TYPE = self.rtyper.annotator.bookkeeper.immutablevalue(TYPE)
        c_TYPE = hop.inputconst(lltype.Void, TYPE)
        s_result = annmodel.lltype_to_annotation(TYPE)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_getgreenbox,
                  [self.s_JITState, annmodel.SomeInteger(nonneg=True), s_TYPE],
                  [v_jitstate     , c_index                          , c_TYPE],
                  s_result)

    def translate_op_is_early_constant(self, hop):
        hs = hop.args_s[0]
        if hs.is_green():
            return hop.inputconst(lltype.Bool, True)
        return self.translate_op_is_constant(hop)

    def translate_op_is_constant(self, hop):
        hs = hop.args_s[0]
        r_arg = self.getredrepr(originalconcretetype(hs))
        [v_arg] = hop.inputargs(r_arg)
        return hop.llops.genmixlevelhelpercall(rvalue.ll_is_constant,
                                               [self.s_RedBox],
                                               [v_arg        ],
                                               annmodel.SomeBool())

    def translate_op_revealconst(self, hop):
        hs = hop.args_s[0]
        TYPE = originalconcretetype(hs)
        r_arg = self.getredrepr(TYPE)
        [v_arg] = hop.inputargs(r_arg)
        s_TYPE = self.rtyper.annotator.bookkeeper.immutablevalue(TYPE)
        c_TYPE = hop.inputconst(lltype.Void, TYPE)
        s_result = annmodel.lltype_to_annotation(TYPE)
        return hop.llops.genmixlevelhelpercall(rvalue.ll_getvalue,
                                               [self.s_RedBox, s_TYPE],
                                               [v_arg        , c_TYPE],
                                               s_result)

    def wrap_green_vars(self, llops, vars):
        v_jitstate = llops.getjitstate()
        for var in vars:
            s_var = annmodel.lltype_to_annotation(var.concretetype)
            yield llops.genmixlevelhelpercall(rvalue.ll_gv_fromvalue,
                                              [self.s_JITState, s_var],
                                              [v_jitstate,      var  ],
                                              self.s_ConstOrVar)

    def translate_op_split(self, hop, splitfn=rtimeshift.split,
                                      reverse=False,
                                      s_result=annmodel.s_Bool):
        if splitfn is rtimeshift.split:
            nb_fixed_args = 2
        else:
            nb_fixed_args = 3

        r_switch = self.getredrepr(lltype.Bool)
        GREENS = [v.concretetype for v in hop.args_v[nb_fixed_args:]]
        extra_r = [self.getgreenrepr(TYPE) for TYPE in GREENS]
        if splitfn is rtimeshift.split_raisingop:
            r_switch = lltype.Void
            extra_r.insert(0, lltype.Void)
        elif splitfn is not rtimeshift.split:
            TYPE = originalconcretetype(hop.args_s[2])
            r_ptrbox = self.getredrepr(TYPE)
            extra_r.insert(0, r_ptrbox)
        vlist = hop.inputargs(r_switch, lltype.Signed, *extra_r)

        v_jitstate = hop.llops.getjitstate()
        v_switch = vlist[0]
        c_resumepoint = vlist[1]
        greens_v = list(self.wrap_green_vars(hop.llops,
                                             vlist[nb_fixed_args:]))

        s_Int = annmodel.SomeInteger(nonneg=True)
        args_s = [self.s_JITState, self.s_RedBox, s_Int]
        args_v = [v_jitstate, v_switch, c_resumepoint]

        if splitfn is rtimeshift.split_raisingop:
            bk = self.rtyper.annotator.bookkeeper
            excclass = vlist[2].value
            exccdef = bk.getuniqueclassdef(excclass)
            ll_exc = self.rtyper.exceptiondata.get_standard_ll_exc_instance(
                self.rtyper, exccdef)
            LL_EXC = lltype.typeOf(ll_exc)
            c_excinstance = hop.inputconst(LL_EXC, ll_exc)
            s_excinstance = annmodel.lltype_to_annotation(LL_EXC)
            del args_s[1]    # no v_switch in this case
            del args_v[1]
            args_s += [s_excinstance]
            args_v += [c_excinstance]
        elif splitfn is not rtimeshift.split:
            v_ptrbox = vlist[2]
            c_reverse = hop.inputconst(lltype.Bool, reverse)
            args_s += [self.s_PtrRedBox,                 annmodel.s_Bool]
            args_v += [hop.llops.as_ptrredbox(v_ptrbox), c_reverse      ]

        args_s += [self.s_ConstOrVar] * len(greens_v)
        args_v += greens_v
        return hop.llops.genmixlevelhelpercall(splitfn,
                                               args_s, args_v,
                                               s_result)

    def translate_op_split_ptr_nonzero(self, hop):
        return self.translate_op_split(hop, rtimeshift.split_ptr_nonzero,
                                            reverse=False)

    def translate_op_split_ptr_iszero(self, hop):
        return self.translate_op_split(hop, rtimeshift.split_ptr_nonzero,
                                            reverse=True)

    def translate_op_split_raisingop(self, hop):
        self.translate_op_split(hop, rtimeshift.split_raisingop,
                                s_result=annmodel.s_None)

    def translate_op_collect_split(self, hop):
        GREENS = [v.concretetype for v in hop.args_v[1:]]
        greens_r = [self.getgreenrepr(TYPE) for TYPE in GREENS]
        vlist = hop.inputargs(lltype.Signed, *greens_r)

        v_jitstate = hop.llops.getjitstate()
        c_resumepoint = vlist[0]
        greens_v = list(self.wrap_green_vars(hop.llops, vlist[1:]))

        s_Int = annmodel.SomeInteger(nonneg=True)
        args_s = [self.s_JITState, s_Int]
        args_s += [self.s_ConstOrVar] * len(greens_v)
        args_v = [v_jitstate, c_resumepoint]
        args_v += greens_v
        v_newjs = hop.llops.genmixlevelhelpercall(rtimeshift.collect_split,
                                                  args_s, args_v,
                                                  self.s_JITState)
        hop.llops.setjitstate(v_newjs)

    def translate_op_merge_point(self, hop, global_resumer=None):
        mpfamily = hop.args_v[0].value
        attrname = hop.args_v[1].value
        DispatchQueueSubclass = self.get_dispatch_subclass(mpfamily)

        if global_resumer is not None:
            states_dic = {}
            def merge_point(jitstate, *key):
                return rtimeshift.retrieve_jitstate_for_merge(states_dic,
                                                              jitstate, key,
                                                              global_resumer)
        else:
            def merge_point(jitstate, *key):
                dispatchqueue = jitstate.frame.dispatchqueue
                assert isinstance(dispatchqueue, DispatchQueueSubclass)
                states_dic = getattr(dispatchqueue, attrname)
                return rtimeshift.retrieve_jitstate_for_merge(states_dic,
                                                              jitstate, key,
                                                              global_resumer)

        greens_v = []
        greens_s = []
        for r, v in zip(hop.args_r[2:], hop.args_v[2:]):
            s_precise_type = r.annotation()
            s_erased_type  = r.erased_annotation()
            r_precise_type = self.rtyper.getrepr(s_precise_type)
            r_erased_type  = self.rtyper.getrepr(s_erased_type)
            if r_precise_type.lowleveltype == lltype.Char:
                v_green = hop.llops.genop('cast_char_to_int', [v],
                                          resulttype = lltype.Signed)
            else:
                v_green = hop.llops.convertvar(v, r_precise_type, r_erased_type)

            greens_v.append(v_green)
            greens_s.append(s_erased_type)
        # YYY possibly reorder the variables to avoid too many
        #     specialized versions of retrieve_jitstate_for_merge

        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(merge_point,
                             [self.s_JITState] + greens_s,
                             [v_jitstate     ] + greens_v,
                             annmodel.SomeBool())

    def translate_op_guard_global_merge(self, hop):
        [c_resumepoint] = hop.inputargs(lltype.Signed)
        v_jitstate = hop.llops.getjitstate()

        s_Int = annmodel.SomeInteger(nonneg=True)
        return hop.llops.genmixlevelhelpercall(rtimeshift.guard_global_merge,
                                               [self.s_JITState, s_Int],
                                               [v_jitstate     , c_resumepoint],
                                               annmodel.s_None)
        
    def translate_op_global_merge_point(self, hop):
        mpfamily = hop.args_v[0].value
        attrname = hop.args_v[1].value
        N = mpfamily.resumepoint_after_mergepoint[attrname]
        tsgraph = mpfamily.tsgraph
        ts_fnptr = self.naked_tsfnptr(tsgraph)
        TS_FUNC = lltype.typeOf(ts_fnptr)
        dummy_args = [ARG._defl() for ARG in TS_FUNC.TO.ARGS[1:]]
        dummy_args = tuple(dummy_args)
        JITSTATE = self.r_JITState.lowleveltype
        RESIDUAL_FUNCTYPE = self.get_residual_functype(tsgraph)
        residualSigToken = self.RGenOp.sigToken(RESIDUAL_FUNCTYPE)
        ll_finish_jitstate = self.ll_finish_jitstate
        exceptiondesc = self.exceptiondesc

        args_s = [self.s_JITState] + [annmodel.lltype_to_annotation(ARG)
                                      for ARG in TS_FUNC.TO.ARGS[1:]]
        s_res = self.s_JITState
        tsfn = annlowlevel.PseudoHighLevelCallable(ts_fnptr, args_s, s_res)

        DispatchQueueSubclass = self.get_dispatch_subclass(mpfamily)

        def call_for_global_resuming(jitstate, resuming):
            dispatchqueue = DispatchQueueSubclass()
            dispatchqueue.resuming = resuming
            jitstate.frame.dispatchqueue = dispatchqueue
            jitstate.resumepoint = N
            finaljitstate = tsfn(jitstate, *dummy_args)
            if finaljitstate is not None:
                ll_finish_jitstate(finaljitstate, exceptiondesc,
                                   residualSigToken)

        return self.translate_op_merge_point(hop,
                        global_resumer = call_for_global_resuming)

    def translate_op_save_return(self, hop):
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.save_return,
                                               [self.s_JITState],
                                               [v_jitstate     ],
                                               annmodel.s_None)

    def translate_op_dispatch_next(self, hop):
        v_newjs = hop.llops.genmixlevelhelpercall(rtimeshift.dispatch_next,
                                                  [self.s_Queue],
                                                  [self.v_queue],
                                                  self.s_JITState)
        hop.llops.setjitstate(v_newjs)

    def translate_op_getresumepoint(self, hop):
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.getresumepoint,
                                               [self.s_JITState],
                                               [v_jitstate     ],
                                               annmodel.SomeInteger())

    def translate_op_promote(self, hop):
        TYPE = originalconcretetype(hop.args_s[0])
        r_arg = self.getredrepr(TYPE)
        [v_box] = hop.inputargs(r_arg)
        ERASED = self.RGenOp.erasedType(TYPE)
        desc = rtimeshift.PromotionDesc(ERASED, self)
        s_desc = self.rtyper.annotator.bookkeeper.immutablevalue(desc)
        c_desc = hop.inputconst(lltype.Void, desc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_promote,
                                    [self.s_JITState, self.s_RedBox, s_desc],
                                    [v_jitstate     , v_box        , c_desc],
                                    annmodel.SomeBool())

    def translate_op_rpyexc_raise(self, hop):
        EXCTYPE  = originalconcretetype(hop.args_s[0])
        EXCVALUE = originalconcretetype(hop.args_s[1])
        [v_exctype, v_excvalue] = hop.inputargs(self.getredrepr(EXCTYPE),
                                                self.getredrepr(EXCVALUE))
        v_exctype  = hop.llops.as_ptrredbox(v_exctype)
        v_excvalue = hop.llops.as_ptrredbox(v_excvalue)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.setexception,
                         [self.s_JITState, self.s_PtrRedBox, self.s_PtrRedBox],
                         [v_jitstate     , v_exctype       , v_excvalue      ],
                         annmodel.s_None)

    # handling of the various kinds of calls

    def translate_op_oopspec_was_residual(self, hop):
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.oopspec_was_residual,
                                               [self.s_JITState],
                                               [v_jitstate     ],
                                               annmodel.s_Bool)

    def translate_op_oopspec_call(self, hop, can_raise=True):
        # special-cased call, for things like list methods
        from pypy.jit.timeshifter.oop import OopSpecDesc, Index

        c_func = hop.args_v[0]
        fnobj = c_func.value._obj
        oopspecdesc = OopSpecDesc(self, fnobj, can_raise)
        hop.r_s_popfirstarg()

        args_v = []
        for obj in oopspecdesc.argtuple:
            if isinstance(obj, Index):
                hs = hop.args_s[obj.n]
                r_arg = self.getredrepr(originalconcretetype(hs))
                v = hop.inputarg(r_arg, arg=obj.n)
            else:
                v = hop.inputconst(self.getredrepr(lltype.typeOf(obj)), obj)
            args_v.append(v)

        # if the ll_handler() takes more arguments, it must be 'None' defaults.
        # Pass them as constant Nones.
        ts = self
        ll_handler = oopspecdesc.ll_handler

        couldfold = oopspecdesc.couldfold
        
        missing_args = ((ll_handler.func_code.co_argcount - 2 - couldfold) -
                        len(oopspecdesc.argtuple))
        assert missing_args >= 0
        if missing_args > 0:
            assert (ll_handler.func_defaults[-missing_args:] ==
                    (None,) * missing_args)
            ll_None = lltype.nullptr(ts.r_RedBox.lowleveltype.TO)
            args_v.extend([hop.llops.genconst(ll_None)] * missing_args)

        args_s = [ts.s_RedBox] * len(args_v)

        if oopspecdesc.is_method:
            args_s[0] = ts.s_PtrRedBox    # for more precise annotations
            args_v[0] = hop.llops.as_ptrredbox(args_v[0])

        if couldfold:
            args_s.insert(0, annmodel.s_Bool)
            hs_self = hop.args_s[oopspecdesc.argtuple[0].n]
            c_deepfrozen = inputconst(lltype.Bool, hs_self.deepfrozen)
            args_v.insert(0, c_deepfrozen)
        
        RESULT = originalconcretetype(hop.s_result)
        if RESULT is lltype.Void:
            s_result = annmodel.s_None
        else:
            s_result = ts.s_RedBox

        (s_oopspecdesc,
         r_oopspecdesc) = self.s_r_instanceof(oopspecdesc.__class__)
        ll_oopspecdesc = ts.annhelper.delayedconst(r_oopspecdesc,
                                                   oopspecdesc)
        c_oopspecdesc  = hop.llops.genconst(ll_oopspecdesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(ll_handler,
                                      [ts.s_JITState, s_oopspecdesc] + args_s,
                                      [v_jitstate,    c_oopspecdesc] + args_v,
                                      s_result)

    def translate_op_oopspec_call_noexc(self, hop):
        return self.translate_op_oopspec_call(hop, False)

    def translate_op_green_call(self, hop):
        for r_arg in hop.args_r:
            assert isinstance(r_arg, GreenRepr)
        assert isinstance(hop.r_result, GreenRepr)

        FUNC = hop.args_v[0].concretetype
        calldesc = rtimeshift.CallDesc(self.RGenOp, FUNC.TO)
        args_v = hop.args_v
        args_s = [annmodel.lltype_to_annotation(v.concretetype)
                  for v in args_v]
        s_result = annmodel.lltype_to_annotation(FUNC.TO.RESULT)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(calldesc.green_call,
                                               [self.s_JITState] + args_s,
                                               [v_jitstate     ] + args_v,
                                               s_result)

    def translate_op_green_call_noexc(self, hop):
        for r_arg in hop.args_r:
            assert isinstance(r_arg, GreenRepr)
        assert isinstance(hop.r_result, GreenRepr)
        v = hop.genop('direct_call', hop.args_v, hop.r_result.lowleveltype)
        return v

    def translate_op_green_indirect_call_noexc(self, hop):
        for r_arg in hop.args_r[:-1]:
            assert isinstance(r_arg, GreenRepr)
        assert isinstance(hop.r_result, GreenRepr)
        v = hop.genop('indirect_call', hop.args_v, hop.r_result.lowleveltype)
        return v

    def translate_op_red_call(self, hop):
        bk = self.annotator.bookkeeper
        v_jitstate = hop.llops.getjitstate()
        tsgraph = hop.args_v[0].value
        hop.r_s_popfirstarg()
        args_v = hop.inputargs(*self.get_args_r(tsgraph))
        fnptr = self.gettscallable(tsgraph)
        args_v[:0] = [hop.llops.genconst(fnptr), v_jitstate]
        RESULT = lltype.typeOf(fnptr).TO.RESULT
        v_newjitstate = hop.genop('direct_call', args_v, RESULT)
        hop.llops.setjitstate(v_newjitstate)
        return hop.genop('ptr_iszero', [v_newjitstate],
                         resulttype = lltype.Bool)

    def translate_op_indirect_red_call(self, hop):
        v_jitstate = hop.llops.getjitstate()
        FUNC = originalconcretetype(hop.args_s[0])
        v_func = hop.inputarg(self.getgreenrepr(FUNC), arg=0)
        graph2ts = hop.args_v[-1].value
        hop.r_s_pop(0)
        hop.r_s_pop()
        mapper, TS_FUNC, args_r = self.get_timeshift_mapper(graph2ts)
        v_tsfunc = hop.llops.genmixlevelhelpercall(mapper,
                                                   [annmodel.SomePtr(FUNC)],
                                                   [v_func                ],
                                                   annmodel.SomePtr(TS_FUNC))
        args_v = [v_tsfunc, v_jitstate] + hop.inputargs(*args_r)
        RESULT = v_tsfunc.concretetype.TO.RESULT
        args_v.append(hop.inputconst(lltype.Void, graph2ts.values()))
        v_newjitstate = hop.genop('indirect_call', args_v, RESULT)
        hop.llops.setjitstate(v_newjitstate)
        return hop.genop('ptr_iszero', [v_newjitstate],
                         resulttype = lltype.Bool)

    translate_op_gray_call            = translate_op_red_call
    translate_op_indirect_gray_call   = translate_op_indirect_red_call

    translate_op_yellow_call          = translate_op_red_call
    translate_op_indirect_yellow_call = translate_op_indirect_red_call

    def translate_op_residual_red_call(self, hop, color='red'):
        FUNC = originalconcretetype(hop.args_s[0])
        [v_funcbox] = hop.inputargs(self.getredrepr(FUNC))
        calldesc = rtimeshift.CallDesc(self.RGenOp, FUNC.TO)
        c_calldesc = inputconst(lltype.Void, calldesc)
        s_calldesc = self.rtyper.annotator.bookkeeper.immutablevalue(calldesc)
        v_jitstate = hop.llops.getjitstate()
        v_res = hop.llops.genmixlevelhelpercall(
                                 rtimeshift.ll_gen_residual_call,
                                 [self.s_JITState, s_calldesc, self.s_RedBox],
                                 [v_jitstate,      c_calldesc, v_funcbox    ],
                                 self.s_RedBox)
        return v_res

    def translate_op_residual_gray_call(self, hop):
        self.translate_op_residual_red_call(hop, color='gray')

    translate_op_residual_yellow_call       = translate_op_residual_red_call

    def translate_op_after_residual_call(self, hop):
        dopts = hop.args_v[0].value
        withexc = dopts['withexc']
        oop = dopts['oop']
        v_jitstate = hop.llops.getjitstate()
        if withexc:
            c_exception_desc = hop.inputconst(lltype.Void, self.exceptiondesc)
        else:
            c_exception_desc = hop.inputconst(lltype.Void, None)
        bk = self.rtyper.annotator.bookkeeper
        s_exception_desc = bk.immutablevalue(c_exception_desc.value)
        c_check_forced = hop.inputconst(lltype.Bool, not oop)
        v_after = hop.llops.genmixlevelhelpercall(
            rtimeshift.ll_after_residual_call,
            [self.s_JITState, s_exception_desc, annmodel.s_Bool],
            [v_jitstate     , c_exception_desc, c_check_forced ],
            self.s_RedBox)
        return v_after

    def translate_op_residual_fetch(self, hop):
        dopts = hop.args_v[1].value
        oop = dopts['oop']
        v_jitstate = hop.llops.getjitstate()
        v_flags = hop.inputarg(self.getredrepr(lltype.Signed), arg=0)
        bk = self.rtyper.annotator.bookkeeper
        c_exception_desc = hop.inputconst(lltype.Void, self.exceptiondesc)
        s_exception_desc = bk.immutablevalue(c_exception_desc.value)
        c_check_forced = hop.inputconst(lltype.Bool, not oop)
        return hop.llops.genmixlevelhelpercall(rtimeshift.residual_fetch,
           [self.s_JITState, s_exception_desc, annmodel.s_Bool, self.s_RedBox],
           [v_jitstate     , c_exception_desc, c_check_forced , v_flags      ],
           annmodel.s_None)

    def translate_op_reverse_split_queue(self, hop):
        hop.llops.genmixlevelhelpercall(rtimeshift.reverse_split_queue,
                                        [self.s_Queue],
                                        [self.v_queue],
                                        annmodel.s_None)


class HintLowLevelOpList(LowLevelOpList):
    """Warning: the HintLowLevelOpList's rtyper is the *original*
    rtyper, while the HighLevelOp's rtyper is actually our HintRTyper...
    """
    def __init__(self, hrtyper):
        LowLevelOpList.__init__(self, hrtyper.rtyper)
        self.hrtyper = hrtyper

    def hasparentgraph(self):
        return False   # for now

    def genmixlevelhelpercall(self, function, args_s, args_v, s_result):
        # XXX first approximation, will likely need some fine controlled
        # specialisation for these helpers too

        if isinstance(function, types.MethodType):
            if function.im_self is not None:
                # bound method => function and an extra first argument
                bk = self.rtyper.annotator.bookkeeper
                s_self = bk.immutablevalue(function.im_self)
                r_self = self.rtyper.getrepr(s_self)
                v_self = inputconst(r_self.lowleveltype,
                                    r_self.convert_const(function.im_self))
                args_s = [s_self] + args_s
                args_v = [v_self] + args_v
            function = function.im_func

        assert len(args_s) == len(args_v)
        graph = self.hrtyper.annhelper.getgraph(function, args_s, s_result)
        self.record_extra_call(graph) # xxx

        c = self.hrtyper.annhelper.graph2const(graph)

        # build the 'direct_call' operation
        try:
            RESULT = annmodel.annotation_to_lltype(s_result)
        except ValueError:
            RESULT = self.rtyper.getrepr(s_result).lowleveltype
        return self.genop('direct_call', [c]+args_v,
                          resulttype = RESULT)

    def getjitstate(self):
        return self.genop('getjitstate', [],
                          resulttype = self.hrtyper.r_JITState)

    def setjitstate(self, v_newjitstate):
        self.genop('setjitstate', [v_newjitstate])

    def as_redbox(self, v_ptrredbox):
        return self.genop('cast_pointer', [v_ptrredbox],
                          resulttype = self.hrtyper.r_RedBox)

    def as_ptrredbox(self, v_redbox):
        return self.genop('cast_pointer', [v_redbox],
                          resulttype = self.hrtyper.r_PtrRedBox)

# ____________________________________________________________

class __extend__(pairtype(HintTypeSystem, hintmodel.SomeLLAbstractValue)):

    def rtyper_makerepr((ts, hs_c), hrtyper):
        if hs_c.is_green():
            return hrtyper.getgreenrepr(hs_c.concretetype)
        else:
            return hrtyper.getredrepr(hs_c.concretetype)

    def rtyper_makekey((ts, hs_c), hrtyper):
        is_green = hs_c.is_green()
        return hs_c.__class__, is_green, hs_c.concretetype

class __extend__(pairtype(HintTypeSystem, hintmodel.SomeLLAbstractContainer)):

    def rtyper_makerepr((ts, hs_container), hrtyper):
        vstructdef = hs_container.contentdef
        assert isinstance(vstructdef, hintcontainer.VirtualStructDef)
        if vstructdef.degenerated:
            # fall back to a red repr
            return hrtyper.getredrepr(hs_container.concretetype)
        return BlueStructRepr(hs_container.concretetype, vstructdef,
                              hrtyper)

    def rtyper_makekey((ts, hs_container), hrtyper):        
        vstructdef = hs_container.contentdef
        assert isinstance(vstructdef, hintcontainer.VirtualStructDef)
        if vstructdef.degenerated:
            # fall back to a red repr
            return hs_container.__class__, "red", hs_container.concretetype

        T = None
        if vstructdef.vparent is not None:
            T = vstructdef.vparent.T

        key = [hs_container.__class__, vstructdef.T, T, vstructdef.vparentindex]
        for name in vstructdef.names:
            fielditem = vstructdef.fields[name]
            key.append(fielditem)

        return tuple(key)

class __extend__(pairtype(HintTypeSystem, annmodel.SomeImpossibleValue)):

    def rtyper_makerepr((ts, hs_c), hrtyper):
        return green_void_repr

    def rtyper_makekey((ts, hs_c), hrtyper):
        return hs_c.__class__,

class RedRepr(Repr):
    def __init__(self, original_concretetype, hrtyper):
        assert original_concretetype is not lltype.Void, (
            "cannot make red boxes for the lltype Void")
        self.original_concretetype = original_concretetype
        self.lowleveltype = hrtyper.r_RedBox.lowleveltype
        self.hrtyper = hrtyper
        self.build_portal_arg_helpers()

    def build_portal_arg_helpers(self):
        def collect_residual_args(v):
            return (v,)
        self.collect_residual_args = collect_residual_args

        TYPE = self.original_concretetype
        kind = self.hrtyper.RGenOp.kindToken(TYPE)
        boxcls = rvalue.ll_redboxcls(TYPE)
        
        def make_arg_redbox(jitstate, inputargs_gv, i):
            gv_arg = inputargs_gv[i]
            box = boxcls(kind, gv_arg)
            return box
        self.make_arg_redbox = make_arg_redbox
        make_arg_redbox.consumes = 1

##    def get_genop_var(self, v, llops):
##        ts = self.hrtyper
##        v_jitstate = hop.llops.getjitstate()
##        return llops.genmixlevelhelpercall(rtimeshift.ll_gvar_from_redbox,
##                       [ts.s_JITState, llops.hrtyper.s_RedBox],
##                       [v_jitstate,    v],
##                       ts.s_ConstOrVar)

    def convert_const(self, ll_value):
        RGenOp = self.hrtyper.RGenOp
        redbox = rvalue.redbox_from_prebuilt_value(RGenOp, ll_value)
        hrtyper = self.hrtyper
        return hrtyper.annhelper.delayedconst(hrtyper.r_RedBox, redbox)

    def residual_values(self, ll_value):
        return [ll_value]

    def residual_argtypes(self):
        return [self.original_concretetype]

    def residual_args_collector(self):
        return self.collect_residual_args

    def arg_redbox_maker(self):
        return self.make_arg_redbox

class RedStructRepr(RedRepr):
    typedesc = None
    _s_c_typedesc = None

    def gettypedesc(self):
        if self.typedesc is None:
            hrtyper = self.hrtyper
            T = self.original_concretetype.TO
            self.typedesc = rcontainer.StructTypeDesc(hrtyper, T)
        return self.typedesc

    def s_c_typedesc(self):
        if self._s_c_typedesc is not None:
            return self._s_c_typedesc
        ts = self.hrtyper
        typedesc = self.gettypedesc()
        annhelper = ts.annhelper
        s_r = annhelper.s_r_instanceof(rcontainer.StructTypeDesc)
        s_typedesc, r_typedesc = s_r 
        typedesc_ptr = ts.annhelper.delayedconst(r_typedesc, typedesc)
        ctypedesc = inputconst(lltype.typeOf(typedesc_ptr), typedesc_ptr)
        self._s_c_typedesc = s_typedesc, ctypedesc
        return self._s_c_typedesc

    def create(self, hop):
        ts = self.hrtyper
        s_typedesc, ctypedesc = self.s_c_typedesc()
        v_jitstate = hop.llops.getjitstate()
        v_ptrbox = hop.llops.genmixlevelhelpercall(rcontainer.create,
            [ts.s_JITState, s_typedesc], [v_jitstate, ctypedesc],
            ts.s_PtrRedBox)
        return hop.llops.as_redbox(v_ptrbox)

    def create_varsize(self, hop, v_size):
        ts = self.hrtyper
        s_typedesc, ctypedesc = self.s_c_typedesc()
        v_jitstate = hop.llops.getjitstate()
        v_ptrbox = hop.llops.genmixlevelhelpercall(rcontainer.create_varsize,
            [ts.s_JITState, s_typedesc, ts.s_RedBox],
            [v_jitstate,    ctypedesc,  v_size     ], ts.s_PtrRedBox)
        return hop.llops.as_redbox(v_ptrbox)

class RedVirtualizableStructRepr(RedStructRepr):

    def build_portal_arg_helpers(self):
        typedesc = self.gettypedesc()
        redirected_fielddescs = unrolling_iterable(
                                    typedesc.redirected_fielddescs)
        TYPE = self.original_concretetype
        kind = self.hrtyper.RGenOp.kindToken(TYPE)

        def make_arg_redbox(jitstate, inputargs_gv, i):
            box = typedesc.factory()
            jitstate.add_virtualizable(box)
            content = box.content
            assert isinstance(content, rcontainer.VirtualizableStruct)
            content_boxes = content.content_boxes
            gv_outside = inputargs_gv[i]
            i += 1
            for fieldesc, j in redirected_fielddescs:
                content_boxes[j] = fieldesc.makebox(None, inputargs_gv[i])
                i += 1
            content_boxes[-1] = rvalue.PtrRedBox(content_boxes[-1].kind,
                                                 gv_outside,
                                                 known_nonzero = True)
            return box
        
        self.make_arg_redbox = make_arg_redbox
        make_arg_redbox.consumes = len(typedesc.redirected_fielddescs)+1

    def residual_argtypes(self):
        argtypes = [self.original_concretetype]
        getredrepr = self.hrtyper.getredrepr
        typedesc = self.gettypedesc()
        for fielddesc, _ in typedesc.redirected_fielddescs:
            FIELDTYPE = fielddesc.RESTYPE
            argtypes.append(FIELDTYPE)
        return argtypes

    def residual_args_collector(self):
        typedesc = self.gettypedesc()
        return typedesc.collect_residual_args
    

##class VoidRedRepr(Repr):
##    def __init__(self, hrtyper):
##        self.lowleveltype = hrtyper.r_RedBox.lowleveltype

##    def convert_const(self, ll_value):
##        return lltype.nullptr(self.lowleveltype.TO)


class BlueRepr(Repr):
    # XXX todo
    pass


class GreenRepr(Repr):
    def __init__(self, lowleveltype):
        self.lowleveltype = lowleveltype
        self.original_concretetype = lowleveltype        

    def annotation(self):
        return annmodel.lltype_to_annotation(self.lowleveltype)

    def erased_annotation(self):
        T = self.lowleveltype
        if isinstance(T, lltype.Ptr):
            return annmodel.SomeAddress()
        elif T is lltype.Float:
            return annmodel.SomeFloat()
        elif T is lltype.Void:
            return annmodel.s_ImpossibleValue
        else:
            return annmodel.SomeInteger()

##    def get_genop_var(self, v, llops):
##        ts = self.hrtyper
##        v_jitstate = hop.llops.getjitstate()
##        return llops.genmixlevelhelpercall(rtimeshift.ll_gvar_from_constant,
##                                           [ts.s_JITState, self.annotation()],
##                                           [v_jitstate,    v],
##                                           ts.s_ConstOrVar)

    def convert_const(self, ll_value):
        return ll_value

    def residual_values(self, ll_value):
        return []

    #def timeshift_getsubstruct(self, hop):
    #    ...

green_signed_repr = GreenRepr(lltype.Signed)
green_void_repr   = GreenRepr(lltype.Void)

# collect the global precomputed reprs
PRECOMPUTED_GREEN_REPRS = {}
for _r in globals().values():
    if isinstance(_r, GreenRepr):
        PRECOMPUTED_GREEN_REPRS[_r.lowleveltype] = _r


class __extend__(pairtype(GreenRepr, RedRepr)):

    def convert_from_to((r_from, r_to), v, llops):
        assert r_from.lowleveltype == r_to.original_concretetype
        ts = llops.hrtyper
        v_jitstate = llops.getjitstate()
        return llops.genmixlevelhelpercall(rvalue.ll_fromvalue,
                        [ts.s_JITState, r_from.annotation()],
                        [v_jitstate,    v],
                        ts.s_RedBox)

c_void = flowmodel.Constant(None, concretetype=lltype.Void)

# ____________________________________________________________

def opname2vstr(name):
    lls = string_repr.convert_const(name)
    return inputconst(string_repr.lowleveltype, lls)
