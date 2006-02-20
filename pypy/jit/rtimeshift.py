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


class RedBox(object):

    def same_constant(self, other):
        return False


class VarRedBox(RedBox):
    "A red box that contains a run-time variable."

    def __init__(self, genvar):
        self.genvar = genvar

    def getgenvar(self):
        return self.genvar


class ConstRedBox(RedBox):
    "A red box that contains a run-time constant."

    def ll_fromvalue(value):
        T = lltype.typeOf(value)
        if isinstance(T, lltype.Ptr):
            return AddrRedBox(objectmodel.cast_ptr_to_adr(value))
        elif T is lltype.Float:
            return DoubleRedBox(value)
        else:
            assert T is not lltype.Void, "cannot make red boxes of voids"
            # XXX what about long longs?
            return IntRedBox(lltype.cast_primitive(lltype.Signed, value))
    ll_fromvalue = staticmethod(ll_fromvalue)

    def ll_getvalue(self, T):
        # note: this is specialized by low-level type T, as a low-level helper
        if isinstance(T, lltype.Ptr):
            assert isinstance(self, AddrRedBox)
            return objectmodel.cast_adr_to_ptr(self.adrvalue, T)
        elif T is lltype.Float:
            assert isinstance(self, DoubleRedBox)
            return self.dblvalue
        else:
            assert T is not lltype.Void, "no red box contains voids"
            assert isinstance(self, IntRedBox)
            # XXX what about long longs?
            return lltype.cast_primitive(T, self.intvalue)

def ll_getvalue(box, T):
    return box.ll_getvalue(T)
        

class IntRedBox(ConstRedBox):
    "A red box that contains a constant integer-like value."

    def __init__(self, intvalue):
        self.intvalue = intvalue

    def getgenvar(self):
        return rgenop.genconst(self.intvalue)

    def same_constant(self, other):
        return isinstance(other, IntRedBox) and self.intvalue == other.intvalue


class DoubleRedBox(ConstRedBox):
    "A red box that contains a constant double-precision floating point value."

    def __init__(self, dblvalue):
        self.dblvalue = dblvalue

    def getgenvar(self):
        return rgenop.genconst(self.dblvalue)

    def same_constant(self, other):
        return isinstance(other, DoubleRedBox) and self.intvalue == other.dblvalue


class AddrRedBox(ConstRedBox):
    "A red box that contains a constant address."

    def __init__(self, adrvalue):
        self.adrvalue = adrvalue

    def getgenvar(self):
        return rgenop.genconst(self.adrvalue)

    def same_constant(self, other):
        return isinstance(other, AddrRedBox) and self.intvalue == other.adrvalue


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
    if isinstance(argbox, ConstRedBox):
        arg = argbox.ll_getvalue(ARG0)
        res = opdesc.llop(RESULT, arg)
        return ConstRedBox.ll_fromvalue(res)
    op_args = lltype.malloc(VARLIST.TO, 1)
    op_args[0] = argbox.getgenvar()
    genvar = rgenop.genop(jitstate.curblock, opdesc.opname, op_args,
                          rgenop.constTYPE(RESULT))
    return VarRedBox(genvar)

def ll_generate_operation2(opdesc, jitstate, argbox0, argbox1):
    ARG0 = opdesc.ARG0
    ARG1 = opdesc.ARG1
    RESULT = opdesc.RESULT
    opname = opdesc.name
    if isinstance(argbox0, ConstRedBox) and isinstance(argbox1, ConstRedBox):
        # const propagate
        arg0 = argbox0.ll_getvalue(ARG0)
        arg1 = argbox1.ll_getvalue(ARG1)
        res = opdesc.llop(RESULT, arg0, arg1)
        return ConstRedBox.ll_fromvalue(res)
    op_args = lltype.malloc(VARLIST.TO, 2)
    op_args[0] = argbox0.getgenvar()
    op_args[1] = argbox1.getgenvar()
    genvar = rgenop.genop(jitstate.curblock, opdesc.opname, op_args,
                          rgenop.constTYPE(RESULT))
    return VarRedBox(genvar)

# ____________________________________________________________
# other jitstate/graph level operations


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
        if isinstance(oldbox, VarRedBox):  # Always a match
            incoming.append(newbox.getgenvar())
            continue
        if oldbox.same_constant(newbox):
            continue
        # Mismatch. Generalize to a var
        break
    else:
        rgenop.closelink(jitstate.curoutgoinglink, incoming, oldblock)
        return None
    
    # Make a more general block
    newblock = rgenop.newblock()
    incoming = []
    for i in range(len(redboxes)):
        oldbox = oldboxes[i]
        newbox = redboxes[i]
        if not oldbox.same_constant(newbox):
            incoming.append(newbox.getgenvar())
            newgenvar = rgenop.geninputarg(newblock, TYPES[i])
            redboxes[i] = VarRedBox(newgenvar)

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
        if isinstance(redbox, VarRedBox):
            incoming.append(redbox.genvar)
            newgenvar = rgenop.geninputarg(newblock, TYPES[i])
            redboxes[i] = VarRedBox(newgenvar)
    rgenop.closelink(jitstate.curoutgoinglink, incoming, newblock)
    jitstate.curblock = newblock
    jitstate.curoutgoinglink = lltype.nullptr(rgenop.LINK.TO)
    return jitstate

def leave_block(jitstate):
    jitstate.curoutgoinglink = rgenop.closeblock1(jitstate.curblock)
    return jitstate

def leave_block_split(jitstate, switchredbox, exitindex, redboxes):
    if isinstance(switchredbox, IntRedBox):
        jitstate.curoutgoinglink = rgenop.closeblock1(jitstate.curblock)        
        return bool(switchredbox.intvalue)
    else:
        exitgvar = switchredbox.getgenvar()
        linkpair = rgenop.closeblock2(jitstate.curblock, exitgvar)    
        false_link, true_link = linkpair.item0, linkpair.item1
        later_jitstate = jitstate.copystate()
        jitstate.curoutgoinglink = true_link
        later_jitstate.curoutgoinglink = false_link
        jitstate.split_queue.append((exitindex, later_jitstate, redboxes))
        return True

def schedule_return(jitstate, redbox):
    jitstate.return_queue.append((jitstate.curoutgoinglink, redbox))

novars = lltype.malloc(VARLIST.TO, 0)

def dispatch_next(jitstate, outredboxes, RETURN_TYPE):
    split_queue = jitstate.split_queue
    if split_queue:
        exitindex, later_jitstate, redboxes = split_queue.pop()
        jitstate.curblock = later_jitstate.curblock
        jitstate.curoutgoinglink = later_jitstate.curoutgoinglink
        jitstate.curvalue = later_jitstate.curvalue
        for box in redboxes:
            outredboxes.append(box)
        return exitindex
    return_queue = jitstate.return_queue
    first_redbox = return_queue[0][1]
    finalblock = rgenop.newblock()
    jitstate.curblock = finalblock
    if isinstance(first_redbox, ConstRedBox):
        for link, redbox in return_queue:
            if not redbox.same_constant(first_redbox):
                break
        else:
            for link, _ in return_queue:
                rgenop.closelink(link, novars, finalblock)
            finallink = rgenop.closeblock1(finalblock)
            jitstate.curoutgoinglink = finallink
            jitstate.curvalue = first_redbox
            return -1

    finalvar = rgenop.geninputarg(finalblock, RETURN_TYPE)
    for link, redbox in return_queue:
        genvar = redbox.getgenvar()
        rgenop.closelink(link, [genvar], finalblock)
    finallink = rgenop.closeblock1(finalblock)
    jitstate.curoutgoinglink = finallink
    jitstate.curvalue = VarRedBox(finalvar)
    return -1

def ll_gvar_from_redbox(redbox):
    return redbox.getgenvar()

def ll_gvar_from_constant(ll_value):
    return rgenop.genconst(ll_value)

# ____________________________________________________________

class JITState(object):
    # XXX obscure interface

    def setup(self):
        self.return_queue = []
        self.split_queue = []
        self.curblock = rgenop.newblock()
        self.curvalue = None

    def end_setup(self):
        self.curoutgoinglink = rgenop.closeblock1(self.curblock)

    def close(self, return_gvar):
        rgenop.closereturnlink(self.curoutgoinglink, return_gvar)

    def copystate(self):
        other = JITState()
        other.return_queue = self.return_queue
        other.split_queue = self.split_queue
        other.curblock = self.curblock
        other.curoutgoinglink = self.curoutgoinglink
        other.curvalue = self.curvalue
        return other

def ll_build_jitstate():
    jitstate = JITState()
    jitstate.setup()
    return jitstate

def ll_signed_box(jitstate, value):
    value = lltype.cast_primitive(lltype.Signed, value)
    return ConstRedBox.ll_fromvalue(value)

def ll_var_box(jitstate, gv_TYPE):
    genvar = rgenop.geninputarg(jitstate.curblock, gv_TYPE)
    return VarRedBox(genvar)
    
def ll_end_setup_jitstate(jitstate):
    jitstate.end_setup()
    return jitstate.curblock

def ll_close_jitstate(jitstate):
    result_genvar = jitstate.curvalue.getgenvar()
    jitstate.close(result_genvar)
