from pypy.tool.pairtype import extendabletype
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.objectmodel import specialize
from pypy.jit.codegen.model import AbstractRGenOp, GenBuilder, GenLabel
from pypy.jit.codegen.model import GenVarOrConst, GenVar, GenConst, CodeGenSwitch
from pypy.jit.codegen.cli import operation as ops
from pypy.jit.codegen.cli.dumpgenerator import DumpGenerator
from pypy.translator.cli.dotnet import CLR, typeof, new_array, box, unbox
System = CLR.System
Utils = CLR.pypy.runtime.Utils
DelegateHolder = CLR.pypy.runtime.DelegateHolder
OpCodes = System.Reflection.Emit.OpCodes

DUMP_IL = False
DEBUG = False

SM_INT__INT_1 = ootype.StaticMethod([ootype.Signed], ootype.Signed)
SM_INT__INT_2 = ootype.StaticMethod([ootype.Signed] * 2, ootype.Signed)
SM_INT__INT_3 = ootype.StaticMethod([ootype.Signed] * 3, ootype.Signed)
SM_INT__INT_100 = ootype.StaticMethod([ootype.Signed] * 100, ootype.Signed)

def token2clitype(tok):
    if tok == '<Signed>':
        return typeof(System.Int32)
    else:
        assert False

def sigtoken2clitype(tok):
    if tok == (['<Signed>'], '<Signed>'):
        return typeof(SM_INT__INT_1)
    elif tok == (['<Signed>', '<Signed>'], '<Signed>'):
        return typeof(SM_INT__INT_2)
    elif tok == (['<Signed>'] * 3, '<Signed>'):
        return typeof(SM_INT__INT_3)
    elif tok == (['<Signed>'] * 100, '<Signed>'):
        return typeof(SM_INT__INT_100)
    else:
        assert False

class __extend__(GenVarOrConst):
    __metaclass__ = extendabletype

    def getCliType(self):
        raise NotImplementedError
    
    def load(self, builder):
        raise NotImplementedError

    def store(self, builder):
        raise NotImplementedError

class GenArgVar(GenVar):
    def __init__(self, index, cliType):
        self.index = index
        self.cliType = cliType

    def getCliType(self):
        return self.cliType

    def load(self, builder):
        if self.index == 0:
            builder.il.Emit(OpCodes.Ldarg_0)
        elif self.index == 1:
            builder.il.Emit(OpCodes.Ldarg_1)
        elif self.index == 2:
            builder.il.Emit(OpCodes.Ldarg_2)
        elif self.index == 3:
            builder.il.Emit(OpCodes.Ldarg_3)
        else:
            builder.il.Emit(OpCodes.Ldarg, self.index)

    def store(self, builder):
        builder.il.Emit(OpCodes.Starg, self.index)

    def __repr__(self):
        return "GenArgVar(%d)" % self.index

class GenLocalVar(GenVar):
    def __init__(self, v):
        self.v = v

    def getCliType(self):
        return self.v.get_LocalType()

    def load(self, builder):
        builder.il.Emit(OpCodes.Ldloc, self.v)

    def store(self, builder):
        builder.il.Emit(OpCodes.Stloc, self.v)


class IntConst(GenConst):

    def __init__(self, value):
        self.value = value

    @specialize.arg(1)
    def revealconst(self, T):
        if T is ootype.Signed:
            return self.value
        elif T is ootype.Bool:
            return bool(self.value)
        else:
            assert False

    def getCliType(self):
        return typeof(System.Int32)

    def load(self, builder):
        builder.il.Emit(OpCodes.Ldc_I4, self.value)

    def __repr__(self):
        return "const=%s" % self.value

class BaseConst(GenConst):

    def _get_index(self, builder):
        # check whether there is already an index associated to this const
        try:
            index = builder.genconsts[self]
        except KeyError:
            index = len(builder.genconsts)
            builder.genconsts[self] = index
        return index

    def _load_from_array(self, builder, index, clitype):
        builder.il.Emit(OpCodes.Ldarg_0)
        builder.il.Emit(OpCodes.Ldc_I4, index)
        builder.il.Emit(OpCodes.Ldelem_Ref)
        builder.il.Emit(OpCodes.Castclass, clitype)

    def getobj(self):
        raise NotImplementedError

class ObjectConst(BaseConst):

    def __init__(self, obj):
        self.obj = obj

    def getobj(self):
        return self.obj

    def load(self, builder):
        index = self._get_index(builder)
        t = self.obj.GetType()
        self._load_from_array(builder, index, t)

    @specialize.arg(1)
    def revealconst(self, T):
        assert isinstance(T, ootype.OOType)
        return unbox(self.obj, T)


class FunctionConst(BaseConst):

    def __init__(self, delegatetype):
        self.holder = DelegateHolder()
        self.delegatetype = delegatetype

    def getobj(self):
        return self.holder

    def load(self, builder):
        holdertype = box(self.holder).GetType()
        funcfield = holdertype.GetField('func')
        delegatetype = self.delegatetype
        index = self._get_index(builder)
        self._load_from_array(builder, index, holdertype)
        builder.il.Emit(OpCodes.Ldfld, funcfield)
        builder.il.Emit(OpCodes.Castclass, delegatetype)

    @specialize.arg(1)
    def revealconst(self, T):
        assert isinstance(T, ootype.OOType)
        return unbox(self.holder.GetFunc(), T)

class Label(GenLabel):
    def __init__(self, label, inputargs_gv):
        self.label = label
        self.inputargs_gv = inputargs_gv


class RCliGenOp(AbstractRGenOp):

    def __init__(self):
        self.meth = None
        self.il = None
        self.constcount = 0

    @specialize.genconst(1)
    def genconst(self, llvalue):
        T = ootype.typeOf(llvalue)
        if T is ootype.Signed:
            return IntConst(llvalue)
        elif T is ootype.Bool:
            return IntConst(int(llvalue))
        elif isinstance(T, ootype.OOType):
            return ObjectConst(box(llvalue))
        else:
            assert False, "XXX not implemented"

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        """Return a token describing the signature of FUNCTYPE."""
        # XXX: the right thing to do would be to have a way to
        # represent typeof(t) as a pbc
        args = [RCliGenOp.kindToken(T) for T in FUNCTYPE.ARGS]
        res = RCliGenOp.kindToken(FUNCTYPE.RESULT)
        return args, res

    @staticmethod
    @specialize.memo()
    def kindToken(T):
        return repr(T)

    def newgraph(self, sigtoken, name):
        argtoks, restok = sigtoken
        args = new_array(System.Type, len(argtoks)+1)
        args[0] = System.Type.GetType("System.Object[]")
        for i in range(len(argtoks)):
            args[i+1] = token2clitype(argtoks[i])
        res = token2clitype(restok)
        builder = Builder(self, name, res, args, sigtoken)
        return builder, builder.gv_entrypoint, builder.inputargs_gv[:]


class Builder(GenBuilder):

    def __init__(self, rgenop, name, res, args, sigtoken):
        self.rgenop = rgenop
        self.meth = Utils.CreateDynamicMethod(name, res, args)
        self.il = self.meth.GetILGenerator()
        if DUMP_IL:
            self.il = DumpGenerator(self.il)
        self.inputargs_gv = []
        # we start from 1 because the 1st arg is an Object[] containing the genconsts
        for i in range(1, len(args)):
            self.inputargs_gv.append(GenArgVar(i, args[i]))
        self.delegatetype = sigtoken2clitype(sigtoken)
        self.gv_entrypoint = FunctionConst(self.delegatetype)
        self.isOpen = False
        self.operations = []
        self.branches = []
        self.returnblocks = []
        self.genconsts = {}

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        opcls = ops.getopclass1(opname)
        op = opcls(self, gv_arg)
        self.emit(op)
        gv_res = op.gv_res()
        if DEBUG:
            self.il.EmitWriteLine(opname)
            self.writeline_gv(gv_arg)
            self.writeline_gv(gv_res)
            self.il.EmitWriteLine('')
        return gv_res
    
    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        opcls = ops.getopclass2(opname)
        op = opcls(self, gv_arg1, gv_arg2)
        self.emit(op)
        gv_res = op.gv_res()
        if DEBUG:
            self.il.EmitWriteLine(opname)
            self.writeline_gv(gv_arg1)
            self.writeline_gv(gv_arg2)
            self.writeline_gv(gv_res)
            self.il.EmitWriteLine('')
        return gv_res

    def writeline_gv(self, gv):
        if isinstance(gv, GenLocalVar):
            self.il.EmitWriteLine(gv.v)
        elif isinstance(gv, IntConst):
            self.il.EmitWriteLine('%s' % gv.value)
        else:
            assert False

    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        op = ops.Call(self, sigtoken, gv_fnptr, args_gv)
        self.emit(op)
        return op.gv_res()

    def genop_same_as(self, kindtoken, gv_x):
        op = ops.SameAs(self, gv_x)
        self.emit(op)
        return op.gv_res()
        
    def emit(self, op):
        op.emit()

    def appendbranch(self, branch):
        self.branches.append(branch)

    def appendreturn(self, retlabel, gv_returnvar):
        self.returnblocks.append((retlabel, gv_returnvar))

    def start_writing(self):
        self.isOpen = True

    def finish_and_return(self, sigtoken, gv_returnvar):
        retlabel = self.il.DefineLabel()
        op = ops.Branch(self, None, OpCodes.Br, retlabel)
        self.emit(op)
        self.appendreturn(retlabel, gv_returnvar)
        self.isOpen = False

    def finish_and_goto(self, outputargs_gv, target):
        inputargs_gv = target.inputargs_gv
        assert len(inputargs_gv) == len(outputargs_gv)
        op = ops.FollowLink(self, outputargs_gv, inputargs_gv, target.label)
        self.emit(op)
        self.isOpen = False

    def end(self):
        # render all the pending branches
        for branch in self.branches:
            branch.replayops()

        # render the return blocks for last, else the verifier could complain
        for retlabel, gv_returnvar in self.returnblocks:
            self.il.MarkLabel(retlabel)
            op = ops.Return(self, gv_returnvar)
            self.emit(op)

        # initialize the array of genconsts
        consts = new_array(System.Object, len(self.genconsts))
        for gv_const, i in self.genconsts.iteritems():
            consts[i] = gv_const.getobj()
        # build the delegate
        myfunc = self.meth.CreateDelegate(self.delegatetype, consts)
        self.gv_entrypoint.holder.SetFunc(myfunc)

    def enter_next_block(self, kinds, args_gv):
        for i in range(len(args_gv)):
            op = ops.SameAs(self, args_gv[i])
            op.emit()
            args_gv[i] = op.gv_res()
        label = self.il.DefineLabel()
        self.emit(ops.MarkLabel(self, label))
        return Label(label, args_gv)

    def _jump_if(self, gv_condition, opcode):
        label = self.il.DefineLabel()
        op = ops.Branch(self, gv_condition, opcode, label)
        self.emit(op)
        branch = BranchBuilder(self, label)
        self.appendbranch(branch)
        return branch

    def jump_if_false(self, gv_condition, args_for_jump_gv):
        return self._jump_if(gv_condition, OpCodes.Brfalse)

    def jump_if_true(self, gv_condition, args_for_jump_gv):
        return self._jump_if(gv_condition, OpCodes.Brtrue)

class BranchBuilder(Builder):

    def __init__(self, parent, label):
        self.parent = parent
        self.label = label
        self.il = parent.il
        self.operations = []
        self.isOpen = False
        self.genconsts = parent.genconsts

    def start_writing(self):
        self.isOpen = True

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        # XXX: this only serves to mask a bug in gencli which I don't
        # feel like fixing now. Try to uncomment this and run
        # test_goto_compile to see why it fails
        return Builder.genop2(self, opname, gv_arg1, gv_arg2)

    def emit(self, op):
        self.operations.append(op)

    def appendbranch(self, branch):
        self.parent.appendbranch(branch)

    def appendreturn(self, retlabel, gv_returnvar):
        self.parent.appendreturn(retlabel, gv_returnvar)

    def end(self):
        self.parent.end()

    def replayops(self):
        assert not self.isOpen
        assert not self.parent.isOpen
        il = self.parent.il
        il.MarkLabel(self.label)        
        for op in self.operations:
            op.emit()

global_rgenop = RCliGenOp()
RCliGenOp.constPrebuiltGlobal = global_rgenop.genconst
