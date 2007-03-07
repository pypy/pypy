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

    def test_simple_aspect_before_execution(self):
        from  aop import PointCut, Aspect, before
        from app_test import sample_aop_code
        __aop__._clear_all()
        sample_aop_code.write_module('aop_before_execution')
        
        class AspectTest:
            __metaclass__ = Aspect 
            def __init__(self):
                self.executed = False
            @before(PointCut('foo').execution())
            def advice_before_execution(self, tjp):
                self.executed = True
                self.argnames = tjp._argnames
                self.flags = tjp._flags

        assert __aop__.advices == []
        aspect = AspectTest()
        assert __aop__.advices == [(aspect, AspectTest.advice_before_execution)] 
        assert not aspect.executed

        from app_test import aop_before_execution
        assert  aspect.executed == 0
        answ = aop_before_execution.foo(1,2)
        assert aspect.executed == 1
        assert aspect.argnames == ['b', 'c']
        assert aspect.flags == 0
        assert answ == 47
        sample_aop_code.clean_module('aop_before_execution')

    def test_simple_aspect_after_execution(self):
        from  aop import PointCut, Aspect, after
        from app_test import sample_aop_code
        __aop__._clear_all()
        sample_aop_code.write_module('aop_after_execution')
        class AspectTest:
            __metaclass__ = Aspect 
            def __init__(self):
                self.executed = 0
            @after(PointCut('foo').execution())
            def advice_after_execution(self, tjp):
                self.executed += 1

        assert __aop__.advices == []
        aspect = AspectTest()
        assert __aop__.advices == [(aspect, AspectTest.advice_after_execution)] 
        assert not aspect.executed
        from app_test import aop_after_execution
        assert aspect.executed == 0
        answ = aop_after_execution.foo(1,2)
        assert aspect.executed == 1
        assert answ == 47
        sample_aop_code.clean_module('aop_after_execution')

    def test_simple_aspect_around_execution(self):
        from  aop import PointCut, Aspect, around
        from app_test import sample_aop_code
        __aop__._clear_all()
        sample_aop_code.write_module('aop_around_execution')
        class AspectTest:
            __metaclass__ = Aspect 
            def __init__(self):
                self.executed_before = 0
                self.executed_after = 0
            @around(PointCut('foo').execution())
            def advice_around_execution(self, tjp):
                print '>>>in', tjp.arguments()
                self.executed_before += 1
                args, kwargs = tjp.arguments()
                tjp.proceed(*args, **kwargs)
                self.executed_after += 1
                self.result = tjp.result()
                print '<<<out'
                return tjp.result()
        
        aspect = AspectTest()
        from app_test import aop_around_execution
        assert aspect.executed_before == 0
        assert aspect.executed_after == 0
        answ = aop_around_execution.foo(1,2)
        assert aspect.executed_before == 1
        assert aspect.executed_after == 1
        assert aspect.result == 47
        assert answ == 47
        sample_aop_code.clean_module('aop_around_execution')
        
