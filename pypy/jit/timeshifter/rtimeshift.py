import operator, weakref
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype, lloperation, llmemory
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.timeshifter import rvalue
from pypy.rpython.unroll import unrolling_iterable
from pypy.rpython.annlowlevel import cachedtype, base_ptr_lltype
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance

FOLDABLE_OPS = dict.fromkeys(lloperation.enum_foldable_ops())

# ____________________________________________________________
# emit ops


class OpDesc(object):
    """
    Description of a low-level operation
    that can be passed around to low level helpers
    to inform op generation
    """
    
    def _freeze_(self):
        return True

    def __init__(self, RGenOp, opname, ARGS, RESULT):
        self.RGenOp = RGenOp
        self.opname = opname
        self.llop = lloperation.LL_OPERATIONS[opname]
        self.nb_args = len(ARGS)
        self.ARGS = ARGS
        self.RESULT = RESULT
        self.result_kind = RGenOp.kindToken(RESULT)
        self.redboxcls = rvalue.ll_redboxcls(RESULT)
        self.canfold = opname in FOLDABLE_OPS

    def __getattr__(self, name): # .ARGx -> .ARGS[x]
        if name.startswith('ARG'):
            index = int(name[3:])
            return self.ARGS[index]
        else:
            raise AttributeError("don't know about %r in OpDesc" % name)

    def compact_repr(self): # goes in ll helper names
        return self.opname.upper()

_opdesc_cache = {}

def make_opdesc(hop):
    hrtyper = hop.rtyper
    op_key = (hrtyper.RGenOp, hop.spaceop.opname,
              tuple([originalconcretetype(s_arg) for s_arg in hop.args_s]),
              originalconcretetype(hop.s_result))
    try:
        return _opdesc_cache[op_key]
    except KeyError:
        opdesc = OpDesc(*op_key)
        _opdesc_cache[op_key] = opdesc
        return opdesc

def ll_gen1(opdesc, jitstate, argbox):
    ARG0 = opdesc.ARG0
    RESULT = opdesc.RESULT
    opname = opdesc.name
    if opdesc.canfold and argbox.is_constant():
        arg = rvalue.ll_getvalue(argbox, ARG0)
        res = opdesc.llop(RESULT, arg)
        return rvalue.ll_fromvalue(jitstate, res)
    gv_arg = argbox.getgenvar(jitstate.curbuilder)
    genvar = jitstate.curbuilder.genop1(opdesc.opname, gv_arg)
    return opdesc.redboxcls(opdesc.result_kind, genvar)

def ll_gen2(opdesc, jitstate, argbox0, argbox1):
    ARG0 = opdesc.ARG0
    ARG1 = opdesc.ARG1
    RESULT = opdesc.RESULT
    opname = opdesc.name
    if opdesc.canfold and argbox0.is_constant() and argbox1.is_constant():
        # const propagate
        arg0 = rvalue.ll_getvalue(argbox0, ARG0)
        arg1 = rvalue.ll_getvalue(argbox1, ARG1)
        res = opdesc.llop(RESULT, arg0, arg1)
        return rvalue.ll_fromvalue(jitstate, res)
    gv_arg0 = argbox0.getgenvar(jitstate.curbuilder)
    gv_arg1 = argbox1.getgenvar(jitstate.curbuilder)
    genvar = jitstate.curbuilder.genop2(opdesc.opname, gv_arg0, gv_arg1)
    return opdesc.redboxcls(opdesc.result_kind, genvar)

def ll_genmalloc_varsize(jitstate, contdesc, sizebox):
    gv_size = sizebox.getgenvar(jitstate.curbuilder)
    alloctoken = contdesc.varsizealloctoken
    genvar = jitstate.curbuilder.genop_malloc_varsize(alloctoken, gv_size)
    return rvalue.PtrRedBox(contdesc.ptrkind, genvar)

def ll_gengetfield(jitstate, fielddesc, argbox):
    if fielddesc.immutable and argbox.is_constant():
        res = getattr(rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE),
                      fielddesc.fieldname)
        return rvalue.ll_fromvalue(jitstate, res)
    assert isinstance(argbox, rvalue.PtrRedBox)
    if argbox.content is None:
        gv_ptr = argbox.getgenvar(jitstate.curbuilder)
        return fielddesc.generate_get(jitstate.curbuilder, gv_ptr)
    else:
        return argbox.content.op_getfield(jitstate, fielddesc)

def ll_gensetfield(jitstate, fielddesc, destbox, valuebox):
    assert isinstance(destbox, rvalue.PtrRedBox)
    if destbox.content is None:
        gv_ptr = destbox.getgenvar(jitstate.curbuilder)
        fielddesc.generate_set(jitstate.curbuilder, gv_ptr, valuebox)
    else:
        destbox.content.op_setfield(jitstate, fielddesc, valuebox)

def ll_gengetsubstruct(jitstate, fielddesc, argbox):
    if argbox.is_constant():
        res = getattr(rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE),
                      fielddesc.fieldname)
        return rvalue.ll_fromvalue(jitstate, res)
    assert isinstance(argbox, rvalue.PtrRedBox)
    if argbox.content is None:
        gv_ptr = argbox.getgenvar(jitstate.curbuilder)
        return fielddesc.generate_getsubstruct(jitstate.curbuilder, gv_ptr)
    else:
        return argbox.content.op_getsubstruct(jitstate, fielddesc)


def ll_gengetarrayitem(jitstate, fielddesc, argbox, indexbox):
    if fielddesc.immutable and argbox.is_constant() and indexbox.is_constant():
        array = rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE)
        res = array[rvalue.ll_getvalue(indexbox, lltype.Signed)]
        return rvalue.ll_fromvalue(jitstate, res)
    genvar = jitstate.curbuilder.genop_getarrayitem(
        fielddesc.arraytoken,
        argbox.getgenvar(jitstate.curbuilder),
        indexbox.getgenvar(jitstate.curbuilder))
                                                    
    return fielddesc.redboxcls(fielddesc.kind, genvar)

def ll_gensetarrayitem(jitstate, fielddesc, destbox, indexbox, valuebox):
    genvar = jitstate.curbuilder.genop_setarrayitem(
        fielddesc.arraytoken,
        destbox.getgenvar(jitstate.curbuilder),
        indexbox.getgenvar(jitstate.curbuilder),
        valuebox.getgenvar(jitstate.curbuilder)
        )
                                                    
    return fielddesc.redboxcls(fielddesc.kind, genvar)

def ll_gengetarraysize(jitstate, fielddesc, argbox):
    if argbox.is_constant():
        array = rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE)
        res = len(array)
        return rvalue.ll_fromvalue(jitstate, res)
    genvar = jitstate.curbuilder.genop_getarraysize(
        fielddesc.arraytoken,
        argbox.getgenvar(jitstate.curbuilder))
    return rvalue.IntRedBox(fielddesc.indexkind, genvar)

def ll_genptrnonzero(jitstate, argbox, reverse):
    if argbox.is_constant():
        addr = rvalue.ll_getvalue(argbox, llmemory.Address)
        return rvalue.ll_fromvalue(jitstate, bool(addr) ^ reverse)
    assert isinstance(argbox, rvalue.PtrRedBox)
    builder = jitstate.curbuilder
    if argbox.content is None:
        gv_addr = argbox.getgenvar(builder)
        if reverse:
            gv_res = builder.genop1("ptr_iszero", gv_addr)
        else:
            gv_res = builder.genop1("ptr_nonzero", gv_addr)
    else:
        gv_res = builder.rgenop.genconst(True ^ reverse)
    return rvalue.IntRedBox(builder.rgenop.kindToken(lltype.Bool), gv_res)

# ____________________________________________________________
# other jitstate/graph level operations

def enter_next_block(jitstate, incoming):
    linkargs = []
    kinds = []
    for redbox in incoming:
        linkargs.append(redbox.genvar)
        kinds.append(redbox.kind)
    newblock = jitstate.curbuilder.enter_next_block(kinds, linkargs)
    for i in range(len(incoming)):
        incoming[i].genvar = linkargs[i]
    return newblock

def start_new_block(states_dic, jitstate, key, global_resumer):
    memo = rvalue.freeze_memo()
    frozen = jitstate.freeze(memo)
    memo = rvalue.exactmatch_memo()
    outgoingvarboxes = []
    res = frozen.exactmatch(jitstate, outgoingvarboxes, memo)
    assert res, "exactmatch() failed"
    newblock = enter_next_block(jitstate, outgoingvarboxes)
    states_dic[key] = frozen, newblock
    if global_resumer:
        greens_gv = jitstate.greens
        rgenop = jitstate.curbuilder.rgenop
        jitstate.promotion_path = PromotionPathRoot(greens_gv, rgenop,
                                                    frozen, newblock,
                                                    global_resumer)
start_new_block._annspecialcase_ = "specialize:arglltype(2)"

def retrieve_jitstate_for_merge(states_dic, jitstate, key, global_resumer):
    if key not in states_dic:
        start_new_block(states_dic, jitstate, key, global_resumer)
        return False   # continue

    frozen, oldblock = states_dic[key]
    memo = rvalue.exactmatch_memo()
    outgoingvarboxes = []

    if frozen.exactmatch(jitstate, outgoingvarboxes, memo):
        linkargs = []
        for box in outgoingvarboxes:
            linkargs.append(box.getgenvar(jitstate.curbuilder))
        jitstate.curbuilder.finish_and_goto(linkargs, oldblock)
        return True    # finished

    # We need a more general block.  Do it by generalizing all the
    # redboxes from outgoingvarboxes, by making them variables.
    # Then we make a new block based on this new state.
    replace_memo = rvalue.copy_memo()
    for box in outgoingvarboxes:
        box.forcevar(jitstate.curbuilder, replace_memo)
    if replace_memo.boxes:
        jitstate.replace(replace_memo)
    start_new_block(states_dic, jitstate, key, global_resumer)
    return False       # continue
retrieve_jitstate_for_merge._annspecialcase_ = "specialize:arglltype(2)"

def enter_block(jitstate):
    incoming = []
    memo = rvalue.enter_block_memo()
    jitstate.enter_block(incoming, memo)
    enter_next_block(jitstate, incoming)

def split(jitstate, switchredbox, resumepoint, *greens_gv):
    exitgvar = switchredbox.getgenvar(jitstate.curbuilder)
    if exitgvar.is_const:
        return exitgvar.revealconst(lltype.Bool)
    else:
        if jitstate.resuming is None:
            later_builder = jitstate.curbuilder.jump_if_false(exitgvar)
            jitstate.split(later_builder, resumepoint, list(greens_gv))
            return True
        else:
            return jitstate.resuming.path.pop()

def collect_split(jitstate_chain, resumepoint, *greens_gv):
    greens_gv = list(greens_gv)
    pending = jitstate_chain
    while True:
        jitstate = pending
        pending = pending.next
        jitstate.greens.extend(greens_gv)   # item 0 is the return value
        jitstate.resumepoint = resumepoint
        if pending is None:
            break
    dispatch_queue = jitstate_chain.frame.dispatch_queue
    jitstate.next = dispatch_queue.split_chain
    dispatch_queue.split_chain = jitstate_chain.next
    # XXX obscurity++ above

def dispatch_next(oldjitstate):
    dispatch_queue = oldjitstate.frame.dispatch_queue
    if dispatch_queue.split_chain is not None:
        jitstate = dispatch_queue.split_chain
        dispatch_queue.split_chain = jitstate.next
        enter_block(jitstate)
        return jitstate
    else:
        oldjitstate.resumepoint = -1
        return oldjitstate

def getresumepoint(jitstate):
    return jitstate.resumepoint

def save_locals(jitstate, *redboxes):
    redboxes = list(redboxes)
    assert None not in redboxes
    jitstate.frame.local_boxes = redboxes

def save_greens(jitstate, *greens_gv):
    jitstate.greens = list(greens_gv)

def getlocalbox(jitstate, i):
    return jitstate.frame.local_boxes[i]

def ll_getgreenbox(jitstate, i, T):
    return jitstate.greens[i].revealconst(T)

def getreturnbox(jitstate):
    return jitstate.returnbox

def getexctypebox(jitstate):
    return jitstate.exc_type_box

def getexcvaluebox(jitstate):
    return jitstate.exc_value_box

def setexctypebox(jitstate, box):
    jitstate.exc_type_box = box

def setexcvaluebox(jitstate, box):
    jitstate.exc_value_box = box

def save_return(jitstate):
    # add 'jitstate' to the chain of return-jitstates
    dispatch_queue = jitstate.frame.dispatch_queue
    jitstate.next = dispatch_queue.return_chain
    dispatch_queue.return_chain = jitstate

##def ll_gvar_from_redbox(jitstate, redbox):
##    return redbox.getgenvar(jitstate.curbuilder)

##def ll_gvar_from_constant(jitstate, ll_value):
##    return jitstate.curbuilder.rgenop.genconst(ll_value)

class CallDesc:
    __metaclass__ = cachedtype

    def __init__(self, RGenOp, FUNCTYPE):
        self.sigtoken = RGenOp.sigToken(FUNCTYPE)
        self.result_kind = RGenOp.kindToken(FUNCTYPE.RESULT)
        self.redboxbuilder = rvalue.ll_redboxbuilder(FUNCTYPE.RESULT)

    def _freeze_(self):
        return True

def ll_gen_residual_call(jitstate, calldesc, funcbox):
    builder = jitstate.curbuilder
    gv_funcbox = funcbox.getgenvar(builder)
    argboxes = jitstate.frame.local_boxes
    args_gv = [argbox.getgenvar(builder) for argbox in argboxes]
    gv_result = builder.genop_call(calldesc.sigtoken, gv_funcbox, args_gv)
    return calldesc.redboxbuilder(calldesc.result_kind, gv_result)


class ResumingInfo(object):
    def __init__(self, promotion_point, gv_value, path):
        self.promotion_point = promotion_point
        self.gv_value = gv_value
        self.path = path

class PromotionPoint(object):
    def __init__(self, flexswitch, switchblock, promotion_path):
        assert promotion_path is not None
        self.flexswitch = flexswitch
        self.switchblock = switchblock
        self.promotion_path = promotion_path

class AbstractPromotionPath(object):
    pass

class PromotionPathRoot(AbstractPromotionPath):
    def __init__(self, greens_gv, rgenop, frozen, portalblock, global_resumer):
        self.greens_gv = greens_gv
        self.rgenop = rgenop
        self.frozen = frozen
        self.portalblock = portalblock
        self.global_resumer = global_resumer

    def follow_path(self, path):
        return self

    def continue_compilation(self, resuminginfo):
        incoming = []
        memo = rvalue.unfreeze_memo()
        jitstate = self.frozen.unfreeze(incoming, memo)
        kinds = [box.kind for box in incoming]
        builder, vars_gv = self.rgenop.replay(self.portalblock, kinds)
        for i in range(len(incoming)):
            incoming[i].genvar = vars_gv[i]
        jitstate.curbuilder = builder
        jitstate.greens = self.greens_gv
        jitstate.resuming = resuminginfo
        assert jitstate.frame.backframe is None
        self.global_resumer(jitstate)
        builder.show_incremental_progress()

class PromotionPathNode(AbstractPromotionPath):
    def __init__(self, next):
        self.next = next
    def follow_path(self, path):
        path.append(self.answer)
        return self.next.follow_path(path)

class PromotionPathYes(PromotionPathNode):
    answer = True

class PromotionPathNo(PromotionPathNode):
    answer = False

class PromotionPathNoWithArg(PromotionPathNo):

    def __init__(self, next, arg):
        self.next = next
        self.arg = arg

    def follow_path(self, path):
        path.append(self.arg)
        return PromotionPathNo.follow_path(self, path)
        

def ll_continue_compilation(promotion_point_ptr, value):
    try:
        promotion_point = cast_base_ptr_to_instance(PromotionPoint,
                                                    promotion_point_ptr)
        path = []
        root = promotion_point.promotion_path.follow_path(path)
        gv_value = root.rgenop.genconst(value)
        resuminginfo = ResumingInfo(promotion_point, gv_value, path)
        root.continue_compilation(resuminginfo)
    except Exception, e:
        lloperation.llop.debug_fatalerror(lltype.Void,
                                          "compilation-time error", e)

class PromotionDesc:
    __metatype__ = cachedtype

    def __init__(self, ERASED, hrtyper):
##        (s_PromotionPoint,
##         r_PromotionPoint) = hrtyper.s_r_instanceof(PromotionPoint)
        fnptr = hrtyper.annhelper.delayedfunction(
            ll_continue_compilation,
            [annmodel.SomePtr(base_ptr_lltype()),
             annmodel.lltype_to_annotation(ERASED)],
            annmodel.s_None, needtype=True)
        RGenOp = hrtyper.RGenOp
        self.gv_continue_compilation = RGenOp.constPrebuiltGlobal(fnptr)
        self.sigtoken = RGenOp.sigToken(lltype.typeOf(fnptr).TO)
##        self.PROMOTION_POINT = r_PromotionPoint.lowleveltype

    def _freeze_(self):
        return True

def ll_promote(jitstate, box, promotiondesc):
    builder = jitstate.curbuilder
    gv_switchvar = box.getgenvar(builder)
    if gv_switchvar.is_const:
        return False
    else:
        incoming = []
        memo = rvalue.enter_block_memo()
        jitstate.enter_block(incoming, memo)
        switchblock = enter_next_block(jitstate, incoming)

        if jitstate.resuming is None:
            gv_switchvar = box.genvar
            flexswitch = builder.flexswitch(gv_switchvar)
            # default case of the switch:
            enter_block(jitstate)
            pm = PromotionPoint(flexswitch, switchblock,
                                jitstate.promotion_path)
            ll_pm = cast_instance_to_base_ptr(pm)
            gv_pm = builder.rgenop.genconst(ll_pm)
            gv_switchvar = box.genvar
            builder.genop_call(promotiondesc.sigtoken,
                               promotiondesc.gv_continue_compilation,
                               [gv_pm, gv_switchvar])
            linkargs = []
            for box in incoming:
                linkargs.append(box.getgenvar(builder))
            builder.finish_and_goto(linkargs, switchblock)
            return True
        else:
            assert jitstate.promotion_path is None
            resuming = jitstate.resuming
            assert len(resuming.path) == 0
            pm = resuming.promotion_point

            kinds = [box.kind for box in incoming]
            vars_gv = jitstate.curbuilder.rgenop.stop_replay(pm.switchblock,
                                                             kinds)
            for i in range(len(incoming)):
                incoming[i].genvar = vars_gv[i]
            box.genvar = resuming.gv_value

            newbuilder = pm.flexswitch.add_case(resuming.gv_value)

            jitstate.resuming = None
            jitstate.promotion_path = pm.promotion_path
            jitstate.curbuilder = newbuilder
            enter_block(jitstate)
            return False

# ____________________________________________________________

class BaseDispatchQueue(object):
    parent_promotion_path = None
    parent_resuming = None
    
    def __init__(self):
        self.split_chain = None
        self.return_chain = None

def build_dispatch_subclass(attrnames):
    if len(attrnames) == 0:
        return BaseDispatchQueue
    attrnames = unrolling_iterable(attrnames)
    class DispatchQueue(BaseDispatchQueue):
        def __init__(self):
            BaseDispatchQueue.__init__(self)
            for name in attrnames:
                setattr(self, name, {})     # the new dicts have various types!
    return DispatchQueue


class FrozenVirtualFrame(object):
    fz_backframe = None
    #fz_local_boxes = ... set by freeze()

    def exactmatch(self, vframe, outgoingvarboxes, memo):
        self_boxes = self.fz_local_boxes
        live_boxes = vframe.local_boxes
        fullmatch = True
        for i in range(len(self_boxes)):
            if not self_boxes[i].exactmatch(live_boxes[i],
                                            outgoingvarboxes,
                                            memo):
                fullmatch = False
        if self.fz_backframe is not None:
            assert vframe.backframe is not None
            if not self.fz_backframe.exactmatch(vframe.backframe,
                                                outgoingvarboxes,
                                                memo):
                fullmatch = False
        else:
            assert vframe.backframe is None
        return fullmatch

    def unfreeze(self, incomingvarboxes, memo):
        local_boxes = []
        for fzbox in self.fz_local_boxes:
            local_boxes.append(fzbox.unfreeze(incomingvarboxes, memo))
        if self.fz_backframe is not None:
            backframe = self.fz_backframe.unfreeze(incomingvarboxes, memo)
        else:
            backframe = None
        vframe = VirtualFrame(backframe, BaseDispatchQueue())
        vframe.local_boxes = local_boxes
        return vframe


class FrozenJITState(object):
    #fz_frame = ...           set by freeze()
    #fz_exc_type_box = ...    set by freeze()
    #fz_exc_value_box = ...   set by freeze()

    def exactmatch(self, jitstate, outgoingvarboxes, memo):
        fullmatch = True
        if not self.fz_frame.exactmatch(jitstate.frame,
                                        outgoingvarboxes,
                                        memo):
            fullmatch = False
        if not self.fz_exc_type_box.exactmatch(jitstate.exc_type_box,
                                               outgoingvarboxes,
                                               memo):
            fullmatch = False
        if not self.fz_exc_value_box.exactmatch(jitstate.exc_value_box,
                                                outgoingvarboxes,
                                                memo):
            fullmatch = False
        return fullmatch

    def unfreeze(self, incomingvarboxes, memo):
        frame         = self.fz_frame        .unfreeze(incomingvarboxes, memo)
        exc_type_box  = self.fz_exc_type_box .unfreeze(incomingvarboxes, memo)
        exc_value_box = self.fz_exc_value_box.unfreeze(incomingvarboxes, memo)
        return JITState(None, frame, exc_type_box, exc_value_box)


class VirtualFrame(object):

    def __init__(self, backframe, dispatch_queue):
        self.backframe = backframe
        self.dispatch_queue = dispatch_queue
        #self.local_boxes = ... set by callers

    def enter_block(self, incoming, memo):
        for box in self.local_boxes:
            box.enter_block(incoming, memo)
        if self.backframe is not None:
            self.backframe.enter_block(incoming, memo)

    def freeze(self, memo):
        result = FrozenVirtualFrame()
        frozens = [box.freeze(memo) for box in self.local_boxes]
        result.fz_local_boxes = frozens
        if self.backframe is not None:
            result.fz_backframe = self.backframe.freeze(memo)
        return result

    def copy(self, memo):
        if self.backframe is None:
            newbackframe = None
        else:
            newbackframe = self.backframe.copy(memo)
        result = VirtualFrame(newbackframe, self.dispatch_queue)
        result.local_boxes = [box.copy(memo) for box in self.local_boxes]
        return result

    def replace(self, memo):
        local_boxes = self.local_boxes
        for i in range(len(local_boxes)):
            local_boxes[i] = local_boxes[i].replace(memo)
        if self.backframe is not None:
            self.backframe.replace(memo)


class JITState(object):
    returnbox = None
    next      = None   # for linked lists
    resuming  = None   # or a ResumingInfo

    def __init__(self, builder, frame, exc_type_box, exc_value_box,
                 resumepoint=-1, newgreens=[], promotion_path=None):
        self.curbuilder = builder
        self.frame = frame
        self.exc_type_box = exc_type_box
        self.exc_value_box = exc_value_box
        self.resumepoint = resumepoint
        self.greens = newgreens
        self.promotion_path = promotion_path

    def split(self, newbuilder, newresumepoint, newgreens):
        memo = rvalue.copy_memo()
        later_jitstate = JITState(newbuilder,
                                  self.frame.copy(memo),
                                  self.exc_type_box .copy(memo),
                                  self.exc_value_box.copy(memo),
                                  newresumepoint,
                                  newgreens,
                                  PromotionPathNo(self.promotion_path))
        self.promotion_path = PromotionPathYes(self.promotion_path)
        # add the later_jitstate to the chain of pending-for-dispatch_next()
        dispatch_queue = self.frame.dispatch_queue
        later_jitstate.next = dispatch_queue.split_chain
        dispatch_queue.split_chain = later_jitstate

    def enter_block(self, incoming, memo):
        self.frame.enter_block(incoming, memo)
        self.exc_type_box .enter_block(incoming, memo)
        self.exc_value_box.enter_block(incoming, memo)

    def freeze(self, memo):
        result = FrozenJITState()
        result.fz_frame = self.frame.freeze(memo)
        result.fz_exc_type_box  = self.exc_type_box .freeze(memo)
        result.fz_exc_value_box = self.exc_value_box.freeze(memo)
        return result

    def replace(self, memo):
        self.frame.replace(memo)
        self.exc_type_box  = self.exc_type_box .replace(memo)
        self.exc_value_box = self.exc_value_box.replace(memo)


def enter_graph(jitstate, DispatchQueueClass):
    dispatchqueue = DispatchQueueClass()
    enter_frame(jitstate, dispatchqueue)
enter_graph._annspecialcase_ = 'specialize:arg(1)'

def enter_frame(jitstate, dispatchqueue):
    resuming = jitstate.resuming
    if resuming is None:
        dispatchqueue.parent_promotion_path = jitstate.promotion_path
        jitstate.promotion_path = PromotionPathYes(jitstate.promotion_path)
    else:
        dispatchqueue.parent_resuming = resuming
        taking = resuming.path.pop()
        if not taking:
            jitstate.resuming = None
    jitstate.frame = VirtualFrame(jitstate.frame, dispatchqueue)
                
class CompilationInterrupted(Exception):
    pass

def merge_returning_jitstates(jitstate):
    return_chain = jitstate.frame.dispatch_queue.return_chain
    return_cache = {}
    still_pending = None
    while return_chain is not None:
        jitstate = return_chain
        return_chain = return_chain.next
        res = retrieve_jitstate_for_merge(return_cache, jitstate, (), None)
        if res is False:    # not finished
            jitstate.next = still_pending
            still_pending = jitstate
    if still_pending is None:
        raise CompilationInterrupted
    most_general_jitstate = still_pending
    still_pending = still_pending.next
    while still_pending is not None:
        jitstate = still_pending
        still_pending = still_pending.next
        res = retrieve_jitstate_for_merge(return_cache, jitstate, (), None)
        assert res is True   # finished
    return most_general_jitstate

def leave_graph_red(jitstate):
    jitstate = merge_returning_jitstates(jitstate)
    myframe = jitstate.frame
    leave_frame(jitstate)
    jitstate.returnbox = myframe.local_boxes[0]
    # ^^^ fetched by a 'fetch_return' operation
    return jitstate

def leave_graph_gray(jitstate):
    jitstate = merge_returning_jitstates(jitstate)
    leave_frame(jitstate)
    return jitstate

def leave_frame(jitstate):
    myframe = jitstate.frame
    jitstate.frame = myframe.backframe
    assert jitstate.resuming is None
    mydispatchqueue = myframe.dispatch_queue
    resuming = mydispatchqueue.parent_resuming
    if resuming is None:
        parent_promotion_path = mydispatchqueue.parent_promotion_path
        jitstate.promotion_path = PromotionPathNo(parent_promotion_path)
    else:
        jitstate.resuming = resuming
        jitstate.promotion_path = None
    
def leave_graph_yellow(jitstate):
    mydispatchqueue = jitstate.frame.dispatch_queue
    return_chain = mydispatchqueue.return_chain
    jitstate = return_chain
    resuming = mydispatchqueue.parent_resuming
    if resuming is None:
        n = 0
        parent_promotion_path = mydispatchqueue.parent_promotion_path
        while jitstate is not None:
            assert jitstate.resuming is None
            node = PromotionPathNoWithArg(parent_promotion_path, n)
            jitstate.promotion_path = node
            n += 1
            jitstate.frame = jitstate.frame.backframe
            jitstate = jitstate.next
        return return_chain    # a jitstate, which is the head of the chain
    else:
        n = resuming.path.pop()
        for i in range(n):
            assert jitstate.resuming is None
            jitstate = jitstate.next
        jitstate.resuming = resuming
        jitstate.promotion_path = None
        jitstate.frame = jitstate.frame.backframe
        jitstate.next = None
        return jitstate
