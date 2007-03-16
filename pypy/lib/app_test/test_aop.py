from pypy.conftest import gettestobjspace


class AppTestAOPGeneral(object):
    def test_init(self):
        import aop

class AppTestPointCut(object):
    def test_static_dynamic_advice_and_pointcut(self):
        from  aop import PointCut, introduce, before, around, after

        dyn_pc = PointCut(func='foo').call()
        assert dyn_pc.isdynamic

        stat_pc = PointCut(func='bar')
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


    def test_pointcut_func(self):
        from  aop import PointCut
        pc = PointCut(func='foobar')
        expected = {'func_re': 'foobar',
                    'class_re': '.*',
                    'module_re':'.*'}
        for key, value in expected.items():
            assert getattr(pc, key).pattern == expected[key]

    def test_pointcut_class_func(self):
        from aop import PointCut
        pc = PointCut(klass='^Mumble.*$', func='foobar')
        expected = {'func_re': 'foobar',
                    'class_re': '^Mumble.*$',
                    'module_re':'.*'}
        for key, value in expected.items():
            assert getattr(pc, key).pattern == expected[key]
            
    def test_pointcut_module_class_func(self):
        from aop import PointCut
        pc = PointCut(module=r'logilab\..*', klass='^Mumble.*$', func='foobar')
        expected = {'func_re': 'foobar',
                    'class_re': '^Mumble.*$',
                    'module_re':r'logilab\..*'}
        for key, value in expected.items():
            assert getattr(pc, key).pattern == expected[key]

    def test_pointcut_match_module(self):
        from aop import PointCut
        pc = PointCut(module=r'logilab\..+', klass='^Mumble.*$', func='foobar')
        assert pc.match_module('logilab.common')
        assert not pc.match_module('logilab')
        assert not pc.match_module('common.logilab')
            
class AppTestWeavingAtExecution(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{'objspace.usepycfiles':False})

    def test_simple_aspect_before_execution(self):
        from  aop import PointCut, Aspect, before
        from app_test import sample_aop_code
        __aop__._clear_all()
        sample_aop_code.write_module('aop_before_execution')
        
        class AspectTest:
            __metaclass__ = Aspect 
            def __init__(self):
                self.executed = False
            @before(PointCut(func='foo').execution())
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
            @after(PointCut(func='foo').execution())
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
            @around(PointCut(func='foo').execution())
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
        

class AppTestWeavingAtCall(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{'objspace.usepycfiles':False})

    def test_simple_aspect_before_call(self):
        from  aop import PointCut, Aspect, before
        from app_test import sample_aop_code
        __aop__._clear_all()
        sample_aop_code.write_module('aop_before_call')
        
        class AspectTest:
            __metaclass__ = Aspect 
            def __init__(self):
                self.executed = False
            @before(PointCut(func='bar').call())
            def advice_before_call(self, tjp):
                print "IN advice before call"
                self.executed = True
                self.arguments = tjp._arguments
                print "OUT advice before call"

        assert __aop__.advices == []
        aspect = AspectTest()
        assert __aop__.advices == [(aspect, AspectTest.advice_before_call)] 
        assert not aspect.executed

        from app_test import aop_before_call
        assert  aspect.executed == 0
        answ = aop_before_call.foo(1,2)
        assert aspect.executed == 1
        assert answ == 47
        sample_aop_code.clean_module('aop_before_call')

    def test_simple_aspect_after_call(self):
        from  aop import PointCut, Aspect, after
        from app_test import sample_aop_code
        __aop__._clear_all()
        sample_aop_code.write_module('aop_after_call')
        
        class AspectTest:
            __metaclass__ = Aspect 
            def __init__(self):
                self.executed = False
                self.result = None
            @after(PointCut(func='bar').call())
            def advice_after_call(self, tjp):
                print "IN advice after call"
                self.executed = True
                self.arguments = tjp._arguments
                self.result = tjp.result()
                print "OUT advice after call"
                print "result", self.result
                return self.result

        assert __aop__.advices == []
        aspect = AspectTest()
        assert __aop__.advices == [(aspect, AspectTest.advice_after_call)] 
        assert not aspect.executed

        from app_test import aop_after_call
        assert not aspect.executed 
        answ = aop_after_call.foo(1,2)
        assert aspect.executed 
        assert answ == 47
        assert aspect.result == 42
        sample_aop_code.clean_module('aop_after_call')

    
