from pypy.tool.pairtype import extendabletype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli import dotnet
from pypy.translator.cli.dotnet import CLR
from pypy.jit.metainterp import history
from pypy.jit.metainterp.history import AbstractValue, Const
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.jit.backend.cli.methodfactory import get_method_wrapper

System = CLR.System
OpCodes = System.Reflection.Emit.OpCodes
LoopDelegate = CLR.pypy.runtime.LoopDelegate
InputArgs = CLR.pypy.runtime.InputArgs

cVoid = ootype.nullruntimeclass


class __extend__(AbstractValue):
    __metaclass__ = extendabletype

    def getCliType(self):
        if self.type == history.INT:
            return dotnet.typeof(System.Int32)
        elif self.type == history.OBJ:
            return dotnet.typeof(System.Object)
        else:
            assert False, 'Unknown type: %s' % self.type

    def load(self, meth):
        v = meth.var_for_box(self)
        meth.il.Emit(OpCodes.Ldloc, v)

    def store(self, meth):
        v = meth.var_for_box(self)
        meth.il.Emit(OpCodes.Stloc, v)


class __extend__(Const):
    __metaclass__ = extendabletype

    def load(self, meth):
        raise NotImplementedError

    def store(self, meth):
        assert False, 'cannot store() to Constant'


class MethodArgument(AbstractValue):
    def __init__(self, index, cliType):
        self.index = index
        self.cliType = cliType

    def getCliType(self):
        return self.cliType

    def load(self, meth):
        if self.index == 0:
            meth.il.Emit(OpCodes.Ldarg_0)
        elif self.index == 1:
            meth.il.Emit(OpCodes.Ldarg_1)
        elif self.index == 2:
            meth.il.Emit(OpCodes.Ldarg_2)
        elif self.index == 3:
            meth.il.Emit(OpCodes.Ldarg_3)
        else:
            meth.il.Emit(OpCodes.Ldarg, self.index)

    def store(self, meth):
        meth.il.Emit(OpCodes.Starg, self.index)

    def __repr__(self):
        return "MethodArgument(%d)" % self.index


class Method(object):

    def __init__(self, cpu, name, loop):
        self.cpu = cpu
        self.name = name
        self.loop = loop
        self.boxes = {} # box --> local var
        self.meth_wrapper = self._get_meth_wrapper()
        self.il = self.meth_wrapper.get_il_generator()
        self.av_consts = MethodArgument(0, System.Type.GetType("System.Object[]"))
        self.av_inputargs = MethodArgument(1, dotnet.typeof(InputArgs))
        self.emit_load_inputargs()
        self.emit_operations()
        self.emit_end()
        delegatetype = dotnet.typeof(LoopDelegate)
        consts = dotnet.new_array(System.Object, 0)
        self.func = self.meth_wrapper.create_delegate(delegatetype, consts)


    def _get_meth_wrapper(self):
        restype = dotnet.class2type(cVoid)
        args = self._get_args_array([dotnet.typeof(InputArgs)])
        return get_method_wrapper(self.name, restype, args)

    def _get_args_array(self, arglist):
        array = dotnet.new_array(System.Type, len(arglist)+1)
        array[0] = System.Type.GetType("System.Object[]")
        for i in range(len(arglist)):
            array[i+1] = arglist[i]
        return array

    def var_for_box(self, box):
        try:
            return self.boxes[box]
        except KeyError:
            v = self.il.DeclareLocal(box.getCliType())
            self.boxes[box] = v
            return v

    def get_inputarg_field(self, type):
        t = dotnet.typeof(InputArgs)
        if type == history.INT:
            fieldname = 'ints'
        elif type == history.OBJ:
            fieldname = 'objs'
        else:
            assert False, 'Unknown type %s' % type
        return t.GetField(fieldname)        

    def load_inputarg(self, i, type, clitype):
        field = self.get_inputarg_field(type)
        self.av_inputargs.load(self)
        self.il.Emit(OpCodes.Ldfld, field)
        self.il.Emit(OpCodes.Ldc_I4, i)
        self.il.Emit(OpCodes.Ldelem, clitype)

    def store_inputarg(self, i, type, clitype, valuebox):
        field = self.get_inputarg_field(type)
        self.av_inputargs.load(self)
        self.il.Emit(OpCodes.Ldfld, field)
        self.il.Emit(OpCodes.Ldc_I4, i)
        valuebox.load(self)
        self.il.Emit(OpCodes.Stelem, clitype)

    def emit_load_inputargs(self):
        i = 0
        for box in self.loop.inputargs:
            self.load_inputarg(i, box.type, box.getCliType())
            box.store(self)
            i+=1

    def emit_operations(self):
        for op in self.loop.operations:
            if op.opnum == rop.INT_LSHIFT:
                for box in op.args:
                    box.load(self)
                self.il.Emit(OpCodes.Shl)
                op.result.store(self)
            elif op.opnum == rop.FAIL:
                i = 0
                for box in op.args:
                    self.store_inputarg(i, box.type,
                                        box.getCliType(), box)
                self.il.Emit(OpCodes.Ret)
            else:
                assert False, 'TODO'

    def emit_end(self):
        self.il.Emit(OpCodes.Ret)
