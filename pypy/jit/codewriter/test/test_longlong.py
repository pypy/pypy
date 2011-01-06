import py, sys

from pypy.rlib.rarithmetic import r_longlong
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant
from pypy.translator.unsimplify import varoftype
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codewriter.jtransform import Transformer, NotSupported
from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.jit.codewriter.test.test_jtransform import const


class FakeRTyper:
    pass

class FakeBuiltinCallControl:
    def guess_call_kind(self, op):
        return 'builtin'
    def getcalldescr(self, op, oopspecindex=None):
        assert oopspecindex is not None    # in this test
        return 'calldescr-%d' % oopspecindex
    def calldescr_canraise(self, calldescr):
        return False

class FakeCPU:
    def __init__(self, supports_longlong):
        self.supports_longlong = supports_longlong
        self.rtyper = FakeRTyper()


class TestLongLong:
    def setup_class(cls):
        if sys.maxint > 2147483647:
            py.test.skip("only for 32-bit platforms")

    def test_unsupported_binary_op(self):
        tr = Transformer(FakeCPU([]), FakeBuiltinCallControl())
        for opname, oopspecindex in [
                ('llong_add', EffectInfo.OS_LLONG_ADD),
                ('ullong_add', EffectInfo.OS_LLONG_ADD),
            ]:
            v1 = varoftype(lltype.SignedLongLong)
            v2 = varoftype(lltype.SignedLongLong)
            v3 = varoftype(lltype.SignedLongLong)
            op = SpaceOperation(opname, [v1, v2], v3)
            op1 = tr.rewrite_operation(op)
            assert op1.opname == 'residual_call_irf_f'
            assert op1.args[0].value == opname.lstrip('u')
            assert op1.args[1] == 'calldescr-%d' % oopspecindex
            assert list(op1.args[2]) == []
            assert list(op1.args[3]) == []
            assert list(op1.args[4]) == [v1, v2]
            assert op1.result == v3

    def test_prebuilt_constant_32(self):
        c_x = const(r_longlong(-171))
        op = SpaceOperation('foobar', [c_x], None)
        oplist = Transformer(FakeCPU(['foobar'])).rewrite_operation(op)
        assert len(oplist) == 2
        assert oplist[0].opname == 'cast_int_to_longlong'
        assert oplist[0].args == [c_x]
        v = oplist[0].result
        assert isinstance(v, Variable)
        assert oplist[1].opname == 'foobar'
        assert oplist[1].args == [v]
