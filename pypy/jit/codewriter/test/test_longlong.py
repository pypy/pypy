import py, sys

from pypy.rlib.rarithmetic import r_longlong
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant
from pypy.translator.unsimplify import varoftype
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codewriter.jtransform import Transformer, NotSupported
from pypy.jit.codewriter.test.test_jtransform import const


class FakeCPU:
    def __init__(self, supports_longlong):
        self.supports_longlong = supports_longlong


class TestLongLong:
    def setup_class(cls):
        if sys.maxint > 2147483647:
            py.test.skip("only for 32-bit platforms")

    def test_unsupported_op(self):
        tr = Transformer(FakeCPU([]))
        # without a long long
        op = SpaceOperation('foobar', [const(123)], varoftype(lltype.Signed))
        op1 = tr.rewrite_operation(op)
        assert op1 == op
        # with a long long argument
        op = SpaceOperation('foobar', [const(r_longlong(123))],
                            varoftype(lltype.Signed))
        py.test.raises(NotSupported, tr.rewrite_operation, op)
        # with a long long result
        op = SpaceOperation('foobar', [const(123)],
                            varoftype(lltype.SignedLongLong))
        py.test.raises(NotSupported, tr.rewrite_operation, op)

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
