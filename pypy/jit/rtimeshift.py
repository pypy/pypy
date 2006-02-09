from pypy.rpython.lltypesystem import lltype
from pypy.rpython import rgenop


STATE = lltype.GcStruct("jitstate", ("curblock", rgenop.BLOCK))
STATE_PTR = lltype.Ptr(STATE)

REDBOX = lltype.GcStruct("redbox", ("genvar", rgenop.CONSTORVAR))
REDBOX_PTR = lltype.Ptr(REDBOX)

SIGNED_REDBOX = lltype.GcStruct("signed_redbox", 
                                ('basebox', REDBOX),
                                ("value", lltype.Signed))
SIGNED_REDBOX_PTR = lltype.Ptr(SIGNED_REDBOX)


def ll_gvar_from_redbox(jitstate, box):
    if not box.genvar:
        # XXX other ll types!
        # XXX support for polymorphism needs rethinking
        sbox = lltype.cast_pointer(SIGNED_REDBOX_PTR, box)
        box.genvar = ll_gvar_from_const(jitstate, sbox.value)
    return box.genvar

def ll_gvar_from_const(jitstate, value):
    return rgenop.genconst(jitstate.curblock, value)

def ll_generate_operation(jitstate, opname, args, RESULTTYPE):
    gvar = rgenop.genop(jitstate.curblock, opname, args, RESULTTYPE)
    box = lltype.malloc(REDBOX)
    box.genvar = gvar
    return box

def ll_setup_jitstate():
    jitstate = lltype.malloc(STATE)
    jitstate.curblock = rgenop.newblock()
    return jitstate

def ll_close_jitstate(jitstate, return_gvar):
    link = rgenop.closeblock1(jitstate.curblock)
    rgenop.closereturnlink(link, return_gvar)
    return jitstate.curblock

def ll_input_redbox(jitstate, TYPE):
    box = lltype.malloc(REDBOX)
    box.genvar = rgenop.geninputarg(jitstate.curblock, TYPE)
    return box
