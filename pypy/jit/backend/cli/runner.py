from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp.history import AbstractDescr, AbstractMethDescr
from pypy.jit.metainterp.history import Box, BoxInt, BoxObj
from pypy.jit.metainterp import executor
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.jit.backend import model
from pypy.jit.backend.minimal.runner import cached_method
from pypy.jit.backend.llgraph.runner import TypeDescr, FieldDescr
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

CPU = CliCPU

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(CPU)
