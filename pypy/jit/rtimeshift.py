from pypy.rpython.lltypesystem import lltype
from pypy.rpython import objectmodel
from pypy.rpython import rgenop

# ____________________________________________________________
# types and adts

def ll_fixed_items(l):
    return l

VARLIST = lltype.Ptr(lltype.GcArray(rgenop.CONSTORVAR,
                                    adtmeths = {
                                        "ll_items": ll_fixed_items,
                                    }))

STATE = lltype.GcStruct("jitstate", ("curblock", rgenop.BLOCK))
STATE_PTR = lltype.Ptr(STATE)


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
    gvar = rgenop.genop(jitstate.curblock, opdesc.opname, op_args, RESULT)
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
    gvar = rgenop.genop(jitstate.curblock, opdesc.opname, op_args, RESULT)
    return REDBOX.ll_make_for_gvar(gvar)

#def ll_generate_operation(jitstate, opname, args, RESULTTYPE):
#    gvar = rgenop.genop(jitstate.curblock, opname, args, RESULTTYPE)
#    return REDBOX.ll_make_for_gvar(gvar)

# ____________________________________________________________
# other jitstate/graph level operations


# XXX dummy for now, playing with mix level annotation
def retrieve_jitstate_for_merge(states_dic, jitstate, key, redboxes):
    # modifies redbox in place
    states_dic[key] = redboxes
    # fun playing junk
    if not redboxes[0].isvar and redboxes[0].ll_getvalue(lltype.Signed) == 0:
        redboxes[0] = redboxes[0]
    return jitstate # XXX
retrieve_jitstate_for_merge._annspecialcase_ = "specialize:arglltype2"
    

def ll_setup_jitstate():
    jitstate = lltype.malloc(STATE)
    jitstate.curblock = rgenop.newblock()
    return jitstate

def ll_close_jitstate(jitstate, return_gvar):
    link = rgenop.closeblock1(jitstate.curblock)
    rgenop.closereturnlink(link, return_gvar)
    return jitstate.curblock

def ll_input_redbox(jitstate, TYPE):
    genvar = rgenop.geninputarg(jitstate.curblock, TYPE)
    return REDBOX.ll_make_for_gvar(genvar)
