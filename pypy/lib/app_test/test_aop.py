from pypy.conftest import gettestobjspace

class AppTestAop(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{'objspace.usepycfiles':False})

    def test_init(self):
        import aop

    def test_static_dynamic_advice_and_pointcut(self):
        from  aop import PointCut, introduce, before, around, after

        dyn_pc = PointCut('foo').call()
        assert dyn_pc.isdynamic

        stat_pc = PointCut('bar')
        assert not stat_pc.isdynamic

        assert not introduce.requires_dynamic_pointcut
        raises(TypeError, introduce, dyn_pc)
        adv = introduce(stat_pc)
        assert adv is not None

        for advice in before, around, after:
            assert advice.requires_dynamic_pointcut
            raises(TypeError, advice, stat_pc)
            adv = advice(dyn_pc)
            assert adv is not None

    def test_is_aop(self):
        from aop import is_aop_call
        import parser
        func = """
def f():
    __aop__(1)
    g(12)
    __aop__(12)
"""
        funcast = parser.source2ast(func).node.nodes[0]
        result = [is_aop_call(n) for n in funcast.code.nodes]
        assert result == [True, False, True]

    def test_simple_aspect(self):
        from  aop import PointCut, Aspect, before
        
        class AspectTest:
            __metaclass__ = Aspect 
            def __init__(self):
                self.executed = False
            @before(PointCut('foo').execution())
            def advice_before_excecution(self, tjp):
                self.executed = True

        assert __aop__.advices == []
        aspect = AspectTest()
        assert __aop__.advices == [(aspect, AspectTest.advice_before_excecution)] 
        assert not aspect.executed

        from app_test import sample_aop_code
        assert not aspect.executed
        sample_aop_code.foo(1,2)
        assert aspect.executed

