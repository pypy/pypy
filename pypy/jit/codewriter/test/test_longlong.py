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

    def do_check(self, opname, oopspecindex, ARGS, RESULT):
        vlist = [varoftype(ARG) for ARG in ARGS]
        v_result = varoftype(RESULT)
        op = SpaceOperation(opname, vlist, v_result)
        tr = Transformer(FakeCPU([]), FakeBuiltinCallControl())
        op1 = tr.rewrite_operation(op)
        #
        def is_ll(TYPE):
            return (TYPE == lltype.SignedLongLong or
                    TYPE == lltype.UnsignedLongLong)
        assert [ARG for ARG in ARGS if is_ll(ARG)]
        if is_ll(RESULT):
            assert op1.opname == 'residual_call_irf_f'
        else:
            assert op1.opname == 'residual_call_irf_i'
        assert op1.args[0].value == opname.lstrip('u')
        assert op1.args[1] == 'calldescr-%d' % oopspecindex
        assert list(op1.args[2]) == []
        assert list(op1.args[3]) == []
        assert list(op1.args[4]) == vlist
        assert op1.result == v_result

    def test_is_true(self):
        self.do_check('llong_is_true', EffectInfo.OS_LLONG_IS_TRUE,
                      [lltype.SignedLongLong], lltype.Bool)
        self.do_check('ullong_is_true', EffectInfo.OS_LLONG_IS_TRUE,
                      [lltype.SignedLongLong], lltype.Bool)

##    def test_unary_op(self):
##        tr = Transformer(FakeCPU([]), FakeBuiltinCallControl())
##        for opname, oopspecindex in [
##                ('llong_neg',     EffectInfo.OS_LLONG_NEG),
##                ('llong_invert',  EffectInfo.OS_LLONG_INVERT),
                
##                ('ullong_is_true', EffectInfo.OS_LLONG_IS_TRUE),
##                ('ullong_neg', EffectInfo.OS_LLONG_NEG),

##                ('llong_lt', EffectInfo.OS_LLONG_LT),
##                ('llong_le', EffectInfo.OS_LLONG_LE),
##                ('llong_eq', EffectInfo.OS_LLONG_EQ),
##                ('llong_ne', EffectInfo.OS_LLONG_NE),
##                ('llong_gt', EffectInfo.OS_LLONG_GT),
##                ('llong_ge', EffectInfo.OS_LLONG_GE),

    def test_binary_op(self):
        self.do_check('llong_add', EffectInfo.OS_LLONG_ADD,
                      [lltype.SignedLongLong, lltype.SignedLongLong],
                      lltype.SignedLongLong)
        self.do_check('ullong_add', EffectInfo.OS_LLONG_ADD,
                      [lltype.UnsignedLongLong, lltype.UnsignedLongLong],
                      lltype.UnsignedLongLong)

##        tr = Transformer(FakeCPU([]), FakeBuiltinCallControl())
##        for opname, oopspecindex in [
##                ('llong_add',    EffectInfo.OS_LLONG_ADD),
##                ('llong_sub',    EffectInfo.OS_LLONG_SUB),
##                ('llong_mul',    EffectInfo.OS_LLONG_MUL),
##                ('llong_and',    EffectInfo.OS_LLONG_AND),
##                ('llong_or',     EffectInfo.OS_LLONG_OR),
##                ('llong_xor',    EffectInfo.OS_LLONG_XOR),




##                ('llong_lshift', EffectInfo.OS_LLONG_LSHIFT),
##                ('', EffectInfo.OS_LLONG_RSHIFT),


##    'llong_is_true':        LLOp(canfold=True),
##    'llong_neg':            LLOp(canfold=True),
##    'llong_neg_ovf':        LLOp(canraise=(OverflowError,), tryfold=True),
##    'llong_abs':            LLOp(canfold=True),
##    'llong_abs_ovf':        LLOp(canraise=(OverflowError,), tryfold=True),
##    'llong_invert':         LLOp(canfold=True),

##    'llong_add':            LLOp(canfold=True),
##    'llong_sub':            LLOp(canfold=True),
##    'llong_mul':            LLOp(canfold=True),
##    'llong_floordiv':       LLOp(canfold=True),
##    'llong_floordiv_zer':   LLOp(canraise=(ZeroDivisionError,), tryfold=True),
##    'llong_mod':            LLOp(canfold=True),
##    'llong_mod_zer':        LLOp(canraise=(ZeroDivisionError,), tryfold=True),
##    'llong_lt':             LLOp(canfold=True),
##    'llong_le':             LLOp(canfold=True),
##    'llong_eq':             LLOp(canfold=True),
##    'llong_ne':             LLOp(canfold=True),
##    'llong_gt':             LLOp(canfold=True),
##    'llong_ge':             LLOp(canfold=True),
##    'llong_and':            LLOp(canfold=True),
##    'llong_or':             LLOp(canfold=True),
##    'llong_lshift':         LLOp(canfold=True),
##    'llong_rshift':         LLOp(canfold=True),
##    'llong_xor':            LLOp(canfold=True),

##    'ullong_is_true':       LLOp(canfold=True),
##    'ullong_invert':        LLOp(canfold=True),

##    'ullong_add':           LLOp(canfold=True),
##    'ullong_sub':           LLOp(canfold=True),
##    'ullong_mul':           LLOp(canfold=True),
##    'ullong_floordiv':      LLOp(canfold=True),
##    'ullong_floordiv_zer':  LLOp(canraise=(ZeroDivisionError,), tryfold=True),
##    'ullong_mod':           LLOp(canfold=True),
##    'ullong_mod_zer':       LLOp(canraise=(ZeroDivisionError,), tryfold=True),
##    'ullong_lt':            LLOp(canfold=True),
##    'ullong_le':            LLOp(canfold=True),
##    'ullong_eq':            LLOp(canfold=True),
##    'ullong_ne':            LLOp(canfold=True),
##    'ullong_gt':            LLOp(canfold=True),
##    'ullong_ge':            LLOp(canfold=True),
##    'ullong_and':           LLOp(canfold=True),
##    'ullong_or':            LLOp(canfold=True),
##    'ullong_lshift':        LLOp(canfold=True),
##    'ullong_rshift':        LLOp(canfold=True),
##    'ullong_xor':           LLOp(canfold=True),

##            ]:



##                ('', EffectInfo.OS_LLONG_FROM_INT),
##                ('', EffectInfo.OS_LLONG_TO_INT),
##                ('', EffectInfo.OS_LLONG_FROM_FLOAT),
##                ('', EffectInfo.OS_LLONG_TO_FLOAT),


##    def test_prebuilt_constant_32(self):
##        c_x = const(r_longlong(-171))
##        op = SpaceOperation('foobar', [c_x], None)
##        oplist = Transformer(FakeCPU(['foobar'])).rewrite_operation(op)
##        assert len(oplist) == 2
##        assert oplist[0].opname == 'cast_int_to_longlong'
##        assert oplist[0].args == [c_x]
##        v = oplist[0].result
##        assert isinstance(v, Variable)
##        assert oplist[1].opname == 'foobar'
##        assert oplist[1].args == [v]
