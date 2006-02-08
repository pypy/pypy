from pypy.rpython.lltypesystem import lltype
from pypy.rpython import rgenop


STATE = lltype.GcStruct("jitstate", ("curblock", rgenop.BLOCK))
STATE_PTR = lltype.Ptr(STATE)

REDBOX = lltype.GcStruct("redbox", ("genvar", rgenop.CONSTORVAR))
REDBOX_PTR = lltype.Ptr(REDBOX)


def ll_gvar_from_redbox(jitstate, box):
    return box.genvar

def ll_gvar_from_const(jitstate, value):
    return rgenop.genconst(jitstate.curblock, value)

def ll_generate_operation(jitstate, opname, args, RESULTTYPE):
    gvar = rgenop.genop(jitstate.curblock, opname, args, RESULTTYPE)
    box = lltype.malloc(REDBOX)
    box.genvar = gvar
    return box
