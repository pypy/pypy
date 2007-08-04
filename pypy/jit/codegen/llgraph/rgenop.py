from pypy.rlib.objectmodel import specialize, debug_assert
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.jit.codegen.llgraph import llimpl
from pypy.rpython.lltypesystem.rclass import fishllattr
from pypy.rpython.module.support import LLSupport


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

    def revealconstrepr(self):
        return LLSupport.from_rstr(llimpl.revealconstrepr(self.v))

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
gv_Bool = gv_TYPE(lltype.Bool)
gv_dummy_placeholder = LLConst(llimpl.dummy_placeholder)
gv_flavor_gc = LLConst(llimpl.placeholder({'flavor': 'gc'}))

gv_Address = gv_TYPE(llmemory.Address)

class LLLabel(GenLabel):
    def __init__(self, b, g):
        self.b = b
        self.g = g

class LLPlace:
    absorbed = False
    def __init__(self, v, info):
        self.v    = v
        self.info = info

class LLFlexSwitch(CodeGenSwitch):
    
    def __init__(self, rgenop, b, g, args_gv):
        self.rgenop = rgenop
        self.b = b
        self.gv_f = g
        self.cases_gv = []
        self.args_gv = args_gv

    def add_case(self, gv_case):
        self.cases_gv.append(gv_case)  # not used so far, but keeps ptrs alive
        l_case = llimpl.add_case(self.b, gv_case.v)
        b = llimpl.closelinktofreshblock(l_case, self.args_gv, self.l_default)
        builder = LLBuilder(self.rgenop, self.gv_f, b)
        debug_assert(self.rgenop.currently_writing is None or
                     # special case: we stop replaying and add a case after
                     # a call to flexswitch() on a replay builder
                     self.rgenop.currently_writing.is_default_builder,
                     "add_case: currently_writing elsewhere")
        self.rgenop.currently_writing = builder
        return builder

    def _add_default(self):
        l_default = llimpl.add_default(self.b)
        self.l_default = l_default
        b = llimpl.closelinktofreshblock(l_default, self.args_gv, None)
        builder = LLBuilder(self.rgenop, self.gv_f, b)
        debug_assert(self.rgenop.currently_writing is None,
                     "_add_default: currently_writing elsewhere")
        self.rgenop.currently_writing = builder
        builder.is_default_builder = True
        return builder

class LLBuilder(GenBuilder):
    jumped_from = None
    is_default_builder = False

    def __init__(self, rgenop, g, block):
        self.rgenop = rgenop
        self.gv_f = g
        self.b = block

    def end(self):
        debug_assert(self.rgenop.currently_writing is None,
                     "end: currently_writing")
        llimpl.end(self.gv_f)
        
    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop1: bad currently_writing")
        return LLVar(llimpl.genop(self.b, opname, [gv_arg], llimpl.guess))

    @specialize.arg(1)
    def genraisingop1(self, opname, gv_arg):
        debug_assert(self.rgenop.currently_writing is self,
                     "genraisingop1: bad currently_writing")
        gv_res = LLVar(llimpl.genop(self.b, opname, [gv_arg], llimpl.guess))
        gv_exc = LLVar(llimpl.genop(self.b, "check_and_clear_exc", [],
                                    gv_Bool.v))
        return gv_res, gv_exc

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop2: bad currently_writing")
        return LLVar(llimpl.genop(self.b, opname, [gv_arg1, gv_arg2],
                                  llimpl.guess))

    @specialize.arg(1)
    def genraisingop2(self, opname, gv_arg1, gv_arg2):
        debug_assert(self.rgenop.currently_writing is self,
                     "genraisingop2: bad currently_writing")
        gv_res = LLVar(llimpl.genop(self.b, opname, [gv_arg1, gv_arg2],
                                    llimpl.guess))
        gv_exc = LLVar(llimpl.genop(self.b, "check_and_clear_exc", [],
                                    gv_Bool.v))
        return gv_res, gv_exc

    def genop_call(self, (ARGS_gv, gv_RESULT, _), gv_callable, args_gv):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_call: bad currently_writing")
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
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_getfield: bad currently_writing")
        vars_gv = [llimpl.cast(self.b, gv_PTRTYPE.v, gv_ptr.v), gv_name.v]
        return LLVar(llimpl.genop(self.b, 'getfield', vars_gv,
                                  gv_FIELDTYPE.v))        
    
    def genop_setfield(self, (gv_name, gv_PTRTYPE, gv_FIELDTYPE), gv_ptr,
                                                                  gv_value):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_setfield: bad currently_writing")
        vars_gv = [llimpl.cast(self.b, gv_PTRTYPE.v, gv_ptr.v),
                   gv_name.v,
                   llimpl.cast(self.b, gv_FIELDTYPE.v, gv_value.v)]
        return LLVar(llimpl.genop(self.b, 'setfield', vars_gv,
                                  gv_Void.v))        
    
    def genop_getsubstruct(self, (gv_name, gv_PTRTYPE, gv_FIELDTYPE), gv_ptr):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_getsubstruct: bad currently_writing")
        vars_gv = [llimpl.cast(self.b, gv_PTRTYPE.v, gv_ptr.v), gv_name.v]
        return LLVar(llimpl.genop(self.b, 'getsubstruct', vars_gv,
                                  gv_FIELDTYPE.v))        

    def genop_getarrayitem(self, gv_ITEMTYPE, gv_ptr, gv_index):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_getarrayitem: bad currently_writing")
        vars_gv = [gv_ptr.v, gv_index.v]
        return LLVar(llimpl.genop(self.b, 'getarrayitem', vars_gv,
                                  gv_ITEMTYPE.v))

    def genop_getarraysubstruct(self, gv_ITEMTYPE, gv_ptr, gv_index):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_getarraysubstruct: bad currently_writing")
        vars_gv = [gv_ptr.v, gv_index.v]
        return LLVar(llimpl.genop(self.b, 'getarraysubstruct', vars_gv,
                                  gv_ITEMTYPE.v))

    def genop_setarrayitem(self, gv_ITEMTYPE, gv_ptr, gv_index, gv_value):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_setarrayitem: bad currently_writing")
        vars_gv = [gv_ptr.v, gv_index.v, gv_value.v]
        return LLVar(llimpl.genop(self.b, 'setarrayitem', vars_gv,
                                  gv_Void.v))

    def genop_getarraysize(self, gv_ITEMTYPE, gv_ptr):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_getarraysize: bad currently_writing")
        return LLVar(llimpl.genop(self.b, 'getarraysize', [gv_ptr.v],
                                  gv_Signed.v))

    def genop_malloc_fixedsize(self, (gv_TYPE, gv_PTRTYPE)):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_malloc_fixedsize: bad currently_writing")
        vars_gv = [gv_TYPE.v, gv_flavor_gc.v]
        return LLVar(llimpl.genop(self.b, 'malloc', vars_gv,
                                  gv_PTRTYPE.v))

    def genop_malloc_varsize(self, (gv_TYPE, gv_PTRTYPE), gv_length):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_malloc_varsize: bad currently_writing")
        vars_gv = [gv_TYPE.v, gv_flavor_gc.v, gv_length.v]
        return LLVar(llimpl.genop(self.b, 'malloc_varsize', vars_gv,
                                  gv_PTRTYPE.v))

    def genop_same_as(self, gv_TYPE, gv_value):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_same_as: bad currently_writing")
        gv_value = llimpl.cast(self.b, gv_TYPE.v, gv_value.v)
        return LLVar(llimpl.genop(self.b, 'same_as', [gv_value], gv_TYPE.v))

    def genop_ptr_iszero(self, gv_PTRTYPE, gv_ptr):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_ptr_iszero: bad currently_writing")
        gv_ptr = llimpl.cast(self.b, gv_PTRTYPE.v, gv_ptr.v)
        return LLVar(llimpl.genop(self.b, 'ptr_iszero', [gv_ptr], gv_Bool.v))

    def genop_ptr_nonzero(self, gv_PTRTYPE, gv_ptr):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_ptr_nonzero: bad currently_writing")
        gv_ptr = llimpl.cast(self.b, gv_PTRTYPE.v, gv_ptr.v)
        return LLVar(llimpl.genop(self.b, 'ptr_nonzero', [gv_ptr], gv_Bool.v))
                                  
    def genop_ptr_eq(self, gv_PTRTYPE, gv_ptr1, gv_ptr2):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_ptr_eq: bad currently_writing")
        gv_ptr1 = llimpl.cast(self.b, gv_PTRTYPE.v, gv_ptr1.v)
        gv_ptr2 = llimpl.cast(self.b, gv_PTRTYPE.v, gv_ptr2.v)        
        return LLVar(llimpl.genop(self.b, 'ptr_eq', [gv_ptr1, gv_ptr2],
                                  gv_Bool.v))

    def genop_ptr_ne(self, gv_PTRTYPE, gv_ptr1, gv_ptr2):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_ptr_ne: bad currently_writing")
        gv_ptr1 = llimpl.cast(self.b, gv_PTRTYPE.v, gv_ptr1.v)
        gv_ptr2 = llimpl.cast(self.b, gv_PTRTYPE.v, gv_ptr2.v)        
        return LLVar(llimpl.genop(self.b, 'ptr_ne', [gv_ptr1, gv_ptr2],
                                  gv_Bool.v))

    def genop_cast_int_to_ptr(self, gv_PTRTYPE, gv_int):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_cast_int_to_ptr: bad currently_writing")
        return LLVar(llimpl.genop(self.b, 'cast_int_to_ptr', [gv_int],
                                  gv_PTRTYPE.v))

    def _newblock(self, kinds):
        self.b = newb = llimpl.newblock()
        return [LLVar(llimpl.geninputarg(newb, kind.v)) for kind in kinds]

    def enter_next_block(self, kinds, args_gv):
        debug_assert(self.rgenop.currently_writing is self,
                     "enter_next_block: bad currently_writing")
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
        debug_assert(self.rgenop.currently_writing is self,
                     "_jump: bad currently_writing")
        self.b = llimpl.closelinktofreshblock(l_no_jump, None, None)
        b2 = llimpl.closelinktofreshblock(l_jump, args_for_jump_gv, None)
        later_builder = LLBuilder(self.rgenop, self.gv_f, llimpl.nullblock)
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
        flexswitch = LLFlexSwitch(self.rgenop, self.b, self.gv_f, args_gv)
        self._close()
        return (flexswitch, flexswitch._add_default())

    def _close(self):
        debug_assert(self.rgenop.currently_writing is self,
                     "_close: bad currently_writing")
        self.rgenop.currently_writing = None
        self.b = llimpl.nullblock

    def start_writing(self):
        assert self.b == llimpl.nullblock
        if self.jumped_from:
            assert self.jumped_from.b == llimpl.nullblock
        assert self.later_block != llimpl.nullblock
        self.b = self.later_block
        self.later_block = llimpl.nullblock
        debug_assert(self.rgenop.currently_writing is None,
                     "start_writing: currently_writing")
        self.rgenop.currently_writing = self

    def pause_writing(self, args_gv):
        lnk = llimpl.closeblock1(self.b)
        b2 = llimpl.closelinktofreshblock(lnk, args_gv, None)
        self._close()
        later_builder = LLBuilder(self.rgenop, self.gv_f, llimpl.nullblock)
        later_builder.later_block = b2
        return later_builder

    def show_incremental_progress(self):
        llimpl.show_incremental_progress(self.gv_f)


    # read_frame_var support

    def genop_get_frame_base(self):
        debug_assert(self.rgenop.currently_writing is self,
                     "genop_get_frame_base: bad currently_writing")
        return LLVar(llimpl.genop(self.b, 'get_frame_base', [],
                                  gv_Address.v))

    def get_frame_info(self, vars):
        debug_assert(self.rgenop.currently_writing is self,
                     "get_frame_info: bad currently_writing")
        return llimpl.get_frame_info(self.b, vars)

    def alloc_frame_place(self, gv_TYPE, gv_initial_value=None):
        debug_assert(self.rgenop.currently_writing is self,
                     "alloc_frame_place: bad currently_writing")
        if gv_initial_value is None:
            gv_initial_value = self.rgenop.genzeroconst(gv_TYPE)
        gv_initial_value = llimpl.cast(self.b, gv_TYPE.v, gv_initial_value.v)
        v = LLVar(llimpl.genop(self.b, 'same_as', [gv_initial_value],
                               gv_TYPE.v))
        return LLPlace(v, llimpl.get_frame_info(self.b, [v]))

    def genop_absorb_place(self, gv_TYPE, place):
        debug_assert(self.rgenop.currently_writing is self,
                     "alloc_frame_place: bad currently_writing")
        debug_assert(not place.absorbed, "place already absorbed")
        place.absorbed = True
        return place.v


class RGenOp(AbstractRGenOp):
    gv_Void = gv_Void
    currently_writing = None

    def newgraph(self, (ARGS_gv, gv_RESULT, gv_FUNCTYPE), name):
        gv_func = llimpl.newgraph(gv_FUNCTYPE.v, name)
        builder = LLBuilder(self, gv_func, llimpl.nullblock)
        builder.later_block = llimpl.getstartblock(gv_func)
        inputargs_gv = [LLVar(llimpl.getinputarg(builder.later_block, i))
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

    @staticmethod
    def genzeroconst(gv_TYPE):
        return LLConst(llimpl.genzeroconst(gv_TYPE.v))

    def replay(self, label, kinds):
        builder = LLBuilder(self, label.g, llimpl.nullblock)
        args_gv = builder._newblock(kinds)
        debug_assert(self.currently_writing is None,
                     "replay: currently_writing")
        self.currently_writing = builder
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

    @staticmethod
    @specialize.arg(0)
    def read_frame_var(T, base, info, index):
        return llimpl.read_frame_var(T, base, info, index)

    @staticmethod
    @specialize.arg(0)
    def write_frame_place(T, base, place, value):
        llimpl.write_frame_var(base, place.info, 0, value)

    @staticmethod
    @specialize.arg(0)
    def read_frame_place(T, base, place):
        return llimpl.read_frame_var(T, base, place.info, 0)


    @staticmethod
    def get_python_callable(FUNC, gv):
        # return a closure that will run the graph on the llinterp
        from pypy.jit.codegen.llgraph.llimpl import testgengraph
        ptr = gv.revealconst(FUNC)
        graph = ptr._obj.graph
        def runner(*args):
            return testgengraph(graph, list(args))
        return runner


rgenop = RGenOp()      # no real point in using a full class in llgraph
