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
                loc = self.builder.il.DeclareLocal(restype)
                self._gv_res = GenLocalVar(loc)
        return self._gv_res

    def emit(self):
        raise NotImplementedError

    def pushAllArgs(self):
        raise NotImplementedError

    def storeResult(self):
        self.gv_res().store(self.builder)


class UnaryOp(Operation):
    def __init__(self, builder, gv_x):
        self.builder = builder
        self.gv_x = gv_x

    def pushAllArgs(self):
        self.gv_x.load(self.builder)

    def emit(self):
        self.pushAllArgs()
        self.builder.il.Emit(self.getOpCode())
        self.storeResult()

    def getOpCode(self):
        raise NotImplementedError

class BinaryOp(Operation):
    def __init__(self, builder, gv_x, gv_y):
        self.builder = builder
        self.gv_x = gv_x
        self.gv_y = gv_y

    def pushAllArgs(self):
        self.gv_x.load(self.builder)
        self.gv_y.load(self.builder)

    def emit(self):
        self.pushAllArgs()
        self.builder.il.Emit(self.getOpCode())
        self.storeResult()

    def getOpCode(self):
        raise NotImplementedError


class SameAs(UnaryOp):
    def emit(self):
        gv_res = self.gv_res()
        self.gv_x.load(self.builder)
        self.gv_res().store(self.builder)

class MarkLabel(Operation):

    def __init__(self, builder, label):
        self.builder = builder
        self.label = label

    def restype(self):
        return None

    def emit(self):
        self.builder.il.MarkLabel(self.label)

class FollowLink(Operation):
    
    def __init__(self, builder, outputargs_gv, inputargs_gv, label):
        self.builder = builder
        self.outputargs_gv = outputargs_gv
        self.inputargs_gv = inputargs_gv
        self.label = label

    def restype(self):
        return None

    def emit(self):
        for i in range(len(self.outputargs_gv)):
            self.outputargs_gv[i].load(self.builder)
            self.inputargs_gv[i].store(self.builder)
        self.builder.il.Emit(OpCodes.Br, self.label)

class Branch(Operation):
    
    def __init__(self, builder, gv_cond, opcode, label):
        self.builder = builder
        self.gv_cond = gv_cond
        self.opcode = opcode
        self.label = label

    def restype(self):
        return None

    def emit(self):
        if self.gv_cond is not None:
            self.gv_cond.load(self.builder)
        self.builder.il.Emit(self.opcode, self.label)

class Return(Operation):

    def __init__(self, builder, gv_x):
        self.builder = builder
        self.gv_x = gv_x

    def restype(self):
        return None

    def emit(self):
        self.gv_x.load(self.builder)
        self.builder.il.Emit(OpCodes.Ret)

class Call(Operation):

    def __init__(self, builder, sigtoken, gv_fnptr, args_gv):
        from pypy.jit.codegen.cli.rgenop import class2type
        self.builder = builder
        self.sigtoken = sigtoken
        self.gv_fnptr = gv_fnptr
        self.args_gv = args_gv
        self._restype = class2type(sigtoken.res)

    def restype(self):
        return self._restype

    def emit(self):
        from pypy.jit.codegen.cli.rgenop import class2type
        delegate_type = class2type(self.sigtoken.funcclass)
        meth_invoke = delegate_type.GetMethod('Invoke')
        self.gv_fnptr.load(self.builder)
        self.builder.il.Emit(OpCodes.Castclass, delegate_type)
        for gv_arg in self.args_gv:
            gv_arg.load(self.builder)
        self.builder.il.EmitCall(OpCodes.Callvirt, meth_invoke, None)
        self.storeResult()

        

def opcode2attrname(opcode):
    if opcode == 'ldc.r8 0':
        return 'Ldc_R8, 0' # XXX this is a hack
    if opcode == 'ldc.i8 0':
        return 'Ldc_I8, 0' # XXX this is a hack
    parts = map(str.capitalize, opcode.split('.'))
    return '_'.join(parts)

def is_comparison(opname):
    suffixes = '_lt _le _eq _ne _gt _ge'.split()
    for suffix in suffixes:
        if opname.endswith(suffix):
            return True
    return False

def restype_bool(self):     return typeof(System.Boolean)
def restype_int(self):      return typeof(System.Int32)
def restype_uint(self):     return typeof(System.Int32)
def restype_float(self):    return typeof(System.Double)
def restype_char(self):     return typeof(System.Char)
def restype_unichar(self):  return typeof(System.Char)
def restype_longlong(self): return typeof(System.Int64)

def fillops(ops, baseclass):
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
        elif value is cli_opcodes.DoNothing:
            out[opname] = SameAs
        else:
            renderCustomOp(opname, baseclass, value, out)

        # fix the restype for comparison ops and casts
        if is_comparison(opname):
            out[opname].restype = restype_bool
        elif opname != 'cast_primitive' and opname.startswith('cast_'):
            _, _, _, to = opname.split('_')
            funcname = 'restype_%s' % to
            out[opname].restype = globals()[funcname]

    return out

def renderCustomOp(opname, baseclass, steps, out):
    assert steps
    body = []
    for step in steps:
        if step is cli_opcodes.PushAllArgs:
            body.append('self.pushAllArgs()')
        elif step is cli_opcodes.StoreResult:
            body.append('self.storeResult()')
        elif isinstance(step, str):
            if 'call' in step:
                return # XXX, fix this
            attrname = opcode2attrname(step)
            body.append('self.builder.il.Emit(OpCodes.%s)' % attrname)
        elif isinstance(step, cli_opcodes.MapException):
            return # XXX, TODO
        else:
            return # ignore it for now

    if cli_opcodes.StoreResult not in steps:
        body.append('self.storeResult()')

    emit = py.code.Source('\n'.join(body))
    emit = emit.putaround('def emit(self):')
    source = emit.putaround('class %(opname)s (%(baseclass)s):' % locals())
    code = source.compile()
    exec code in globals(), out


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
