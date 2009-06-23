import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin


class V(object):
    _virtualizable2_ = ['v']

    def __init__(self, v):
        self.v = v

class BaseTest(BaseRtypingTest):
    def test_generate_promote_virtualizable(self):
        py.test.skip("later")
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
        assert TYPE._hints['virtualizable2'] == True

    def test_accessor(self):
        class Base(object):
            pass
        class V(Base):
            _virtualizable2_ = ['v1', 'v2[*]']
        class W(V):
            pass
        #
        def fn1(n):
            Base().base1 = 42
            V().v1 = 43
            V().v2 = ['x', 'y']
            W().w1 = 44
            return V()
        _, _, graph = self.gengraph(fn1, [int])
        v_inst = graph.getreturnvar()
        TYPE = self.gettype(v_inst)
        accessor = TYPE._hints['virtualizable2_accessor']
        assert accessor.TYPE == TYPE
        assert accessor.redirected_fields == [self.prefix + 'v1',
                                              self.prefix + 'v2[*]']
        #
        def fn2(n):
            Base().base1 = 42
            V().v1 = 43
            V().v2 = ['x', 'y']
            W().w1 = 44
            return W()
        _, _, graph = self.gengraph(fn2, [int])
        w_inst = graph.getreturnvar()
        TYPE = self.gettype(w_inst)
        assert 'virtualizable2_accessor' not in TYPE._hints


class TestLLtype(LLRtypeMixin, BaseTest):
    prefix = 'inst_'

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
        py.test.skip("later")
        assert not res.vable_rti

class TestOOtype(OORtypeMixin, BaseTest):
    prefix = 'o'

    def gettype(self, v):
        return v.concretetype

