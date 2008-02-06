from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.dotnet import CLR, typeof
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


class Branch(Operation):
    
    def __init__(self, il, label):
        self.il = il
        self.label = label

    def emit(self):
        self.il.emit(OpCodes.Br, self.label)


class UnaryOp(Operation):
    def __init__(self, il, gv_x):
        self.il = il
        self.gv_x = gv_x


class AbstractBranchIf(UnaryOp):

    def __init__(self, il, gv_x, label):
        self.il = il
        self.gv_x = gv_x
        self.label = label

    def restype(self):
        return None

    def emit(self):
        self.il.emit(self.getOpCode(), self.label)

    def getOpCode(self):
        return OpCodes.Brtrue


class BrFalse(AbstractBranchIf):

    def getOpCode(self):
        return OpCodes.Brfalse

class BrTrue(AbstractBranchIf):

    def getOpCode(self):
        return OpCodes.Brtrue


class SameAs(UnaryOp):
    def emit(self):
        gv_res = self.gv_res()
        self.gv_x.load(self.il)
        self.gv_res().store(self.il)


class BinaryOp(Operation):
    def __init__(self, il, gv_x, gv_y):
        self.il = il
        self.gv_x = gv_x
        self.gv_y = gv_y

    def emit(self):
        self.gv_x.load(self.il)
        self.gv_y.load(self.il)
        self.il.Emit(self.getOpCode())
        self.gv_res().store(self.il)

    def getOpCode(self):
        raise NotImplementedError


class Add(BinaryOp):
    def getOpCode(self):
        return OpCodes.Add


class Sub(BinaryOp):
    def getOpCode(self):
        return OpCodes.Sub

class Gt(BinaryOp):
    def restype(self):
        return typeof(System.Boolean)

    def getOpCode(self):
        return OpCodes.Cgt
