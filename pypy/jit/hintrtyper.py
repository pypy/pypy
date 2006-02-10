from pypy.annotation import model as annmodel
from pypy.annotation.pairtype import pair, pairtype
from pypy.rpython.rtyper import RPythonTyper, LowLevelOpList
from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.rstr import string_repr
from pypy.rpython.typesystem import TypeSystem
from pypy.rpython.lltypesystem import lltype
from pypy.rpython import rgenop
from pypy.jit import hintmodel, rtimeshift

class HintTypeSystem(TypeSystem):
    name = "hinttypesystem"

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
            r = RedRepr(lowleveltype)
            self.red_reprs[lowleveltype] = r
            return r

    def generic_translate_operation(self, hop):
        # detect all-green operations
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
        # XXX constant propagate if possible
        opdesc = rtimeshift.make_opdesc(hop)
        if opdesc.nb_args == 1:
            ll_generate = rtimeshift.ll_generate_operation1
        elif opdesc.nb_args == 2:
            ll_generate = rtimeshift.ll_generate_operation2
        c_opdesc = inputconst(lltype.Void, opdesc)
        return hop.gendirectcall(ll_generate,
                                 c_opdesc,
                                 hop.llops.getjitstate(),
                                 *hop.args_v)
        #v_args = hop.genop('malloc_varsize',
        #                   [hop.inputconst(lltype.Void, VARLIST.TO),
        #                    hop.inputconst(lltype.Signed, len(hop.args_v))],
        #                   resulttype = VARLIST)
        #for i in range(len(hop.args_v)):
        #    v_gvar = hop.args_r[i].get_genop_var(hop.args_v[i], hop.llops)
        #    hop.genop('setarrayitem', [v_args,
        #                               hop.inputconst(lltype.Signed, i),
        #                               v_gvar])
        #RESTYPE = originalconcretetype(hop.s_result)
        #c_restype = hop.inputconst(lltype.Void, RESTYPE)
        #return hop.gendirectcall(rtimeshift.ll_generate_operation,
        #                         hop.llops.getjitstate(),
        #                         opname2vstr(hop.spaceop.opname),
        #                         v_args, c_restype)

class HintLowLevelOpList(LowLevelOpList):
    """Warning: the HintLowLevelOpList's rtyper is the *original*
    rtyper, while the HighLevelOp's rtyper is actually our HintRTyper...
    """
    def __init__(self, timeshifter, originalblock):
        LowLevelOpList.__init__(self, timeshifter.rtyper, originalblock)
        self.timeshifter = timeshifter

    def hasparentgraph(self):
        return False   # for now

    def getjitstate(self):
        v_jitstate = self.originalblock.inputargs[0]
        assert v_jitstate.concretetype == rtimeshift.STATE_PTR
        return v_jitstate

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
    lowleveltype = rtimeshift.REDBOX_PTR

    def __init__(self, original_concretetype):
        self.original_concretetype = original_concretetype

    def get_genop_var(self, v, llops):
        c_TYPE = inputconst(lltype.Void, self.original_concretetype)
        return llops.gendirectcall(rtimeshift.ll_gvar_from_redbox,
                                   llops.getjitstate(), v, c_TYPE)

    def convert_const(self, ll_value):
        return rtimeshift.REDBOX.make_from_const(ll_value)

    def residual_values(self, ll_value):
        return [ll_value]

class GreenRepr(Repr):
    def __init__(self, lowleveltype):
        self.lowleveltype = lowleveltype

    def get_genop_var(self, v, llops):
        return llops.gendirectcall(rtimeshift.ll_gvar_from_constant,
                                   llops.getjitstate(), v)

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

# ____________________________________________________________

class SomeJITState(annmodel.SomeObject):
    pass

s_JITState = SomeJITState()

class __extend__(pairtype(HintTypeSystem, SomeJITState)):

    def rtyper_makerepr((ts, hs_j), hrtyper):
        return jitstate_repr

    def rtyper_makekey((ts, hs_j), hrtyper):
        return hs_j.__class__,

class JITStateRepr(Repr):
    lowleveltype = rtimeshift.STATE_PTR

jitstate_repr = JITStateRepr()

# ____________________________________________________________

def opname2vstr(name):
    lls = string_repr.convert_const(name)
    return inputconst(string_repr.lowleveltype, lls)
