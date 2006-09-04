import operator, weakref
from pypy.rpython.lltypesystem import lltype, lloperation, llmemory
from pypy.jit.timeshifter import rvalue

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
              tuple([hrtyper.originalconcretetype(s_arg) for s_arg in hop.args_s]),
              hrtyper.originalconcretetype(hop.s_result))
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

def ll_gengetarraysize(jitstate, fielddesc, argbox):
    if argbox.is_constant():
        array = rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE)
        res = len(array)
        return rvalue.ll_fromvalue(jitstate, res)
    genvar = jitstate.curbuilder.genop_getarraysize(
        fielddesc.arraytoken,
        argbox.getgenvar(jitstate.curbuilder))
    return rvalue.IntRedBox(fielddesc.indexkind, genvar)

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

def retrieve_jitstate_for_merge(states_dic, jitstate, key, redboxes):
    jitstate.local_boxes = redboxes
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
        box = box.forcevar(jitstate.curbuilder, replace_memo)
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

def leave_block_split(jitstate, switchredbox, exitindex,
                      redboxes_true, redboxes_false):
    if switchredbox.is_constant():
        return rvalue.ll_getvalue(switchredbox, lltype.Bool)
    else:
        exitgvar = switchredbox.getgenvar(jitstate.curbuilder)
        later_builder = jitstate.curbuilder.jump_if_false(exitgvar)
        memo = rvalue.copy_memo()
        jitstate.local_boxes = redboxes_false
        later_jitstate = jitstate.copy(memo)
        later_jitstate.curbuilder = later_builder
        later_jitstate.exitindex = exitindex
        jitstate.split_queue.append(later_jitstate)
        jitstate.local_boxes = redboxes_true
        enter_block(jitstate)
        return True

def dispatch_next(oldjitstate, return_cache):
    split_queue = oldjitstate.split_queue
    if split_queue:
        jitstate = split_queue.pop()
        enter_block(jitstate)
        return jitstate
    else:
        return_queue = oldjitstate.return_queue
        for jitstate in return_queue[:-1]:
            res = retrieve_jitstate_for_merge(return_cache, jitstate, (),
                                              jitstate.local_boxes)
            assert res is True   # finished
        frozen, block = return_cache[()]
        jitstate = return_queue[-1]
        retbox = jitstate.local_boxes[0]
        backstate = jitstate.backstate
        backstate.curbuilder = jitstate.curbuilder
        backstate.local_boxes.append(retbox)
        backstate.exitindex = -1
        # XXX for now the return value box is put in the parent's local_boxes,
        # where a 'restore_local' operation will fetch it
        return backstate

def getexitindex(jitstate):
    return jitstate.exitindex

def getlocalbox(jitstate, i):
    return jitstate.local_boxes[i]

def save_return(jitstate):
    jitstate.return_queue.append(jitstate)

def ll_gvar_from_redbox(jitstate, redbox):
    return redbox.getgenvar(jitstate.curbuilder)

def ll_gvar_from_constant(jitstate, ll_value):
    return jitstate.curbuilder.rgenop.genconst(ll_value)

def save_locals(jitstate, redboxes):
    jitstate.local_boxes = redboxes

# ____________________________________________________________


class FrozenJITState(object):
    fz_backstate = None
    #fz_local_boxes = ... set by freeze()

    def exactmatch(self, jitstate, outgoingvarboxes, memo):
        self_boxes = self.fz_local_boxes
        live_boxes = jitstate.local_boxes
        fullmatch = True
        for i in range(len(self_boxes)):
            if not self_boxes[i].exactmatch(live_boxes[i],
                                            outgoingvarboxes,
                                            memo):
                fullmatch = False
        if self.fz_backstate is not None:
            assert jitstate.backstate is not None
            if not self.fz_backstate.exactmatch(jitstate.backstate,
                                                outgoingvarboxes,
                                                memo):
                fullmatch = False
        else:
            assert jitstate.backstate is None
        return fullmatch


class JITState(object):
    exitindex = -1

    def __init__(self, split_queue, return_queue, builder, backstate):
        self.split_queue = split_queue
        self.return_queue = return_queue
        self.curbuilder = builder
        self.backstate = backstate
        #self.local_boxes = ... set by callers

    def enter_block(self, incoming, memo):
        for box in self.local_boxes:
            box.enter_block(incoming, memo)
        if self.backstate is not None:
            self.backstate.enter_block(incoming, memo)

    def freeze(self, memo):
        result = FrozenJITState()
        frozens = [box.freeze(memo) for box in self.local_boxes]
        result.fz_local_boxes = frozens
        if self.backstate is not None:
            result.fz_backstate = self.backstate.freeze(memo)
        return result

    def copy(self, memo):
        if self.backstate is None:
            newbackstate = None
        else:
            newbackstate = self.backstate.copy(memo)
        result = JITState(self.split_queue,
                          self.return_queue,
                          None,
                          newbackstate)
        result.local_boxes = [box.copy(memo) for box in self.local_boxes]
        return result

    def replace(self, memo):
        local_boxes = self.local_boxes
        for i in range(len(local_boxes)):
            local_boxes[i] = local_boxes[i].replace(memo)
        if self.backstate is not None:
            self.backstate.replace(memo)


def enter_graph(backstate):
    return JITState([], [], backstate.curbuilder, backstate)

def fresh_jitstate(builder):
    jitstate = JITState([], [], builder, None)
    jitstate.local_boxes = []
    return jitstate
