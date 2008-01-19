# Fake stuff for the tests.

from pypy.jit.codegen.model import GenVarOrConst, GenVar, GenConst
from pypy.rpython.lltypesystem import lltype
from pypy.jit.timeshifter import rvalue, rcontainer


class FakeJITState(object):
    def __init__(self):
        self.curbuilder = FakeBuilder()

class FakeRGenOp(object):
    def genzeroconst(self, kind):
        if kind == "dummy pointer":
            return FakeGenConst("NULL")
        return FakeGenConst(0)

    @staticmethod
    def kindToken(TYPE):
        return ("kind", TYPE)

    @staticmethod
    def fieldToken(TYPE, name):
        return ("field", TYPE, name)

    @staticmethod
    def allocToken(TYPE):
        return ("alloc", TYPE)

    @staticmethod
    def constPrebuiltGlobal(value):
        return FakeGenConst(value)


class FakeBuilder(object):
    ops_with_no_retval = set(['setfield'])
    
    def __init__(self):
        self.ops = []
        self.varcount = 1
        self.rgenop = FakeRGenOp()

    def __getattr__(self, name):
        if name.startswith('genop_'):
            opname = name[len('genop_'):]            
            def genop_(*args):
                if opname in self.ops_with_no_retval:
                    v = None
                else:
                    v = FakeGenVar(self.varcount)
                    self.varcount += 1
                self.ops.append((opname, args, v))
                return v
            genop_.func_name = name
            return genop_
        else:
            raise AttributeError, name


class FakeHRTyper(object):
    RGenOp = FakeRGenOp

fakehrtyper = FakeHRTyper()

class FakeGenVar(GenVar):
    def __init__(self, count=0):
        self.count=count
    
    def __repr__(self):
        return "V%d" % self.count

    def __eq__(self, other):
        return self.count == other.count


class FakeGenConst(GenConst):
    def __init__(self, _value=None):
        self._value = _value

    def revealconst(self, T):
        return self._value

# ____________________________________________________________

signed_kind = FakeRGenOp.kindToken(lltype.Signed)

def vmalloc(TYPE, *boxes):
    jitstate = FakeJITState()
    assert isinstance(TYPE, lltype.Struct)   # for now
    structdesc = rcontainer.StructTypeDesc(fakehrtyper, TYPE)
    box = structdesc.factory()
    for fielddesc, valuebox in zip(structdesc.fielddescs, boxes):
        if valuebox is None:
            break
        box.op_setfield(jitstate, fielddesc, valuebox)
    assert jitstate.curbuilder.ops == []
    return box

def makebox(value):
    if not isinstance(value, GenVarOrConst):
        assert isinstance(value, int)    # for now
        value = FakeGenConst(value)
    return rvalue.IntRedBox(signed_kind, value)

def getfielddesc(STRUCT, name):
    assert isinstance(STRUCT, lltype.Struct)
    structdesc = rcontainer.StructTypeDesc(fakehrtyper, STRUCT)
    return structdesc.fielddesc_by_name[name]
