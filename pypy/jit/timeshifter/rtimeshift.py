import operator, weakref
from pypy.rpython.lltypesystem import lltype, lloperation, llmemory
from pypy.rpython import rgenop
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

    def __init__(self, opname, ARGS, RESULT):
        self.opname = opname
        self.llop = lloperation.LL_OPERATIONS[opname]
        self.nb_args = len(ARGS)
        self.ARGS = ARGS
        self.RESULT = RESULT
        self.gv_RESULT = rgenop.constTYPE(RESULT)
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
    op_key = (hop.spaceop.opname,
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
        return rvalue.ll_fromvalue(res)
    op_args = lltype.malloc(rgenop.VARLIST.TO, 1)
    op_args[0] = argbox.getgenvar(jitstate.curbuilder)
    genvar = jitstate.curbuilder.genop(opdesc.opname, op_args,
                                      opdesc.gv_RESULT)
    return opdesc.redboxcls(opdesc.gv_RESULT, genvar)

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
        return rvalue.ll_fromvalue(res)
    op_args = lltype.malloc(rgenop.VARLIST.TO, 2)
    op_args[0] = argbox0.getgenvar(jitstate.curbuilder)
    op_args[1] = argbox1.getgenvar(jitstate.curbuilder)
    genvar = jitstate.curbuilder.genop(opdesc.opname, op_args,
                                       opdesc.gv_RESULT)
    return opdesc.redboxcls(opdesc.gv_RESULT, genvar)

def ll_generate_getfield(jitstate, fielddesc, argbox):
    if fielddesc.immutable and argbox.is_constant():
        res = getattr(rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE),
                      fielddesc.fieldname)
        return rvalue.ll_fromvalue(res)
    assert isinstance(argbox, rvalue.PtrRedBox)
    if argbox.content is None:
        op_args = lltype.malloc(rgenop.VARLIST.TO, 2)
        op_args[0] = argbox.getgenvar(jitstate.curbuilder)
        op_args[1] = fielddesc.fieldname_gv[-1]
        genvar = jitstate.curbuilder.genop('getfield', op_args,
                                           fielddesc.gv_resulttype)
        return fielddesc.redboxcls(fielddesc.gv_resulttype, genvar)        
    else:
        return argbox.content.op_getfield(jitstate, fielddesc)

def ll_generate_setfield(jitstate, fielddesc, destbox, valuebox):
    assert isinstance(destbox, rvalue.PtrRedBox)
    if destbox.content is None:
        op_args = lltype.malloc(rgenop.VARLIST.TO, 3)
        op_args[0] = destbox.getgenvar(jitstate.curbuilder)
        op_args[1] = fielddesc.fieldname_gv[-1]
        op_args[2] = valuebox.getgenvar(jitstate.curbuilder)
        jitstate.curbuilder.genop('setfield', op_args,
                                  rgenop.gv_Void)       
    else:
        destbox.content.op_setfield(jitstate, fielddesc, valuebox)

def ll_generate_getsubstruct(jitstate, fielddesc, argbox):
    if argbox.is_constant():
        res = getattr(rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE),
                      fielddesc.fieldname)
        return rvalue.ll_fromvalue(res)
    assert isinstance(argbox, rvalue.PtrRedBox)
    if argbox.content is None:
        op_args = lltype.malloc(rgenop.VARLIST.TO, 2)
        op_args[0] = argbox.getgenvar(jitstate.curbuilder)
        op_args[1] = fielddesc.gv_fieldname
        genvar = jitstate.curbuilder.genop('getsubstruct', op_args,
                                           fielddesc.gv_resulttype)
        return fielddesc.redboxcls(fielddesc.gv_resulttype, genvar)        
    else:
        return argbox.content.op_getsubstruct(jitstate, fielddesc)


def ll_generate_getarrayitem(jitstate, fielddesc, argbox, indexbox):
    if fielddesc.immutable and argbox.is_constant() and indexbox.is_constant():
        array = rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE)
        res = array[rvalue.ll_getvalue(indexbox, lltype.Signed)]
        return rvalue.ll_fromvalue(res)
    op_args = lltype.malloc(rgenop.VARLIST.TO, 2)
    op_args[0] = argbox.getgenvar(jitstate.curbuilder)
    op_args[1] = indexbox.getgenvar(jitstate.curbuilder)
    genvar = jitstate.curbuilder.genop('getarrayitem', op_args,
                                       fielddesc.gv_resulttype)
    return fielddesc.redboxcls(fielddesc.gv_resulttype, genvar)

# ____________________________________________________________
# other jitstate/graph level operations

def enter_graph(builder):
    return builder.build_jitstate()

def retrieve_jitstate_for_merge(states_dic, jitstate, key, redboxes):
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
            box.genvar = rgenop.geninputarg(newblock, box.gv_type)
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
        box.genvar = rgenop.geninputarg(newblock, box.gv_type)
    if replace_memo.boxes:
        for i in range(len(redboxes)):
            redboxes[i] = redboxes[i].replace(replace_memo)
    jitstate.curbuilder.leave_block()
    jitstate.curbuilder.enter_block(linkargs, newblock)
    memo = rvalue.freeze_memo()
    frozens = [redbox.freeze(memo) for redbox in redboxes]
    states_dic[key] = frozens, newblock
    return jitstate
retrieve_jitstate_for_merge._annspecialcase_ = "specialize:arglltype(2)"
    
def enter_block(jitstate, redboxes):
    newblock = rgenop.newblock()
    incoming = []
    memo = rvalue.enter_block_memo()
    for i in range(len(redboxes)):
        redboxes[i].enter_block(newblock, incoming, memo)
    jitstate.curbuilder.enter_block(incoming, newblock)
    return jitstate

def dyn_enter_block(jitstate, redboxes):
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

novars = lltype.malloc(rgenop.VARLIST.TO, 0)

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
    
def prepare_return(jitstate, cache, gv_return_type):
    for builder, retbox in jitstate.return_queue[:-1]:
        builder.leave_block()
        jitstate.curbuilder = builder
        retrieve_jitstate_for_merge(cache, jitstate, (), [retbox])
    frozens, block = cache[()]
    _, returnbox = jitstate.return_queue[-1]
    builder = ResidualGraphBuilder(block)
    builder.valuebox = returnbox
    return builder

def ll_gvar_from_redbox(jitstate, redbox):
    return redbox.getgenvar(jitstate.curbuilder)

def ll_gvar_from_constant(ll_value):
    return rgenop.genconst(ll_value)

def before_call(jitstate):
    leave_block(jitstate)
    return jitstate.curbuilder

def after_call(jitstate, newbuilder):
    jitstate.curbuilder = newbuilder
    return newbuilder.valuebox

# ____________________________________________________________

class ResidualGraphBuilder(rgenop.LowLevelOpBuilder):
    def __init__(self, block=rgenop.nullblock, link=rgenop.nulllink):
        rgenop.LowLevelOpBuilder.__init__(self, block)
        self.outgoinglink = link
        self.valuebox = None

    def build_jitstate(self):
        return JITState(self)

    def enter_block(self, linkargs, newblock):
        rgenop.closelink(self.outgoinglink, linkargs, newblock)
        self.block = newblock
        self.outgoinglink = rgenop.nulllink
   
    def leave_block(self):
        self.outgoinglink = rgenop.closeblock1(self.block)

    def leave_block_split(self, exitgvar):
        linkpair = rgenop.closeblock2(self.block, exitgvar)    
        false_link, true_link = linkpair.item0, linkpair.item1
        later_builder = ResidualGraphBuilder(link=false_link)
        self.outgoinglink = true_link
        return later_builder

    def finish_and_goto(self, linkargs, targetblock):
        rgenop.closelink(self.outgoinglink, linkargs, targetblock)
        self.outgoinglink = rgenop.nulllink
        
    def finish_and_return(self):
        gv_retval = self.valuebox.getgenvar(self)
        returnlink = rgenop.closeblock1(self.block)
        rgenop.closereturnlink(returnlink, gv_retval)
        
    def clone(self):
        XXX

def ll_make_builder():
    return ResidualGraphBuilder(rgenop.newblock())

def ll_int_box(gv_type, gv):
    return rvalue.IntRedBox(gv_type, gv)

def ll_double_box(gv_type, gv):
    return rvalue.DoubleRedBox(gv_type, gv)

def ll_addr_box(gv_type, gv):
    return rvalue.PtrRedBox(gv_type, gv)

def ll_geninputarg(builder, gv_TYPE):
    return rgenop.geninputarg(builder.block, gv_TYPE)

def ll_end_setup_builder(builder):
    builder.leave_block()
    return builder.block
    
def ll_close_builder(builder):
    builder.finish_and_return()
        
class JITState(object):
    # XXX obscure interface

    def __init__(self, builder):
        self.split_queue = []
        self.return_queue = []
        self.curbuilder = builder


