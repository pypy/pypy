from pypy.annotation import model as annmodel
from pypy.annotation.pairtype import pair, pairtype
from pypy.rpython import annlowlevel
from pypy.rpython.rtyper import RPythonTyper, LowLevelOpList, TyperError
from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.rstr import string_repr
from pypy.rpython.typesystem import TypeSystem
from pypy.rpython.lltypesystem import lltype
from pypy.rpython import rgenop
from pypy.jit import hintmodel, rtimeshift

class HintTypeSystem(TypeSystem):
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
            r = RedRepr(lowleveltype, self.timeshifter)
            self.red_reprs[lowleveltype] = r
            return r

    def generic_translate_operation(self, hop):
        # detect constant-foldable all-green operations
        if hop.spaceop.opname not in rtimeshift.FOLDABLE_OPS:
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

    def translate_op_getfield(self, hop):
        ts = self.timeshifter
        PTRTYPE = originalconcretetype(hop.args_s[0])
        RESTYPE = originalconcretetype(hop.s_result)
        v_argbox, c_fieldname = hop.inputargs(self.getredrepr(PTRTYPE),
                                              green_void_repr)
        fielddesc = rtimeshift.make_fielddesc(PTRTYPE, c_fieldname.value)
        c_fielddesc = inputconst(lltype.Void, fielddesc)
        s_fielddesc = ts.rtyper.annotator.bookkeeper.immutablevalue(fielddesc)
        gv_fieldname  = rgenop.constFieldName(c_fieldname.value)
        gv_resulttype = rgenop.constTYPE(RESTYPE)
        c_fieldname  = hop.inputconst(rgenop.CONSTORVAR, gv_fieldname)
        c_resulttype = hop.inputconst(rgenop.CONSTORVAR, gv_resulttype)
        v_jitstate = hop.llops.getjitstate()
        s_CONSTORVAR = annmodel.SomePtr(rgenop.CONSTORVAR)
        return hop.llops.genmixlevelhelpercall(rtimeshift.ll_generate_getfield,
            [ts.s_JITState, s_fielddesc, ts.s_RedBox, s_CONSTORVAR, s_CONSTORVAR],
            [v_jitstate,    c_fielddesc, v_argbox,    c_fieldname,  c_resulttype],
            ts.s_RedBox)


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
        rtyper = self.timeshifter.rtyper

        graph = self.timeshifter.annhelper.getgraph(function, args_s, s_result)
        self.record_extra_call(graph) # xxx

        ARGS = [rtyper.getrepr(s_arg).lowleveltype for s_arg in args_s]
        RESULT = rtyper.getrepr(s_result).lowleveltype

        F = lltype.FuncType(ARGS, RESULT)

        fptr = lltype.functionptr(F, graph.name, graph=graph)

        # build the 'direct_call' operation
        c = inputconst(lltype.Ptr(F), fptr)
        return self.genop('direct_call', [c]+args_v,
                          resulttype = RESULT)

    def getjitstate(self):
        assert self.originalblock is not None
        return self.timeshifter.block2jitstate[self.originalblock]

# ____________________________________________________________

class __extend__(pairtype(HintTypeSystem, hintmodel.SomeLLAbstractConstant)):

    def rtyper_makerepr((ts, hs_c), hrtyper):
        if hs_c.is_fixed() or hs_c.eager_concrete:
            return hrtyper.getgreenrepr(hs_c.concretetype)
        else:
            return hrtyper.getredrepr(hs_c.concretetype)

    def rtyper_makekey((ts, hs_c), hrtyper):
        if hs_c.is_fixed() or hs_c.eager_concrete:
            return hs_c.__class__, "green", hs_c.concretetype
        else:
            return hs_c.__class__, "red", hs_c.concretetype

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
        return llops.genmixlevelhelpercall(rtimeshift.ll_gvar_from_redbox,
                                           [llops.timeshifter.s_RedBox],
                                           [v],
                                           annmodel.SomePtr(rgenop.CONSTORVAR))

    def convert_const(self, ll_value):
        redbox = rtimeshift.ConstRedBox.ll_fromvalue(ll_value)
        timeshifter = self.timeshifter
        return timeshifter.annhelper.delayedconst(timeshifter.r_RedBox, redbox)

    def residual_values(self, ll_value):
        return [ll_value]

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
        return llops.genmixlevelhelpercall(rtimeshift.ll_gvar_from_constant,
                                           [self.annotation()], [v],
                                           annmodel.SomePtr(rgenop.CONSTORVAR))

    def convert_const(self, ll_value):
        return ll_value

    def residual_values(self, ll_value):
        return []

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
        return llops.genmixlevelhelpercall(rtimeshift.ConstRedBox.ll_fromvalue,
                                           [r_from.annotation()], [v],
                                           llops.timeshifter.s_RedBox)

# ____________________________________________________________

def opname2vstr(name):
    lls = string_repr.convert_const(name)
    return inputconst(string_repr.lowleveltype, lls)
