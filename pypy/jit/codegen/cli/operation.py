from pypy.translator.cli.dotnet import CLR
OpCodes = CLR.System.Reflection.Emit.OpCodes

class Operation:
    restype = None
    _gv_res = None

    def gv_res(self):
        from pypy.jit.codegen.cli.rgenop import GenLocalVar
        if self._gv_res is None:
            # if restype is None, assume it's the same as the first arg
            t = self.restype or self.gv_x.getCliType()
            loc = self.il.DeclareLocal(t)
            self._gv_res = GenLocalVar(loc)
        return self._gv_res

    def emit(self):
        raise NotImplementedError


class UnaryOp(Operation):
    def __init__(self, il, gv_x):
        self.il = il
        self.gv_x = gv_x


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
