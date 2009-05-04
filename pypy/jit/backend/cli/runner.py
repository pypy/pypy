from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp.history import AbstractDescr, AbstractMethDescr
from pypy.jit.metainterp.history import Box, BoxInt, BoxObj
from pypy.jit.metainterp import executor
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.jit.backend import model
from pypy.jit.backend.minimal.runner import cached_method
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

    def do_call(self, args, calldescr):
        assert isinstance(calldescr, StaticMethDescr)
        funcbox, args = args[0], args[1:]
        return calldescr.callfunc(funcbox, args)


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


CPU = CliCPU

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(CPU)
