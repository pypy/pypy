from pypy.jit.backend.ppc.ppc_assembler import PPCAssembler
from pypy.jit.backend.ppc.symbol_lookup import lookup
from pypy.jit.backend.ppc.regname import *

def load_arg(code, argi, typecode):
    rD = r3+argi
    code.lwz(rD, r4, 12 + 4*argi)
    if typecode == 'i':
        code.load_word(r0, lookup("PyInt_Type"))
        code.lwz(r31, rD, 4) # XXX ick!
        code.cmpw(r0, r31)
        code.bne("argserror")
        code.lwz(rD, rD, 8)
    elif typecode == 'f':
        code.load_word(r0, lookup("PyFloat_Type"))
        code.lwz(r31, rD, 4)
        code.cmpw(r0, r31)
        code.bne("argserror")
        code.lfd(rD-2, rD, 8)
    elif typecode != "O":
        raise Exception, "erk"

FAST_ENTRY_LABEL = "FAST-ENTRY-LABEL"

def make_func(code, retcode, signature, localwords=0):
    """code shouldn't contain prologue/epilogue (or touch r31)"""

    stacksize = 80 + 4*localwords

    argcount = len(signature)

    ourcode = MyPPCAssembler()
    ourcode.mflr(r0)
    ourcode.stmw(r31, r1, -4)
    ourcode.stw(r0, r1, 8)
    ourcode.stwu(r1, r1, -stacksize)

    ourcode.lwz(r3, r4, 8)
    ourcode.cmpwi(r3, argcount)
    ourcode.bne("argserror")

    assert argcount < 9

    if argcount > 0:
        load_arg(ourcode, 0, signature[0])
    for i in range(2, argcount):
        load_arg(ourcode, i, signature[i])
    if argcount > 1:
        load_arg(ourcode, 1, signature[1])

    ourcode.bl(FAST_ENTRY_LABEL)

    if retcode == 'i':
        s = lookup("PyInt_FromLong")
        ourcode.load_word(r0, s)
        ourcode.mtctr(r0)
        ourcode.bctrl()
    elif retcode == 'f':
        s = lookup("PyFloat_FromDouble")
        ourcode.load_word(r0, s)
        ourcode.mtctr(r0)
        ourcode.bctrl()

    ourcode.label("epilogue")
    ourcode.lwz(r0, r1, stacksize + 8)
    ourcode.addi(r1, r1, stacksize)
    ourcode.mtlr(r0)
    ourcode.lmw(r31, r1, -4)
    ourcode.blr()

    err_set = lookup("PyErr_SetObject")
    exc = lookup("PyExc_TypeError")

    ourcode.label("argserror")
    ourcode.load_word(r5, err_set)
    ourcode.mtctr(r5)
    ourcode.load_from(r3, exc)
    ourcode.mr(r4, r3)
    ourcode.bctrl()

    ourcode.li(r3, 0)
    ourcode.b("epilogue")

    ourcode.label(FAST_ENTRY_LABEL)
    # err, should be an Assembler method:
    l = {}
    for k in code.labels:
        l[k] = code.labels[k] + 4*len(ourcode.insts)
    r = code.rlabels.copy()
    for k in code.rlabels:
        r[k + 4*len(ourcode.insts)] = code.rlabels[k]
    ourcode.insts.extend(code.insts)
    ourcode.labels.update(l)
    ourcode.rlabels.update(r)

    r = ourcode.assemble()
    r.FAST_ENTRY_LABEL = ourcode.labels[FAST_ENTRY_LABEL]
    return r

def wrap(funcname, retcode, signature):

    argcount = len(signature)

    ourcode = MyPPCAssembler()
    ourcode.mflr(r0)
    ourcode.stmw(r31, r1, -4)
    ourcode.stw(r0, r1, 8)
    ourcode.stwu(r1, r1, -80)

    ourcode.lwz(r3, r4, 8)
    ourcode.cmpwi(r3, argcount)
    ourcode.bne("argserror")

    assert argcount < 9

    if argcount > 0:
        load_arg(ourcode, 0, signature[0])
    for i in range(2, argcount):
        load_arg(ourcode, i, signature[i])
    if argcount > 1:
        load_arg(ourcode, 1, signature[1])


    ourcode.load_word(r0, lookup(funcname))
    ourcode.mtctr(r0)
    ourcode.bctrl()

    if retcode == 'i':
        s = lookup("PyInt_FromLong")
        ourcode.load_word(r0, s)
        ourcode.mtctr(r0)
        ourcode.bctrl()
    elif retcode == 'f':
        s = lookup("PyFloat_FromDouble")
        ourcode.load_word(r0, s)
        ourcode.mtctr(r0)
        ourcode.bctrl()

    ourcode.label("epilogue")
    ourcode.lwz(r0, r1, 88)
    ourcode.addi(r1, r1, 80)
    ourcode.mtlr(r0)
    ourcode.lmw(r31, r1, -4)
    ourcode.blr()

    err_set = lookup("PyErr_SetObject")
    exc = lookup("PyExc_TypeError")

    ourcode.label("argserror")
    ourcode.load_word(r5, err_set)
    ourcode.mtctr(r5)
    ourcode.load_from(r3, exc)
    ourcode.mr(r4, r3)
    ourcode.bctrl()

    ourcode.li(r3, 0)
    ourcode.b("epilogue")

    return ourcode.assemble()

