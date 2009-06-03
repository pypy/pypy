from pypy.tool.pairtype import extendabletype
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.metainterp.history import AbstractDescr, AbstractMethDescr
from pypy.jit.metainterp.history import Box, BoxInt, BoxObj, ConstObj, Const
from pypy.jit.metainterp.history import TreeLoop
from pypy.jit.metainterp import executor
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.jit.backend import model
from pypy.jit.backend.llgraph.runner import KeyManager
from pypy.translator.cli import dotnet
from pypy.translator.cli.dotnet import CLR

System = CLR.System
OpCodes = System.Reflection.Emit.OpCodes
InputArgs = CLR.pypy.runtime.InputArgs
cpypyString = dotnet.classof(CLR.pypy.runtime.String)

class __extend__(TreeLoop):
    __metaclass__ = extendabletype

    _cli_funcbox = None
    _cli_meth = None
    _cli_count = 0

    def _get_cli_name(self):
        return '%s(r%d)' % (self.name, self._cli_count)


class CliCPU(model.AbstractCPU):

    is_oo = True

    def __init__(self, rtyper, stats, translate_support_code=False,
                 mixlevelann=None, gcdescr=None):
        self.rtyper = rtyper
        if rtyper:
            assert rtyper.type_system.name == "ootypesystem"
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
    def calldescrof(FUNC, ARGS, RESULT):
        return StaticMethDescr.new(FUNC, ARGS, RESULT)

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

    # ----------------------

    def compile_operations(self, loop, bridge=None):
        from pypy.jit.backend.cli.method import Method, ConstFunction
        if loop._cli_funcbox is None:
            loop._cli_funcbox = ConstFunction(loop.name)
        else:
            # discard previously compiled loop
            loop._cli_funcbox.holder.SetFunc(None)
        loop._cli_meth = Method(self, loop._get_cli_name(), loop)
        loop._cli_count += 1

    def execute_operations(self, loop):
        func = loop._cli_funcbox.holder.GetFunc()
        func(self.get_inputargs())
        return self.failing_ops[self.inputargs.get_failed_op()]

    def set_future_value_int(self, index, intvalue):
        self.get_inputargs().set_int(index, intvalue)

    def set_future_value_obj(self, index, objvalue):
        obj = dotnet.cast_to_native_object(objvalue)
        self.get_inputargs().set_obj(index, obj)

    def get_latest_value_int(self, index):
        return self.get_inputargs().get_int(index)

    def get_latest_value_obj(self, index):
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

    def set_overflow_error(self):
        exc_obj = ootype.cast_to_object(self.ll_ovf_exc)
        exc_value = dotnet.cast_to_native_object(exc_obj)
        self.get_inputargs().set_exc_value(exc_value)

    def set_zero_division_error(self):
        exc_obj = ootype.cast_to_object(self.ll_zero_exc)
        exc_value = dotnet.cast_to_native_object(exc_obj)
        self.get_inputargs().set_exc_value(exc_value)

    # ----------------------

    def do_new_with_vtable(self, args, typedescr):
        assert isinstance(typedescr, TypeDescr)
        assert len(args) == 1 # but we don't need it, so ignore
        return typedescr.create()

    def do_new_array(self, args, typedescr):
        assert isinstance(typedescr, TypeDescr)
        assert len(args) == 1
        return typedescr.create_array(args[0])

    def do_runtimenew(self, args, descr):
        classbox = args[0]
        classobj = ootype.cast_from_object(ootype.Class, classbox.getobj())
        res = ootype.runtimenew(classobj)
        return BoxObj(ootype.cast_to_object(res))

    def do_instanceof(self, args, typedescr):
        assert isinstance(typedescr, TypeDescr)
        assert len(args) == 1
        return typedescr.instanceof(args[0])

    def do_getfield_gc(self, args, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        return fielddescr.getfield(args[0])

    def do_setfield_gc(self, args, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        return fielddescr.setfield(args[0], args[1])

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

    def do_oosend(self, args, descr=None):
        assert isinstance(descr, MethDescr)
        selfbox = args[0]
        argboxes = args[1:]
        return descr.callmeth(selfbox, argboxes)

    def do_getarrayitem_gc(self, args, descr):
        assert isinstance(descr, TypeDescr)
        assert len(args) == 2
        arraybox = args[0]
        ibox = args[1]
        return descr.getarrayitem(arraybox, ibox)

    def do_setarrayitem_gc(self, args, descr):
        assert isinstance(descr, TypeDescr)
        assert len(args) == 3
        arraybox = args[0]
        ibox = args[1]
        valuebox = args[2]
        descr.setarrayitem(arraybox, ibox, valuebox)

    def do_arraylen_gc(self, args, descr):
        assert isinstance(descr, TypeDescr)
        assert len(args) == 1
        arraybox = args[0]
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


def get_class_for_type(T):
    if T is ootype.Void:
        return ootype.nullruntimeclass
    elif T is ootype.Signed:
        return dotnet.classof(System.Int32)
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
        from pypy.jit.metainterp.warmspot import unwrap
        ARRAY = ootype.Array(TYPE)
        def create():
            if isinstance(TYPE, ootype.OOType):
                return boxresult(TYPE, ootype.new(TYPE))
            return None
        def create_array(lengthbox):
            n = lengthbox.getint()
            return boxresult(ARRAY, ootype.oonewarray(ARRAY, n))
        def getarrayitem(arraybox, ibox):
            array = ootype.cast_from_object(ARRAY, arraybox.getobj())
            i = ibox.getint()
            if TYPE is not ootype.Void:
                return boxresult(TYPE, array.ll_getitem_fast(i))
        def setarrayitem(arraybox, ibox, valuebox):
            array = ootype.cast_from_object(ARRAY, arraybox.getobj())
            i = ibox.getint()
            value = unwrap(TYPE, valuebox)
            array.ll_setitem_fast(i, value)
        def getarraylength(arraybox):
            array = ootype.cast_from_object(ARRAY, arraybox.getobj())
            return boxresult(ootype.Signed, array.ll_length())
        def instanceof(box):
            if isinstance(TYPE, ootype.Instance):
                obj = ootype.cast_from_object(ootype.ROOT, box.getobj())
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

    def __init__(self, FUNC, ARGS, RESULT):
        DescrWithKey.__init__(self, (FUNC, ARGS, RESULT))
        from pypy.jit.backend.llgraph.runner import boxresult, make_getargs
        getargs = make_getargs(FUNC.ARGS)
        def callfunc(funcbox, argboxes):
            funcobj = ootype.cast_from_object(FUNC, funcbox.getobj())
            funcargs = getargs(argboxes)
            res = funcobj(*funcargs)
            if RESULT is not ootype.Void:
                return boxresult(RESULT, res)
        self.callfunc = callfunc
        self.funcclass = dotnet.classof(FUNC)
        self.has_result = (FUNC.RESULT != ootype.Void)
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
            selfobj = ootype.cast_from_object(SELFTYPE, selfbox.getobj())
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

    def __init__(self, TYPE, fieldname):
        DescrWithKey.__init__(self, (TYPE, fieldname))
        from pypy.jit.backend.llgraph.runner import boxresult
        from pypy.jit.metainterp.warmspot import unwrap
        _, T = TYPE._lookup_field(fieldname)
        def getfield(objbox):
            obj = ootype.cast_from_object(TYPE, objbox.getobj())
            value = getattr(obj, fieldname)
            return boxresult(T, value)
        def setfield(objbox, valuebox):
            obj = ootype.cast_from_object(TYPE, objbox.getobj())
            value = unwrap(T, valuebox)
            setattr(obj, fieldname, value)
            
        self.getfield = getfield
        self.setfield = setfield
        self.selfclass = ootype.runtimeClass(TYPE)
        self.fieldname = fieldname
        self.key = key_manager.getkey((TYPE, fieldname))

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
