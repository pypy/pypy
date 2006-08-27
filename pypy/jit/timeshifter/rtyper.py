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
from pypy.jit.timeshifter import rtimeshift, rvalue, rcontainer

class HintTypeSystem(LowLevelTypeSystem):
    name = "hinttypesystem"

    offers_exceptiondata = False
    
    def perform_normalizations(self, rtyper):
        pass   # for now

HintTypeSystem.instance = HintTypeSystem()

# ___________________________________________________________


def originalconcretetype(hs):
    if isinstance(hs, annmodel.SomeImpossibleValue):
        return lltype.Void
    else:
        return hs.concretetype

class HintRTyper(RPythonTyper):

    def __init__(self, hannotator, timeshifter):
        RPythonTyper.__init__(self, hannotator, 
                              type_system=HintTypeSystem.instance)
        self.green_reprs = PRECOMPUTED_GREEN_REPRS.copy()
        self.red_reprs = {}
        self.timeshifter = timeshifter
        self.RGenOp = timeshifter.RGenOp

    originalconcretetype = staticmethod(originalconcretetype)

    def make_new_lloplist(self, block):
        return HintLowLevelOpList(self.timeshifter, block)

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
            r = redreprcls(lowleveltype, self.timeshifter)
            self.red_reprs[lowleveltype] = r
            return r

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
            ll_generate = rtimeshift.ll_generate_operation1
        elif opdesc.nb_args == 2:
            ll_generate = rtimeshift.ll_generate_operation2
        ts = self.timeshifter
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
        return hop.inputarg(hop.r_result, arg=0)

    def translate_op_keepalive(self,hop):
        pass

    def translate_op_same_as(self, hop):
        [v] = hop.inputargs(hop.r_result)
        return v

    def translate_op_getfield(self, hop):
        if isinstance(hop.args_r[0], BlueRepr):
            return hop.args_r[0].timeshift_getfield(hop)
        # non virtual case        
        PTRTYPE = originalconcretetype(hop.args_s[0])
        if PTRTYPE.TO._hints.get('immutable', False): # foldable if all green
            res = self.generic_translate_operation(hop, force=True)
            if res is not None:
                return res
            
        ts = self.timeshifter
        v_argbox, c_fieldname = hop.inputargs(self.getredrepr(PTRTYPE),
                                              green_void_repr)
        structdesc = rcontainer.StructTypeDesc(self.RGenOp, PTRTYPE.TO)
        fielddesc = structdesc.getfielddesc(c_fieldname.value)
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_generate_getfield,
            [ts.s_JITState, s_fielddesc, ts.s_RedBox],
            [v_jitstate,    c_fielddesc, v_argbox   ],
            ts.s_RedBox)

    def translate_op_getarrayitem(self, hop):
        PTRTYPE = originalconcretetype(hop.args_s[0])
        if PTRTYPE.TO._hints.get('immutable', False): # foldable if all green
            res = self.generic_translate_operation(hop, force=True)
            if res is not None:
                return res

        ts = self.timeshifter
        v_argbox, v_index = hop.inputargs(self.getredrepr(PTRTYPE),
                                          self.getredrepr(lltype.Signed))
        fielddesc = rcontainer.ArrayFieldDesc(self.RGenOp, PTRTYPE)
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_generate_getarrayitem,
            [ts.s_JITState, s_fielddesc, ts.s_RedBox, ts.s_RedBox],
            [v_jitstate,    c_fielddesc, v_argbox,    v_index    ],
            ts.s_RedBox)

    def translate_op_setfield(self, hop):
        if isinstance(hop.args_r[0], BlueRepr):
            return hop.args_r[0].timeshift_setfield(hop)
        # non virtual case ...
        ts = self.timeshifter        
        PTRTYPE = originalconcretetype(hop.args_s[0])
        VALUETYPE = originalconcretetype(hop.args_s[2])
        v_destbox, c_fieldname, v_valuebox = hop.inputargs(self.getredrepr(PTRTYPE),
                                                           green_void_repr,
                                                           self.getredrepr(VALUETYPE)
                                                           )
        structdesc = rcontainer.StructTypeDesc(self.RGenOp, PTRTYPE.TO)
        fielddesc = structdesc.getfielddesc(c_fieldname.value)
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_generate_setfield,
            [ts.s_JITState, s_fielddesc, ts.s_RedBox, ts.s_RedBox],
            [v_jitstate,    c_fielddesc, v_destbox,   v_valuebox],
            annmodel.s_None)

    def translate_op_getsubstruct(self, hop):
        if isinstance(hop.args_r[0], BlueRepr):        
            return hop.args_r[0].timeshift_getsubstruct(hop)
        # non virtual case
        ts = self.timeshifter
        PTRTYPE = originalconcretetype(hop.args_s[0])
        v_argbox, c_fieldname = hop.inputargs(self.getredrepr(PTRTYPE),
                                              green_void_repr)
        fielddesc = rcontainer.NamedFieldDesc(self.RGenOp, PTRTYPE,
                                              c_fieldname.value) # XXX
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        v_jitstate = hop.llops.getjitstate()
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_generate_getsubstruct,
            [ts.s_JITState, s_fielddesc, ts.s_RedBox],
            [v_jitstate,    c_fielddesc, v_argbox   ],
            ts.s_RedBox)
        

    def translate_op_malloc(self, hop):
        r_result = hop.r_result
        return r_result.create(hop)

    def translate_op_direct_call(self, hop):
        c_func = hop.args_v[0]
        assert isinstance(c_func, flowmodel.Constant)
        fnobj = c_func.value._obj
        if hasattr(fnobj._callable, 'oopspec'):
            # special-cased call, for things like list methods
            hop.r_s_popfirstarg()
            return self.handle_highlevel_operation(fnobj, hop)
        elif (originalconcretetype(hop.s_result) is not lltype.Void and
              isinstance(hop.r_result, GreenRepr)):
            # green-returning call, for now (XXX) we assume it's an
            # all-green function that we can just call
            for r_arg in hop.args_r:
                assert isinstance(r_arg, GreenRepr)
            v = hop.genop('direct_call', hop.args_v, hop.r_result.lowleveltype)
            return v
        else:
            bk = self.annotator.bookkeeper
            # first close the current block
            ts = self.timeshifter
            v_jitstate = hop.llops.getjitstate()
            v_builder = hop.llops.genmixlevelhelpercall(rtimeshift.before_call,
                                                        [ts.s_JITState],
                                                        [v_jitstate],
                                                     ts.s_ResidualGraphBuilder)
            hop.r_s_popfirstarg()
            args_hs = hop.args_s[:]
            # fixed is always false here
            graph = bk.get_graph_for_call(fnobj.graph, False, args_hs)
            args_r = [self.getrepr(hs) for hs in args_hs]
            args_v = hop.inputargs(*args_r)
            ARGS = [ts.r_ResidualGraphBuilder.lowleveltype,
                    ts.r_JITState.lowleveltype]
            ARGS += [r.lowleveltype for r in args_r]
            RESULT = ts.r_ResidualGraphBuilder.lowleveltype
            fnptr = lltype.functionptr(lltype.FuncType(ARGS, RESULT),
                                       graph.name,
                                       graph=graph,
                                       _callable = graph.func)
            self.timeshifter.schedule_graph(graph)
            args_v[:0] = [hop.llops.genconst(fnptr), v_builder, v_jitstate]
            v_newbuilder = hop.genop('direct_call', args_v, RESULT)
            return hop.llops.genmixlevelhelpercall(rtimeshift.after_call,
                                   [ts.s_JITState, ts.s_ResidualGraphBuilder],
                                   [v_jitstate,    v_newbuilder],
                                   ts.s_RedBox)

    def translate_op_save_locals(self, hop):
        ts = self.timeshifter
        v_jitstate = hop.llops.getjitstate()
        boxes_v = []
        for r, v in zip(hop.args_r, hop.args_v):
            if isinstance(r, RedRepr):
                boxes_v.append(v)
        v_boxes = ts.build_box_list(hop.llops, boxes_v)
        hop.llops.genmixlevelhelpercall(rtimeshift.save_locals,
                                        [ts.s_JITState, ts.s_box_list],
                                        [v_jitstate,    v_boxes],
                                        annmodel.s_None)

    def handle_highlevel_operation(self, fnobj, hop):
        from pypy.jit.timeshifter.oop import OopSpecDesc, Index
        oopspecdesc = OopSpecDesc(self.RGenOp, fnobj)

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
        ts = self.timeshifter
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


class HintLowLevelOpList(LowLevelOpList):
    """Warning: the HintLowLevelOpList's rtyper is the *original*
    rtyper, while the HighLevelOp's rtyper is actually our HintRTyper...
    """
    def __init__(self, timeshifter, originalblock):
        LowLevelOpList.__init__(self, timeshifter.rtyper, originalblock)
        self.timeshifter = timeshifter

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

        graph = self.timeshifter.annhelper.getgraph(function, args_s, s_result)
        self.record_extra_call(graph) # xxx

        c = self.timeshifter.annhelper.graph2const(graph)

        # build the 'direct_call' operation
        rtyper = self.timeshifter.rtyper
        RESULT = rtyper.getrepr(s_result).lowleveltype
        return self.genop('direct_call', [c]+args_v,
                          resulttype = RESULT)

    def getjitstate(self):
        assert self.originalblock is not None
        return self.timeshifter.block2jitstate[self.originalblock]

# ____________________________________________________________

class __extend__(pairtype(HintTypeSystem, hintmodel.SomeLLAbstractConstant)):

    def rtyper_makerepr((ts, hs_c), hrtyper):
        if (hs_c.is_fixed() or hs_c.eager_concrete or
            hs_c.concretetype is lltype.Void):
            return hrtyper.getgreenrepr(hs_c.concretetype)
        else:
            return hrtyper.getredrepr(hs_c.concretetype)

    def rtyper_makekey((ts, hs_c), hrtyper):
        if hs_c.is_fixed() or hs_c.eager_concrete:
            return hs_c.__class__, "green", hs_c.concretetype
        else:
            return hs_c.__class__, "red", hs_c.concretetype

class __extend__(pairtype(HintTypeSystem, hintmodel.SomeLLAbstractVariable)):

    def rtyper_makerepr((ts, hs_v), hrtyper):
        return hrtyper.getredrepr(hs_v.concretetype)

    def rtyper_makekey((ts, hs_v), hrtyper):
        return hs_v.__class__, "red", hs_v.concretetype

class __extend__(pairtype(HintTypeSystem, hintmodel.SomeLLAbstractContainer)):

    def rtyper_makerepr((ts, hs_container), hrtyper):
        vstructdef = hs_container.contentdef
        assert isinstance(vstructdef, hintcontainer.VirtualStructDef)
        if vstructdef.degenerated:
            # fall back to a red repr
            return hrtyper.getredrepr(hs_container.concretetype)
        return BlueStructRepr(hs_container.concretetype, vstructdef,
                              hrtyper.timeshifter)

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
    def __init__(self, original_concretetype, timeshifter):
        assert original_concretetype is not lltype.Void, (
            "cannot make red boxes for the lltype Void")
        self.original_concretetype = original_concretetype
        self.lowleveltype = timeshifter.r_RedBox.lowleveltype
        self.timeshifter = timeshifter

    def get_genop_var(self, v, llops):
        ts = self.timeshifter
        v_jitstate = hop.llops.getjitstate()
        return llops.genmixlevelhelpercall(rtimeshift.ll_gvar_from_redbox,
                       [ts.s_JITState, llops.timeshifter.s_RedBox],
                       [v_jitstate,    v],
                       ts.s_ConstOrVar)

    def convert_const(self, ll_value):
        RGenOp = self.timeshifter.RGenOp
        redbox = rvalue.redbox_from_prebuilt_value(RGenOp, ll_value)
        timeshifter = self.timeshifter
        return timeshifter.annhelper.delayedconst(timeshifter.r_RedBox, redbox)

    def residual_values(self, ll_value):
        return [ll_value]


class RedStructRepr(RedRepr):
    typedesc = None

    def create(self, hop):
        ts = self.timeshifter
        if self.typedesc is None:
            T = self.original_concretetype.TO
            self.typedesc = rcontainer.StructTypeDesc(ts.RGenOp, T)
        return hop.llops.genmixlevelhelpercall(self.typedesc.ll_factory,
            [], [], ts.s_RedBox)


class BlueRepr(Repr):
    pass


# merging can probably be implemented as: flatten incoming state as list of redboxes -> merge -> reconstruct
# this can reuse the current merge logic and the flattening/reconstructing can be done externally driven
# by the known types and annotations

## class BlueStructRepr(BlueRepr):
##     def __init__(self, original_concretetype, virtualstructdef, timeshifter):
##         self.original_concretetype = original_concretetype
##         self.timeshifter = timeshifter
##         # xxx
##         # this could avoid using a wrapper box completely
##         # which means that if the fields are all green we could get back the original situation
##         # but is unclear whether there are issues with gc tracking for non-gc struct pointers,
##         # likely things are preserved but the timeshifted graph may introduce sufficient
##         # differences to make that a problem
##         self.lowleveltype = timeshifter.r_RedBox.lowleveltype 
##         if virtualstructdef.vparent is None:
##             self.ENVELOPE = lltype.GcForwardReference()                                 
##         self.vstructdef = virtualstructdef        

##     def fldname(self, name):
##         return name

##     def _setup_repr(self):
##         field_reprs = {}
##         fields = []
##         vstructdef = self.vstructdef
##         hrtyper = self.timeshifter.hrtyper
##         T = self.original_concretetype.TO
##         for name in vstructdef.names:
##             fieldvalue = vstructdef.fields[name]
##             field_repr = hrtyper.getrepr(fieldvalue.s_value)
##             field_reprs[name] = field_repr
##             SUBFIELD = getattr(T, name)
##             if isinstance(SUBFIELD, lltype.Struct):
##                 # virtual substructure case
##                 field_lltype = field_repr.DATA
##             else:
##                 field_lltype = field_repr.lowleveltype
##             fields.append((self.fldname(name), field_lltype))
##         self.field_reprs = field_reprs
##         self.DATA = lltype.Struct('vstruct', *fields)
##         if vstructdef.vparent is None:
##             self.ENVELOPE.become(lltype.GcStruct('vstruct_envelope', ('tag', rtimeshift.VCONTAINER),
##                                                                      ('data', self.DATA)))
            
##     # helpers

##     def create(self, hop):
##         llops = hop.llops
##         c_ENVELOPE = inputconst(lltype.Void, self.ENVELOPE)
##         v_envelope = hop.genop('malloc', [c_ENVELOPE], resulttype=lltype.Ptr(self.ENVELOPE))
##         c_data = inputconst(lltype.Void, 'data')
##         v_data = hop.genop('getsubstruct', [v_envelope, c_data], lltype.Ptr(self.DATA))
##         for name, field_repr in self.field_reprs.iteritems():
##             if isinstance(field_repr, RedRepr):
##                 T = field_repr.original_concretetype
##                 c_defl = inputconst(T, T._defl())
##                 s_defl = annmodel.lltype_to_annotation(T)
##                 v_field = llops.genmixlevelhelpercall(rtimeshift.ConstRedBox.ll_fromvalue,
##                                                       [s_defl], [c_defl],
##                                                       self.timeshifter.s_RedBox)
##                 c_name = inputconst(lltype.Void, self.fldname(name))
##                 hop.genop('setfield', [v_data, c_name, v_field])            
##         VCONTPTR = lltype.Ptr(rtimeshift.VCONTAINER)
##         v_envelope = hop.genop('cast_pointer', [v_envelope],
##                                resulttype=VCONTPTR)
##         v_content = hop.genop('cast_ptr_to_adr', [v_data], resulttype=llmemory.Address)
##         return llops.genmixlevelhelpercall(rtimeshift.ContainerRedBox.ll_make_container_box,
##                                            [annmodel.SomePtr(VCONTPTR), annmodel.SomeAddress()],
##                                            [v_envelope,                 v_content],
##                                            self.timeshifter.s_RedBox)

##     def getdata(self, hop, v_box):
##         llops = hop.llops
##         rtyper = self.timeshifter.rtyper
##         DATAPTR = lltype.Ptr(self.DATA)
##         v_data_addr = llops.genmixlevelhelpercall(rtimeshift.ll_getcontent,
##                                                   [self.timeshifter.s_RedBox],
##                                                   [v_box],
##                                                   annmodel.SomeAddress())
##         # cannot do this inside ll_getcontent because DATAPTR parts can be setup only later :(
##         v_data = hop.genop('cast_adr_to_ptr', [v_data_addr], resulttype=DATAPTR)
##         return v_data

        
##     def timeshift_setfield(self, hop):
##         llops = hop.llops        
##         assert hop.args_s[1].is_constant()
##         name = hop.args_s[1].const
##         field_repr = self.field_reprs[name]
##         v_box = hop.inputarg(self, arg=0)
##         v_value = hop.inputarg(field_repr, arg=2)
##         v_data = self.getdata(hop, v_box)
##         c_name = inputconst(lltype.Void, self.fldname(name))
##         hop.genop('setfield', [v_data, c_name, v_value])

##     def timeshift_getfield(self, hop):
##         llops = hop.llops        
##         assert hop.args_s[1].is_constant()
##         name = hop.args_s[1].const
##         field_repr = self.field_reprs[name]
##         v_box = hop.inputarg(self, arg=0)
##         v_data = self.getdata(hop, v_box)
##         c_name = inputconst(lltype.Void, self.fldname(name))
##         return hop.genop('getfield', [v_data, c_name],
##                          resulttype=field_repr.lowleveltype)

##     def timeshift_getsubstruct(self, hop):
##         llops = hop.llops        
##         assert hop.args_s[1].is_constant()
##         name = hop.args_s[1].const
##         field_repr = self.field_reprs[name]
##         v_box = hop.inputarg(self, arg=0)
##         v_data = self.getdata(hop, v_box)
##         c_name = inputconst(lltype.Void, self.fldname(name))
##         NEWDATAPTR = lltype.Ptr(field_repr.DATA)
##         v_newdata = hop.genop('getsubstruct', [v_data, c_name],
##                               resulttype=NEWDATAPTR)
##         v_content = hop.genop('cast_ptr_to_adr', [v_newdata], resulttype=llmemory.Address)
##         return llops.genmixlevelhelpercall(rtimeshift.ContainerRedBox.ll_make_subcontainer_box,
##                                            [self.timeshifter.s_RedBox, annmodel.SomeAddress()],
##                                            [v_box,                     v_content],
##                                            self.timeshifter.s_RedBox)
        


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

    def get_genop_var(self, v, llops):
        ts = self.timeshifter
        v_jitstate = hop.llops.getjitstate()
        return llops.genmixlevelhelpercall(rtimeshift.ll_gvar_from_constant,
                                           [ts.s_JITState, self.annotation()],
                                           [v_jitstate,    v],
                                           ts.s_ConstOrVar)

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
        ts = llops.timeshifter
        v_jitstate = llops.getjitstate()
        return llops.genmixlevelhelpercall(rvalue.ll_fromvalue,
                        [ts.s_JITState, r_from.annotation()],
                        [v_jitstate,    v],
                        llops.timeshifter.s_RedBox)

# ____________________________________________________________

def opname2vstr(name):
    lls = string_repr.convert_const(name)
    return inputconst(string_repr.lowleveltype, lls)
