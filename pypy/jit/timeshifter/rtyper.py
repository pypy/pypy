import types
from pypy.objspace.flow import model as flowmodel
from pypy.annotation import model as annmodel
from pypy.annotation.pairtype import pair, pairtype
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
from pypy.jit.timeshifter.transform import HintGraphTransformer
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

        (self.s_CodeGenerator,
         self.r_CodeGenerator) = self.s_r_instanceof(cgmodel.CodeGenerator)
        (self.s_JITState,
         self.r_JITState)      = self.s_r_instanceof(rtimeshift.JITState)
        (self.s_RedBox,
         self.r_RedBox)        = self.s_r_instanceof(rvalue.RedBox)
        (self.s_PtrRedBox,
         self.r_PtrRedBox)     = self.s_r_instanceof(rvalue.PtrRedBox)
        (self.s_OopSpecDesc,
         self.r_OopSpecDesc)   = self.s_r_instanceof(oop.OopSpecDesc)
        (self.s_ConstOrVar,
         self.r_ConstOrVar)    = self.s_r_instanceof(cgmodel.GenVarOrConst)
        (self.s_Block,
         self.r_Block)         = self.s_r_instanceof(cgmodel.CodeGenBlock)

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
            return rtimeshift.JITState(builder, None,
                                       null_exc_type_box,
                                       null_exc_value_box)
        self.ll_fresh_jitstate = ll_fresh_jitstate

        def ll_finish_jitstate(jitstate, graphsigtoken):
            returnbox = rtimeshift.getreturnbox(jitstate)
            gv_ret = returnbox.getgenvar(jitstate.curbuilder)
            store_global_excdata(jitstate)
            jitstate.curbuilder.finish_and_return(graphsigtoken, gv_ret)
        self.ll_finish_jitstate = ll_finish_jitstate

    def specialize(self, view=False):
        """
        Driver for running the timeshifter.
        """
        self.type_system.perform_normalizations(self)
        self.annotator.bookkeeper.compute_after_normalization()
        entrygraph = self.annotator.translator.graphs[0]
        pending = [entrygraph]
        seen = {entrygraph: True}
        while pending:
            graph = pending.pop()
            for nextgraph in self.transform_graph(graph):
                if nextgraph not in seen:
                    pending.append(nextgraph)
                    seen[nextgraph] = True
        if view:
            self.annotator.translator.view()     # in the middle
        for graph in seen:
            self.timeshift_graph(graph)

    def transform_graph(self, graph):
        # prepare the graphs by inserting all bookkeeping/dispatching logic
        # as special operations
        assert graph.startblock in self.annotator.annotated
        transformer = HintGraphTransformer(self.annotator, graph)
        transformer.transform()
        flowmodel.checkgraph(graph)    # for now
        return transformer.tsgraphs_seen

    def timeshift_graph(self, graph):
        # specialize all blocks of this graph
        for block in list(graph.iterblocks()):
            self.annotator.annotated[block] = graph
            self.specialize_block(block)
        # "normalize" the graphs by putting an explicit v_jitstate variable
        # everywhere
        self.insert_v_jitstate_everywhere(graph)
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

    def make_new_lloplist(self, block):
        return HintLowLevelOpList(self)

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
                    redreprcls = RedStructRepr
            r = redreprcls(lowleveltype, self)
            self.red_reprs[lowleveltype] = r
            return r

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
            attrnames = mergepointfamily.getattrnames()
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
        from pypy.translator.unsimplify import varoftype
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

    def generic_translate_operation(self, hop, force=False):
        # detect constant-foldable all-green operations
        if not force and hop.spaceop.opname not in rtimeshift.FOLDABLE_OPS:
            return None
        green = True
        for r_arg in hop.args_r:
            green = green and isinstance(r_arg, GreenRepr)
        if green and isinstance(hop.r_result, GreenRepr):
            # Just generate the same operation in the timeshifted graph.
            hop.llops.append(hop.spaceop)
            return hop.spaceop.result
        else:
            print "RED op", hop.spaceop
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

    def translate_op_hint(self, hop):
        # don't try to generate hint operations, just discard them
        hints = hop.args_v[-1].value
        if hints.get('forget', False):
            T = originalconcretetype(hop.args_s[0])
            v_redbox = hop.inputarg(self.getredrepr(T), arg=0)
            assert isinstance(hop.r_result, GreenRepr)
            ts = self
            c_T = hop.inputconst(lltype.Void, T)
            s_T = ts.rtyper.annotator.bookkeeper.immutablevalue(T)
            s_res = annmodel.lltype_to_annotation(T)
            return hop.llops.genmixlevelhelpercall(rvalue.ll_getvalue,
                                                   [ts.s_RedBox, s_T],
                                                   [v_redbox,    c_T],
                                                   s_res)
                                                   
        return hop.inputarg(hop.r_result, arg=0)

    def translate_op_debug_log_exc(self, hop): # don't timeshift debug_log_exc
        pass

    def translate_op_keepalive(self,hop):
        pass

    def translate_op_same_as(self, hop):
        [v] = hop.inputargs(hop.r_result)
        return v

    def translate_op_getfield(self, hop):
        if isinstance(hop.args_r[0], BlueRepr):
            return hop.args_r[0].timeshift_getfield(hop)
        ts = self
        if hop.args_v[0] == ts.cexcdata:
            # reading one of the exception boxes (exc_type or exc_value)
            fieldname = hop.args_v[1].value
            if fieldname.endswith('exc_type'):
                reader = rtimeshift.getexctypebox
            elif fieldname.endswith('exc_value'):
                reader = rtimeshift.getexcvaluebox
            else:
                raise Exception("getfield(exc_data, %r)" % (fieldname,))
            v_jitstate = hop.llops.getjitstate()
            return hop.llops.genmixlevelhelpercall(reader,
                                                   [ts.s_JITState],
                                                   [v_jitstate   ],
                                                   ts.s_RedBox)
        # non virtual case        
        PTRTYPE = originalconcretetype(hop.args_s[0])
        if PTRTYPE.TO._hints.get('immutable', False): # foldable if all green
            res = self.generic_translate_operation(hop, force=True)
            if res is not None:
                return res
            
        v_argbox, c_fieldname = hop.inputargs(self.getredrepr(PTRTYPE),
                                              green_void_repr)
        structdesc = rcontainer.StructTypeDesc(self.RGenOp, PTRTYPE.TO)
        fielddesc = structdesc.getfielddesc(c_fieldname.value)
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_gengetfield,
            [ts.s_JITState, s_fielddesc, ts.s_RedBox],
            [v_jitstate,    c_fielddesc, v_argbox   ],
            ts.s_RedBox)

    def translate_op_getarrayitem(self, hop):
        PTRTYPE = originalconcretetype(hop.args_s[0])
        if PTRTYPE.TO._hints.get('immutable', False): # foldable if all green
            res = self.generic_translate_operation(hop, force=True)
            if res is not None:
                return res

        ts = self
        v_argbox, v_index = hop.inputargs(self.getredrepr(PTRTYPE),
                                          self.getredrepr(lltype.Signed))
        fielddesc = rcontainer.ArrayFieldDesc(self.RGenOp, PTRTYPE.TO)
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(
            rtimeshift.ll_gengetarrayitem,
            [ts.s_JITState, s_fielddesc, ts.s_RedBox, ts.s_RedBox],
            [v_jitstate,    c_fielddesc, v_argbox,    v_index    ],
            ts.s_RedBox)

    def translate_op_getarraysize(self, hop):
        res = self.generic_translate_operation(hop, force=True)
        if res is not None:
            return res
        
        PTRTYPE = originalconcretetype(hop.args_s[0])
        ts = self
        [v_argbox] = hop.inputargs(self.getredrepr(PTRTYPE))
        
        fielddesc = rcontainer.ArrayFieldDesc(self.RGenOp, PTRTYPE.TO)
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
        if hop.args_v[0] == ts.cexcdata:
            # reading one of the exception boxes (exc_type or exc_value)
            fieldname = hop.args_v[1].value
            if fieldname.endswith('exc_type'):
                writer = rtimeshift.setexctypebox
            elif fieldname.endswith('exc_value'):
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
        structdesc = rcontainer.StructTypeDesc(self.RGenOp, PTRTYPE.TO)
        fielddesc = structdesc.getfielddesc(c_fieldname.value)
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_gensetfield,
            [ts.s_JITState, s_fielddesc, ts.s_RedBox, ts.s_RedBox],
            [v_jitstate,    c_fielddesc, v_destbox,   v_valuebox],
            annmodel.s_None)

    def translate_op_setarrayitem(self, hop):
        PTRTYPE = originalconcretetype(hop.args_s[0])
        VALUETYPE = PTRTYPE.TO.OF
        ts = self
        v_argbox, v_index, v_valuebox= hop.inputargs(self.getredrepr(PTRTYPE),
                                                     self.getredrepr(lltype.Signed),
                                                     self.getredrepr(VALUETYPE))
        fielddesc = rcontainer.ArrayFieldDesc(self.RGenOp, PTRTYPE.TO)
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
        fielddesc = rcontainer.NamedFieldDesc(self.RGenOp, PTRTYPE,
                                              c_fieldname.value)
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_gengetsubstruct,
            [ts.s_JITState, s_fielddesc, ts.s_RedBox],
            [v_jitstate,    c_fielddesc, v_argbox   ],
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
        if isinstance(TYPE, lltype.Struct):
            contdesc = rcontainer.StructTypeDesc(self.RGenOp, TYPE)
        else:
            contdesc = rcontainer.ArrayFieldDesc(self.RGenOp, TYPE)
        c_contdesc = inputconst(lltype.Void, contdesc)
        s_contdesc = ts.rtyper.annotator.bookkeeper.immutablevalue(contdesc)
        v_jitstate = hop.llops.getjitstate()
        v_size = hop.inputarg(self.getredrepr(lltype.Signed), arg=1)
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_genmalloc_varsize,
                   [ts.s_JITState, s_contdesc, ts.s_RedBox],
                   [v_jitstate,    c_contdesc, v_size     ], ts.s_RedBox)
        
        
    def translate_op_ptr_nonzero(self, hop, reverse=False):
        ts = self
        PTRTYPE = originalconcretetype(hop.args_s[0])
        v_argbox, = hop.inputargs(self.getredrepr(PTRTYPE))
        v_jitstate = hop.llops.getjitstate()
        c_reverse = hop.inputconst(lltype.Bool, reverse)
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_genptrnonzero,
            [ts.s_JITState, ts.s_RedBox, annmodel.SomeBool()],
            [v_jitstate,    v_argbox,    c_reverse          ],
            ts.s_RedBox)

    def translate_op_ptr_iszero(self, hop):
        return self.translate_op_ptr_nonzero(hop, reverse=True)


    # special operations inserted by the HintGraphTransformer

    def translate_op_enter_graph(self, hop):
        mpfamily = hop.args_v[0].value
        subclass = self.get_dispatch_subclass(mpfamily)
        s_subclass = self.rtyper.annotator.bookkeeper.immutablevalue(subclass)
        c_subclass = inputconst(lltype.Void, subclass)
        v_jitstate = hop.llops.getjitstate()
        hop.llops.genmixlevelhelpercall(rtimeshift.enter_graph,
                                        [self.s_JITState, s_subclass],
                                        [v_jitstate     , c_subclass],
                                        annmodel.s_None)

    def translate_op_leave_graph_red(self, hop):
        v_jitstate = hop.llops.getjitstate()
        v_newjs = hop.llops.genmixlevelhelpercall(rtimeshift.leave_graph_red,
                                                  [self.s_JITState],
                                                  [v_jitstate     ],
                                                  self.s_JITState)
        hop.llops.setjitstate(v_newjs)

    def translate_op_leave_graph_gray(self, hop):
        v_jitstate = hop.llops.getjitstate()
        v_newjs = hop.llops.genmixlevelhelpercall(rtimeshift.leave_graph_gray,
                                                  [self.s_JITState],
                                                  [v_jitstate     ],
                                                  self.s_JITState)
        hop.llops.setjitstate(v_newjs)

    def translate_op_leave_graph_yellow(self, hop):
        v_jitstate = hop.llops.getjitstate()
        v_njs = hop.llops.genmixlevelhelpercall(rtimeshift.leave_graph_yellow,
                                                [self.s_JITState],
                                                [v_jitstate     ],
                                                self.s_JITState)
        hop.llops.setjitstate(v_njs)

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

    def translate_op_fetch_return(self, hop):
        ts = self
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.getreturnbox,
                                               [ts.s_JITState],
                                               [v_jitstate   ],
                                               ts.s_RedBox)

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

    def translate_op_split(self, hop):
        r_switch = self.getredrepr(lltype.Bool)
        GREENS = [v.concretetype for v in hop.args_v[2:]]
        greens_r = [self.getgreenrepr(TYPE) for TYPE in GREENS]
        vlist = hop.inputargs(r_switch, lltype.Signed, *greens_r)

        v_jitstate = hop.llops.getjitstate()
        v_switch = vlist[0]
        c_resumepoint = vlist[1]
        greens_v = list(self.wrap_green_vars(hop.llops, vlist[2:]))

        s_Int = annmodel.SomeInteger(nonneg=True)
        args_s = [self.s_JITState, self.s_RedBox, s_Int]
        args_s += [self.s_ConstOrVar] * len(greens_v)
        args_v = [v_jitstate, v_switch, c_resumepoint]
        args_v += greens_v
        hop.llops.genmixlevelhelpercall(rtimeshift.split, args_s, args_v,
                                        annmodel.s_None)

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
        hop.llops.genmixlevelhelpercall(rtimeshift.collect_split,
                                        args_s, args_v,
                                        annmodel.s_None)

    def translate_op_merge_point(self, hop):
        mpfamily = hop.args_v[0].value
        attrname = hop.args_v[1].value
        DispatchQueueSubclass = self.get_dispatch_subclass(mpfamily)

        def merge_point(jitstate, *key):
            dispatch_queue = jitstate.frame.dispatch_queue
            assert isinstance(dispatch_queue, DispatchQueueSubclass)
            states_dic = getattr(dispatch_queue, attrname)
            return rtimeshift.retrieve_jitstate_for_merge(states_dic,
                                                          jitstate, key)

        greens_v = []
        greens_s = []
        for r, v in zip(hop.args_r[2:], hop.args_v[2:]):
            s_precise_type = r.annotation()
            s_erased_type  = r.erased_annotation()
            r_precise_type = self.rtyper.getrepr(s_precise_type)
            r_erased_type  = self.rtyper.getrepr(s_erased_type)
            greens_v.append(hop.llops.convertvar(v, r_precise_type,
                                                    r_erased_type))
            greens_s.append(s_erased_type)

        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(merge_point,
                             [self.s_JITState] + greens_s,
                             [v_jitstate     ] + greens_v,
                             annmodel.SomeBool())

    def translate_op_save_return(self, hop):
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.save_return,
                                               [self.s_JITState],
                                               [v_jitstate     ],
                                               annmodel.s_None)

    def translate_op_dispatch_next(self, hop):
        v_jitstate = hop.llops.getjitstate()
        v_newjs = hop.llops.genmixlevelhelpercall(rtimeshift.dispatch_next,
                                                  [self.s_JITState],
                                                  [v_jitstate     ],
                                                  self.s_JITState)
        hop.llops.setjitstate(v_newjs)
        return hop.llops.genmixlevelhelpercall(rtimeshift.getresumepoint,
                                               [self.s_JITState],
                                               [v_newjs        ],
                                               annmodel.SomeInteger())

    # handling of the various kinds of calls

    def translate_op_oopspec_call(self, hop):
        # special-cased call, for things like list methods
        from pypy.jit.timeshifter.oop import OopSpecDesc, Index

        c_func = hop.args_v[0]
        fnobj = c_func.value._obj
        oopspecdesc = OopSpecDesc(self, fnobj)
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
        missing_args = ((ll_handler.func_code.co_argcount - 2) -
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
            args_v[0] = hop.llops.genop('cast_pointer', [args_v[0]],
                               resulttype = ts.r_PtrRedBox.lowleveltype)
        RESULT = originalconcretetype(hop.s_result)
        if RESULT is lltype.Void:
            s_result = annmodel.s_None
        else:
            s_result = ts.s_RedBox

        s_oopspecdesc  = ts.s_OopSpecDesc
        ll_oopspecdesc = ts.annhelper.delayedconst(ts.r_OopSpecDesc,
                                                   oopspecdesc)
        c_oopspecdesc  = hop.llops.genconst(ll_oopspecdesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(ll_handler,
                                      [ts.s_JITState, s_oopspecdesc] + args_s,
                                      [v_jitstate,    c_oopspecdesc] + args_v,
                                      s_result)

    def translate_op_green_call(self, hop):
        for r_arg in hop.args_r:
            assert isinstance(r_arg, GreenRepr)
        v = hop.genop('direct_call', hop.args_v, hop.r_result.lowleveltype)
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

    def translate_op_indirect_red_call(self, hop):
        bk = self.annotator.bookkeeper
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

    translate_op_gray_call            = translate_op_red_call
    translate_op_indirect_gray_call   = translate_op_indirect_red_call

    translate_op_yellow_call          = translate_op_red_call
    translate_op_indirect_yellow_call = translate_op_indirect_red_call


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


class RedStructRepr(RedRepr):
    typedesc = None

    def create(self, hop):
        ts = self.hrtyper
        if self.typedesc is None:
            T = self.original_concretetype.TO
            self.typedesc = rcontainer.StructTypeDesc(ts.RGenOp, T)
        return hop.llops.genmixlevelhelpercall(self.typedesc.ll_factory,
            [], [], ts.s_RedBox)


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

# ____________________________________________________________

def opname2vstr(name):
    lls = string_repr.convert_const(name)
    return inputconst(string_repr.lowleveltype, lls)
