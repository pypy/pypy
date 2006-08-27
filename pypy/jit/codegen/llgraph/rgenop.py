from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.model import AbstractRGenOp, CodeGenBlock, CodeGenLink
from pypy.jit.codegen.model import GenVar, GenConst
from pypy.jit.codegen.llgraph import llimpl
from pypy.rpython.lltypesystem.rclass import fishllattr


class LLVar(GenVar):
    def __init__(self, v):
        self.v = v


class LLConst(GenConst):
    def __init__(self, v):
        self.v = v

    def revealconst(self, T):
        return llimpl.revealconst(T, self.v)
    revealconst._annspecialcase_ = 'specialize:arg(1)'


gv_Void = LLConst(llimpl.constTYPE(lltype.Void))


class LLBlock(CodeGenBlock):
    def __init__(self, b):
        self.b = b

    def geninputarg(self, gv_TYPE):
        return LLVar(llimpl.geninputarg(self.b, gv_TYPE.v))

    def genop(self, opname, vars_gv, gv_RESULT_TYPE=None):
        return LLVar(llimpl.genop(self.b, opname, vars_gv,
                                  (gv_RESULT_TYPE or gv_Void).v))
    genop._annspecialcase_ = 'specialize:arg(1)'

    def close1(self):
        return LLLink(llimpl.closeblock1(self.b))

    def close2(self, gv_exitswitch):
        l1, l2 = llimpl.closeblock2(self.b, gv_exitswitch.v)
        return LLLink(l1), LLLink(l2)


class LLLink(CodeGenLink):
    def __init__(self, l):
        self.l = l

    def close(self, vars_gv, targetblock):
        llimpl.closelink(self.l, vars_gv, targetblock.b)

    def closereturn(self, gv_returnvar):
        llimpl.closereturnlink(self.l, gv_returnvar.v)


class RGenOp(AbstractRGenOp):
    gv_Void = gv_Void

    def newblock(self):
        return LLBlock(llimpl.newblock())

    def gencallableconst(self, name, targetblock, gv_FUNCTYPE):
        return LLConst(llimpl.gencallableconst(name, targetblock.b,
                                               gv_FUNCTYPE.v))

    def genconst(llvalue):
        return LLConst(llimpl.genconst(llvalue))
    genconst._annspecialcase_ = 'specialize:genconst(0)'
    genconst = staticmethod(genconst)

    def constTYPE(T):
        return LLConst(llimpl.constTYPE(T))
    constTYPE._annspecialcase_ = 'specialize:memo'
    constTYPE = staticmethod(constTYPE)

    def placeholder(dummy):
        return LLConst(llimpl.placeholder(dummy))
    placeholder._annspecialcase_ = 'specialize:arg(0)'
    placeholder = staticmethod(placeholder)

    def constFieldName(T, name):
        assert name in T._flds
        return LLConst(llimpl.constFieldName(name))
    constFieldName._annspecialcase_ = 'specialize:memo'
    constFieldName = staticmethod(constFieldName)

    constPrebuiltGlobal = genconst

    # not RPython, just for debugging.  Specific to llgraph.
    def reveal(gv):
        if hasattr(gv, 'v'):
            v = gv.v
        else:
            v = fishllattr(gv, 'v')
        return llimpl.reveal(v)
    reveal = staticmethod(reveal)

    # Builds a real flow.model.FunctionGraph. Specific to llgraph.
    def buildgraph(block):
        if hasattr(block, 'b'):
            b = block.b
        else:
            b = fishllattr(block, 'b')
        return llimpl.buildgraph(b)
    buildgraph = staticmethod(buildgraph)

    def _freeze_(self):
        return True    # no real point in using a full class in llgraph


rgenop = RGenOp()      # no real point in using a full class in llgraph
