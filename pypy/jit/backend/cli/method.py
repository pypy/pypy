import py
import os
from pypy.rlib.debug import debug_start, debug_stop
from pypy.tool.pairtype import extendabletype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli import dotnet
from pypy.translator.cli.dotnet import CLR
from pypy.translator.cli import opcodes
from pypy.jit.metainterp import history
from pypy.jit.metainterp.history import (AbstractValue, Const, ConstInt, ConstFloat,
                                         ConstObj, BoxInt, LoopToken)
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.jit.metainterp.typesystem import oohelper
from pypy.jit.backend.cli import runner
from pypy.jit.backend.cli.methodfactory import get_method_wrapper

System = CLR.System
OpCodes = System.Reflection.Emit.OpCodes
LoopDelegate = CLR.pypy.runtime.LoopDelegate
DelegateHolder = CLR.pypy.runtime.DelegateHolder
InputArgs = CLR.pypy.runtime.InputArgs
ListOfVoid = CLR.pypy.runtime.ListOfVoid
Utils = CLR.pypy.runtime.Utils

cVoid = ootype.nullruntimeclass

class __extend__(AbstractValue):
    __metaclass__ = extendabletype

    def getCliType(self, meth):
        if self in meth.box2type:
            return meth.box2type[self]
        
        if self.type == history.INT:
            return dotnet.typeof(System.Int32)
        elif self.type == history.FLOAT:
            return dotnet.typeof(System.Double)
        elif self.type == history.REF:
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
        index = meth.get_index_for_constant(self)
        meth.av_consts.load(meth)
        meth.il.Emit(OpCodes.Ldc_I4, index)
        meth.il.Emit(OpCodes.Ldelem_Ref)

    def store(self, meth):
        assert False, 'cannot store() to Constant'

    def get_cliobj(self):
        return dotnet.cast_to_native_object(self.getref_base())

class __extend__(ConstInt):
    __metaclass__ = extendabletype

    def load(self, meth):
        meth.il.Emit(OpCodes.Ldc_I4, self.value)


class __extend__(ConstFloat):
    __metaclass__ = extendabletype

    def load(self, meth):
        # we cannot invoke il.Emit(Ldc_R8, self.value) directly because
        # pythonnet would select the wrong overload. The C# version works
        # arond it
        Utils.Emit_Ldc_R8(meth.il, self.value);


class ConstFunction(Const):

    def __init__(self, name):
        self.name = name
        self.holder = DelegateHolder()

    def get_cliobj(self):
        return dotnet.cliupcast(self.holder, System.Object)

    def load(self, meth):
        holdertype = self.holder.GetType()
        funcfield = holdertype.GetField('func')
        Const.load(self, meth)
        meth.il.Emit(OpCodes.Castclass, holdertype)
        meth.il.Emit(OpCodes.Ldfld, funcfield)
        meth.il.Emit(OpCodes.Castclass, dotnet.typeof(LoopDelegate))

    def _getrepr_(self):
        return '<ConstFunction %s>' % self.name

    def __hash__(self):
        return hash(self.holder)


class MethodArgument(AbstractValue):
    def __init__(self, index, cliType):
        self.index = index
        self.cliType = cliType

    def getCliType(self, meth):
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

    operations = [] # overwritten at the end of the module
    debug = False
    tailcall = True
    nocast = True

    def __init__(self, cpu, cliloop):
        self.setoptions()
        self.cpu = cpu
        self.name = cliloop.get_fresh_cli_name()
        self.cliloop = cliloop
        self.boxes = {}       # box --> local var
        self.branches = []
        self.branchlabels = []
        self.consts = {}      # object --> index
        self.meth_wrapper = self._get_meth_wrapper()
        self.il = self.meth_wrapper.get_il_generator()
        self.av_consts = MethodArgument(0, System.Type.GetType("System.Object[]"))
        t_InputArgs = dotnet.typeof(InputArgs)
        self.av_inputargs = MethodArgument(1,t_InputArgs )
        self.av_ovf_flag = BoxInt()
        self.exc_value_field = t_InputArgs.GetField('exc_value')
        if cpu.rtyper:
            self.av_OverflowError = ConstObj(ootype.cast_to_object(cpu.ll_ovf_exc))
            self.av_ZeroDivisionError = ConstObj(ootype.cast_to_object(cpu.ll_zero_exc))
        else:
            self.av_OverflowError = None
            self.av_ZeroDivisionError = None
        self.box2type = {}

    def compile(self):
        # ----
        debug_start('jit-backend-emit_ops')
        if self.nocast:
            self.compute_types()
        self.emit_load_inputargs()
        self.emit_preamble()        
        self.emit_operations(self.cliloop.operations)
        self.emit_branches()
        self.emit_end()
        debug_stop('jit-backend-emit_ops')
        # ----
        debug_start('jit-backend-finish_code')
        res = self.finish_code()
        debug_stop('jit-backend-finish_code')
        return res

    def _parseopt(self, text):
        text = text.lower()
        if text[0] == '-':
            return text[1:], False
        elif text[0] == '+':
            return text[1:], True
        else:
            return text, True

    def setoptions(self):
        opts = os.environ.get('PYPYJITOPT')
        if not opts:
            return
        parts = opts.split(' ')
        for part in parts:
            name, value = self._parseopt(part)
            if name == 'debug':
                self.debug = value
            elif name == 'tailcall':
                self.tailcall = value
            elif name == 'nocast':
                self.nocast = value
            else:
                os.write(2, 'Warning: invalid option name: %s\n' % name)

    def _collect_types(self, operations, box2classes):
        for op in operations:
            if op.opnum in (rop.GETFIELD_GC, rop.SETFIELD_GC):
                box = op.args[0]
                descr = op.descr
                assert isinstance(descr, runner.FieldDescr)
                box2classes.setdefault(box, []).append(descr.selfclass)
            if op in self.cliloop.guard2ops:
                _, suboperations = self.cliloop.guard2ops[op]
                self._collect_types(suboperations, box2classes)

    def compute_types(self):
        box2classes = {} # box --> [ootype.Class]
        self._collect_types(self.cliloop.operations, box2classes)
        for box, classes in box2classes.iteritems():
            cls = classes[0]
            for cls2 in classes[1:]:
                if ootype.subclassof(cls, cls2):
                    cls = cls2
                else:
                    assert ootype.subclassof(cls2, cls)
            self.box2type[box] = dotnet.class2type(cls)

    def finish_code(self):
        delegatetype = dotnet.typeof(LoopDelegate)
        # initialize the array of genconsts
        consts = dotnet.new_array(System.Object, len(self.consts))
        for av_const, i in self.consts.iteritems():
            consts[i] = av_const.get_cliobj()
        # build the delegate
        func = self.meth_wrapper.create_delegate(delegatetype, consts)
        return dotnet.clidowncast(func, LoopDelegate)

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
            v = self.il.DeclareLocal(box.getCliType(self))
            self.boxes[box] = v
            return v

    def match_var_fox_boxes(self, failargs, inputargs):
        failargs = [arg for arg in failargs if arg is not None]
        assert len(failargs) == len(inputargs)
        for i in range(len(failargs)):
            v = self.boxes[failargs[i]]
            self.boxes[inputargs[i]] = v

    def get_index_for_failing_op(self, op):
        try:
            return self.cpu.failing_ops.index(op)
        except ValueError:
            self.cpu.failing_ops.append(op)
            return len(self.cpu.failing_ops)-1

    def get_index_for_constant(self, obj):
        try:
            return self.consts[obj]
        except KeyError:
            index = len(self.consts)
            self.consts[obj] = index
            return index

    def newbranch(self, op):
        # sanity check, maybe we can remove it later
        for myop in self.branches:
            assert myop is not op
        il_label = self.il.DefineLabel()
        self.branches.append(op)
        self.branchlabels.append(il_label)
        return il_label

    def get_inputarg_field(self, type):
        t = dotnet.typeof(InputArgs)
        if type == history.INT:
            fieldname = 'ints'
        elif type == history.FLOAT:
            fieldname = 'floats'
        elif type == history.REF:
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
        self.emit_debug("executing: " + self.name)
        i = 0
        for box in self.cliloop.inputargs:
            self.load_inputarg(i, box.type, box.getCliType(self))
            box.store(self)
            i+=1

    def emit_preamble(self):
        self.il_loop_start = self.il.DefineLabel()
        self.il.MarkLabel(self.il_loop_start)

    def emit_operations(self, oplist):
        self.i = 0
        self.oplist = oplist
        N = len(oplist)
        while self.i < N:
            op = oplist[self.i]
            self.emit_debug(op.repr())
            func = self.operations[op.opnum]
            assert func is not None
            func(self, op)
            self.i += 1

    def emit_branches(self):
        while self.branches:
            branches = self.branches
            branchlabels = self.branchlabels
            self.branches = []
            self.branchlabels = []
            assert len(branches) == len(branchlabels)
            for i in range(len(branches)):
                op = branches[i]
                il_label = branchlabels[i]
                self.il.MarkLabel(il_label)
                self.emit_guard_subops(op)

    def emit_guard_subops(self, op):
        assert op.is_guard()
        if op in self.cliloop.guard2ops:
            inputargs, suboperations = self.cliloop.guard2ops[op]
            self.match_var_fox_boxes(op.fail_args, inputargs)
            self.emit_operations(suboperations)
        else:
            self.emit_return_failed_op(op, op.fail_args)

    def emit_end(self):
        assert self.branches == []
        self.il.Emit(OpCodes.Ret)

    # -----------------------------

    def push_all_args(self, op):
        for box in op.args:
            box.load(self)

    def push_arg(self, op, n):
        op.args[n].load(self)

    def store_result(self, op):
        op.result.store(self)

    def emit_debug(self, msg):
        if self.debug:
            self.il.EmitWriteLine(msg)

    def emit_clear_exception(self):
        self.av_inputargs.load(self)
        self.il.Emit(OpCodes.Ldnull)
        self.il.Emit(OpCodes.Stfld, self.exc_value_field)
        # clear the overflow flag
        self.il.Emit(OpCodes.Ldc_I4_0)
        self.av_ovf_flag.store(self)

    def emit_raising_op(self, op, emit_op, exctypes):
        self.emit_clear_exception()
        lbl = self.il.BeginExceptionBlock()
        emit_op(self, op)
        self.il.Emit(OpCodes.Leave, lbl)
        for exctype in exctypes:
            v = self.il.DeclareLocal(exctype)
            self.il.BeginCatchBlock(exctype)
            if exctype == dotnet.typeof(System.OverflowException) and self.av_OverflowError:
                self.il.Emit(OpCodes.Ldc_I4_1)
                self.av_ovf_flag.store(self)
            else:
                self.il.Emit(OpCodes.Stloc, v)
                self.av_inputargs.load(self)
                self.il.Emit(OpCodes.Ldloc, v)
                self.il.Emit(OpCodes.Stfld, self.exc_value_field)
        self.il.EndExceptionBlock()

    def emit_ovf_op(self, op, emit_op):
        next_op = self.oplist[self.i+1]
        if next_op.opnum == rop.GUARD_NO_OVERFLOW:
                self.i += 1
                self.emit_ovf_op_and_guard(op, next_op, emit_op)
                return
        # clear the overflow flag
        self.il.Emit(OpCodes.Ldc_I4_0)
        self.av_ovf_flag.store(self)
        lbl = self.il.BeginExceptionBlock()
        emit_op(self, op)
        self.il.Emit(OpCodes.Leave, lbl)
        self.il.BeginCatchBlock(dotnet.typeof(System.OverflowException))
        self.il.Emit(OpCodes.Ldc_I4_1)
        self.av_ovf_flag.store(self)
        self.il.EndExceptionBlock()

    def emit_ovf_op_and_guard(self, op, opguard, emit_op):
        # emit the checked operation
        lbl = self.il.BeginExceptionBlock()
        emit_op(self, op)
        self.il.Emit(OpCodes.Leave, lbl)
        self.il.BeginCatchBlock(dotnet.typeof(System.OverflowException))
        # emit the guard
        assert len(opguard.args) == 0
        il_label = self.newbranch(opguard)
        self.il.Emit(OpCodes.Leave, il_label)
        self.il.EndExceptionBlock()

    def mark(self, msg):
        self.il.Emit(OpCodes.Ldstr, msg)
        self.il.Emit(OpCodes.Pop)

    # --------------------------------

    def emit_return_failed_op(self, op, args):
        # store the index of the failed op
        index_op = self.get_index_for_failing_op(op)
        self.av_inputargs.load(self)
        self.il.Emit(OpCodes.Ldc_I4, index_op)
        field = dotnet.typeof(InputArgs).GetField('failed_op')
        self.il.Emit(OpCodes.Stfld, field)
        self.emit_store_opargs(args)
        self.il.Emit(OpCodes.Ret)

    def emit_op_finish(self, op):
        self.emit_return_failed_op(op, op.args)

    def emit_store_opargs(self, args):
        # store the latest values
        i = 0
        for box in args:
            if box is not None:
                self.store_inputarg(i, box.type, box.getCliType(self), box)
            i+=1

    def emit_guard_bool(self, op, opcode):
        assert len(op.args) == 1
        il_label = self.newbranch(op)
        op.args[0].load(self)
        self.il.Emit(opcode, il_label)

    def emit_op_guard_true(self, op):
        self.emit_guard_bool(op, OpCodes.Brfalse)
        
    def emit_op_guard_false(self, op):
        self.emit_guard_bool(op, OpCodes.Brtrue)

    def emit_op_guard_nonnull(self, op):
        self.emit_guard_bool(op, OpCodes.Brfalse)
        
    def emit_op_guard_isnull(self, op):
        self.emit_guard_bool(op, OpCodes.Brtrue)

    def emit_op_guard_value(self, op):
        assert len(op.args) == 2
        il_label = self.newbranch(op)
        self.push_all_args(op)
        self.il.Emit(OpCodes.Bne_Un, il_label)

    def emit_op_guard_class(self, op):
        assert len(op.args) == 2
        il_label = self.newbranch(op)
        self.push_arg(op, 0)
        meth = dotnet.typeof(System.Object).GetMethod("GetType")
        self.il.Emit(OpCodes.Callvirt, meth)
        self.push_arg(op, 1)
        self.il.Emit(OpCodes.Bne_Un, il_label)

    def emit_op_guard_nonnull_class(self, op):
        assert len(op.args) == 2
        il_label = self.newbranch(op)
        # nonnull check
        self.push_arg(op, 0)
        self.il.Emit(OpCodes.Brfalse, il_label)
        # class check
        self.push_arg(op, 0)
        meth = dotnet.typeof(System.Object).GetMethod("GetType")
        self.il.Emit(OpCodes.Callvirt, meth)
        self.push_arg(op, 1)
        self.il.Emit(OpCodes.Bne_Un, il_label)

    def emit_op_guard_no_exception(self, op):
        il_label = self.newbranch(op)
        self.av_inputargs.load(self)
        self.il.Emit(OpCodes.Ldfld, self.exc_value_field)
        self.il.Emit(OpCodes.Brtrue, il_label)

    def emit_op_guard_exception(self, op):
        il_label = self.newbranch(op)
        classbox = op.args[0]
        assert isinstance(classbox, ConstObj)
        oocls = classbox.getref(ootype.Class)
        clitype = dotnet.class2type(oocls)
        self.av_inputargs.load(self)
        self.il.Emit(OpCodes.Ldfld, self.exc_value_field)
        self.il.Emit(OpCodes.Isinst, clitype)
        self.il.Emit(OpCodes.Brfalse, il_label)
        # the guard succeeded, store the result
        self.av_inputargs.load(self)
        self.il.Emit(OpCodes.Ldfld, self.exc_value_field)
        self.store_result(op)

    def emit_guard_overflow_impl(self, op, opcode):
        assert len(op.args) == 0
        il_label = self.newbranch(op)
        self.av_ovf_flag.load(self)
        self.il.Emit(opcode, il_label)

    def emit_op_guard_no_overflow(self, op):
        self.emit_guard_overflow_impl(op, OpCodes.Brtrue)

    def emit_op_guard_overflow(self, op):
        self.emit_guard_overflow_impl(op, OpCodes.Brfalse)

    def emit_op_jump(self, op):
        target_token = op.descr
        assert isinstance(target_token, LoopToken)
        if target_token.cliloop is self.cliloop:
            # jump to the beginning of the loop
            i = 0
            for i in range(len(op.args)):
                op.args[i].load(self)
                self.cliloop.inputargs[i].store(self)
            self.il.Emit(OpCodes.Br, self.il_loop_start)
        else:
            # it's a real bridge
            cliloop = target_token.cliloop
            assert len(op.args) == len(cliloop.inputargs)
            self.emit_debug('jumping to ' + cliloop.name)
            self.emit_store_opargs(op.args)
            cliloop.funcbox.load(self)
            self.av_inputargs.load(self)
            methinfo = dotnet.typeof(LoopDelegate).GetMethod('Invoke')
            if self.tailcall:
                self.il.Emit(OpCodes.Tailcall)
            self.il.Emit(OpCodes.Callvirt, methinfo)
            self.il.Emit(OpCodes.Ret)

    def emit_op_new_with_vtable(self, op):
        clsbox = op.args[0]
        assert isinstance(clsbox, ConstObj)
        cls = clsbox.getref_base()
        descr = self.cpu.class_sizes[cls]
        assert isinstance(descr, runner.TypeDescr)
        clitype = descr.get_clitype()
        ctor_info = descr.get_constructor_info()
        self.il.Emit(OpCodes.Newobj, ctor_info)
        self.store_result(op)

    def emit_op_runtimenew(self, op):
        clitype_utils = dotnet.typeof(Utils)
        methinfo = clitype_utils.GetMethod('RuntimeNew')
        op.args[0].load(self)
        self.il.Emit(OpCodes.Call, methinfo)
        self.store_result(op)

    def emit_op_instanceof(self, op):
        descr = op.descr
        assert isinstance(descr, runner.TypeDescr)
        clitype = descr.get_clitype()
        op.args[0].load(self)
        self.il.Emit(OpCodes.Isinst, clitype)
        self.il.Emit(OpCodes.Ldnull)
        self.il.Emit(OpCodes.Cgt_Un)
        self.store_result(op)

    def emit_op_subclassof(self, op):
        clitype_utils = dotnet.typeof(Utils)
        methinfo = clitype_utils.GetMethod('SubclassOf')
        op.args[0].load(self)
        op.args[1].load(self)
        self.il.Emit(OpCodes.Call, methinfo)
        self.store_result(op)

    def emit_op_call_impl(self, op):
        descr = op.descr
        assert isinstance(descr, runner.StaticMethDescr)
        delegate_type = descr.get_delegate_clitype()
        meth_invoke = descr.get_meth_info()
        self._emit_call(op, OpCodes.Callvirt, delegate_type,
                        meth_invoke, descr.has_result)

    def emit_op_call(self, op):
        emit_op = Method.emit_op_call_impl.im_func
        exctypes = [dotnet.typeof(System.Exception)]
        self.emit_raising_op(op, emit_op, exctypes)

    emit_op_call_pure = emit_op_call

    def emit_op_oosend(self, op):
        descr = op.descr
        assert isinstance(descr, runner.MethDescr)
        clitype = descr.get_self_clitype()
        methinfo = descr.get_meth_info()
        opcode = descr.get_call_opcode()
        self._emit_call(op, opcode, clitype, methinfo, descr.has_result)

    emit_op_oosend_pure = emit_op_oosend

    def _emit_call(self, op, opcode, clitype, methinfo, has_result):
        av_sm, args_av = op.args[0], op.args[1:]
        av_sm.load(self)
        self.il.Emit(OpCodes.Castclass, clitype)
        for av_arg in args_av:
            av_arg.load(self)
        self.il.Emit(opcode, methinfo)
        if has_result:
            self.store_result(op)

    def emit_op_getfield_gc(self, op):
        descr = op.descr
        assert isinstance(descr, runner.FieldDescr)
        clitype = descr.get_self_clitype()
        fieldinfo = descr.get_field_info()
        obj = op.args[0]
        obj.load(self)
        if obj.getCliType(self) is not clitype:
            self.il.Emit(OpCodes.Castclass, clitype)
        self.il.Emit(OpCodes.Ldfld, fieldinfo)
        self.store_result(op)
    
    emit_op_getfield_gc_pure = emit_op_getfield_gc

    def emit_op_setfield_gc(self, op):
        descr = op.descr
        assert isinstance(descr, runner.FieldDescr)
        clitype = descr.get_self_clitype()
        fieldinfo = descr.get_field_info()
        obj = op.args[0]
        obj.load(self)
        if obj.getCliType(self) is not clitype:
            self.il.Emit(OpCodes.Castclass, clitype)
        op.args[1].load(self)
        self.il.Emit(OpCodes.Stfld, fieldinfo)

    def emit_op_getarrayitem_gc(self, op):
        descr = op.descr
        assert isinstance(descr, runner.TypeDescr)
        clitype = descr.get_array_clitype()
        itemtype = descr.get_clitype()
        op.args[0].load(self)
        self.il.Emit(OpCodes.Castclass, clitype)
        op.args[1].load(self)
        self.il.Emit(OpCodes.Ldelem, itemtype)
        self.store_result(op)
    
    emit_op_getarrayitem_gc_pure = emit_op_getarrayitem_gc

    def emit_op_setarrayitem_gc(self, op):
        descr = op.descr
        assert isinstance(descr, runner.TypeDescr)
        clitype = descr.get_array_clitype()
        itemtype = descr.get_clitype()
        op.args[0].load(self)
        self.il.Emit(OpCodes.Castclass, clitype)
        op.args[1].load(self)
        op.args[2].load(self)
        self.il.Emit(OpCodes.Stelem, itemtype)

    def emit_op_arraylen_gc(self, op):
        descr = op.descr
        assert isinstance(descr, runner.TypeDescr)
        clitype = descr.get_array_clitype()
        op.args[0].load(self)
        self.il.Emit(OpCodes.Castclass, clitype)
        self.il.Emit(OpCodes.Ldlen)
        self.store_result(op)

    def emit_op_new_array(self, op):
        descr = op.descr
        assert isinstance(descr, runner.TypeDescr)
        item_clitype = descr.get_clitype()
        if item_clitype is None:
            return self.emit_new_arrayofvoids(op)
        op.args[0].load(self)
        self.il.Emit(OpCodes.Newarr, item_clitype)
        self.store_result(op)

    def emit_new_arrayofvoids(self, op):
        clitype = dotnet.typeof(ListOfVoid)
        ctor = clitype.GetConstructor(dotnet.new_array(System.Type, 0))
        _ll_resize = clitype.GetMethod('_ll_resize')
        self.il.Emit(OpCodes.Newobj, ctor)
        self.il.Emit(OpCodes.Dup)
        op.args[0].load(self)
        self.il.Emit(OpCodes.Callvirt, _ll_resize)
        self.store_result(op)

    def emit_op_debug_merge_point(self, op):
        pass

    def lltype_only(self, op):
        print 'Operation %s is lltype specific, should not get here!' % op.getopname()
        raise NotImplementedError

    emit_op_new = lltype_only
    emit_op_setfield_raw = lltype_only
    emit_op_getfield_raw = lltype_only
    emit_op_getfield_raw_pure = lltype_only
    emit_op_strsetitem = lltype_only
    emit_op_unicodesetitem = lltype_only
    emit_op_cast_int_to_ptr = lltype_only
    emit_op_cast_ptr_to_int = lltype_only
    emit_op_newstr = lltype_only
    emit_op_strlen = lltype_only
    emit_op_strgetitem = lltype_only
    emit_op_newunicode = lltype_only    
    emit_op_unicodelen = lltype_only
    emit_op_unicodegetitem = lltype_only
    emit_op_cond_call_gc_wb = lltype_only
    emit_op_setarrayitem_raw = lltype_only


# --------------------------------------------------------------------
    
# the follwing functions automatically build the various emit_op_*
# operations based on the definitions in translator/cli/opcodes.py

def make_operation_list():
    operations = [None] * (rop._LAST+1)
    for key, value in rop.__dict__.items():
        key = key.lower()
        if key.startswith('_'):
            continue
        methname = 'emit_op_%s' % key
        if hasattr(Method, methname):
            func = getattr(Method, methname).im_func
        else:
            instrlist = opcodes.opcodes[key]
            func = render_op(methname, instrlist)
        operations[value] = func
    return operations

def is_raising_op(instrlist):
    return len(instrlist) == 1 and isinstance(instrlist[0], opcodes.MapException)
        
def render_op(methname, instrlist):
    if is_raising_op(instrlist):
        return render_raising_op(methname, instrlist)
    lines = []
    for instr in instrlist:
        if instr == opcodes.PushAllArgs:
            lines.append('self.push_all_args(op)')
        elif instr == opcodes.StoreResult:
            lines.append('self.store_result(op)')
        elif isinstance(instr, opcodes.PushArg):
            lines.append('self.push_arg(op, %d)' % instr.n)
        elif instr == 'ldc.r8 0':
            lines.append('Utils.Emit_Ldc_R8(self.il, 0.0)')
        else:
            assert isinstance(instr, str), 'unknown instruction %s' % instr
            if instr.startswith('call '):
                signature = instr[len('call '):]
                renderCall(lines, signature)
            else:
                attrname = opcode2attrname(instr)
                lines.append('self.il.Emit(OpCodes.%s)' % attrname)
    body = py.code.Source('\n'.join(lines))
    src = body.putaround('def %s(self, op):' % methname)
    dic = {'OpCodes': OpCodes,
           'System': System,
           'Utils': Utils,
           'dotnet': dotnet}
    exec src.compile() in dic
    return dic[methname]

def parse_exctype(exctype):
    assert exctype.startswith('[mscorlib]')
    return exctype[len('[mscorlib]'):]
    

def render_raising_op(methname, instrlist):
    value = instrlist[0]
    exctypes = [parse_exctype(exctype) for exctype, _ in value.mapping]
    exctypes = ['dotnet.typeof(%s)' % exctype for exctype in exctypes]
    is_ovf = (exctypes == ['dotnet.typeof(System.OverflowException)'])
    impl_func = render_op(methname + '_impl', value.instr)
    if not impl_func:
        return
    if is_ovf:
        src = py.code.Source("""
            def %s(self, op):
                self.emit_ovf_op(op, impl_func)
        """ % (methname,))
    else:
        src = py.code.Source("""
            def %s(self, op):
                exctypes = [%s]
                self.emit_raising_op(op, impl_func, exctypes)
        """ % (methname, ', '.join(exctypes)))
    dic = {'System': System,
           'dotnet': dotnet,
           'impl_func': impl_func}
    exec src.compile() in dic
    return dic[methname]

def opcode2attrname(opcode):
    if opcode == 'ldc.r8 0':
        return 'Ldc_R8, 0' # XXX this is a hack
    if opcode == 'ldc.i8 0':
        return 'Ldc_I8, 0' # XXX this is a hack
    parts = map(str.capitalize, opcode.split('.'))
    return '_'.join(parts)

def renderCall(body, signature):
    # signature is like this:
    # int64 class [mscorlib]System.Foo::Bar(int64, int32)

    typenames = {
        'int32': 'System.Int32',
        'int64': 'System.Int64',
        'float64': 'System.Double',
        }
    
    restype, _, signature = signature.split(' ', 3)
    assert signature.startswith('[mscorlib]'), 'external assemblies '\
                                               'not supported'
    signature = signature[len('[mscorlib]'):]
    typename, signature = signature.split('::')
    methname, signature = signature.split('(')
    assert signature.endswith(')')
    params = signature[:-1].split(',')
    params = map(str.strip, params)
    params = [typenames.get(p, p) for p in params]
    params = ['dotnet.typeof(%s)' % p for p in params]

    body.append("t = System.Type.GetType('%s')" % typename)
    body.append("params = dotnet.init_array(System.Type, %s)" % ', '.join(params))
    body.append("methinfo = t.GetMethod('%s', params)" % methname)
    body.append("self.il.Emit(OpCodes.Call, methinfo)")

Method.operations = make_operation_list()
