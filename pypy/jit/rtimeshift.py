from pypy.rpython.lltypesystem import lltype
from pypy.rpython import objectmodel
from pypy.rpython import rgenop

# ____________________________________________________________
# types and adtmeths

def ll_fixed_items(l):
    return l

def ll_fixed_length(l):
    return len(l)

VARLIST = lltype.Ptr(lltype.GcArray(rgenop.CONSTORVAR,
                                    adtmeths = {
                                        "ll_items": ll_fixed_items,
                                        "ll_length": ll_fixed_length
                                    }))

def make_types_const(TYPES):
    n = len(TYPES)
    l = lltype.malloc(VARLIST.TO, n)
    for i in range(n):
        l[i] = rgenop.constTYPE(TYPES[i])
    return l


def ll_make_for_gvar(gvar):
    box = lltype.malloc(REDBOX)
    box.isvar = True
    box.genvar = gvar
    return box

def ll_make_from_const(value):
    sbox = lltype.malloc(REDBOX_FOR_SIGNED) # XXX Float, Ptr
    sbox.value = lltype.cast_primitive(lltype.Signed, value)
    box = lltype.cast_pointer(REDBOX_PTR, sbox)
    box.genvar = lltype.nullptr(REDBOX.genvar.TO)
    return box

def ll_getvalue(box, T):
    sbox = lltype.cast_pointer(REDBOX_FOR_SIGNED_PTR, box)
    return lltype.cast_primitive(T, sbox.value)

REDBOX = lltype.GcStruct("redbox", ("genvar", rgenop.CONSTORVAR),
                                   ("isvar", lltype.Bool),
                         adtmeths = {
    'll_make_for_gvar': ll_make_for_gvar,
    'll_make_from_const': ll_make_from_const,
    'll_getvalue': ll_getvalue,
    })

REDBOX_PTR = lltype.Ptr(REDBOX)

REDBOX_FOR_SIGNED = lltype.GcStruct("signed_redbox", 
                                    ('basebox', REDBOX),
                                    ("value", lltype.Signed))
REDBOX_FOR_SIGNED_PTR = lltype.Ptr(REDBOX_FOR_SIGNED)
STATE = lltype.GcStruct("jitstate", ("curblock", rgenop.BLOCK),
                                    ("curoutgoinglink", rgenop.LINK),
                                    ("curvalue", REDBOX_PTR))
STATE_PTR = lltype.Ptr(STATE)


# ____________________________________________________________
# ll helpers on boxes


def ll_gvar_from_redbox(jitstate, box, TYPE):
    if not box.genvar:
        value = box.ll_getvalue(TYPE)
        box.genvar = ll_gvar_from_const(jitstate, value)
    return box.genvar

def ll_gvar_from_const(jitstate, value):
    return rgenop.genconst(value)

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
        self.llop = getattr(objectmodel.llop, opname)
        self.nb_args = len(ARGS)
        self.ARGS = ARGS
        self.RESULT = RESULT

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
    if not argbox.isvar: # const propagate
        arg = argbox.ll_getvalue(ARG0)
        res = opdesc.llop(RESULT, arg)
        return REDBOX.ll_make_from_const(res)
    op_args = lltype.malloc(VARLIST.TO, 1)
    op_args[0] = ll_gvar_from_redbox(jitstate, argbox, ARG0)
    gvar = rgenop.genop(jitstate.curblock, opdesc.opname, op_args,
                        rgenop.constTYPE(RESULT))
    return REDBOX.ll_make_for_gvar(gvar)

def ll_generate_operation2(opdesc, jitstate, argbox0, argbox1):
    ARG0 = opdesc.ARG0
    ARG1 = opdesc.ARG1
    RESULT = opdesc.RESULT
    opname = opdesc.name
    if not argbox0.isvar and not argbox1.isvar: # const propagate
        arg0 = argbox0.ll_getvalue(ARG0)
        arg1 = argbox1.ll_getvalue(ARG1)
        res = opdesc.llop(RESULT, arg0, arg1)
        return REDBOX.ll_make_from_const(res)
    op_args = lltype.malloc(VARLIST.TO, 2)
    op_args[0] = ll_gvar_from_redbox(jitstate, argbox0, ARG0)
    op_args[1] = ll_gvar_from_redbox(jitstate, argbox1, ARG1)
    gvar = rgenop.genop(jitstate.curblock, opdesc.opname, op_args,
                        rgenop.constTYPE(RESULT))
    return REDBOX.ll_make_for_gvar(gvar)

#def ll_generate_operation(jitstate, opname, args, RESULTTYPE):
#    gvar = rgenop.genop(jitstate.curblock, opname, args, RESULTTYPE)
#    return REDBOX.ll_make_for_gvar(gvar)

# ____________________________________________________________
# other jitstate/graph level operations


# XXX dummy for now, no appropriate caching, just call enter_block
def retrieve_jitstate_for_merge(states_dic, jitstate, key, redboxes, TYPES):
    if key not in states_dic:
        jitstate = enter_block(jitstate, redboxes, TYPES)
        states_dic[key] = redboxes[:], jitstate.curblock
        return jitstate

    oldboxes, oldblock = states_dic[key]
    incoming = []
    for i in range(len(redboxes)):
        oldbox = oldboxes[i]
        newbox = redboxes[i]
        if oldbox.isvar: # Allways a match
            # incoming.append(ll_gvar_from_redbox(jitstate, newbox, TYPES[i]))
            # XXX: Cheat with Signed for now
            incoming.append(ll_gvar_from_redbox(jitstate, newbox, lltype.Signed))
            continue
        if (not newbox.isvar and ll_getvalue(oldbox, lltype.Signed) ==
            ll_getvalue(newbox, lltype.Signed)):
            continue
        # Missmatch. Generalize to a var
        break
    else:
        rgenop.closelink(jitstate.curoutgoinglink, incoming, oldblock)
        return lltype.nullptr(STATE)
    
    # Make a more general block
    newblock = rgenop.newblock()
    incoming = []
    for i in range(len(redboxes)):
        oldbox = oldboxes[i]
        newbox = redboxes[i]
        if (newbox.isvar or oldbox.isvar or
            ll_getvalue(oldbox, lltype.Signed) !=
            ll_getvalue(newbox, lltype.Signed)):
            # incoming.append(ll_gvar_from_redbox(jitstate, newbox, TYPES[i]))
            # XXX: Cheat with Signed for now
            incoming.append(ll_gvar_from_redbox(jitstate, newbox, lltype.Signed))
            newgenvar = rgenop.geninputarg(newblock, TYPES[i])
            redboxes[i] = REDBOX.ll_make_for_gvar(newgenvar)

    rgenop.closelink(jitstate.curoutgoinglink, incoming, newblock)
    jitstate.curblock = newblock
    jitstate.curoutgoinglink = lltype.nullptr(rgenop.LINK.TO)
    states_dic[key] = redboxes[:], newblock
    return jitstate
            

retrieve_jitstate_for_merge._annspecialcase_ = "specialize:arglltype(2)"
    
def enter_block(jitstate, redboxes, TYPES):
    newblock = rgenop.newblock()
    incoming = []
    for i in range(len(redboxes)):
        redbox = redboxes[i]
        if redbox.isvar:
            incoming.append(redbox.genvar)
            newgenvar = rgenop.geninputarg(newblock, TYPES[i])
            redboxes[i] = REDBOX.ll_make_for_gvar(newgenvar)
    rgenop.closelink(jitstate.curoutgoinglink, incoming, newblock)
    jitstate.curblock = newblock
    jitstate.curoutgoinglink = lltype.nullptr(rgenop.LINK.TO)
    return jitstate

def leave_block(jitstate):
    jitstate.curoutgoinglink = rgenop.closeblock1(jitstate.curblock)
    return jitstate

def leave_block_split(quejitstate, switchredbox, exitindex, redboxes):
    jitstate = lltype.cast_pointer(STATE_PTR, quejitstate)
    if not switchredbox.isvar:
        jitstate.curoutgoinglink = rgenop.closeblock1(jitstate.curblock)        
        return switchredbox.ll_getvalue(lltype.Bool)
    exitgvar = switchredbox.genvar
    linkpair = rgenop.closeblock2(jitstate.curblock, exitgvar)    
    false_link, true_link = linkpair.item0, linkpair.item1
    later_jitstate = quejitstate.ll_copystate()
    later_jitstate = lltype.cast_pointer(STATE_PTR, later_jitstate)
    jitstate.curoutgoinglink = true_link
    later_jitstate.curoutgoinglink = false_link
    quejitstate.ll_get_split_queue().append((exitindex, later_jitstate, redboxes))
    return True
    

def schedule_return(jitstate, redbox):
    return_queue = jitstate.ll_get_return_queue()
    curoutgoinglink = jitstate.ll_basestate().curoutgoinglink
    return_queue.append((curoutgoinglink, redbox))

novars = lltype.malloc(VARLIST.TO, 0)

def dispatch_next(jitstate, outredboxes):
    basestate = jitstate.ll_basestate()
    split_queue = jitstate.ll_get_split_queue()
    if split_queue:
        exitindex, later_jitstate, redboxes = split_queue.pop()
        basestate.curblock = later_jitstate.curblock
        basestate.curoutgoinglink = later_jitstate.curoutgoinglink
        basestate.curvalue = later_jitstate.curvalue
        for box in redboxes:
            outredboxes.append(box)
        return exitindex
    return_queue = jitstate.ll_get_return_queue()
    basestate = jitstate.ll_basestate()
    first_redbox = return_queue[0][1]
    finalblock = rgenop.newblock()
    basestate.curblock = finalblock
    if not first_redbox.isvar:
        for link, redbox in return_queue:
            if (redbox.isvar or
                redbox.ll_getvalue(lltype.Signed) !=
                first_redbox.ll_getvalue(lltype.Signed)):
                break
        else:
            for link, _ in return_queue:
                rgenop.closelink(link, novars, finalblock)
            finallink = rgenop.closeblock1(finalblock)
            basestate.curoutgoinglink = finallink
            basestate.curvalue = first_redbox
            return -1

    finalvar = rgenop.geninputarg(finalblock,
                                  rgenop.constTYPE(lltype.Signed))
    for link, redbox in return_queue:
        gvar = ll_gvar_from_redbox(jitstate, redbox, lltype.Signed)
        rgenop.closelink(link, [gvar], finalblock)
    finallink = rgenop.closeblock1(finalblock)
    basestate.curoutgoinglink = finallink
    basestate.curvalue = REDBOX.ll_make_for_gvar(finalvar)
    return -1


def ll_setup_jitstate(EXT_STATE_PTR):
    jitstate = EXT_STATE_PTR.TO.ll_newstate()
    jitstate = lltype.cast_pointer(STATE_PTR, jitstate)
    jitstate.curblock = rgenop.newblock()
    return jitstate

def ll_end_setup_jitstate(jitstate):
    jitstate.curoutgoinglink = rgenop.closeblock1(jitstate.curblock)

def ll_close_jitstate(final_jitstate, return_gvar):
    rgenop.closereturnlink(final_jitstate.curoutgoinglink, return_gvar)

def ll_input_redbox(jitstate, TYPE):
    genvar = rgenop.geninputarg(jitstate.curblock,
                                rgenop.constTYPE(TYPE))
    return REDBOX.ll_make_for_gvar(genvar)
