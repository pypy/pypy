from pypy.rpython.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.model import AbstractRGenOp, CodeGenBlock, CodeGenerator
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
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
gv_dummy_placeholder = LLConst(llimpl.dummy_placeholder)


class LLBlock(CodeGenBlock):
    def __init__(self, b, g):
        self.b = b
        self.g = g

class LLFlexSwitch(CodeGenSwitch):
    
    def __init__(self, b, g):
        self.b = b
        self.g = g

    def add_case(self, gv_case):
        l_case = llimpl.add_case(self.b, gv_case.v)
        builder = LLBuilder(self.g)
        builder.lnk = l_case
        return builder


class LLBuilder(CodeGenerator):
    lnk = llimpl.nulllink

    def __init__(self, g):
        self.rgenop = rgenop
        self.g = g

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        return LLVar(llimpl.genop(self.b, opname, [gv_arg], llimpl.guess))

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        return LLVar(llimpl.genop(self.b, opname, [gv_arg1, gv_arg2],
                                  llimpl.guess))

    def genop_call(self, (ARGS_gv, gv_RESULT, _), gv_callable, args_gv):
        vars_gv = [gv_callable]
        for i in range(len(ARGS_gv)):
            gv_arg = args_gv[i]
            if gv_arg is not None:
                gv_arg = LLVar(llimpl.cast(self.b, ARGS_gv[i].v, gv_arg.v))
            vars_gv.append(gv_arg)
        if gv_callable.is_const:
            v = llimpl.genop(self.b, 'direct_call', vars_gv, gv_RESULT.v)
        else:
            vars_gv.append(gv_dummy_placeholder)
            v = llimpl.genop(self.b, 'indirect_call', vars_gv, gv_RESULT.v)
        return LLVar(v)

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

    def genop_setarrayitem(self, gv_ITEMTYPE, gv_ptr, gv_index, gv_value):
        vars_gv = [gv_ptr.v, gv_index.v, gv_value.v]
        return LLVar(llimpl.genop(self.b, 'setarrayitem', vars_gv,
                                  gv_Void.v))

    def genop_getarraysize(self, gv_ITEMTYPE, gv_ptr):
        return LLVar(llimpl.genop(self.b, 'getarraysize', [gv_ptr.v],
                                  llimpl.constTYPE(lltype.Signed)))

    def genop_malloc_fixedsize(self, (gv_TYPE, gv_PTRTYPE)):
        vars_gv = [gv_TYPE.v]
        return LLVar(llimpl.genop(self.b, 'malloc', vars_gv,
                                  gv_PTRTYPE.v))

    def genop_malloc_varsize(self, (gv_TYPE, gv_PTRTYPE), gv_length):
        vars_gv = [gv_TYPE.v, gv_length.v]
        return LLVar(llimpl.genop(self.b, 'malloc_varsize', vars_gv,
                                  gv_PTRTYPE.v))

    def genop_same_as(self, gv_TYPE, gv_value):
        return LLVar(gv_value.v)

    def _newblock(self, kinds):
        self.b = newb = llimpl.newblock()
        return [LLVar(llimpl.geninputarg(newb, kind.v)) for kind in kinds]

    def enter_next_block(self, kinds, args_gv):
        lnk = self.lnk or llimpl.closeblock1(self.b)
        self.lnk = llimpl.nulllink
        newb_args_gv = self._newblock(kinds) 
        llimpl.closelink(lnk, args_gv, self.b)
        for i in range(len(args_gv)):
            args_gv[i] = newb_args_gv[i]
        return LLBlock(self.b, self.g)

    def finish_and_goto(self, args_gv, targetblock):
        lnk = self.lnk or llimpl.closeblock1(self.b)
        self.lnk = llimpl.nulllink
        llimpl.closelink(lnk, args_gv, targetblock.b)

    def finish_and_return(self, sigtoken, gv_returnvar):
        gv_returnvar = gv_returnvar or gv_dummy_placeholder
        lnk = self.lnk or llimpl.closeblock1(self.b)
        self.lnk = llimpl.nulllink
        llimpl.closereturnlink(lnk, gv_returnvar.v, self.g)

    def jump_if_true(self, gv_cond):
        l_false, l_true = llimpl.closeblock2(self.b, gv_cond.v)
        self.b = llimpl.nullblock
        later_builder = LLBuilder(self.g)
        later_builder.lnk = l_true
        self.lnk = l_false
        return later_builder

    def jump_if_false(self, gv_cond):
        l_false, l_true = llimpl.closeblock2(self.b, gv_cond.v)
        self.b = llimpl.nullblock
        later_builder = LLBuilder(self.g)
        later_builder.lnk = l_false
        self.lnk = l_true
        return later_builder

    def flexswitch(self, gv_switchvar):
        l_default = llimpl.closeblockswitch(self.b, gv_switchvar.v)
        flexswitch = LLFlexSwitch(self.b, self.g)
        self.b = llimpl.nullblock
        self.lnk = l_default
        return flexswitch

    def show_incremental_progress(self):
        llimpl.show_incremental_progress(self.g)


class RGenOp(AbstractRGenOp):
    gv_Void = gv_Void


    def newgraph(self, (ARGS_gv, gv_RESULT, gv_FUNCTYPE)):
        graph = llimpl.newgraph(gv_FUNCTYPE.v)
        builder = LLBuilder(graph)
        builder.b = llimpl.getstartblock(graph)
        inputargs_gv = [LLVar(llimpl.getinputarg(builder.b, i))
                        for i in range(len(ARGS_gv))]
        return builder, graph, inputargs_gv

    def gencallableconst(self, (ARGS_gv, gv_RESULT, gv_FUNCTYPE), name, graph):
        return LLConst(llimpl.gencallableconst(name, graph,
                                               gv_FUNCTYPE.v))

    @staticmethod
    @specialize.genconst(0)
    def genconst(llvalue):
        return LLConst(llimpl.genconst(llvalue))

    @staticmethod
    def erasedType(T):
        return lltype.erasedType(T)

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

    varsizeAllocToken = allocToken

    @staticmethod
    @specialize.memo()
    def arrayToken(A):
        return LLConst(llimpl.constTYPE(A.OF))

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        return ([LLConst(llimpl.constTYPE(A)) for A in FUNCTYPE.ARGS],
                LLConst(llimpl.constTYPE(FUNCTYPE.RESULT)),
                LLConst(llimpl.constTYPE(FUNCTYPE)))

    constPrebuiltGlobal = genconst

    def replay(self, block, kinds):
        builder = LLBuilder(block.g)
        args_gv = builder._newblock(kinds)
        return builder, args_gv

    def stop_replay(self, endblock, kinds):
        return [LLVar(llimpl.getinputarg(endblock.b, i))
                for i in range(len(kinds))]

    # not RPython, just for debugging.  Specific to llgraph.
    @staticmethod
    def reveal(gv):
        if hasattr(gv, 'v'):
            v = gv.v
        else:
            v = fishllattr(gv, 'v')
        return llimpl.reveal(v)

    def _freeze_(self):
        return True    # no real point in using a full class in llgraph


rgenop = RGenOp()      # no real point in using a full class in llgraph
