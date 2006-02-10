from pypy.rpython.lltypesystem import lltype
from pypy.rpython import rgenop


STATE = lltype.GcStruct("jitstate", ("curblock", rgenop.BLOCK))
STATE_PTR = lltype.Ptr(STATE)


def make_for_gvar(gvar):
    box = lltype.malloc(REDBOX)
    box.isvar = True
    box.genvar = gvar
    return box

def make_from_const(value):
    sbox = lltype.malloc(REDBOX_FOR_SIGNED) # XXX Float, Ptr
    sbox.value = lltype.cast_primitive(lltype.Signed, value)
    box = lltype.cast_pointer(REDBOX_PTR, sbox)
    box.genvar = lltype.nullptr(REDBOX.genvar.TO)
    return box

def getvalue(box, T):
    sbox = lltype.cast_pointer(REDBOX_FOR_SIGNED_PTR, box)
    return lltype.cast_primitive(T, sbox.value)

REDBOX = lltype.GcStruct("redbox", ("genvar", rgenop.CONSTORVAR),
                                   ("isvar", lltype.Bool),
                         adtmeths = {
    'make_for_gvar': make_for_gvar,
    'make_from_const': make_from_const,
    'getvalue': getvalue,
    })

REDBOX_PTR = lltype.Ptr(REDBOX)

REDBOX_FOR_SIGNED = lltype.GcStruct("signed_redbox", 
                                    ('basebox', REDBOX),
                                    ("value", lltype.Signed))
REDBOX_FOR_SIGNED_PTR = lltype.Ptr(REDBOX_FOR_SIGNED)



def ll_gvar_from_redbox(jitstate, box, TYPE):
    if not box.genvar:
        value = box.getvalue(TYPE)
        box.genvar = ll_gvar_from_const(jitstate, value)
    return box.genvar

def ll_gvar_from_const(jitstate, value):
    return rgenop.genconst(value)

def ll_generate_operation(jitstate, opname, args, RESULTTYPE):
    gvar = rgenop.genop(jitstate.curblock, opname, args, RESULTTYPE)
    return REDBOX.make_for_gvar(gvar)

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
    return REDBOX.make_for_gvar(genvar)
