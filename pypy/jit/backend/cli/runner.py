from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp.history import AbstractDescr, AbstractMethDescr
from pypy.jit.metainterp.history import Box, BoxInt, BoxObj
from pypy.jit.metainterp import executor
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.jit.backend import model
from pypy.jit.backend.minimal.runner import cached_method
from pypy.jit.backend.llgraph.runner import TypeDescr, FieldDescr
from pypy.jit.backend.cli.method import Method
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
        self.inputargs = InputArgs()

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
        meth = Method(self, loop.name, loop)
        loop._cli_meth = meth

    def execute_operations(self, loop):
        meth = loop._cli_meth
        meth.func(self.inputargs)
        return meth.failing_ops[self.inputargs.failed_op]

    def set_future_value_int(self, index, intvalue):
        self.inputargs.ints[index] = intvalue

    def set_future_value_obj(self, index, objvalue):
        self.inputargs.objs[index] = objvalue

    def get_latest_value_int(self, index):
        return self.inputargs.ints[index]

    def get_latest_value_obj(self, index):
        return self.inputargs.objs[index]

    # ----------------------

    def do_new_with_vtable(self, args, typedescr):
        assert isinstance(typedescr, TypeDescr)
        assert len(args) == 1 # but we don't need it, so ignore
        return typedescr.create()

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


CPU = CliCPU

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(CPU)
