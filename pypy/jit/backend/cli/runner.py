from pypy.tool.pairtype import extendabletype
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.metainterp import history
from pypy.jit.metainterp.history import AbstractDescr, AbstractMethDescr
from pypy.jit.metainterp.history import AbstractFailDescr, LoopToken
from pypy.jit.metainterp.history import Box, BoxInt, BoxObj, ConstObj, Const
from pypy.jit.metainterp import executor
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.jit.backend import model
from pypy.jit.backend.llgraph.runner import KeyManager
from pypy.translator.cli import dotnet
from pypy.translator.cli.dotnet import CLR
from pypy.jit.metainterp.typesystem import oohelper

System = CLR.System
OpCodes = System.Reflection.Emit.OpCodes
InputArgs = CLR.pypy.runtime.InputArgs
cpypyString = dotnet.classof(CLR.pypy.runtime.String)

LoopToken.cliloop = None
AbstractFailDescr._loop_token = None
AbstractFailDescr._guard_op = None

class CliLoop(object):
    
    def __init__(self, name, inputargs, operations):
        self.name = name
        self.inputargs = inputargs
        self.operations = operations
        self.guard2ops = {}  # guard_op --> (inputargs, operations)
        self.funcbox = None
        self.methcount = 0

    def get_fresh_cli_name(self):
        name = '%s(r%d)' % (self.name, self.methcount)
        self.methcount += 1
        return name


class CliCPU(model.AbstractCPU):

    supports_floats = True
    ts = oohelper

    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 mixlevelann=None, gcdescr=None):
        model.AbstractCPU.__init__(self)
        self.rtyper = rtyper
        if rtyper:
            assert rtyper.type_system.name == "ootypesystem"
        self.loopcount = 0
        self.stats = stats
        self.translate_support_code = translate_support_code
        self.inputargs = None
        self.failing_ops = [] # index --> op
        self.ll_ovf_exc = self._get_prebuilt_exc(OverflowError)
        self.ll_zero_exc = self._get_prebuilt_exc(ZeroDivisionError)

    def _get_prebuilt_exc(self, cls):
        if self.rtyper is None:
            return System.Exception()
        else:
            bk = self.rtyper.annotator.bookkeeper
            clsdef = bk.getuniqueclassdef(cls)
            return self.rtyper.exceptiondata.get_standard_ll_exc_instance(
                self.rtyper, clsdef)

    def get_inputargs(self):
        if self.inputargs is None:
            self.inputargs = InputArgs()
        return self.inputargs
    
    @staticmethod
    def calldescrof(FUNC, ARGS, RESULT, extrainfo=None):
        return StaticMethDescr.new(FUNC, ARGS, RESULT, extrainfo)

    @staticmethod
    def methdescrof(SELFTYPE, methname):
        if SELFTYPE in (ootype.String, ootype.Unicode):
            return StringMethDescr.new(SELFTYPE, methname)
        return MethDescr.new(SELFTYPE, methname)

    @staticmethod
    def typedescrof(TYPE):
        return TypeDescr.new(TYPE)

    @staticmethod
    def arraydescrof(A):
        assert isinstance(A, ootype.Array)
        TYPE = A.ITEM
        return TypeDescr.new(TYPE)

    @staticmethod
    def fielddescrof(T, fieldname):
        T1, _ = T._lookup_field(fieldname)
        return FieldDescr.new(T1, fieldname)

    def typedescr2classbox(self, descr):
        assert isinstance(descr, TypeDescr)
        return ConstObj(ootype.cast_to_object(descr.ooclass))

    # ----------------------

    def _attach_token_to_faildescrs(self, token, operations):
        for op in operations:
            if op.is_guard():
                descr = op.descr
                assert isinstance(descr, AbstractFailDescr)
                descr._loop_token = token
                descr._guard_op = op

    def compile_loop(self, inputargs, operations, looptoken):
        from pypy.jit.backend.cli.method import Method, ConstFunction
        name = 'Loop%d' % self.loopcount
        self.loopcount += 1
        cliloop = CliLoop(name, inputargs, operations)
        looptoken.cliloop = cliloop
        cliloop.funcbox = ConstFunction(cliloop.name)
        self._attach_token_to_faildescrs(cliloop, operations)
        meth = Method(self, cliloop)
        cliloop.funcbox.holder.SetFunc(meth.compile())

    def compile_bridge(self, faildescr, inputargs, operations):
        from pypy.jit.backend.cli.method import Method
        op = faildescr._guard_op
        token = faildescr._loop_token
        token.guard2ops[op] = (inputargs, operations)
        self._attach_token_to_faildescrs(token, operations)
        meth = Method(self, token)
        token.funcbox.holder.SetFunc(meth.compile())
        return token

    def execute_token(self, looptoken):
        cliloop = looptoken.cliloop
        func = cliloop.funcbox.holder.GetFunc()
        func(self.get_inputargs())
        op = self.failing_ops[self.inputargs.get_failed_op()]
        return op.descr
        
    def set_future_value_int(self, index, intvalue):
        self.get_inputargs().set_int(index, intvalue)

    def set_future_value_float(self, index, intvalue):
        self.get_inputargs().set_float(index, intvalue)

    def set_future_value_ref(self, index, objvalue):
        obj = dotnet.cast_to_native_object(objvalue)
        self.get_inputargs().set_obj(index, obj)

    def get_latest_value_int(self, index):
        return self.get_inputargs().get_int(index)

    def get_latest_value_float(self, index):
        return self.get_inputargs().get_float(index)

    def get_latest_value_ref(self, index):
        obj = self.get_inputargs().get_obj(index)
        return dotnet.cast_from_native_object(obj)

    def get_exception(self):
        exc_value = self.get_inputargs().get_exc_value()
        if exc_value:
            exc_obj = dotnet.cast_from_native_object(exc_value)
            exc_inst = ootype.cast_from_object(ootype.ROOT, exc_obj)
            cls = ootype.classof(exc_value)
            return ootype.cast_to_object(cls)
        return ootype.cast_to_object(ootype.nullruntimeclass)

    def get_exc_value(self):
        exc_value = self.get_inputargs().get_exc_value()
        if exc_value:
            return dotnet.cast_from_native_object(exc_value)
        else:
            return ootype.NULL

    def clear_exception(self):
        self.get_inputargs().set_exc_value(None)

    def get_overflow_error(self):
        exc_type = ootype.cast_to_object(ootype.classof(self.ll_ovf_exc))
        exc_value = ootype.cast_to_object(self.ll_ovf_exc)
        return exc_type, exc_value

    def get_zero_division_error(self):
        exc_type = ootype.cast_to_object(ootype.classof(self.ll_zero_exc))
        exc_value = ootype.cast_to_object(self.ll_zero_exc)
        return exc_type, exc_value

    def set_overflow_error(self):
        exc_obj = ootype.cast_to_object(self.ll_ovf_exc)
        exc_value = dotnet.cast_to_native_object(exc_obj)
        self.get_inputargs().set_exc_value(exc_value)

    def set_zero_division_error(self):
        exc_obj = ootype.cast_to_object(self.ll_zero_exc)
        exc_value = dotnet.cast_to_native_object(exc_obj)
        self.get_inputargs().set_exc_value(exc_value)

    # ----------------------

    def do_new_with_vtable(self, classbox):
        cls = classbox.getref_base()
        typedescr = self.class_sizes[cls]
        return typedescr.create()

    def do_new_array(self, lengthbox, typedescr):
        assert isinstance(typedescr, TypeDescr)
        return typedescr.create_array(lengthbox)

    def do_runtimenew(self, classbox):
        classobj = classbox.getref(ootype.Class)
        res = ootype.runtimenew(classobj)
        return BoxObj(ootype.cast_to_object(res))

    def do_instanceof(self, instancebox, typedescr):
        assert isinstance(typedescr, TypeDescr)
        return typedescr.instanceof(instancebox)

    def do_getfield_gc(self, instancebox, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        assert fielddescr.getfield is not None
        return fielddescr.getfield(instancebox)

    def do_setfield_gc(self, instancebox, newvaluebox, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        assert fielddescr.setfield is not None
        return fielddescr.setfield(instancebox, newvaluebox)

    def do_call(self, args, calldescr):
        assert isinstance(calldescr, StaticMethDescr)
        funcbox, args = args[0], args[1:]
        self.clear_exception()
        try:
            return calldescr.callfunc(funcbox, args)
        except Exception, e:
            exc_value = self._cast_instance_to_native_obj(e)
            self.get_inputargs().set_exc_value(exc_value)
            return calldescr.get_errbox()

    def _cast_instance_to_native_obj(self, e):
        from pypy.rpython.annlowlevel import cast_instance_to_base_obj
        inst = cast_instance_to_base_obj(e)      # SomeOOInstance
        obj = ootype.cast_to_object(inst)        # SomeOOObject
        return dotnet.cast_to_native_object(obj) # System.Object

    def do_oosend(self, args, descr):
        assert isinstance(descr, MethDescr)
        assert descr.callmeth is not None
        selfbox = args[0]
        argboxes = args[1:]
        return descr.callmeth(selfbox, argboxes)

    def do_getarrayitem_gc(self, arraybox, indexbox, descr):
        assert isinstance(descr, TypeDescr)
        return descr.getarrayitem(arraybox, indexbox)

    def do_setarrayitem_gc(self, arraybox, indexbox, newvaluebox, descr):
        assert isinstance(descr, TypeDescr)
        descr.setarrayitem(arraybox, indexbox, newvaluebox)

    def do_arraylen_gc(self, arraybox, descr):
        assert isinstance(descr, TypeDescr)
        return descr.getarraylength(arraybox)

# ----------------------------------------------------------------------
key_manager = KeyManager()

descr_cache = {}
class DescrWithKey(AbstractDescr):
    key = -1

    @classmethod
    def new(cls, *args):
        'NOT_RPYTHON'
        key = (cls, args)
        try:
            return descr_cache[key]
        except KeyError:
            res = cls(*args)
            descr_cache[key] = res
            return res


    def __init__(self, key):
        self.key = key_manager.getkey(key)

    def sort_key(self):
        return self.key

    def short_repr(self):
        return ''

    def repr_of_descr(self):
        return self.short_repr()


def get_class_for_type(T):
    if T is ootype.Void:
        return ootype.nullruntimeclass
    elif T is ootype.Signed:
        return dotnet.classof(System.Int32)
    elif T is ootype.Unsigned:
        return dotnet.classof(System.UInt32)
    elif T is ootype.Bool:
        return dotnet.classof(System.Boolean)
    elif T is ootype.Float:
        return dotnet.classof(System.Double)
##     elif T is ootype.String:
##         return dotnet.classof(System.String)
    elif T in (ootype.Char, ootype.UniChar):
        return dotnet.classof(System.Char)
    elif isinstance(T, ootype.OOType):
        return ootype.runtimeClass(T)
    else:
        assert False

class TypeDescr(DescrWithKey):

    def __init__(self, TYPE):
        DescrWithKey.__init__(self, TYPE)
        from pypy.jit.backend.llgraph.runner import boxresult
        from pypy.jit.metainterp.warmstate import unwrap
        ARRAY = ootype.Array(TYPE)
        def create():
            if isinstance(TYPE, ootype.OOType):
                return boxresult(TYPE, ootype.new(TYPE))
            return None
        def create_array(lengthbox):
            n = lengthbox.getint()
            return boxresult(ARRAY, ootype.oonewarray(ARRAY, n))
        def getarrayitem(arraybox, ibox):
            array = arraybox.getref(ARRAY)
            i = ibox.getint()
            if TYPE is not ootype.Void:
                return boxresult(TYPE, array.ll_getitem_fast(i))
        def setarrayitem(arraybox, ibox, valuebox):
            array = arraybox.getref(ARRAY)
            i = ibox.getint()
            value = unwrap(TYPE, valuebox)
            array.ll_setitem_fast(i, value)
        def getarraylength(arraybox):
            array = arraybox.getref(ARRAY)
            return boxresult(ootype.Signed, array.ll_length())
        def instanceof(box):
            if isinstance(TYPE, ootype.Instance):
                obj = box.getref(ootype.ROOT)
                return BoxInt(ootype.instanceof(obj, TYPE))
            return None
        self.create = create
        self.create_array = create_array
        self.getarrayitem = getarrayitem
        self.setarrayitem = setarrayitem
        self.getarraylength = getarraylength
        self.instanceof = instanceof
        self.ooclass = get_class_for_type(TYPE)
        self.typename = TYPE._short_name()
        self._is_array_of_pointers = (history.getkind(TYPE) == 'ref')
        self._is_array_of_floats = (history.getkind(TYPE) == 'float')

    def is_array_of_pointers(self):
        # for arrays, TYPE is the type of the array item.
        return self._is_array_of_pointers

    def is_array_of_floats(self):
        # for arrays, TYPE is the type of the array item.
        return self._is_array_of_floats

    def get_clitype(self):
        return dotnet.class2type(self.ooclass)

    def get_array_clitype(self):
        return self.get_clitype().MakeArrayType()

    def get_constructor_info(self):
        clitype = self.get_clitype()
        return clitype.GetConstructor(dotnet.new_array(System.Type, 0))

    def short_repr(self):
        return self.typename

class StaticMethDescr(DescrWithKey):

    callfunc = None
    funcclass = ootype.nullruntimeclass
    has_result = False

    def __init__(self, FUNC, ARGS, RESULT, extrainfo=None):
        DescrWithKey.__init__(self, (FUNC, ARGS, RESULT))
        from pypy.jit.backend.llgraph.runner import boxresult, make_getargs
        getargs = make_getargs(FUNC.ARGS)
        def callfunc(funcbox, argboxes):
            funcobj = funcbox.getref(FUNC)
            funcargs = getargs(argboxes)
            res = funcobj(*funcargs)
            if RESULT is not ootype.Void:
                return boxresult(RESULT, res)
        self.callfunc = callfunc
        self.funcclass = dotnet.classof(FUNC)
        self.has_result = (FUNC.RESULT != ootype.Void)
        self.extrainfo = extrainfo
        if RESULT is ootype.Void:
            def get_errbox():
                return None
        elif isinstance(RESULT, ootype.OOType):
            def get_errbox():
                return BoxObj()
        else:
            def get_errbox():
                return BoxInt()
        self.get_errbox = get_errbox

    def get_delegate_clitype(self):
        return dotnet.class2type(self.funcclass)

    def get_meth_info(self):
        clitype = self.get_delegate_clitype()
        return clitype.GetMethod('Invoke')

    def get_extra_info(self):
        return self.extrainfo
        

class MethDescr(AbstractMethDescr):

    callmeth = None
    selfclass = ootype.nullruntimeclass
    methname = ''
    has_result = False
    key = -1

    new = classmethod(DescrWithKey.new.im_func)

    def __init__(self, SELFTYPE, methname):
        from pypy.jit.backend.llgraph.runner import boxresult, make_getargs
        _, meth = SELFTYPE._lookup(methname)
        METH = ootype.typeOf(meth)
        getargs = make_getargs(METH.ARGS)
        def callmeth(selfbox, argboxes):
            selfobj = selfbox.getref(SELFTYPE)
            meth = getattr(selfobj, methname)
            methargs = getargs(argboxes)
            res = meth(*methargs)
            if METH.RESULT is not ootype.Void:
                return boxresult(METH.RESULT, res)
        self.callmeth = callmeth
        self.selfclass = ootype.runtimeClass(SELFTYPE)
        self.methname = methname
        self.has_result = (METH.RESULT != ootype.Void)
        self.key = key_manager.getkey((SELFTYPE, methname))

    def sort_key(self):
        return self.key

    def get_self_clitype(self):
        return dotnet.class2type(self.selfclass)
    
    def get_meth_info(self):
        clitype = self.get_self_clitype()
        return clitype.GetMethod(self.methname+'')

    def get_call_opcode(self):
        return OpCodes.Callvirt

    def repr_of_descr(self):
        return "'%s'" % self.methname

class StringMethDescr(MethDescr):

    def get_meth_info(self):
        clitype = dotnet.class2type(cpypyString)
        return clitype.GetMethod(self.methname+'')

    def get_call_opcode(self):
        return OpCodes.Call
        

class FieldDescr(DescrWithKey):

    getfield = None
    setfield = None
    selfclass = ootype.nullruntimeclass
    fieldname = ''
    _is_pointer_field = False
    _is_float_field = False

    def __init__(self, TYPE, fieldname):
        DescrWithKey.__init__(self, (TYPE, fieldname))
        from pypy.jit.backend.llgraph.runner import boxresult
        from pypy.jit.metainterp.warmstate import unwrap
        _, T = TYPE._lookup_field(fieldname)
        def getfield(objbox):
            obj = objbox.getref(TYPE)
            value = getattr(obj, fieldname)
            return boxresult(T, value)
        def setfield(objbox, valuebox):
            obj = objbox.getref(TYPE)
            value = unwrap(T, valuebox)
            setattr(obj, fieldname, value)
            
        self.getfield = getfield
        self.setfield = setfield
        self.selfclass = ootype.runtimeClass(TYPE)
        self.fieldname = fieldname
        self.key = key_manager.getkey((TYPE, fieldname))
        self._is_pointer_field = (history.getkind(T) == 'ref')
        self._is_float_field = (history.getkind(T) == 'float')

    def is_pointer_field(self):
        return self._is_pointer_field

    def is_float_field(self):
        return self._is_float_field

    def equals(self, other):
        assert isinstance(other, FieldDescr)
        return self.key == other.key

    def get_self_clitype(self):
        return dotnet.class2type(self.selfclass)

    def get_field_info(self):
        clitype = self.get_self_clitype()
        return clitype.GetField(self.fieldname+'')

    def short_repr(self):
        return "'%s'" % self.fieldname

CPU = CliCPU

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(CPU)
