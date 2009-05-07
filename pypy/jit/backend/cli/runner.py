from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp.history import AbstractDescr, AbstractMethDescr
from pypy.jit.metainterp.history import Box, BoxInt, BoxObj
from pypy.jit.metainterp import executor
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.jit.backend import model
from pypy.jit.backend.minimal.runner import cached_method
from pypy.jit.backend.llgraph.runner import KeyManager
from pypy.translator.cli import dotnet
from pypy.translator.cli.dotnet import CLR

System = CLR.System
InputArgs = CLR.pypy.runtime.InputArgs


class CliCPU(model.AbstractCPU):

    is_oo = True

    def __init__(self, rtyper, stats, translate_support_code=False,
                 mixlevelann=None):
        self.rtyper = rtyper
        if rtyper:
            assert rtyper.type_system.name == "ootypesystem"
        self.stats = stats
        self.translate_support_code = translate_support_code
        self.inputargs = None

    def get_inputargs(self):
        if self.inputargs is None:
            self.inputargs = InputArgs()
        return self.inputargs
    
    @cached_method('_callcache')
    def calldescrof(self, FUNC, ARGS, RESULT):
        return StaticMethDescr(FUNC, ARGS, RESULT)

    @cached_method('_methcache')
    def methdescrof(self, SELFTYPE, methname):
        return MethDescr(SELFTYPE, methname)

    @cached_method('_typecache')
    def typedescrof(self, TYPE):
        return TypeDescr(TYPE)

    @cached_method('_fieldcache')
    def fielddescrof(self, T, fieldname):
        return FieldDescr(T, fieldname)

    # ----------------------

    def compile_operations(self, loop):
        from pypy.jit.backend.cli.method import Method
        meth = Method(self, loop.name, loop)
        loop._cli_meth = meth

    def execute_operations(self, loop):
        meth = loop._cli_meth
        meth.func(self.get_inputargs())
        return meth.failing_ops[self.inputargs.get_failed_op()]

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
            assert False, 'TODO'
        return ootype.cast_to_object(ootype.nullruntimeclass)

    def get_exc_value(self):
        if self.get_inputargs().get_exc_value():
            assert False, 'TODO'
        else:
            return ootype.NULL

    def clear_exception(self):
        self.get_inputargs().set_exc_value(None)

    def set_overflow_error(self):
        raise NotImplementedError

    def set_zero_division_error(self):
        raise NotImplementedError

    # ----------------------

    def do_new_with_vtable(self, args, typedescr):
        assert isinstance(typedescr, TypeDescr)
        assert len(args) == 1 # but we don't need it, so ignore
        return typedescr.create()

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
        return calldescr.callfunc(funcbox, args)

    def do_oosend(self, args, descr=None):
        assert isinstance(descr, MethDescr)
        selfbox = args[0]
        argboxes = args[1:]
        return descr.callmeth(selfbox, argboxes)


# ----------------------------------------------------------------------
key_manager = KeyManager()


class TypeDescr(AbstractDescr):

    def __init__(self, TYPE):
        from pypy.jit.backend.llgraph.runner import boxresult
        def create():
            return boxresult(TYPE, ootype.new(TYPE))
        def create_array(lengthbox):
            n = lengthbox.getint()
            return boxresult(ARRAY, ootype.oonewarray(ARRAY, n))
        def getarrayitem(arraybox, ibox):
            array = ootype.cast_from_object(ARRAY, arraybox.getobj())
            i = ibox.getint()
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
            obj = ootype.cast_from_object(ootype.ROOT, box.getobj())
            return history.BoxInt(ootype.instanceof(obj, TYPE))
        self.create = create
        self.create_array = create_array
        self.getarrayitem = getarrayitem
        self.setarrayitem = setarrayitem
        self.getarraylength = getarraylength
        self.instanceof = instanceof
        self.ooclass = ootype.runtimeClass(TYPE)

    def get_clitype(self):
        return dotnet.class2type(self.ooclass)

    def get_constructor_info(self):
        clitype = self.get_clitype()
        return clitype.GetConstructor(dotnet.new_array(System.Type, 0))

class StaticMethDescr(AbstractDescr):

    def __init__(self, FUNC, ARGS, RESULT):
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

    def get_delegate_clitype(self):
        return dotnet.class2type(self.funcclass)

    def get_meth_info(self):
        clitype = self.get_delegate_clitype()
        return clitype.GetMethod('Invoke')
        

class MethDescr(AbstractMethDescr):

    callmeth = None
    
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

    def get_self_clitype(self):
        return dotnet.class2type(self.selfclass)
    
    def get_meth_info(self):
        clitype = self.get_self_clitype()
        return clitype.GetMethod(str(self.methname))


class FieldDescr(AbstractDescr):

    getfield = None
    _keys = KeyManager()

    def __init__(self, TYPE, fieldname):
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

    def sort_key(self):
        return self.key

    def equals(self, other):
        assert isinstance(other, FieldDescr)
        return self.key == other.key

    def get_self_clitype(self):
        return dotnet.class2type(self.selfclass)

    def get_field_info(self):
        clitype = self.get_self_clitype()
        return clitype.GetField(str(self.fieldname))


CPU = CliCPU

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(CPU)
