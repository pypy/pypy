import os
import struct
from pypy.jit.backend.ppc.ppcgen.ppc_form import PPCForm as Form
from pypy.jit.backend.ppc.ppcgen.ppc_field import ppc_fields
from pypy.jit.backend.ppc.ppcgen.regalloc import (TempInt, PPCFrameManager,
                                                  Regalloc)
from pypy.jit.backend.ppc.ppcgen.assembler import Assembler
from pypy.jit.backend.ppc.ppcgen.symbol_lookup import lookup
from pypy.jit.backend.ppc.ppcgen.arch import (IS_PPC_32, WORD, NONVOLATILES,
                                              GPR_SAVE_AREA, IS_PPC_64)
from pypy.jit.backend.ppc.ppcgen.helper.assembler import gen_emit_cmp_op
import pypy.jit.backend.ppc.ppcgen.register as r
import pypy.jit.backend.ppc.ppcgen.condition as c
from pypy.jit.metainterp.history import (Const, ConstPtr, JitCellToken, 
                                         TargetToken, AbstractFailDescr)
from pypy.jit.backend.llsupport.asmmemmgr import (BlockBuilderMixin, AsmMemoryManager, MachineDataBlockWrapper)
from pypy.jit.backend.llsupport.regalloc import (RegisterManager, 
                                                 compute_vars_longevity)
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.model import CompiledLoopToken
from pypy.rpython.lltypesystem import lltype, rffi, rstr, llmemory
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import (BoxInt, ConstInt, ConstPtr,
                                         ConstFloat, Box, INT, REF, FLOAT)
from pypy.jit.backend.x86.support import values_array
from pypy.tool.udir import udir
from pypy.rlib.objectmodel import we_are_translated

from pypy.translator.tool.cbuild import ExternalCompilationInfo

A = Form("frD", "frA", "frB", "XO3", "Rc")
A1 = Form("frD", "frB", "XO3", "Rc")
A2 = Form("frD", "frA", "frC", "XO3", "Rc")
A3 = Form("frD", "frA", "frC", "frB", "XO3", "Rc")

I = Form("LI", "AA", "LK")

B = Form("BO", "BI", "BD", "AA", "LK")

SC = Form("AA") # fudge

DD = Form("rD", "rA", "SIMM")
DDO = Form("rD", "rA", "ds", "XO4")
DS = Form("rA", "rS", "UIMM")

X = Form("XO1")
XS = Form("rA", "rS", "rB", "XO1", "Rc")
XSO = Form("rS", "rA", "rB", "XO1")
XD = Form("rD", "rA", "rB", "XO1")
XO = Form("rD", "rA", "rB", "OE", "XO2", "Rc")
XO0 = Form("rD", "rA", "OE", "XO2", "Rc")
XDB = Form("frD", "frB", "XO1", "Rc")
XS0 = Form("rA", "rS", "XO1", "Rc")
X0 = Form("rA", "rB", "XO1")
XcAB = Form("crfD", "rA", "rB", "XO1")
XN = Form("rD", "rA", "NB", "XO1")
XL = Form("crbD", "crbA", "crbB", "XO1")
XL1 = Form("crfD", "crfS")
XL2 = Form("crbD", "XO1", "Rc")
XFL = Form("FM", "frB", "XO1", "Rc")
XFX = Form("CRM", "rS", "XO1")

MI = Form("rA", "rS", "SH", "MB", "ME", "Rc")
MB = Form("rA", "rS", "rB", "MB", "ME", "Rc")
MDI = Form("rA", "rS", "sh", "mbe", "XO5", "Rc")
MDS = Form("rA", "rS", "rB", "mbe", "XO7", "Rc")

class BasicPPCAssembler(Assembler):

    def disassemble(cls, inst, labels={}, pc=0):
        cache = cls.__dict__.get('idesc cache')
        if cache is None:
            idescs = cls.get_idescs()
            cache = {}
            for n, i in idescs:
                cache.setdefault(i.specializations[ppc_fields['opcode']],
                                 []).append((n,i))
            setattr(cls, 'idesc cache', cache)
        matches = []
        idescs = cache[ppc_fields['opcode'].decode(inst)]
        for name, idesc in idescs:
            m = idesc.match(inst)
            if m > 0:
                matches.append((m, idesc, name))
        if matches:
            score, idesc, name = max(matches)
            return idesc.disassemble(name, inst, labels, pc)
    disassemble = classmethod(disassemble)

    # "basic" means no simplified mnemonics

    # I form
    b   = I(18, AA=0, LK=0)
    ba  = I(18, AA=1, LK=0)
    bl  = I(18, AA=0, LK=1)
    bla = I(18, AA=1, LK=1)

    # B form
    bc   = B(16, AA=0, LK=0)
    bcl  = B(16, AA=0, LK=1)
    bca  = B(16, AA=1, LK=0)
    bcla = B(16, AA=1, LK=1)

    # SC form
    sc = SC(17, AA=1) # it's not really the aa field...

    # D form
    addi   = DD(14)
    addic  = DD(12)
    addicx = DD(13)
    addis  = DD(15)

    andix  = DS(28)
    andisx = DS(29)

    cmpi  = Form("crfD", "L", "rA", "SIMM")(11)
    cmpi.default(L=0).default(crfD=0)
    cmpli = Form("crfD", "L", "rA", "UIMM")(10)
    cmpli.default(L=0).default(crfD=0)

    lbz  = DD(34)
    lbzu = DD(35)
    ld   = DDO(58, XO4=0)
    ldu  = DDO(58, XO4=1)
    lfd  = DD(50)
    lfdu = DD(51)
    lfs  = DD(48)
    lfsu = DD(49)
    lha  = DD(42)
    lhau = DD(43)
    lhz  = DD(40)
    lhzu = DD(41)
    lmw  = DD(46)
    lwa  = DDO(58, XO4=2)
    lwz  = DD(32)
    lwzu = DD(33)

    mulli = DD(7)
    ori   = DS(24)
    oris  = DS(25)

    stb   = DD(38)
    stbu  = DD(39)
    std   = DDO(62, XO4=0)
    stdu  = DDO(62, XO4=1)
    stfd  = DD(54)
    stfdu = DD(55)
    stfs  = DD(52)
    stfsu = DD(53)
    sth   = DD(44)
    sthu  = DD(45)
    stmw  = DD(47)
    stw   = DD(36)
    stwu  = DD(37)

    subfic = DD(8)
    tdi    = Form("TO", "rA", "SIMM")(2)
    twi    = Form("TO", "rA", "SIMM")(3)
    xori   = DS(26)
    xoris  = DS(27)

    # X form

    and_  = XS(31, XO1=28, Rc=0)
    and_x = XS(31, XO1=28, Rc=1)

    andc_  = XS(31, XO1=60, Rc=0)
    andc_x = XS(31, XO1=60, Rc=1)

    # is the L bit for 64 bit compares? hmm
    cmp  = Form("crfD", "L", "rA", "rB", "XO1")(31, XO1=0)
    cmp.default(L=0).default(crfD=0)
    cmpl = Form("crfD", "L", "rA", "rB", "XO1")(31, XO1=32)
    cmpl.default(L=0).default(crfD=0)

    cntlzd  = XS0(31, XO1=58, Rc=0)
    cntlzdx = XS0(31, XO1=58, Rc=1)
    cntlzw  = XS0(31, XO1=26, Rc=0)
    cntlzwx = XS0(31, XO1=26, Rc=1)

    dcba   = X0(31, XO1=758)
    dcbf   = X0(31, XO1=86)
    dcbi   = X0(31, XO1=470)
    dcbst  = X0(31, XO1=54)
    dcbt   = X0(31, XO1=278)
    dcbtst = X0(31, XO1=246)
    dcbz   = X0(31, XO1=1014)

    eciwx = XD(31, XO1=310)
    ecowx = XS(31, XO1=438, Rc=0)

    eieio = X(31, XO1=854)

    eqv  = XS(31, XO1=284, Rc=0)
    eqvx = XS(31, XO1=284, Rc=1)

    extsb  = XS0(31, XO1=954, Rc=0)
    extsbx = XS0(31, XO1=954, Rc=1)

    extsh  = XS0(31, XO1=922, Rc=0)
    extshx = XS0(31, XO1=922, Rc=1)

    extsw  = XS0(31, XO1=986, Rc=0)
    extswx = XS0(31, XO1=986, Rc=1)

    fabs  = XDB(63, XO1=264, Rc=0)
    fabsx = XDB(63, XO1=264, Rc=1)

    fcmpo = XcAB(63, XO1=32)
    fcmpu = XcAB(63, XO1=0)

    fcfid  = XDB(63, XO1=846, Rc=0)
    fcfidx = XDB(63, XO1=846, Rc=1)

    fctid  = XDB(63, XO1=814, Rc=0)
    fctidx = XDB(63, XO1=814, Rc=1)

    fctidz  = XDB(63, XO1=815, Rc=0)
    fctidzx = XDB(63, XO1=815, Rc=1)

    fctiw  = XDB(63, XO1=14, Rc=0)
    fctiwx = XDB(63, XO1=14, Rc=1)

    fctiwz  = XDB(63, XO1=15, Rc=0)
    fctiwzx = XDB(63, XO1=15, Rc=1)

    fmr  = XDB(63, XO1=72, Rc=0)
    fmrx = XDB(63, XO1=72, Rc=1)

    fnabs  = XDB(63, XO1=136, Rc=0)
    fnabsx = XDB(63, XO1=136, Rc=1)

    fneg  = XDB(63, XO1=40, Rc=0)
    fnegx = XDB(63, XO1=40, Rc=1)

    frsp  = XDB(63, XO1=12, Rc=0)
    frspx = XDB(63, XO1=12, Rc=1)

    fsqrt = XDB(63, XO1=22, Rc=0)

    icbi = X0(31, XO1=982)

    lbzux = XD(31, XO1=119)
    lbzx  = XD(31, XO1=87)
    ldarx = XD(31, XO1=84)
    ldux  = XD(31, XO1=53)
    ldx   = XD(31, XO1=21)
    lfdux = XD(31, XO1=631)
    lfdx  = XD(31, XO1=599)
    lfsux = XD(31, XO1=567)
    lfsx  = XD(31, XO1=535)
    lhaux = XD(31, XO1=375)
    lhax  = XD(31, XO1=343)
    lhbrx = XD(31, XO1=790)
    lhzux = XD(31, XO1=311)
    lhzx  = XD(31, XO1=279)
    lswi  = XD(31, XO1=597)
    lswx  = XD(31, XO1=533)
    lwarx = XD(31, XO1=20)
    lwaux = XD(31, XO1=373)
    lwax  = XD(31, XO1=341)
    lwbrx = XD(31, XO1=534)
    lwzux = XD(31, XO1=55)
    lwzx  = XD(31, XO1=23)

    mcrfs  = Form("crfD", "crfS", "XO1")(63, XO1=64)
    mcrxr  = Form("crfD", "XO1")(31, XO1=512)
    mfcr   = Form("rD", "XO1")(31, XO1=19)
    mffs   = Form("frD", "XO1", "Rc")(63, XO1=583, Rc=0)
    mffsx  = Form("frD", "XO1", "Rc")(63, XO1=583, Rc=1)
    mfmsr  = Form("rD", "XO1")(31, XO1=83)
    mfsr   = Form("rD", "SR", "XO1")(31, XO1=595)
    mfsrin = XDB(31, XO1=659, Rc=0)

    add   = XO(31, XO2=266, OE=0, Rc=0)
    addx  = XO(31, XO2=266, OE=0, Rc=1)
    addo  = XO(31, XO2=266, OE=1, Rc=0)
    addox = XO(31, XO2=266, OE=1, Rc=1)

    addc   = XO(31, XO2=10, OE=0, Rc=0)
    addcx  = XO(31, XO2=10, OE=0, Rc=1)
    addco  = XO(31, XO2=10, OE=1, Rc=0)
    addcox = XO(31, XO2=10, OE=1, Rc=1)

    adde   = XO(31, XO2=138, OE=0, Rc=0)
    addex  = XO(31, XO2=138, OE=0, Rc=1)
    addeo  = XO(31, XO2=138, OE=1, Rc=0)
    addeox = XO(31, XO2=138, OE=1, Rc=1)

    addme   = XO(31, rB=0, XO2=234, OE=0, Rc=0)
    addmex  = XO(31, rB=0, XO2=234, OE=0, Rc=1)
    addmeo  = XO(31, rB=0, XO2=234, OE=1, Rc=0)
    addmeox = XO(31, rB=0, XO2=234, OE=1, Rc=1)

    addze   = XO(31, rB=0, XO2=202, OE=0, Rc=0)
    addzex  = XO(31, rB=0, XO2=202, OE=0, Rc=1)
    addzeo  = XO(31, rB=0, XO2=202, OE=1, Rc=0)
    addzeox = XO(31, rB=0, XO2=202, OE=1, Rc=1)

    bcctr  = Form("BO", "BI", "XO1", "LK")(19, XO1=528, LK=0)
    bcctrl = Form("BO", "BI", "XO1", "LK")(19, XO1=528, LK=1)

    bclr  = Form("BO", "BI", "XO1", "LK")(19, XO1=16, LK=0)
    bclrl = Form("BO", "BI", "XO1", "LK")(19, XO1=16, LK=1)

    crand  = XL(19, XO1=257)
    crandc = XL(19, XO1=129)
    creqv  = XL(19, XO1=289)
    crnand = XL(19, XO1=225)
    crnor  = XL(19, XO1=33)
    cror   = XL(19, XO1=449)
    crorc  = XL(19, XO1=417)
    crxor  = XL(19, XO1=193)

    divd    = XO(31, XO2=489, OE=0, Rc=0)
    divdx   = XO(31, XO2=489, OE=0, Rc=1)
    divdo   = XO(31, XO2=489, OE=1, Rc=0)
    divdox  = XO(31, XO2=489, OE=1, Rc=1)

    divdu   = XO(31, XO2=457, OE=0, Rc=0)
    divdux  = XO(31, XO2=457, OE=0, Rc=1)
    divduo  = XO(31, XO2=457, OE=1, Rc=0)
    divduox = XO(31, XO2=457, OE=1, Rc=1)

    divw    = XO(31, XO2=491, OE=0, Rc=0)
    divwx   = XO(31, XO2=491, OE=0, Rc=1)
    divwo   = XO(31, XO2=491, OE=1, Rc=0)
    divwox  = XO(31, XO2=491, OE=1, Rc=1)

    divwu   = XO(31, XO2=459, OE=0, Rc=0)
    divwux  = XO(31, XO2=459, OE=0, Rc=1)
    divwuo  = XO(31, XO2=459, OE=1, Rc=0)
    divwuox = XO(31, XO2=459, OE=1, Rc=1)

    fadd   = A(63, XO3=21, Rc=0)
    faddx  = A(63, XO3=21, Rc=1)
    fadds  = A(59, XO3=21, Rc=0)
    faddsx = A(59, XO3=21, Rc=1)

    fdiv   = A(63, XO3=18, Rc=0)
    fdivx  = A(63, XO3=18, Rc=1)
    fdivs  = A(59, XO3=18, Rc=0)
    fdivsx = A(59, XO3=18, Rc=1)

    fmadd   = A3(63, XO3=19, Rc=0)
    fmaddx  = A3(63, XO3=19, Rc=1)
    fmadds  = A3(59, XO3=19, Rc=0)
    fmaddsx = A3(59, XO3=19, Rc=1)

    fmsub   = A3(63, XO3=28, Rc=0)
    fmsubx  = A3(63, XO3=28, Rc=1)
    fmsubs  = A3(59, XO3=28, Rc=0)
    fmsubsx = A3(59, XO3=28, Rc=1)

    fmul   = A2(63, XO3=25, Rc=0)
    fmulx  = A2(63, XO3=25, Rc=1)
    fmuls  = A2(59, XO3=25, Rc=0)
    fmulsx = A2(59, XO3=25, Rc=1)

    fnmadd   = A3(63, XO3=31, Rc=0)
    fnmaddx  = A3(63, XO3=31, Rc=1)
    fnmadds  = A3(59, XO3=31, Rc=0)
    fnmaddsx = A3(59, XO3=31, Rc=1)

    fnmsub   = A3(63, XO3=30, Rc=0)
    fnmsubx  = A3(63, XO3=30, Rc=1)
    fnmsubs  = A3(59, XO3=30, Rc=0)
    fnmsubsx = A3(59, XO3=30, Rc=1)

    fres     = A1(59, XO3=24, Rc=0)
    fresx    = A1(59, XO3=24, Rc=1)

    frsp     = A1(63, XO3=12, Rc=0)
    frspx    = A1(63, XO3=12, Rc=1)

    frsqrte  = A1(63, XO3=26, Rc=0)
    frsqrtex = A1(63, XO3=26, Rc=1)

    fsel     = A3(63, XO3=23, Rc=0)
    fselx    = A3(63, XO3=23, Rc=1)

    frsqrt   = A1(63, XO3=22, Rc=0)
    frsqrtx  = A1(63, XO3=22, Rc=1)
    frsqrts  = A1(59, XO3=22, Rc=0)
    frsqrtsx = A1(59, XO3=22, Rc=1)

    fsub   = A(63, XO3=20, Rc=0)
    fsubx  = A(63, XO3=20, Rc=1)
    fsubs  = A(59, XO3=20, Rc=0)
    fsubsx = A(59, XO3=20, Rc=1)

    isync = X(19, XO1=150)

    mcrf = XL1(19)

    mfspr = Form("rD", "spr", "XO1")(31, XO1=339)
    mftb  = Form("rD", "spr", "XO1")(31, XO1=371)

    mtcrf = XFX(31, XO1=144)

    mtfsb0  = XL2(63, XO1=70, Rc=0)
    mtfsb0x = XL2(63, XO1=70, Rc=1)
    mtfsb1  = XL2(63, XO1=38, Rc=0)
    mtfsb1x = XL2(63, XO1=38, Rc=1)

    mtfsf   = XFL(63, XO1=711, Rc=0)
    mtfsfx  = XFL(63, XO1=711, Rc=1)

    mtfsfi  = Form("crfD", "IMM", "XO1", "Rc")(63, XO1=134, Rc=0)
    mtfsfix = Form("crfD", "IMM", "XO1", "Rc")(63, XO1=134, Rc=1)

    mtmsr = Form("rS", "XO1")(31, XO1=146)

    mtspr = Form("rS", "spr", "XO1")(31, XO1=467)

    mtsr   = Form("rS", "SR", "XO1")(31, XO1=210)
    mtsrin = Form("rS", "rB", "XO1")(31, XO1=242)

    mulhd   = XO(31, OE=0, XO2=73, Rc=0)
    mulhdx  = XO(31, OE=0, XO2=73, Rc=1)

    mulhdu  = XO(31, OE=0, XO2=9, Rc=0)
    mulhdux = XO(31, OE=0, XO2=9, Rc=1)

    mulld   = XO(31, OE=0, XO2=233, Rc=0)
    mulldx  = XO(31, OE=0, XO2=233, Rc=1)
    mulldo  = XO(31, OE=1, XO2=233, Rc=0)
    mulldox = XO(31, OE=1, XO2=233, Rc=1)

    mulhw   = XO(31, OE=0, XO2=75, Rc=0)
    mulhwx  = XO(31, OE=0, XO2=75, Rc=1)

    mulhwu  = XO(31, OE=0, XO2=11, Rc=0)
    mulhwux = XO(31, OE=0, XO2=11, Rc=1)

    mullw   = XO(31, OE=0, XO2=235, Rc=0)
    mullwx  = XO(31, OE=0, XO2=235, Rc=1)
    mullwo  = XO(31, OE=1, XO2=235, Rc=0)
    mullwox = XO(31, OE=1, XO2=235, Rc=1)

    nand  = XS(31, XO1=476, Rc=0)
    nandx = XS(31, XO1=476, Rc=1)

    neg   = XO0(31, OE=0, XO2=104, Rc=0)
    negx  = XO0(31, OE=0, XO2=104, Rc=1)
    nego  = XO0(31, OE=1, XO2=104, Rc=0)
    negox = XO0(31, OE=1, XO2=104, Rc=1)

    nor   = XS(31, XO1=124, Rc=0)
    norx  = XS(31, XO1=124, Rc=1)

    or_   = XS(31, XO1=444, Rc=0)
    or_x  = XS(31, XO1=444, Rc=1)

    orc   = XS(31, XO1=412, Rc=0)
    orcx  = XS(31, XO1=412, Rc=1)

    rfi   = X(19, XO1=50)

    rfid  = X(19, XO1=18)

    rldcl   = MDS(30, XO7=8, Rc=0)
    rldclx  = MDS(30, XO7=8, Rc=1)
    rldcr   = MDS(30, XO7=9, Rc=0)
    rldcrx  = MDS(30, XO7=9, Rc=1)

    rldic   = MDI(30, XO5=2, Rc=0)
    rldicx  = MDI(30, XO5=2, Rc=1)
    rldicl  = MDI(30, XO5=0, Rc=0)
    rldiclx = MDI(30, XO5=0, Rc=1)
    rldicr  = MDI(30, XO5=1, Rc=0)
    rldicrx = MDI(30, XO5=1, Rc=1)
    rldimi  = MDI(30, XO5=3, Rc=0)
    rldimix = MDI(30, XO5=3, Rc=1)

    rlwimi  = MI(20, Rc=0)
    rlwimix = MI(20, Rc=1)

    rlwinm  = MI(21, Rc=0)
    rlwinmx = MI(21, Rc=1)

    rlwnm   = MB(23, Rc=0)
    rlwnmx  = MB(23, Rc=1)

    sld     = XS(31, XO1=27, Rc=0)
    sldx    = XS(31, XO1=27, Rc=1)

    slw     = XS(31, XO1=24, Rc=0)
    slwx    = XS(31, XO1=24, Rc=1)

    srad    = XS(31, XO1=794, Rc=0)
    sradx   = XS(31, XO1=794, Rc=1)

    sradi   = Form("rA", "rS", "SH", "XO6", "sh", "Rc")(31, XO6=413, Rc=0)
    sradix  = Form("rA", "rS", "SH", "XO6", "sh", "Rc")(31, XO6=413, Rc=1)

    sraw    = XS(31, XO1=792, Rc=0)
    srawx   = XS(31, XO1=792, Rc=1)

    srawi   = Form("rA", "rS", "SH", "XO1", "Rc")(31, XO1=824, Rc=0)
    srawix  = Form("rA", "rS", "SH", "XO1", "Rc")(31, XO1=824, Rc=1)

    srd     = XS(31, XO1=539, Rc=0)
    srdx    = XS(31, XO1=539, Rc=1)

    srw     = XS(31, XO1=536, Rc=0)
    srwx    = XS(31, XO1=536, Rc=1)

    stbux   = XSO(31, XO1=247)
    stbx    = XSO(31, XO1=215)
    stdcxx  = Form("rS", "rA", "rB", "XO1", "Rc")(31, XO1=214, Rc=1)
    stdux   = XSO(31, XO1=181)
    stdx    = XSO(31, XO1=149)
    stfdux  = XSO(31, XO1=759)
    stfdx   = XSO(31, XO1=727)
    stfiwx  = XSO(31, XO1=983)
    stfsux  = XSO(31, XO1=695)
    stfsx   = XSO(31, XO1=663)
    sthbrx  = XSO(31, XO1=918)
    sthux   = XSO(31, XO1=439)
    sthx    = XSO(31, XO1=407)
    stswi   = Form("rS", "rA", "NB", "XO1")(31, XO1=725)
    stswx   = XSO(31, XO1=661)
    stwbrx  = XSO(31, XO1=662)
    stwcxx  = Form("rS", "rA", "rB", "XO1", "Rc")(31, XO1=150, Rc=1)
    stwux   = XSO(31, XO1=183)
    stwx    = XSO(31, XO1=151)

    subf    = XO(31, XO2=40, OE=0, Rc=0)
    subfx   = XO(31, XO2=40, OE=0, Rc=1)
    subfo   = XO(31, XO2=40, OE=1, Rc=0)
    subfox  = XO(31, XO2=40, OE=1, Rc=1)

    subfc   = XO(31, XO2=8, OE=0, Rc=0)
    subfcx  = XO(31, XO2=8, OE=0, Rc=1)
    subfco  = XO(31, XO2=8, OE=1, Rc=0)
    subfcox = XO(31, XO2=8, OE=1, Rc=1)

    subfe   = XO(31, XO2=136, OE=0, Rc=0)
    subfex  = XO(31, XO2=136, OE=0, Rc=1)
    subfeo  = XO(31, XO2=136, OE=1, Rc=0)
    subfeox = XO(31, XO2=136, OE=1, Rc=1)

    subfme  = XO0(31, OE=0, XO2=232, Rc=0)
    subfmex = XO0(31, OE=0, XO2=232, Rc=1)
    subfmeo = XO0(31, OE=1, XO2=232, Rc=0)
    subfmeox= XO0(31, OE=1, XO2=232, Rc=1)

    subfze  = XO0(31, OE=0, XO2=200, Rc=0)
    subfzex = XO0(31, OE=0, XO2=200, Rc=1)
    subfzeo = XO0(31, OE=1, XO2=200, Rc=0)
    subfzeox= XO0(31, OE=1, XO2=200, Rc=1)

    sync    = X(31, XO1=598)

    tlbia = X(31, XO1=370)
    tlbie = Form("rB", "XO1")(31, XO1=306)
    tlbsync = X(31, XO1=566)

    td = Form("TO", "rA", "rB", "XO1")(31, XO1=68)
    tw = Form("TO", "rA", "rB", "XO1")(31, XO1=4)

    xor = XS(31, XO1=316, Rc=0)
    xorx = XS(31, XO1=316, Rc=1)

class PPCAssembler(BasicPPCAssembler):
    BA = BasicPPCAssembler

    # awkward mnemonics:
    # mftb
    # most of the branch mnemonics...

    # F.2 Simplified Mnemonics for Subtract Instructions

    def subi(self, rD, rA, value):
        self.addi(rD, rA, -value)
    def subis(self, rD, rA, value):
        self.addis(rD, rA, -value)
    def subic(self, rD, rA, value):
        self.addic(rD, rA, -value)
    def subicx(self, rD, rA, value):
        self.addicx(rD, rA, -value)

    def sub(self, rD, rA, rB):
        self.subf(rD, rB, rA)
    def subc(self, rD, rA, rB):
        self.subfc(rD, rB, rA)
    def subx(self, rD, rA, rB):
        self.subfx(rD, rB, rA)
    def subcx(self, rD, rA, rB):
        self.subfcx(rD, rB, rA)
    def subo(self, rD, rA, rB):
        self.subfo(rD, rB, rA)
    def subco(self, rD, rA, rB):
        self.subfco(rD, rB, rA)
    def subox(self, rD, rA, rB):
        self.subfox(rD, rB, rA)
    def subcox(self, rD, rA, rB):
        self.subfcox(rD, rB, rA)

    # F.3 Simplified Mnemonics for Compare Instructions

    cmpdi  = BA.cmpi(L=1)
    cmpwi  = BA.cmpi(L=0)
    cmpldi = BA.cmpli(L=1)
    cmplwi = BA.cmpli(L=0)
    cmpd   = BA.cmp(L=1)
    cmpw   = BA.cmp(L=0)
    cmpld  = BA.cmpl(L=1)
    cmplw  = BA.cmpl(L=0)

    # F.4 Simplified Mnemonics for Rotate and Shift Instructions

    def extlwi(self, rA, rS, n, b):
        self.rlwinm(rA, rS, b, 0, n-1)

    def extrwi(self, rA, rS, n, b):
        self.rlwinm(rA, rS, b+n, 32-n, 31)

    def inslwi(self, rA, rS, n, b):
        self.rwlimi(rA, rS, 32-b, b, b + n -1)

    def insrwi(self, rA, rS, n, b):
        self.rwlimi(rA, rS, 32-(b+n), b, b + n -1)

    def rotlwi(self, rA, rS, n):
        self.rlwinm(rA, rS, n, 0, 31)

    def rotrwi(self, rA, rS, n):
        self.rlwinm(rA, rS, 32-n, 0, 31)

    def rotlw(self, rA, rS, rB):
        self.rlwnm(rA, rS, rB, 0, 31)

    def slwi(self, rA, rS, n):
        self.rlwinm(rA, rS, n, 0, 31-n)

    def srwi(self, rA, rS, n):
        self.rlwinm(rA, rS, 32-n, n, 31)

    def sldi(self, rA, rS, n):
        self.rldicr(rA, rS, n, 63-n)

    def srdi(self, rA, rS, n):
        self.rldicl(rA, rS, 64-n, n)

    # F.5 Simplified Mnemonics for Branch Instructions

    # there's a lot of these!
    bt       = BA.bc(BO=12)
    bf       = BA.bc(BO=4)
    bdnz     = BA.bc(BO=16, BI=0)
    bdnzt    = BA.bc(BO=8)
    bdnzf    = BA.bc(BO=0)
    bdz      = BA.bc(BO=18)
    bdzt     = BA.bc(BO=10)
    bdzf     = BA.bc(BO=2)

    bta      = BA.bca(BO=12)
    bfa      = BA.bca(BO=4)
    bdnza    = BA.bca(BO=16, BI=0)
    bdnzta   = BA.bca(BO=8)
    bdnzfa   = BA.bca(BO=0)
    bdza     = BA.bca(BO=18)
    bdzta    = BA.bca(BO=10)
    bdzfa    = BA.bca(BO=2)

    btl      = BA.bcl(BO=12)
    bfl      = BA.bcl(BO=4)
    bdnzl    = BA.bcl(BO=16, BI=0)
    bdnztl   = BA.bcl(BO=8)
    bdnzfl   = BA.bcl(BO=0)
    bdzl     = BA.bcl(BO=18)
    bdztl    = BA.bcl(BO=10)
    bdzfl    = BA.bcl(BO=2)

    btla     = BA.bcla(BO=12)
    bfla     = BA.bcla(BO=4)
    bdnzla   = BA.bcla(BO=16, BI=0)
    bdnztla  = BA.bcla(BO=8)
    bdnzfla  = BA.bcla(BO=0)
    bdzla    = BA.bcla(BO=18)
    bdztla   = BA.bcla(BO=10)
    bdzfla   = BA.bcla(BO=2)

    blr      = BA.bclr(BO=20, BI=0)
    btlr     = BA.bclr(BO=12)
    bflr     = BA.bclr(BO=4)
    bdnzlr   = BA.bclr(BO=16, BI=0)
    bdnztlr  = BA.bclr(BO=8)
    bdnzflr  = BA.bclr(BO=0)
    bdzlr    = BA.bclr(BO=18, BI=0)
    bdztlr   = BA.bclr(BO=10)
    bdzflr   = BA.bclr(BO=2)

    bctr     = BA.bcctr(BO=20, BI=0)
    btctr    = BA.bcctr(BO=12)
    bfctr    = BA.bcctr(BO=4)

    blrl     = BA.bclrl(BO=20, BI=0)
    btlrl    = BA.bclrl(BO=12)
    bflrl    = BA.bclrl(BO=4)
    bdnzlrl  = BA.bclrl(BO=16, BI=0)
    bdnztlrl = BA.bclrl(BO=8)
    bdnzflrl = BA.bclrl(BO=0)
    bdzlrl   = BA.bclrl(BO=18, BI=0)
    bdztlrl  = BA.bclrl(BO=10)
    bdzflrl  = BA.bclrl(BO=2)

    bctrl    = BA.bcctrl(BO=20, BI=0)
    btctrl   = BA.bcctrl(BO=12)
    bfctrl   = BA.bcctrl(BO=4)

    # these should/could take a[n optional] crf argument, but it's a
    # bit hard to see how to arrange that.

    blt      = BA.bc(BO=12, BI=0)
    ble      = BA.bc(BO=4,  BI=1)
    beq      = BA.bc(BO=12, BI=2)
    bge      = BA.bc(BO=4,  BI=0)
    bgt      = BA.bc(BO=12, BI=1)
    bnl      = BA.bc(BO=4,  BI=0)
    bne      = BA.bc(BO=4,  BI=2)
    bng      = BA.bc(BO=4,  BI=1)
    bso      = BA.bc(BO=12, BI=3)
    bns      = BA.bc(BO=4,  BI=3)
    bun      = BA.bc(BO=12, BI=3)
    bnu      = BA.bc(BO=4,  BI=3)

    blta     = BA.bca(BO=12, BI=0)
    blea     = BA.bca(BO=4,  BI=1)
    beqa     = BA.bca(BO=12, BI=2)
    bgea     = BA.bca(BO=4,  BI=0)
    bgta     = BA.bca(BO=12, BI=1)
    bnla     = BA.bca(BO=4,  BI=0)
    bnea     = BA.bca(BO=4,  BI=2)
    bnga     = BA.bca(BO=4,  BI=1)
    bsoa     = BA.bca(BO=12, BI=3)
    bnsa     = BA.bca(BO=4,  BI=3)
    buna     = BA.bca(BO=12, BI=3)
    bnua     = BA.bca(BO=4,  BI=3)

    bltl     = BA.bcl(BO=12, BI=0)
    blel     = BA.bcl(BO=4,  BI=1)
    beql     = BA.bcl(BO=12, BI=2)
    bgel     = BA.bcl(BO=4,  BI=0)
    bgtl     = BA.bcl(BO=12, BI=1)
    bnll     = BA.bcl(BO=4,  BI=0)
    bnel     = BA.bcl(BO=4,  BI=2)
    bngl     = BA.bcl(BO=4,  BI=1)
    bsol     = BA.bcl(BO=12, BI=3)
    bnsl     = BA.bcl(BO=4,  BI=3)
    bunl     = BA.bcl(BO=12, BI=3)
    bnul     = BA.bcl(BO=4,  BI=3)

    bltla    = BA.bcla(BO=12, BI=0)
    blela    = BA.bcla(BO=4,  BI=1)
    beqla    = BA.bcla(BO=12, BI=2)
    bgela    = BA.bcla(BO=4,  BI=0)
    bgtla    = BA.bcla(BO=12, BI=1)
    bnlla    = BA.bcla(BO=4,  BI=0)
    bnela    = BA.bcla(BO=4,  BI=2)
    bngla    = BA.bcla(BO=4,  BI=1)
    bsola    = BA.bcla(BO=12, BI=3)
    bnsla    = BA.bcla(BO=4,  BI=3)
    bunla    = BA.bcla(BO=12, BI=3)
    bnula    = BA.bcla(BO=4,  BI=3)

    bltlr    = BA.bclr(BO=12, BI=0)
    blelr    = BA.bclr(BO=4,  BI=1)
    beqlr    = BA.bclr(BO=12, BI=2)
    bgelr    = BA.bclr(BO=4,  BI=0)
    bgtlr    = BA.bclr(BO=12, BI=1)
    bnllr    = BA.bclr(BO=4,  BI=0)
    bnelr    = BA.bclr(BO=4,  BI=2)
    bnglr    = BA.bclr(BO=4,  BI=1)
    bsolr    = BA.bclr(BO=12, BI=3)
    bnslr    = BA.bclr(BO=4,  BI=3)
    bunlr    = BA.bclr(BO=12, BI=3)
    bnulr    = BA.bclr(BO=4,  BI=3)

    bltctr   = BA.bcctr(BO=12, BI=0)
    blectr   = BA.bcctr(BO=4,  BI=1)
    beqctr   = BA.bcctr(BO=12, BI=2)
    bgectr   = BA.bcctr(BO=4,  BI=0)
    bgtctr   = BA.bcctr(BO=12, BI=1)
    bnlctr   = BA.bcctr(BO=4,  BI=0)
    bnectr   = BA.bcctr(BO=4,  BI=2)
    bngctr   = BA.bcctr(BO=4,  BI=1)
    bsoctr   = BA.bcctr(BO=12, BI=3)
    bnsctr   = BA.bcctr(BO=4,  BI=3)
    bunctr   = BA.bcctr(BO=12, BI=3)
    bnuctr   = BA.bcctr(BO=4,  BI=3)

    bltlrl   = BA.bclrl(BO=12, BI=0)
    blelrl   = BA.bclrl(BO=4,  BI=1)
    beqlrl   = BA.bclrl(BO=12, BI=2)
    bgelrl   = BA.bclrl(BO=4,  BI=0)
    bgtlrl   = BA.bclrl(BO=12, BI=1)
    bnllrl   = BA.bclrl(BO=4,  BI=0)
    bnelrl   = BA.bclrl(BO=4,  BI=2)
    bnglrl   = BA.bclrl(BO=4,  BI=1)
    bsolrl   = BA.bclrl(BO=12, BI=3)
    bnslrl   = BA.bclrl(BO=4,  BI=3)
    bunlrl   = BA.bclrl(BO=12, BI=3)
    bnulrl   = BA.bclrl(BO=4,  BI=3)

    bltctrl  = BA.bcctrl(BO=12, BI=0)
    blectrl  = BA.bcctrl(BO=4,  BI=1)
    beqctrl  = BA.bcctrl(BO=12, BI=2)
    bgectrl  = BA.bcctrl(BO=4,  BI=0)
    bgtctrl  = BA.bcctrl(BO=12, BI=1)
    bnlctrl  = BA.bcctrl(BO=4,  BI=0)
    bnectrl  = BA.bcctrl(BO=4,  BI=2)
    bngctrl  = BA.bcctrl(BO=4,  BI=1)
    bsoctrl  = BA.bcctrl(BO=12, BI=3)
    bnsctrl  = BA.bcctrl(BO=4,  BI=3)
    bunctrl  = BA.bcctrl(BO=12, BI=3)
    bnuctrl  = BA.bcctrl(BO=4,  BI=3)

    # whew!  and we haven't even begun the predicted versions...

    # F.6 Simplified Mnemonics for Condition Register
    #     Logical Instructions

    crset = BA.creqv(crbA="crbD", crbB="crbD")
    crclr = BA.crxor(crbA="crbD", crbB="crbD")
    crmove = BA.cror(crbA="crbB")
    crnot = BA.crnor(crbA="crbB")

    # F.7 Simplified Mnemonics for Trap Instructions

    trap = BA.tw(TO=31, rA=0, rB=0)
    twlt = BA.tw(TO=16)
    twle = BA.tw(TO=20)
    tweq = BA.tw(TO=4)
    twge = BA.tw(TO=12)
    twgt = BA.tw(TO=8)
    twnl = BA.tw(TO=12)
    twng = BA.tw(TO=24)
    twllt = BA.tw(TO=2)
    twlle = BA.tw(TO=6)
    twlge = BA.tw(TO=5)
    twlgt = BA.tw(TO=1)
    twlnl = BA.tw(TO=5)
    twlng = BA.tw(TO=6)

    twlti = BA.twi(TO=16)
    twlei = BA.twi(TO=20)
    tweqi = BA.twi(TO=4)
    twgei = BA.twi(TO=12)
    twgti = BA.twi(TO=8)
    twnli = BA.twi(TO=12)
    twnei = BA.twi(TO=24)
    twngi = BA.twi(TO=20)
    twllti = BA.twi(TO=2)
    twllei = BA.twi(TO=6)
    twlgei = BA.twi(TO=5)
    twlgti = BA.twi(TO=1)
    twlnli = BA.twi(TO=5)
    twlngi = BA.twi(TO=6)

    # F.8 Simplified Mnemonics for Special-Purpose
    #     Registers

    mfctr = BA.mfspr(spr=9)
    mflr  = BA.mfspr(spr=8)
    mftbl = BA.mftb(spr=268)
    mftbu = BA.mftb(spr=269)
    mfxer = BA.mfspr(spr=1)

    mtctr = BA.mtspr(spr=9)
    mtlr  = BA.mtspr(spr=8)
    mtxer = BA.mtspr(spr=1)

    # F.9 Recommended Simplified Mnemonics

    nop = BA.ori(rS=0, rA=0, UIMM=0)

    li = BA.addi(rA=0)
    lis = BA.addis(rA=0)

    mr = BA.or_(rB="rS")
    mrx = BA.or_x(rB="rS")

    not_ = BA.nor(rB="rS")
    not_x = BA.norx(rB="rS")

    mtcr = BA.mtcrf(CRM=0xFF)

    def emit(self, insn):
        bytes = struct.pack("i", insn)
        for byte in bytes:
            self.writechar(byte)

def hi(w):
    return w >> 16

def ha(w):
    if (w >> 15) & 1:
        return (w >> 16) + 1
    else:
        return w >> 16

def lo(w):
    return w & 0x0000FFFF

def la(w):
    v = w & 0x0000FFFF
    if v & 0x8000:
        return -((v ^ 0xFFFF) + 1) # "sign extend" to 32 bits
    return v

def highest(w):
    return w >> 48

def higher(w):
    return (w >> 32) & 0x0000FFFF

def high(w):
    return (w >> 16) & 0x0000FFFF

# XXX check this
if we_are_translated():
    eci = ExternalCompilationInfo(includes = ['asm_ppc.h'])

    flush_icache = rffi.llexternal(
        "LL_flush_icache",
        [lltype.Signed, lltype.Signed],
        lltype.Void,
        compilation_info=eci,
        _nowrapper=True,
        sandboxsafe=True)
else:
    def flush_icache(x, y): pass

class GuardToken(object):
    def __init__(self, descr, failargs, faillocs, offset,
                                        save_exc=False, is_invalidate=False):
        self.descr = descr
        self.offset = offset
        self.is_invalidate = is_invalidate
        self.failargs = failargs
        self.faillocs = faillocs
        self.save_exc = save_exc

class OverwritingBuilder(PPCAssembler):
    def __init__(self, cb, start, num_insts):
        PPCAssembler.__init__(self)
        self.cb = cb
        self.index = start
        self.num_insts = num_insts

    def currpos(self):
        assert 0, "not implemented"

    def overwrite(self):
        assert len(self.insts) <= self.num_insts
        startindex  = self.index / 4
        for i, new_inst in enumerate(self.insts):
            self.cb.insts[i + startindex] = new_inst

class PPCBuilder(BlockBuilderMixin, PPCAssembler):
    def __init__(self, failargs_limit=1000, r0_in_use=False):
        PPCAssembler.__init__(self)
        self.init_block_builder()
        self.fail_boxes_int = values_array(lltype.Signed, failargs_limit)
        self.r0_in_use = r0_in_use

    def load_imm(self, rD, word):
        rD = rD.as_key()
        if word <= 32767 and word >= -32768:
            self.li(rD, word)
        elif IS_PPC_32 or (word <= 2147483647 and word >= -2147483648):
            self.lis(rD, hi(word))
            if word & 0xFFFF != 0:
                self.ori(rD, rD, lo(word))
        else:
            self.lis(rD, highest(word))
            self.ori(rD, rD, higher(word))
            self.sldi(rD, rD, 32)
            self.oris(rD, rD, high(word))
            self.ori(rD, rD, lo(word))

    def load_from_addr(self, rD, addr):
        self.load_imm(rD, addr)
        if IS_PPC_32:
            self.lwzx(rD.value, 0, rD.value)
        else:
            self.ldx(rD.value, 0, rD.value)

    def store_reg(self, source_reg, addr):
        self.alloc_scratch_reg(addr)
        if IS_PPC_32:
            self.stwx(source_reg.value, 0, r.SCRATCH.value)
        else:
            self.stdx(source_reg.value, 0, r.SCRATCH.value)
        self.free_scratch_reg()

    def b_offset(self, target):
        curpos = self.currpos()
        offset = target - curpos
        assert offset < (1 << 24)
        self.b(offset)

    def b_cond_offset(self, offset, condition):
        BI = condition[0]
        BO = condition[1]

        pos = self.currpos()
        target_ofs = offset - pos
        self.bc(BO, BI, target_ofs)

    def b_cond_abs(self, addr, condition):
        BI = condition[0]
        BO = condition[1]

        self.alloc_scratch_reg(addr)
        self.mtctr(r.SCRATCH.value)
        self.free_scratch_reg()
        self.bcctr(BO, BI)

    def b_abs(self, address, trap=False):
        self.alloc_scratch_reg(address)
        self.mtctr(r.SCRATCH.value)
        self.free_scratch_reg()
        if trap:
            self.trap()
        self.bctr()

    def call(self, address):
        """ do a call to an absolute address
        """
        self.alloc_scratch_reg()
        if IS_PPC_32:
            self.load_imm(r.SCRATCH, address)
        else:
            self.store(r.TOC.value, r.SP.value, 5 * WORD)
            self.load_imm(r.r11, address)
            self.load(r.SCRATCH.value, r.r11.value, 0)
            self.load(r.r2.value, r.r11.value, WORD)
            self.load(r.r11.value, r.r11.value, 2 * WORD)
        self.mtctr(r.SCRATCH.value)
        self.free_scratch_reg()
        self.bctrl()

        if IS_PPC_64:
            self.load(r.TOC.value, r.SP.value, 5 * WORD)

    def load(self, target_reg, base_reg, offset):
        if IS_PPC_32:
            self.lwz(target_reg, base_reg, offset)
        else:
            self.ld(target_reg, base_reg, offset)

    def loadx(self, target_reg, base_reg, offset_reg):
        if IS_PPC_32:
            self.lwzx(target_reg, base_reg, offset_reg)
        else:
            self.ldx(target_reg, base_reg, offset_reg)

    def store(self, from_reg, base_reg, offset):
        if IS_PPC_32:
            self.stw(from_reg, base_reg, offset)
        else:
            self.std(from_reg, base_reg, offset)

    def storex(self, from_reg, base_reg, offset_reg):
        if IS_PPC_32:
            self.stwx(from_reg, base_reg, offset_reg)
        else:
            self.stdx(from_reg, base_reg, offset_reg)

    def prepare_insts_blocks(self, show=False):
        self.assemble(show)
        insts = self.insts
        for inst in insts:
            self.write32(inst.assemble())

    def _dump_trace(self, addr, name, formatter=-1):
        if not we_are_translated():
            if formatter != -1:
                name = name % formatter
            dir = udir.ensure('asm', dir=True)
            f = dir.join(name).open('wb')
            data = rffi.cast(rffi.CCHARP, addr)
            for i in range(self.currpos()):
                f.write(data[i])
            f.close()

    def write32(self, word):
        self.writechar(chr((word >> 24) & 0xFF))
        self.writechar(chr((word >> 16) & 0xFF))
        self.writechar(chr((word >> 8) & 0xFF))
        self.writechar(chr(word & 0xFF))

    def write64(self, word):
        self.writechar(chr((word >> 56) & 0xFF))
        self.writechar(chr((word >> 48) & 0xFF))
        self.writechar(chr((word >> 40) & 0xFF))
        self.writechar(chr((word >> 32) & 0xFF))
        self.writechar(chr((word >> 24) & 0xFF))
        self.writechar(chr((word >> 16) & 0xFF))
        self.writechar(chr((word >> 8) & 0xFF))
        self.writechar(chr(word & 0xFF))

    def currpos(self):
        return self.get_rel_pos()

    def flush_cache(self, addr):
        startaddr = rffi.cast(lltype.Signed, addr)
        size = rffi.cast(lltype.Signed, self.get_relative_pos())
        flush_icache(startaddr, size)

    def copy_to_raw_memory(self, addr):
        self._copy_to_raw_memory(addr)
        self.flush_cache(addr)

    def cmp_op(self, block, a, b, imm=False, signed=True):
        if IS_PPC_32:
            if signed:
                if imm:
                    # 32 bit immediate signed
                    self.cmpwi(block, a, b)
                else:
                    # 32 bit signed
                    self.cmpw(block, a, b)
            else:
                if imm:
                    # 32 bit immediate unsigned
                    self.cmplwi(block, a, b)
                else:
                    # 32 bit unsigned
                    self.cmplw(block, a, b)
        else:
            if signed:
                if imm:
                    # 64 bit immediate signed
                    self.cmpdi(block, a, b)
                else:
                    # 64 bit signed
                    self.cmpd(block, a, b)
            else:
                if imm:
                    # 64 bit immediate unsigned
                    self.cmpldi(block, a, b)
                else:
                    # 64 bit unsigned
                    self.cmpld(block, a, b)
                
    def alloc_scratch_reg(self, value=None):
        assert not self.r0_in_use
        self.r0_in_use = True
        if value is not None:
            self.load_imm(r.r0, value)

    def free_scratch_reg(self):
        assert self.r0_in_use
        self.r0_in_use = False

    def _dump_trace(self, addr, name, formatter=-1):
        if not we_are_translated():
            if formatter != -1:
                name = name % formatter
            dir = udir.ensure('asm', dir=True)
            f = dir.join(name).open('wb')
            data = rffi.cast(rffi.CCHARP, addr)
            for i in range(self.currpos()):
                f.write(data[i])
            f.close()

class BranchUpdater(PPCAssembler):
    def __init__(self):
        PPCAssembler.__init__(self)
        self.init_block_builder()

    def write_to_mem(self, addr):
        self.assemble()
        self.copy_to_raw_memory(addr)
        
    def assemble(self, dump=os.environ.has_key('PYPY_DEBUG')):
        insns = self.assemble0(dump)
        for i in insns:
            self.emit(i)

def b(n):
    r = []
    for i in range(32):
        r.append(n&1)
        n >>= 1
    r.reverse()
    return ''.join(map(str, r))

def make_operations():
    def not_implemented(builder, trace_op, cpu, *rest_args):
        import pdb; pdb.set_trace()

    oplist = [None] * (rop._LAST + 1)
    for key, val in rop.__dict__.items():
        if key.startswith("_"):
            continue
        opname = key.lower()
        methname = "emit_%s" % opname
        if hasattr(PPCBuilder, methname):
            oplist[val] = getattr(PPCBuilder, methname).im_func
        else:
            oplist[val] = not_implemented
    return oplist

PPCBuilder.operations = make_operations()
