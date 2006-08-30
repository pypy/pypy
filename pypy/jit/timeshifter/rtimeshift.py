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
    op_args = [argbox.getgenvar(jitstate.curbuilder)]
    genvar = jitstate.curbuilder.genop(opdesc.opname, op_args,
                                      opdesc.result_kind)
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
    op_args = [argbox0.getgenvar(jitstate.curbuilder),
               argbox1.getgenvar(jitstate.curbuilder)]
    genvar = jitstate.curbuilder.genop(opdesc.opname, op_args,
                                       opdesc.result_kind)
    return opdesc.redboxcls(opdesc.result_kind, genvar)

def ll_generate_getfield(jitstate, fielddesc, argbox):
    if fielddesc.immutable and argbox.is_constant():
        res = getattr(rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE),
                      fielddesc.fieldname)
        return rvalue.ll_fromvalue(jitstate, res)
    assert isinstance(argbox, rvalue.PtrRedBox)
    if argbox.content is None:
        genvar = jitstate.curbuilder.genop_getfield(fielddesc.fieldtokens[-1],
                                                    argbox.getgenvar(jitstate.curbuilder))
        return fielddesc.redboxcls(fielddesc.kind, genvar)        
    else:
        return argbox.content.op_getfield(jitstate, fielddesc)

def ll_generate_setfield(jitstate, fielddesc, destbox, valuebox):
    assert isinstance(destbox, rvalue.PtrRedBox)
    if destbox.content is None:
        builder = jitstate.curbuilder
        builder.genop_setfield(fielddesc.fieldtokens[-1],
                                destbox.getgenvar(builder),
                                valuebox.getgenvar(builder))
    else:
        destbox.content.op_setfield(jitstate, fielddesc, valuebox)

def ll_generate_getsubstruct(jitstate, fielddesc, argbox):
    if argbox.is_constant():
        res = getattr(rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE),
                      fielddesc.fieldname)
        return rvalue.ll_fromvalue(jitstate, res)
    assert isinstance(argbox, rvalue.PtrRedBox)
    if argbox.content is None:
        genvar = jitstate.curbuilder.genop_getsubstruct(fielddesc.fieldtoken, argbox.getgenvar(jitstate.curbuilder))
        return fielddesc.redboxcls(fielddesc.kind, genvar)        
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

# ____________________________________________________________
# other jitstate/graph level operations

def enter_graph(builder, backstate=None):
    return builder.build_jitstate(backstate)

def retrieve_jitstate_for_merge(states_dic, jitstate, key, redboxes):
    rgenop = jitstate.rgenop
    mylocalredboxes = redboxes
    redboxes = list(redboxes)
    jitstate.extend_with_parent_locals(redboxes)
    if key not in states_dic:
        memo = rvalue.freeze_memo()
        frozens = [redbox.freeze(memo) for redbox in redboxes]
        memo = rvalue.exactmatch_memo()
        outgoingvarboxes = []
        for i in range(len(redboxes)):
            res = frozens[i].exactmatch(redboxes[i], outgoingvarboxes, memo)
            assert res, "exactmatch() failed"
        newblock = rgenop.newblock()
        linkargs = []
        for box in outgoingvarboxes:
            linkargs.append(box.getgenvar(None))
            box.genvar = newblock.geninputarg(box.kind)
        jitstate.curbuilder.enter_block(linkargs, newblock)
        states_dic[key] = frozens, newblock
        return jitstate

    frozens, oldblock = states_dic[key]
    memo = rvalue.exactmatch_memo()
    outgoingvarboxes = []
    exactmatch = True
    for i in range(len(redboxes)):
        frozen = frozens[i]
        if not frozen.exactmatch(redboxes[i], outgoingvarboxes, memo):
            exactmatch = False

    if exactmatch:
        jitstate = dyn_enter_block(jitstate, outgoingvarboxes)
        linkargs = []
        for box in outgoingvarboxes:
            linkargs.append(box.getgenvar(jitstate.curbuilder))
        jitstate.curbuilder.leave_block()
        jitstate.curbuilder.finish_and_goto(linkargs, oldblock)
        return None
    
    # Make a more general block
    jitstate = dyn_enter_block(jitstate, outgoingvarboxes)
    newblock = rgenop.newblock()
    linkargs = []
    replace_memo = rvalue.copy_memo()
    for box in outgoingvarboxes:
        linkargs.append(box.getgenvar(jitstate.curbuilder))
    for box in outgoingvarboxes:
        if box.is_constant():            # constant boxes considered immutable:
            box = box.copy(replace_memo) # copy to avoid patching the original
        box.genvar = newblock.geninputarg(box.kind)
    if replace_memo.boxes:
        for i in range(len(mylocalredboxes)):
            newbox = redboxes[i].replace(replace_memo)
            mylocalredboxes[i] = redboxes[i] = newbox
    jitstate.curbuilder.leave_block()
    jitstate.curbuilder.enter_block(linkargs, newblock)
    memo = rvalue.freeze_memo()
    frozens = [redbox.freeze(memo) for redbox in redboxes]
    states_dic[key] = frozens, newblock
    return jitstate
retrieve_jitstate_for_merge._annspecialcase_ = "specialize:arglltype(2)"
    
def enter_block(jitstate, redboxes):
    # 'redboxes' is a fixed-size list (s_box_list) of the current red boxes
    rgenop = jitstate.rgenop
    newblock = rgenop.newblock()
    incoming = []
    memo = rvalue.enter_block_memo()
    for redbox in redboxes:
        redbox.enter_block(newblock, incoming, memo)
    js = jitstate.backstate
    while js is not None:
        lrb = js.localredboxes
        assert lrb is not None
        for redbox in lrb:
            redbox.enter_block(newblock, incoming, memo)
        js = js.backstate
    jitstate.curbuilder.enter_block(incoming, newblock)
    return jitstate

def dyn_enter_block(jitstate, redboxes):
    # 'redboxes' is a var-sized list (s_box_accum) of *all* the boxes
    # including the ones from the callers' locals
    rgenop = jitstate.rgenop
    newblock = rgenop.newblock()
    incoming = []
    memo = rvalue.enter_block_memo()
    for redbox in redboxes:
        redbox.enter_block(newblock, incoming, memo)
    jitstate.curbuilder.enter_block(incoming, newblock)
    return jitstate

def leave_block(jitstate):
    jitstate.curbuilder.leave_block()
    return jitstate

def leave_block_split(jitstate, switchredbox, exitindex, redboxes):
    if switchredbox.is_constant():
        jitstate.curbuilder.leave_block()
        return rvalue.ll_getvalue(switchredbox, lltype.Bool)
    else:
        exitgvar = switchredbox.getgenvar(jitstate.curbuilder)
        later_builder = jitstate.curbuilder.leave_block_split(exitgvar)
        memo = rvalue.copy_memo()
        redboxcopies = [redbox.copy(memo) for redbox in redboxes]        
        jitstate.split_queue.append((exitindex, later_builder, redboxcopies))
        return True

def dispatch_next(jitstate, outredboxes):
    split_queue = jitstate.split_queue
    if split_queue:
        exitindex, later_builder, redboxes = split_queue.pop()
        jitstate.curbuilder = later_builder
        for box in redboxes:
            outredboxes.append(box)
        return exitindex
    return -1

def save_return(jitstate, redboxes):
    returnbox = redboxes[0]
    jitstate.return_queue.append((jitstate.curbuilder, returnbox))
    
def prepare_return(jitstate, cache, return_type):
    for builder, retbox in jitstate.return_queue[:-1]:
        builder.leave_block()
        jitstate.curbuilder = builder
        retrieve_jitstate_for_merge(cache, jitstate, (), [retbox])
    frozens, block = cache[()]
    _, returnbox = jitstate.return_queue[-1]
    rgenop = jitstate.rgenop
    builder = ResidualGraphBuilder(rgenop, block)
    builder.valuebox = returnbox
    return builder

def ll_gvar_from_redbox(jitstate, redbox):
    return redbox.getgenvar(jitstate.curbuilder)

def ll_gvar_from_constant(jitstate, ll_value):
    return jitstate.rgenop.genconst(ll_value)

def save_locals(jitstate, redboxes):
    jitstate.localredboxes = redboxes

def before_call(jitstate):
    leave_block(jitstate)
    return jitstate.curbuilder

def after_call(jitstate, newbuilder):
    jitstate.curbuilder = newbuilder
    return newbuilder.valuebox

# ____________________________________________________________

class ResidualGraphBuilder(object):
    def __init__(self, rgenop, block=None, link=None):
        self.rgenop = rgenop
        self.block = block
        self.outgoinglink = link
        self.valuebox = None

    def genconst(self, llvalue):
        return self.rgenop.genconst(llvalue)
    genconst._annspecialcase_ = 'specialize:genconst(1)'

    def genvoidconst(self, dummy):
        return self.rgenop.placeholder(dummy)
    genvoidconst._annspecialcase_ = 'specialize:arg(1)'

    def genop(self, opname, args_gv, result_kind=None):
        return self.block.genop(opname, args_gv, result_kind)
    genop._annspecialcase_ = 'specialize:arg(1)'

    def genop_getfield(self, fieldtoken, gv_ptr):
        return self.block.genop_getfield(fieldtoken, gv_ptr)

    def genop_setfield(self, fieldtoken, gv_ptr, gv_value):
        return self.block.genop_setfield(fieldtoken, gv_ptr, gv_value)

    def genop_getsubstruct(self, fieldtoken, gv_ptr):
        return self.block.genop_getsubstruct(fieldtoken, gv_ptr)

    def genop_getarrayitem(self, arraytoken, gv_ptr, gv_index):
        return self.block.genop_getarrayitem(arraytoken, gv_ptr, gv_index)

    def genop_malloc_fixedsize(self, alloctoken):
        return self.block.genop_malloc_fixedsize(alloctoken)

    def constTYPE(self, T):
        return self.rgenop.constTYPE(T)
    constTYPE._annspecialcase_ = 'specialize:arg(1)'

    def build_jitstate(self, backstate=None):
        return JITState(self, backstate)

    def enter_block(self, linkargs, newblock):
        self.outgoinglink.close(linkargs, newblock)
        self.block = newblock
        self.outgoinglink = None
   
    def leave_block(self):
        self.outgoinglink = self.block.close1()

    def leave_block_split(self, exitgvar):
        false_link, true_link = self.block.close2(exitgvar)    
        later_builder = ResidualGraphBuilder(self.rgenop, link=false_link)
        self.outgoinglink = true_link
        return later_builder

    def finish_and_goto(self, linkargs, targetblock):
        self.outgoinglink.close(linkargs, targetblock)
        self.outgoinglink = None
        
    def finish_and_return(self):
        gv_retval = self.valuebox.getgenvar(self)
        returnlink = self.block.close1()
        returnlink.closereturn(gv_retval)

def make_builder(rgenop):
    return ResidualGraphBuilder(rgenop, rgenop.newblock())

def ll_int_box(kind, gv):
    return rvalue.IntRedBox(kind, gv)

def ll_double_box(kind, gv):
    return rvalue.DoubleRedBox(kind, gv)

def ll_addr_box(kind, gv):
    return rvalue.PtrRedBox(kind, gv)

def ll_geninputarg(builder, kind):
    return builder.block.geninputarg(kind)

def ll_end_setup_builder(builder):
    builder.leave_block()
    return builder.block
    
def ll_close_builder(builder):
    builder.finish_and_return()

def ll_gencallableconst(builder, name, startblock, gv_functype):
    return builder.rgenop.gencallableconst(name, startblock, gv_functype)

class JITState(object):
    # XXX obscure interface
    localredboxes = None

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
