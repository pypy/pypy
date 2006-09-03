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

def ll_generate_operation1(opdesc, jitstate, argbox):
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

def ll_generate_operation2(opdesc, jitstate, argbox0, argbox1):
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

def ll_generate_getfield(jitstate, fielddesc, argbox):
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

def ll_generate_setfield(jitstate, fielddesc, destbox, valuebox):
    assert isinstance(destbox, rvalue.PtrRedBox)
    if destbox.content is None:
        gv_ptr = destbox.getgenvar(jitstate.curbuilder)
        fielddesc.generate_set(jitstate.curbuilder, gv_ptr, valuebox)
    else:
        destbox.content.op_setfield(jitstate, fielddesc, valuebox)

def ll_generate_getsubstruct(jitstate, fielddesc, argbox):
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


def ll_generate_getarrayitem(jitstate, fielddesc, argbox, indexbox):
    if fielddesc.immutable and argbox.is_constant() and indexbox.is_constant():
        array = rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE)
        res = array[rvalue.ll_getvalue(indexbox, lltype.Signed)]
        return rvalue.ll_fromvalue(jitstate, res)
    genvar = jitstate.curbuilder.genop_getarrayitem(
        fielddesc.arraytoken,
        argbox.getgenvar(jitstate.curbuilder),
        indexbox.getgenvar(jitstate.curbuilder))
                                                    
    return fielddesc.redboxcls(fielddesc.kind, genvar)

def ll_generate_getarraysize(jitstate, fielddesc, argbox):
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

def enter_graph(backstate):
    return JITState(backstate.curbuilder, backstate)

def start_new_block(states_dic, jitstate, key, redboxes):
    memo = rvalue.freeze_memo()
    frozens = [redbox.freeze(memo) for redbox in redboxes]
    memo = rvalue.exactmatch_memo()
    outgoingvarboxes = []
    for i in range(len(redboxes)):
        res = frozens[i].exactmatch(redboxes[i], outgoingvarboxes, memo)
        assert res, "exactmatch() failed"
    linkargs = []
    kinds = []
    for box in outgoingvarboxes: # all variables
        linkargs.append(box.genvar)
        kinds.append(box.kind)
    newblock = jitstate.curbuilder.enter_next_block(kinds, linkargs)
    states_dic[key] = frozens, newblock
    for i in range(len(outgoingvarboxes)):
        box = outgoingvarboxes[i]
        box.genvar = linkargs[i]
    return jitstate
start_new_block._annspecialcase_ = "specialize:arglltype(2)"

def retrieve_jitstate_for_merge(states_dic, jitstate, key, redboxes):
    mylocalredboxes = redboxes
    redboxes = list(redboxes)
    jitstate.extend_with_parent_locals(redboxes)
    if key not in states_dic:
        return start_new_block(states_dic, jitstate, key, redboxes)

    frozens, oldblock = states_dic[key]
    memo = rvalue.exactmatch_memo()
    outgoingvarboxes = []
    exactmatch = True
    for i in range(len(redboxes)):
        frozen = frozens[i]
        if not frozen.exactmatch(redboxes[i], outgoingvarboxes, memo):
            exactmatch = False

    if exactmatch:
        linkargs = []
        for box in outgoingvarboxes:
            linkargs.append(box.getgenvar(jitstate.curbuilder))
        jitstate.curbuilder.finish_and_goto(linkargs, oldblock)
        return None

    # We need a more general block.  Do it by generalizing all the
    # redboxes from outgoingvarboxes, by making them variables.
    # Then we make a new block based on this new state.
    replace_memo = rvalue.copy_memo()
    for box in outgoingvarboxes:
        box = box.forcevar(jitstate.curbuilder, replace_memo)
    if replace_memo.boxes:
        for i in range(len(mylocalredboxes)):
            newbox = redboxes[i].replace(replace_memo)
            mylocalredboxes[i] = redboxes[i] = newbox
    return start_new_block(states_dic, jitstate, key, redboxes)
retrieve_jitstate_for_merge._annspecialcase_ = "specialize:arglltype(2)"
    
def enter_block(jitstate, redboxes):
    # 'redboxes' is a fixed-size list (s_box_list) of the current red boxes
    incoming = []
    memo = rvalue.enter_block_memo()
    for redbox in redboxes:
        redbox.enter_block(incoming, memo)
##    XXX
##    js = jitstate.backstate
##    while js is not None:
##        lrb = js.localredboxes
##        assert lrb is not None
##        for redbox in lrb:
##            redbox.enter_block(incoming, memo)
##        js = js.backstate
    linkargs = []
    kinds = []
    for redbox in incoming: # all variables
        linkargs.append(redbox.genvar)
        kinds.append(redbox.kind)
    jitstate.curbuilder.enter_next_block(kinds, linkargs)
    for i in range(len(incoming)):
        incoming[i].genvar = linkargs[i]

def leave_block_split(jitstate, switchredbox, exitindex,
                      redboxes_true, redboxes_false):
    if switchredbox.is_constant():
        return rvalue.ll_getvalue(switchredbox, lltype.Bool)
    else:
        exitgvar = switchredbox.getgenvar(jitstate.curbuilder)
        later_builder = jitstate.curbuilder.jump_if_false(exitgvar)
        memo = rvalue.copy_memo()
        redboxcopies = [None] * len(redboxes_false)
        for i in range(len(redboxes_false)):
            redboxcopies[i] = redboxes_false[i].copy(memo)
        jitstate.split_queue.append((exitindex, later_builder, redboxcopies))
        enter_block(jitstate, redboxes_true)
        return True

def dispatch_next(jitstate, outredboxes):
    split_queue = jitstate.split_queue
    if split_queue:
        exitindex, later_builder, redboxes = split_queue.pop()
        jitstate.curbuilder = later_builder
        enter_block(jitstate, redboxes)
        for box in redboxes:
            outredboxes.append(box)
        return exitindex
    return -1

def save_return(jitstate, redboxes):
    returnbox = redboxes[0]
    jitstate.return_queue.append((jitstate.curbuilder, returnbox))
    
def prepare_return(jitstate, cache, return_type):
    for builder, retbox in jitstate.return_queue[:-1]:
        jitstate.curbuilder = builder
        res = retrieve_jitstate_for_merge(cache, jitstate, (), [retbox])
        assert res is None
    frozens, block = cache[()]
    builder, returnbox = jitstate.return_queue[-1]
    jitstate.backstate.curbuilder = builder 
    return returnbox

def ll_gvar_from_redbox(jitstate, redbox):
    return redbox.getgenvar(jitstate.curbuilder)

def ll_gvar_from_constant(jitstate, ll_value):
    return jitstate.rgenop.genconst(ll_value)

def save_locals(jitstate, redboxes):
    jitstate.localredboxes = redboxes

# ____________________________________________________________

class JITState(object):
    # XXX obscure interface
    localredboxes = []

    def __init__(self, builder, backstate=None):
        self.split_queue = []
        self.return_queue = []
        self.curbuilder = builder
        self.rgenop = builder.rgenop
        self.backstate = backstate

    def extend_with_parent_locals(self, redboxes):
        js = self.backstate
        while js is not None:
            lrb = js.localredboxes
            assert lrb is not None
            redboxes.extend(lrb)
            js = js.backstate
