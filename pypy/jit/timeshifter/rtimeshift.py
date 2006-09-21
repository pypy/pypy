import operator, weakref
from pypy.rpython.lltypesystem import lltype, lloperation, llmemory
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.timeshifter import rvalue
from pypy.rpython.unroll import unrolling_iterable

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

def start_new_block(states_dic, jitstate, key):
    memo = rvalue.freeze_memo()
    frozen = jitstate.freeze(memo)
    memo = rvalue.exactmatch_memo()
    outgoingvarboxes = []
    res = frozen.exactmatch(jitstate, outgoingvarboxes, memo)
    assert res, "exactmatch() failed"
    newblock = enter_next_block(jitstate, outgoingvarboxes)
    states_dic[key] = frozen, newblock
start_new_block._annspecialcase_ = "specialize:arglltype(2)"

def retrieve_jitstate_for_merge(states_dic, jitstate, key):
    if key not in states_dic:
        start_new_block(states_dic, jitstate, key)
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
    start_new_block(states_dic, jitstate, key)
    return False       # continue
retrieve_jitstate_for_merge._annspecialcase_ = "specialize:arglltype(2)"

def enter_block(jitstate):
    incoming = []
    memo = rvalue.enter_block_memo()
    jitstate.enter_block(incoming, memo)
    enter_next_block(jitstate, incoming)

def split(jitstate, switchredbox, resumepoint, *greens_gv):
    exitgvar = switchredbox.getgenvar(jitstate.curbuilder)
    later_builder = jitstate.curbuilder.jump_if_false(exitgvar)
    jitstate.split(later_builder, resumepoint, list(greens_gv))

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

# ____________________________________________________________

class BaseDispatchQueue(object):
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

    def __init__(self, builder, frame, exc_type_box, exc_value_box,
                 resumepoint=-1, newgreens=[]):
        self.curbuilder = builder
        self.frame = frame
        self.exc_type_box = exc_type_box
        self.exc_value_box = exc_value_box
        self.resumepoint = resumepoint
        self.greens = newgreens

    def split(self, newbuilder, newresumepoint, newgreens):
        memo = rvalue.copy_memo()
        later_jitstate = JITState(newbuilder,
                                  self.frame.copy(memo),
                                  self.exc_type_box .copy(memo),
                                  self.exc_value_box.copy(memo),
                                  newresumepoint,
                                  newgreens)
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
    jitstate.frame = VirtualFrame(jitstate.frame, DispatchQueueClass())
enter_graph._annspecialcase_ = 'specialize:arg(1)'
# XXX is that too many specializations? ^^^

def merge_returning_jitstates(jitstate):
    return_chain = jitstate.frame.dispatch_queue.return_chain
    return_cache = {}
    still_pending = None
    while return_chain is not None:
        jitstate = return_chain
        return_chain = return_chain.next
        res = retrieve_jitstate_for_merge(return_cache, jitstate, ())
        if res is False:    # not finished
            jitstate.next = still_pending
            still_pending = jitstate
    assert still_pending is not None
    most_general_jitstate = still_pending
    still_pending = still_pending.next
    while still_pending is not None:
        jitstate = still_pending
        still_pending = still_pending.next
        res = retrieve_jitstate_for_merge(return_cache, jitstate, ())
        assert res is True   # finished
    return most_general_jitstate

def leave_graph_red(jitstate):
    jitstate = merge_returning_jitstates(jitstate)
    myframe = jitstate.frame
    jitstate.returnbox = myframe.local_boxes[0]
    # ^^^ fetched by a 'fetch_return' operation
    jitstate.frame = myframe.backframe
    return jitstate

def leave_graph_void(jitstate):
    jitstate = merge_returning_jitstates(jitstate)
    myframe = jitstate.frame
    jitstate.frame = myframe.backframe
    return jitstate

def leave_graph_yellow(jitstate):
    return_chain = jitstate.frame.dispatch_queue.return_chain
    jitstate = return_chain
    while jitstate is not None:
        jitstate.frame = jitstate.frame.backframe
        jitstate = jitstate.next
    return return_chain    # a jitstate, which is the head of the chain
