import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin


class V(object):
    _virtualizable2_ = True

    def __init__(self, v):
        self.v = v

class BaseTest(BaseRtypingTest):
    def test_generate_promote_virtualizable(self):
        def fn(n):
            vinst = V(n)
            return vinst.v
        _, _, graph = self.gengraph(fn, [int])
        block = graph.startblock
        op_getfield = block.operations[-1]
        op_promote = block.operations[-2]
        assert op_getfield.opname in ('getfield', 'oogetfield')
        v_inst = op_getfield.args[0]
        assert op_promote.opname == 'promote_virtualizable'
        assert op_promote.args[0] is v_inst
        TYPE = self.gettype(v_inst)
        assert TYPE._hints['virtualizable2']


class TestLLtype(LLRtypeMixin, BaseTest):

    def gettype(self, v):
        return v.concretetype.TO

    def test_simple(self):
        def f(v):
            vinst = V(v)
            return vinst, vinst.v
        res = self.interpret(f, [42])
        assert res.item1 == 42
        res = lltype.normalizeptr(res.item0)
        assert res.inst_v == 42
        assert not res.vable_rti

class TestOOtype(OORtypeMixin, BaseTest):

    def gettype(self, v):
        return v.concretetype

