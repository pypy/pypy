import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rpython.rvirtualizable2 import replace_promote_virtualizable_with_call


class V(object):
    _virtualizable2_ = ['v']

    def __init__(self, v):
        self.v = v
        self.w = v+1

class VArray(object):
    _virtualizable2_ = ['lst[*]']

    def __init__(self, lst):
        self.lst = lst

class BaseTest(BaseRtypingTest):
    def test_generate_promote_virtualizable(self):
        def fn(n):
            vinst = V(n)
            return vinst.v
        _, _, graph = self.gengraph(fn, [int])
        block = graph.startblock
        op_promote = block.operations[-2]
        op_getfield = block.operations[-1]
        assert op_getfield.opname in ('getfield', 'oogetfield')
        v_inst = op_getfield.args[0]
        assert op_promote.opname == 'promote_virtualizable'
        assert op_promote.args[0] is v_inst

    def test_no_promote_virtualizable_for_other_fields(self):
        def fn(n):
            vinst = V(n)
            return vinst.w
        _, _, graph = self.gengraph(fn, [int])
        block = graph.startblock
        op_getfield = block.operations[-1]
        op_call = block.operations[-2]
        assert op_getfield.opname in ('getfield', 'oogetfield')
        assert op_call.opname == 'direct_call'    # to V.__init__

    def test_generate_promote_virtualizable_array(self):
        def fn(n):
            vinst = VArray([n, n+1])
            return vinst.lst[1]
        _, _, graph = self.gengraph(fn, [int])
        block = graph.startblock
        op_promote = block.operations[-3]
        op_getfield = block.operations[-2]
        op_getarrayitem = block.operations[-1]
        assert op_getarrayitem.opname == 'direct_call'  # to ll_getitem_xxx
        assert op_getfield.opname in ('getfield', 'oogetfield')
        v_inst = op_getfield.args[0]
        assert op_promote.opname == 'promote_virtualizable'
        assert op_promote.args[0] is v_inst

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
        assert accessor.fields == [self.prefix + 'v1',
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

    def test_replace_promote_virtualizable_with_call(self):
        def fn(n):
            vinst = V(n)
            return vinst.v
        _, rtyper, graph = self.gengraph(fn, [int])
        block = graph.startblock
        op_getfield = block.operations[-1]
        assert op_getfield.opname in ('getfield', 'oogetfield')
        v_inst_ll_type = op_getfield.args[0].concretetype
        #
        from pypy.annotation import model as annmodel
        from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
        def mycall(vinst_ll):
            pass
        annhelper = MixLevelHelperAnnotator(rtyper)
        if self.type_system == 'lltype':
            s_vinst = annmodel.SomePtr(v_inst_ll_type)
        else:
            s_vinst = annmodel.SomeOOInstance(v_inst_ll_type)
        funcptr = annhelper.delayedfunction(mycall, [s_vinst], annmodel.s_None)
        annhelper.finish()
        replace_promote_virtualizable_with_call([graph], v_inst_ll_type,
                                                funcptr)
        #
        op_promote = block.operations[-2]
        op_getfield = block.operations[-1]
        assert op_getfield.opname in ('getfield', 'oogetfield')
        assert op_promote.opname == 'direct_call'
        assert op_promote.args[0].value == funcptr
        assert op_promote.args[1] == op_getfield.args[0]


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

