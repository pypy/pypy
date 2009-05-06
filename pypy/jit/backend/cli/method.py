import py
from pypy.tool.pairtype import extendabletype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli import dotnet
from pypy.translator.cli.dotnet import CLR
from pypy.translator.cli import opcodes
from pypy.jit.metainterp import history
from pypy.jit.metainterp.history import (AbstractValue, Const, ConstInt,
                                         ConstObj)
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.jit.backend.cli import runner
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
        index = meth.get_index_for_constant(self)
        meth.av_consts.load(meth)
        meth.il.Emit(OpCodes.Ldc_I4, index)
        meth.il.Emit(OpCodes.Ldelem_Ref)

    def store(self, meth):
        assert False, 'cannot store() to Constant'

class __extend__(ConstInt):
    __metaclass__ = extendabletype

    def load(self, meth):
        meth.il.Emit(OpCodes.Ldc_I4, self.value)

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

    operations = [] # overwritten at the end of the module

    def __init__(self, cpu, name, loop):
        self.cpu = cpu
        self.name = name
        self.loop = loop
        self.boxes = {}       # box --> local var
        self.failing_ops = [] # index --> op
        self.branches = []
        self.branchlabels = []
        self.consts = {}      # object --> index
        self.meth_wrapper = self._get_meth_wrapper()
        self.il = self.meth_wrapper.get_il_generator()
        self.av_consts = MethodArgument(0, System.Type.GetType("System.Object[]"))
        t_InputArgs = dotnet.typeof(InputArgs)
        self.av_inputargs = MethodArgument(1,t_InputArgs )
        self.exc_value_field = t_InputArgs.GetField('exc_value')
        # ----
        self.emit_load_inputargs()
        self.emit_preamble()
        self.emit_operations(loop.operations)
        self.emit_branches()
        self.emit_end()
        # ----
        self.finish_code()

    def finish_code(self):
        delegatetype = dotnet.typeof(LoopDelegate)
        # initialize the array of genconsts
        consts = dotnet.new_array(System.Object, len(self.consts))
        for av_const, i in self.consts.iteritems():
            consts[i] = dotnet.cast_to_native_object(av_const.getobj())
        # build the delegate
        func = self.meth_wrapper.create_delegate(delegatetype, consts)
        self.func = dotnet.clidowncast(func, LoopDelegate)

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

    def get_index_for_failing_op(self, op):
        try:
            return self.failing_ops.index(op)
        except ValueError:
            self.failing_ops.append(op)
            return len(self.failing_ops)-1

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

    def emit_preamble(self):
        self.il_loop_start = self.il.DefineLabel()
        self.il.MarkLabel(self.il_loop_start)

    def emit_operations(self, operations):
        for op in operations:
            func = self.operations[op.opnum]
            assert func is not None
            func(self, op)

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
                self.emit_operations(op.suboperations)

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

    def emit_clear_exception(self):
        self.av_inputargs.load(self)
        self.il.Emit(OpCodes.Ldnull)
        self.il.Emit(OpCodes.Stfld, self.exc_value_field)

    def emit_raising_op(self, op, emit_op, exctypes):
        self.emit_clear_exception()
        lbl = self.il.BeginExceptionBlock()
        emit_op(self, op)
        self.il.Emit(OpCodes.Leave, lbl)
        for exctype in exctypes:
            v = self.il.DeclareLocal(exctype)
            self.il.BeginCatchBlock(exctype)
            self.il.Emit(OpCodes.Stloc, v)
            self.av_inputargs.load(self)
            self.il.Emit(OpCodes.Ldloc, v)
            self.il.Emit(OpCodes.Stfld, self.exc_value_field)
        self.il.EndExceptionBlock()

    # --------------------------------

    def emit_op_fail(self, op):
        # store the index of the failed op
        index_op = self.get_index_for_failing_op(op)
        self.av_inputargs.load(self)
        self.il.Emit(OpCodes.Ldc_I4, index_op)
        field = dotnet.typeof(InputArgs).GetField('failed_op')
        self.il.Emit(OpCodes.Stfld, field)
        # store the lates values
        i = 0
        for box in op.args:
            self.store_inputarg(i, box.type, box.getCliType(), box)
            i+=1
        self.il.Emit(OpCodes.Ret)

    def emit_guard_bool(self, op, opcode):
        assert op.suboperations
        assert len(op.args) == 1
        il_label = self.newbranch(op)
        op.args[0].load(self)
        self.il.Emit(opcode, il_label)

    def emit_op_guard_true(self, op):
        self.emit_guard_bool(op, OpCodes.Brfalse)
        
    def emit_op_guard_false(self, op):
        self.emit_guard_bool(op, OpCodes.Brtrue)

    def emit_op_guard_value(self, op):
        assert op.suboperations
        assert len(op.args) == 2
        il_label = self.newbranch(op)
        self.push_all_args(op)
        self.il.Emit(OpCodes.Bne_Un, il_label)

    def emit_op_guard_class(self, op):
        assert op.suboperations
        assert len(op.args) == 2
        il_label = self.newbranch(op)
        self.push_arg(op, 0)
        meth = dotnet.typeof(System.Object).GetMethod("GetType")
        self.il.Emit(OpCodes.Callvirt, meth)
        self.push_arg(op, 1)
        self.il.Emit(OpCodes.Bne_Un, il_label)

    def emit_op_guard_no_exception(self, op):
        assert op.suboperations
        il_label = self.newbranch(op)
        self.av_inputargs.load(self)
        self.il.Emit(OpCodes.Ldfld, self.exc_value_field)
        self.il.Emit(OpCodes.Brtrue, il_label)

    def emit_op_jump(self, op):
        target = op.jump_target
        assert target is self.loop, 'TODO'
        assert len(op.args) == len(target.inputargs)
        i = 0
        for i in range(len(op.args)):
            op.args[i].load(self)
            target.inputargs[i].store(self)
        self.il.Emit(OpCodes.Br, self.il_loop_start)

    def emit_op_new_with_vtable(self, op):
        assert isinstance(op.args[0], ConstObj)
        cls = ootype.cast_from_object(ootype.Class, op.args[0].getobj())
        raise NotImplementedError # XXX finish me

    def emit_op_ooidentityhash(self, op):
        raise NotImplementedError

    def emit_op_call(self, op):
        calldescr = op.descr
        assert isinstance(calldescr, runner.StaticMethDescr)
        delegate_type = dotnet.class2type(calldescr.funcclass)
        meth_invoke = delegate_type.GetMethod('Invoke')
        av_sm, args_av = op.args[0], op.args[1:]
        av_sm.load(self)
        self.il.Emit(OpCodes.Castclass, delegate_type)
        for av_arg in args_av:
            av_arg.load(self)
        self.il.EmitCall(OpCodes.Callvirt, meth_invoke, None)
        if calldescr.has_result:
            self.store_result(op)

    emit_op_call_pure = emit_op_call

    def emit_op_oosend(self, op):
        methdescr = op.descr
        assert isinstance(methdescr, runner.MethDescr)
        clitype = dotnet.class2type(methdescr.selfclass)
        methinfo = clitype.GetMethod(str(methdescr.methname))
        av_sm, args_av = op.args[0], op.args[1:]
        av_sm.load(self)
        self.il.Emit(OpCodes.Castclass, clitype)
        for av_arg in args_av:
            av_arg.load(self)
        self.il.Emit(OpCodes.Callvirt, methinfo)
        if methdescr.has_result:
            self.store_result(op)

    emit_op_oosend_pure = emit_op_oosend


    def not_implemented(self, op):
        raise NotImplementedError

    emit_op_guard_exception = not_implemented
    emit_op_cast_int_to_ptr = not_implemented
    emit_op_guard_nonvirtualized = not_implemented
    emit_op_setarrayitem_gc = not_implemented
    emit_op_unicodelen = not_implemented
    emit_op_setfield_raw = not_implemented
    emit_op_cast_ptr_to_int = not_implemented
    emit_op_newunicode = not_implemented
    emit_op_new_array = not_implemented
    emit_op_unicodegetitem = not_implemented
    emit_op_strgetitem = not_implemented
    emit_op_getfield_raw = not_implemented
    emit_op_setfield_gc = not_implemented
    emit_op_getarrayitem_gc_pure = not_implemented
    emit_op_arraylen_gc = not_implemented
    emit_op_unicodesetitem = not_implemented
    emit_op_getfield_raw_pure = not_implemented
    emit_op_getfield_gc_pure = not_implemented
    emit_op_getarrayitem_gc = not_implemented
    emit_op_getfield_gc = not_implemented
    emit_op_strlen = not_implemented
    emit_op_newstr = not_implemented
    emit_op_strsetitem = not_implemented


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
        else:
            if not isinstance(instr, str):
                print 'WARNING: unknown instruction %s' % instr
                return

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
    impl_func = render_op(methname + '_impl', value.instr)
    if not impl_func:
        return
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
