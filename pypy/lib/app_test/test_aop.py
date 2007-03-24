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

    def test_static_pointcut_match(self):
        from aop import PointCut
        from parser import ASTClass, ASTPass, ASTFunction
        pc = PointCut(klass="Mumble")
        assert pc.match(ASTClass('Mumble', [], None, ASTPass()))
        assert pc.match(ASTClass('MumblesALot', [], None, ASTPass()))
        f = ASTFunction(None, 'MumblesALot', [], [], 0, '', ASTPass())
        f.parent = ASTClass('MumblesALot', [], None, ASTPass())
        assert not pc.match(f)

    def test_exec_pointcut_match(self):
        from aop import PointCut
        from parser import ASTClass, ASTPass, ASTFunction
        pc = PointCut(klass="Mumble", func='frobble').execution()
        f = ASTFunction(None, 'frobble', [], [], 0, '', ASTPass())
        f.parent = ASTClass('MumblesALot', [], None, ASTPass())
        assert pc.match(f)
        f.parent.name = 'Babble'
        assert not pc.match(f)
        c = ASTClass('frobbles_a_bit', [], None, ASTPass())
        c.parent = ASTClass('MumblesALot', [], None, ASTPass())
        assert not pc.match(c)
        
    def test_call_pointcut_match(self):
        from aop import PointCut
        from parser import ASTClass, ASTPass, ASTFunction, ASTName, ASTCallFunc
        pc = PointCut(klass="Mumble", func='frobble').call()
        cf = ASTCallFunc( ASTName('frobble'), [], None, None)
        c = ASTClass('MumblesALot', [], None, ASTPass())
        cf.parent = c
        assert pc.match(cf)
        f = ASTFunction(None, 'frobble', [], [], 0, '', ASTPass())
        f.parent = c
        assert not pc.match(f)
        c2 = ASTClass('frobbles_a_bit', [], None, ASTPass())
        c2.parent = c
        assert not pc.match(c2)
        c.name = 'Babble'
        assert not pc.match(cf)

    def test_init_pointcut_match(self):
        from aop import PointCut
        from parser import ASTClass, ASTPass, ASTFunction
        pc = PointCut(klass="Mumble").initialization()
        init = ASTFunction(None, '__init__', [], [], 0, '', ASTPass())
        c = ASTClass('MumblesALot', [], None, ASTPass())
        init.parent = c
        assert pc.match(init)
        c2 = ASTClass('__init__', [], None, ASTPass())
        c2.parent = c
        assert not pc.match(c2)
        init.name = 'frobble'
        assert not pc.match(init)
        
    def test_destruction_pointcut_match(self):
        from aop import PointCut
        from parser import ASTClass, ASTPass, ASTFunction, ASTCallFunc, ASTName
        pc = PointCut(klass="Mumble").destruction()
        delete = ASTFunction(None, '__del__', [], [], 0, '', ASTPass())
        c = ASTClass('MumblesALot', [], None, ASTPass())
        delete.parent = c
        assert pc.match(delete)
        c2 = ASTClass('__del__', [], None, ASTPass())
        c2.parent = c
        assert not pc.match(c2)
        delete.name = 'frobble'
        assert not pc.match(delete)
        

    def test_and_compound_pointcut_match(self):
        from aop import PointCut
        from parser import ASTClass, ASTPass, ASTFunction, ASTCallFunc, ASTName
        pc1 = PointCut(klass="Mumble")
        pc2 = PointCut(func="frobble")
        pc = (pc1 & pc2).execution()
        f = ASTFunction(None, 'frobble', [], [], 0, '', ASTPass())
        f.parent = ASTClass('MumblesALot', [], None, ASTPass())
        assert pc.match(f)
        f.parent.name = 'Babble'
        assert not pc.match(f)
        c = ASTClass('frobbles_a_bit', [], None, ASTPass())
        c.parent = ASTClass('MumblesALot', [], None, ASTPass())
        assert not pc.match(c)
        
            
class AppTestWeavingAtExecution(object):
    def test_simple_aspect_before_execution(self):
        from  aop import PointCut, Aspect, before
        from app_test import sample_aop_code
        __aop__._clear_all()
        
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

        aop_before_execution = sample_aop_code.import_('aop_before_execution')

        assert  aspect.executed == 0
        answ = aop_before_execution.foo(1,2)
        assert aspect.executed == 1
        assert aspect.argnames == ['b', 'c']
        assert aspect.flags == 0
        assert answ == 47

    def test_aspect_before_meth_execution(self):
        from  aop import PointCut, Aspect, before
        from app_test import sample_aop_code
        __aop__._clear_all()
        
        class AspectTest:
            __metaclass__ = Aspect 
            def __init__(self):
                self.executed = False
            @before(PointCut(func='frobble', klass='Mumble').execution())
            def advice_before_meth_execution(self, tjp):
                self.executed = True
                self.argnames = tjp._argnames
                self.flags = tjp._flags

        assert __aop__.advices == []
        aspect = AspectTest()
        assert __aop__.advices == [(aspect, AspectTest.advice_before_meth_execution)] 
        assert not aspect.executed

        aop_before_meth_execution = sample_aop_code.import_(
            'aop_before_meth_execution')
        assert  aspect.executed == 0
        answ = aop_before_meth_execution.truc()
        assert aspect.executed == 1
        assert aspect.argnames == ['self', 'b']
        assert aspect.flags == 0
        assert answ == 7

    def test_simple_aspect_after_execution(self):
        from  aop import PointCut, Aspect, after
        from app_test import sample_aop_code
        __aop__._clear_all()
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
        aop_after_execution = sample_aop_code.import_('aop_after_execution')
        assert aspect.executed == 0
        answ = aop_after_execution.foo(1,2)
        assert aspect.executed == 1
        assert answ == 47

    def test_simple_aspect_around_execution(self):
        from  aop import PointCut, Aspect, around
        from app_test import sample_aop_code
        __aop__._clear_all()
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
        aop_around_execution = sample_aop_code.import_('aop_around_execution')
        assert aspect.executed_before == 0
        assert aspect.executed_after == 0
        answ = aop_around_execution.foo(1,2)
        assert aspect.executed_before == 1
        assert aspect.executed_after == 1
        assert aspect.result == 47
        assert answ == 47
        

class AppTestWeavingAtCall(object):
    def test_simple_aspect_before_call(self):
        from  aop import PointCut, Aspect, before
        from app_test import sample_aop_code
        __aop__._clear_all()
        
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

        aop_before_call = sample_aop_code.import_('aop_before_call')
        assert  aspect.executed == 0
        answ = aop_before_call.foo(1,2)
        assert aspect.executed == 1
        assert answ == 47

    def test_simple_aspect_after_call(self):
        from  aop import PointCut, Aspect, after
        from app_test import sample_aop_code
        __aop__._clear_all()
        
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

        aop_after_call = sample_aop_code.import_('aop_after_call')
        assert not aspect.executed 
        answ = aop_after_call.foo(1,2)
        assert aspect.executed 
        assert answ == 47
        assert aspect.result == 42

    
    def test_simple_aspect_around_call(self):
        from  aop import PointCut, Aspect, around
        from app_test import sample_aop_code
        __aop__._clear_all()
        class AspectTest:
            __metaclass__ = Aspect 
            def __init__(self):
                self.executed_before = 0
                self.executed_after = 0
            @around(PointCut(func='bar').call())
            def advice_around_call(self, tjp):
                print '>>>in', tjp.arguments()
                self.executed_before += 1
                args, kwargs = tjp.arguments()
                tjp.proceed(*args, **kwargs)
                self.executed_after += 1
                self.result = tjp.result()
                print '<<<out'
                return tjp.result()
        
        aspect = AspectTest()
        aop_around_call = sample_aop_code.import_('aop_around_call')
        assert aspect.executed_before == 0
        assert aspect.executed_after == 0
        answ = aop_around_call.foo(1,2)
        assert aspect.executed_before == 1
        assert aspect.executed_after == 1
        assert aspect.result == 42
        assert answ == 47


class AppTestWeavingIntroduce(object):
    def test_introduce(self):
        from  aop import PointCut, Aspect, introduce
        from app_test import sample_aop_code
        __aop__._clear_all()
        class AspectTest:
            __metaclass__ = Aspect 
            @introduce(PointCut(klass='Mumble'))
            def newmethod(self, it, a, b):
                return it.p*a+b
            
        aspect = AspectTest()
        aop_introduce = sample_aop_code.import_('aop_introduce')
        c = aop_introduce.Mumble(2)
        try:
            answ = c.newmethod(1,3)
        except Exception, exc:
            print exc.__class__.__name__, exc
            assert False
        assert answ == 5
