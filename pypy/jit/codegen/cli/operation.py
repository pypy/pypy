import py
from pypy.rlib.objectmodel import specialize
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.dotnet import CLR, typeof
from pypy.translator.cli import opcodes as cli_opcodes
System = CLR.System
OpCodes = System.Reflection.Emit.OpCodes

class Operation:
    _gv_res = None

    def restype(self):
        return self.gv_x.getCliType()

    def gv_res(self):
        from pypy.jit.codegen.cli.rgenop import GenLocalVar
        if self._gv_res is None:
            restype = self.restype()
            if restype is not None:
                loc = self.il.DeclareLocal(restype)
                self._gv_res = GenLocalVar(loc)
        return self._gv_res

    def emit(self):
        raise NotImplementedError

    def pushAllArgs(self):
        raise NotImplementedError

    def storeResult(self):
        self.gv_res().store(self.il)


class UnaryOp(Operation):
    def __init__(self, il, gv_x):
        self.il = il
        self.gv_x = gv_x

    def pushAllArgs(self):
        self.gv_x.load(self.il)

class BinaryOp(Operation):
    def __init__(self, il, gv_x, gv_y):
        self.il = il
        self.gv_x = gv_x
        self.gv_y = gv_y

    def pushAllArgs(self):
        self.gv_x.load(self.il)
        self.gv_y.load(self.il)

    def emit(self):
        self.pushAllArgs()
        self.il.Emit(self.getOpCode())
        self.storeResult()

    def getOpCode(self):
        raise NotImplementedError


class SameAs(UnaryOp):
    def emit(self):
        gv_res = self.gv_res()
        self.gv_x.load(self.il)
        self.gv_res().store(self.il)


def opcode2attrname(opcode):
    parts = map(str.capitalize, opcode.split('.'))
    return '_'.join(parts)

def is_comparison(opname):
    suffixes = '_lt _le _eq _ne _gt _ge'.split()
    for suffix in suffixes:
        if opname.endswith(suffix):
            return True
    return False

def fillops(ops, baseclass):
    # monkey-patch boolean operations
    def restype(self):
        return typeof(System.Boolean)

    out = {}
    for opname, value in ops.iteritems():
        if isinstance(value, str):
            attrname = opcode2attrname(value)
            source = py.code.Source("""
            class %(opname)s (%(baseclass)s):
                def getOpCode(self):
                    return OpCodes.%(attrname)s
            """ % locals())
            code = source.compile()
            exec code in globals(), out
            if is_comparison(opname):
                out[opname].restype = restype
        elif value is cli_opcodes.DoNothing:
            out[opname] = SameAs
        else:
            pass # XXX: handle remaining ops
    return out

UNARYOPS = fillops(cli_opcodes.unary_ops, "UnaryOp")
BINARYOPS = fillops(cli_opcodes.binary_ops, "BinaryOp")

@specialize.memo()
def getopclass1(opname):
    try:
        return UNARYOPS[opname]
    except KeyError:
        raise MissingBackendOperation(opname)

@specialize.memo()
def getopclass2(opname):
    try:
        return BINARYOPS[opname]
    except KeyError:
        raise MissingBackendOperation(opname)

class MissingBackendOperation(Exception):
    pass
