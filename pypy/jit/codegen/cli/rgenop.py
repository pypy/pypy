from pypy.tool.pairtype import extendabletype
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.objectmodel import specialize
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVarOrConst, GenVar, GenConst, CodeGenSwitch
from pypy.translator.cli.dotnet import CLR, typeof, new_array, clidowncast
System = CLR.System
Utils = CLR.pypy.runtime.Utils
OpCodes = System.Reflection.Emit.OpCodes

def token2clitype(tok):
    if tok == '<Signed>':
        return typeof(System.Int32)
    else:
        assert False

class __extend__(GenVarOrConst):
    __metaclass__ = extendabletype
    
    def load(self, il):
        raise NotImplementedError

    def store(self, il):
        raise NotImplementedError

class GenArgVar(GenVar):
    def __init__(self, index):
        self.index = index
        # XXX maybe we need to store also the type?

    def load(self, il):
        if self.index == 0:
            il.Emit(OpCodes.Ldarg_0)
        elif self.index == 1:
            il.Emit(OpCodes.Ldarg_1)
        elif self.index == 2:
            il.Emit(OpCodes.Ldarg_2)
        elif self.index == 3:
            il.Emit(OpCodes.Ldarg_3)
        else:
            il.Emit(OpCodes.Ldarg, self.index)

    def store(self, il):
        il.Emit(OpCodes.Starg, self.index)

    def __repr__(self):
        return "GenArgVar(%d)" % self.index

class GenLocalVar(GenVar):
    def __init__(self, v):
        self.v = v

    def load(self, il):
        il.Emit(OpCodes.Ldloc, self.v)

    def store(self, il):
        il.Emit(OpCodes.Stloc, self.v)

class IntConst(GenConst):

    def __init__(self, value):
        self.value = value

    @specialize.arg(1)
    def revealconst(self, T):
        assert T is ootype.Signed
        return self.value

    def load(self, il):
        il.Emit(OpCodes.Ldc_I4, self.value)

    def __repr__(self):
        "NOT_RPYTHON"
        return "const=%s" % self.value

class ObjectConst(GenConst):

    def __init__(self, obj):
        self.obj = obj

    @specialize.arg(1)
    def revealconst(self, T):
        DelegateType = CLR.pypy.runtime.DelegateType_int__int # XXX use T
        return clidowncast(DelegateType, self.obj)


class RCliGenOp(AbstractRGenOp):

    def __init__(self):
        self.meth = None
        self.il = None

    @specialize.genconst(1)
    def genconst(self, llvalue):
        T = ootype.typeOf(llvalue)
        if T is ootype.Signed:
            return IntConst(llvalue)
        else:
            assert False, "XXX not implemented"

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        """Return a token describing the signature of FUNCTYPE."""
        # XXX: the right thing to do would be to have a way to
        # represent typeof(t) as a pbc
        args = [repr(T) for T in FUNCTYPE.ARGS]
        res = repr(FUNCTYPE.RESULT)
        return args, res

    def newgraph(self, sigtoken, name):
        argtoks, restok = sigtoken
        args = new_array(System.Type, len(argtoks))
        for i in range(len(argtoks)):
            args[i] = token2clitype(argtoks[i])
        res = token2clitype(restok)
        builder = Builder(self, name, res, args)
        return builder, builder.gv_entrypoint, builder.inputargs_gv[:]



class Builder(GenBuilder):

    def __init__(self, rgenop, name, res, args):
        self.rgenop = rgenop
        self.meth = Utils.CreateDynamicMethod(name, res, args)
        self.il = self.meth.GetILGenerator()
        self.inputargs_gv = []
        for i in range(len(args)):
            self.inputargs_gv.append(GenArgVar(i))
        self.gv_entrypoint = ObjectConst(None) # XXX?
 
    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        assert opname == 'int_add'
        res = self.il.DeclareLocal(typeof(System.Int32))
        gv_res = GenLocalVar(res)
        gv_arg1.load(self.il)
        gv_arg2.load(self.il)
        self.il.Emit(OpCodes.Add)
        gv_res.store(self.il)
        return gv_res

    def finish_and_return(self, sigtoken, gv_returnvar):
        gv_returnvar.load(self.il)
        self.il.Emit(OpCodes.Ret)
        DelegateType = CLR.pypy.runtime.DelegateType_int__int # XXX use sigtoken
        myfunc = self.meth.CreateDelegate(typeof(DelegateType))
        self.gv_entrypoint.obj = myfunc

    def end(self):
        pass
