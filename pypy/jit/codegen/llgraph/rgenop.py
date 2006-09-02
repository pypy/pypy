from pypy.rpython.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.model import AbstractRGenOp, CodeGenBlock, CodeGenLink
from pypy.jit.codegen.model import GenVar, GenConst
from pypy.jit.codegen.llgraph import llimpl
from pypy.rpython.lltypesystem.rclass import fishllattr


class LLVar(GenVar):
    def __init__(self, v):
        self.v = v

    def __repr__(self):
        return repr(RGenOp.reveal(self))


class LLConst(GenConst):
    def __init__(self, v):
        self.v = v

    @specialize.arg(1)
    def revealconst(self, T):
        return llimpl.revealconst(T, self.v)

    def __repr__(self):
        return repr(RGenOp.reveal(self))

gv_Void = LLConst(llimpl.constTYPE(lltype.Void))


class LLBlock(CodeGenBlock):
    def __init__(self, b):
        self.b = b

    def geninputarg(self, gv_TYPE):
        return LLVar(llimpl.geninputarg(self.b, gv_TYPE.v))

    @specialize.arg(1)
    def genop(self, opname, vars_gv, gv_RESULT_TYPE=None):
        return LLVar(llimpl.genop(self.b, opname, vars_gv,
                                  (gv_RESULT_TYPE or gv_Void).v))

    def genop_getfield(self, (gv_name, gv_PTRTYPE, gv_FIELDTYPE), gv_ptr):
        vars_gv = [llimpl.cast(self.b, gv_PTRTYPE.v, gv_ptr.v), gv_name.v]
        return LLVar(llimpl.genop(self.b, 'getfield', vars_gv,
                                  gv_FIELDTYPE.v))        
    
    def genop_setfield(self, (gv_name, gv_PTRTYPE, gv_FIELDTYPE), gv_ptr,
                                                                  gv_value):
        vars_gv = [llimpl.cast(self.b, gv_PTRTYPE.v, gv_ptr.v),
                   gv_name.v,
                   llimpl.cast(self.b, gv_FIELDTYPE.v, gv_value.v)]
        return LLVar(llimpl.genop(self.b, 'setfield', vars_gv,
                                  gv_Void.v))        
    
    def genop_getsubstruct(self, (gv_name, gv_PTRTYPE, gv_FIELDTYPE), gv_ptr):
        vars_gv = [llimpl.cast(self.b, gv_PTRTYPE.v, gv_ptr.v), gv_name.v]
        return LLVar(llimpl.genop(self.b, 'getsubstruct', vars_gv,
                                  gv_FIELDTYPE.v))        

    def genop_getarrayitem(self, gv_ITEMTYPE, gv_ptr, gv_index):
        vars_gv = [gv_ptr.v, gv_index.v]
        return LLVar(llimpl.genop(self.b, 'getarrayitem', vars_gv,
                                  gv_ITEMTYPE.v))

    def genop_malloc_fixedsize(self, (gv_TYPE, gv_PTRTYPE)):
        vars_gv = [gv_TYPE.v]
        return LLVar(llimpl.genop(self.b, 'malloc', vars_gv,
                                  gv_PTRTYPE.v))
                                  
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

    # XXX what kind of type/kind information does this need?
    def gencallableconst(self, name, targetblock, gv_FUNCTYPE):
        return LLConst(llimpl.gencallableconst(name, targetblock.b,
                                               gv_FUNCTYPE.v))

    @staticmethod
    @specialize.genconst(0)
    def genconst(llvalue):
        return LLConst(llimpl.genconst(llvalue))

    @staticmethod
    @specialize.memo()
    def kindToken(T):
        return LLConst(llimpl.constTYPE(T))        

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        assert name in T._flds
        FIELDTYPE = getattr(T, name)
        if isinstance(FIELDTYPE, lltype.ContainerType):
            FIELDTYPE = lltype.Ptr(FIELDTYPE)
        return (LLConst(llimpl.constFieldName(name)),
                LLConst(llimpl.constTYPE(lltype.Ptr(T))),
                LLConst(llimpl.constTYPE(FIELDTYPE)))

    @staticmethod
    @specialize.memo()
    def allocToken(TYPE):
        return (LLConst(llimpl.constTYPE(TYPE)),
                LLConst(llimpl.constTYPE(lltype.Ptr(TYPE))))

    @staticmethod
    @specialize.memo()
    def arrayToken(A):
        return LLConst(llimpl.constTYPE(A.OF))


    @staticmethod
    @specialize.memo()
    def constTYPE(T):
        return LLConst(llimpl.constTYPE(T))

    @staticmethod
    @specialize.arg(0)
    def placeholder(dummy):
        return LLConst(llimpl.placeholder(dummy))

    @staticmethod
    @specialize.memo()
    def constFieldName(T, name):
        assert name in T._flds
        return LLConst(llimpl.constFieldName(name))

    constPrebuiltGlobal = genconst

    # not RPython, just for debugging.  Specific to llgraph.
    @staticmethod
    def reveal(gv):
        if hasattr(gv, 'v'):
            v = gv.v
        else:
            v = fishllattr(gv, 'v')
        return llimpl.reveal(v)

    # Builds a real flow.model.FunctionGraph. Specific to llgraph.
    @staticmethod
    def buildgraph(block, FUNCTYPE):
        if hasattr(block, 'b'):
            b = block.b
        else:
            b = fishllattr(block, 'b')
        return llimpl.buildgraph(b, FUNCTYPE)

    def _freeze_(self):
        return True    # no real point in using a full class in llgraph


rgenop = RGenOp()      # no real point in using a full class in llgraph
