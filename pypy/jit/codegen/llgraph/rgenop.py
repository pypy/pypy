from pypy.rlib.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
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


_gv_TYPE_cache = {}
def gv_TYPE(TYPE):
    try:
        return _gv_TYPE_cache[TYPE]
    except KeyError:
        gv = LLConst(llimpl.constTYPE(TYPE))
        _gv_TYPE_cache[TYPE] = gv
        return gv

gv_Void = gv_TYPE(lltype.Void)
gv_Signed = gv_TYPE(lltype.Signed)
gv_dummy_placeholder = LLConst(llimpl.dummy_placeholder)


class LLLabel(GenLabel):
    def __init__(self, b, g):
        self.b = b
        self.g = g

class LLFlexSwitch(CodeGenSwitch):
    
    def __init__(self, b, g, args_gv):
        self.b = b
        self.gv_f = g
        self.cases_gv = []
        self.args_gv = args_gv

    def add_case(self, gv_case):
        self.cases_gv.append(gv_case)  # not used so far, but keeps ptrs alive
        l_case = llimpl.add_case(self.b, gv_case.v)
        b = llimpl.closelinktofreshblock(l_case, self.args_gv, self.l_default)
        return LLBuilder(self.gv_f, b)

    def _add_default(self):
        l_default = llimpl.add_default(self.b)
        self.l_default = l_default
        b = llimpl.closelinktofreshblock(l_default, self.args_gv, None)
        return LLBuilder(self.gv_f, b)

class LLBuilder(GenBuilder):
    jumped_from = None

    def __init__(self, g, block):
        self.rgenop = rgenop
        self.gv_f = g
        self.b = block

    def end(self):
        llimpl.end(self.gv_f)
        
    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        return LLVar(llimpl.genop(self.b, opname, [gv_arg], llimpl.guess))

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        return LLVar(llimpl.genop(self.b, opname, [gv_arg1, gv_arg2],
                                  llimpl.guess))

    def genop_call(self, (ARGS_gv, gv_RESULT, _), gv_callable, args_gv):
        vars_gv = [gv_callable]
        j = 0
        for i in range(len(ARGS_gv)):
            if ARGS_gv[i] is gv_Void:
                gv_arg = gv_dummy_placeholder
            else:
                gv_arg = LLVar(llimpl.cast(self.b, ARGS_gv[i].v, args_gv[j].v))
                j += 1
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

    def genop_getarraysubstruct(self, gv_ITEMTYPE, gv_ptr, gv_index):
        vars_gv = [gv_ptr.v, gv_index.v]
        return LLVar(llimpl.genop(self.b, 'getarraysubstruct', vars_gv,
                                  gv_ITEMTYPE.v))

    def genop_setarrayitem(self, gv_ITEMTYPE, gv_ptr, gv_index, gv_value):
        vars_gv = [gv_ptr.v, gv_index.v, gv_value.v]
        return LLVar(llimpl.genop(self.b, 'setarrayitem', vars_gv,
                                  gv_Void.v))

    def genop_getarraysize(self, gv_ITEMTYPE, gv_ptr):
        return LLVar(llimpl.genop(self.b, 'getarraysize', [gv_ptr.v],
                                  gv_Signed.v))

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
        lnk = llimpl.closeblock1(self.b)
        newb_args_gv = self._newblock(kinds) 
        llimpl.closelink(lnk, args_gv, self.b)
        for i in range(len(args_gv)):
            args_gv[i] = newb_args_gv[i]
        return LLLabel(self.b, self.gv_f)

    def finish_and_goto(self, args_gv, target):
        lnk = llimpl.closeblock1(self.b)
        llimpl.closelink(lnk, args_gv, target.b)
        self._close()

    def finish_and_return(self, sigtoken, gv_returnvar):
        gv_returnvar = gv_returnvar or gv_dummy_placeholder
        lnk = llimpl.closeblock1(self.b)
        llimpl.closereturnlink(lnk, gv_returnvar.v, self.gv_f)
        self._close()

    def _jump(self, l_jump, l_no_jump, args_for_jump_gv):
        self.b = llimpl.closelinktofreshblock(l_no_jump, None, None)
        b2 = llimpl.closelinktofreshblock(l_jump, args_for_jump_gv, None)
        later_builder = LLBuilder(self.gv_f, llimpl.nullblock)
        later_builder.later_block = b2
        later_builder.jumped_from = self
        return later_builder

    def jump_if_true(self, gv_cond, args_for_jump_gv):
        l_false, l_true = llimpl.closeblock2(self.b, gv_cond.v)
        return self._jump(l_true, l_false, args_for_jump_gv)

    def jump_if_false(self, gv_cond, args_for_jump_gv):
        l_false, l_true = llimpl.closeblock2(self.b, gv_cond.v)
        return self._jump(l_false, l_true, args_for_jump_gv)

    def flexswitch(self, gv_switchvar, args_gv):
        llimpl.closeblockswitch(self.b, gv_switchvar.v)
        flexswitch = LLFlexSwitch(self.b, self.gv_f, args_gv)
        self._close()
        return (flexswitch, flexswitch._add_default())

    def _close(self):
        self.b = llimpl.nullblock

    def start_writing(self):
        assert self.b == llimpl.nullblock
        if self.jumped_from:
            assert self.jumped_from.b == llimpl.nullblock
        assert self.later_block != llimpl.nullblock
        self.b = self.later_block
        self.later_block = llimpl.nullblock

    def pause_writing(self, args_gv):
        lnk = llimpl.closeblock1(self.b)
        b2 = llimpl.closelinktofreshblock(lnk, args_gv, None)
        self._close()
        later_builder = LLBuilder(self.gv_f, llimpl.nullblock)
        later_builder.later_block = b2
        return later_builder

    def show_incremental_progress(self):
        llimpl.show_incremental_progress(self.gv_f)


class RGenOp(AbstractRGenOp):
    gv_Void = gv_Void


    def newgraph(self, (ARGS_gv, gv_RESULT, gv_FUNCTYPE), name):
        gv_func = llimpl.newgraph(gv_FUNCTYPE.v, name)
        builder = LLBuilder(gv_func, llimpl.getstartblock(gv_func))
        inputargs_gv = [LLVar(llimpl.getinputarg(builder.b, i))
                        for i in range(len(ARGS_gv))]
        return builder, LLConst(gv_func), inputargs_gv

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
        return gv_TYPE(T)

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        assert name in T._flds
        FIELDTYPE = getattr(T, name)
        if isinstance(FIELDTYPE, lltype.ContainerType):
            FIELDTYPE = lltype.Ptr(FIELDTYPE)
        return (LLConst(llimpl.constFieldName(name)),
                gv_TYPE(lltype.Ptr(T)),
                gv_TYPE(FIELDTYPE))

    @staticmethod
    @specialize.memo()
    def allocToken(TYPE):
        return (gv_TYPE(TYPE),
                gv_TYPE(lltype.Ptr(TYPE)))

    varsizeAllocToken = allocToken

    @staticmethod
    @specialize.memo()
    def arrayToken(A):
        ITEMTYPE = A.OF
        if isinstance(ITEMTYPE, lltype.ContainerType):
            ITEMTYPE = lltype.Ptr(ITEMTYPE)
        return gv_TYPE(ITEMTYPE)

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        return ([gv_TYPE(A) for A in FUNCTYPE.ARGS],
                gv_TYPE(FUNCTYPE.RESULT),
                gv_TYPE(FUNCTYPE))

    constPrebuiltGlobal = genconst

    def replay(self, label, kinds):
        builder = LLBuilder(label.g, llimpl.nullblock)
        args_gv = builder._newblock(kinds)
        return builder, args_gv

    #def stop_replay(self, endblock, kinds):
    #    return [LLVar(llimpl.getinputarg(endblock.b, i))
    #            for i in range(len(kinds))]

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
