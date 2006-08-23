from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.model import AbstractRGenOp, CodeGenBlock
from pypy.jit.codegen.model import GenVar, GenConst
from pypy.jit.codegen.llgraph import llimpl


class LLVar(GenVar):
    def __init__(self, v):
        self.v = v


class LLConst(GenConst):
    def __init__(self, v):
        self.v = v

    def revealconst(self, T):
        return llimpl.revealconst(T, self.v)
    revealconst._annspecialcase_ = 'specialize:arg(1)'


class LLBlock(CodeGenBlock):
    def __init__(self, b):
        self.b = b

    def geninputarg(self, gv_TYPE):
        return LLVar(llimpl.geninputarg(self.b, gv_TYPE.v))

    def genop(self, opname, vars_gv, gv_RESULT_TYPE):
        return LLVar(llimpl.genop(self.b, opname, vars_gv, gv_RESULT_TYPE.v))
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

    def newblock(self):
        return LLBlock(llimpl.newblock())

    def gencallableconst(self, name, targetblock, gv_FUNCTYPE):
        return LLConst(llimpl.gencallableconst(name, targetblock.b,
                                               gv_FUNCTYPE.v))

    def genconst(llvalue):
        return LLConst(llimpl.genconst(llvalue))
    genconst._annspecialcase_ = 'specialize:ll'
    genconst = staticmethod(genconst)

    def constTYPE(T):
        return LLConst(llimpl.constTYPE(T))
    constTYPE._annspecialcase_ = 'specialize:memo'
    constTYPE = staticmethod(constTYPE)

    def placeholder(dummy):
        return LLConst(llimpl.placerholder(dummy))
    placeholder._annspecialcase_ = 'specialize:arg(0)'
    placeholder = staticmethod(placeholder)

    def constFieldName(T, name):
        return LLConst(llimpl.constFieldName(name))
    constFieldName._annspecialcase_ = 'specialize:memo'
    constFieldName = staticmethod(constFieldName)
