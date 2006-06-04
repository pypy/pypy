class AppTestInterpObjectPickling:

    def test_pickle_code(self):
        def f():
            return 42
        import pickle
        code = f.func_code
        pckl = pickle.dumps(code)
        result = pickle.loads(pckl)
        assert code == result
    
    def test_pickle_global_func(self):
        import new
        mod = new.module('mod')
        import sys
        sys.modules['mod'] = mod
        try:
            def func():
                return 42
            mod.__dict__['func'] = func
            func.__module__ = 'mod'
            import pickle
            pckl = pickle.dumps(func)
            result = pickle.loads(pckl)
            assert func is result
        finally:
            del sys.modules['mod']
    
    def test_pickle_not_imported_module(self):
        import new
        mod = new.module('mod')
        mod.__dict__['a'] = 1
        import pickle
        pckl = pickle.dumps(mod)
        result = pickle.loads(pckl)
        assert mod.__name__ == result.__name__
        assert mod.__dict__ == result.__dict__
    
    def test_pickle_builtin_func(self):
        import pickle
        pckl = pickle.dumps(map)
        result = pickle.loads(pckl)
        assert map is result
    
    def test_pickle_non_top_reachable_func(self):
        def func():
            return 42
        global a
        a = 42
        del globals()['test_pickle_non_top_reachable_func']
        import pickle
        pckl   = pickle.dumps(func)
        result = pickle.loads(pckl)
        assert func.func_name     == result.func_name
        assert func.func_closure  == result.func_closure
        assert func.func_code     == result.func_code
        assert func.func_defaults == result.func_defaults
        assert func.func_dict     == result.func_dict
        assert func.func_doc      == result.func_doc
        assert func.func_globals  == result.func_globals
    
    def test_pickle_cell(self):
        def g():
            x = [42]
            def f():
                x[0] += 1
                return x
            return f.func_closure[0]
        import pickle
        cell = g()
        pckl = pickle.dumps(cell)
        result = pickle.loads(pckl)
        assert cell == result
        assert not (cell != result)

    def test_pickle_frame(self):
        skip("in-progress")
        from sys import exc_info
        def f():
            try:
                raise Exception()
            except:
                exc_type, exc, tb = exc_info()
                return tb.tb_frame
        import pickle
        f1     = f()
        pckl   = pickle.dumps(f1)
        f2     = pickle.loads(pckl)

        assert type(f1) is type(f2)
        assert dir(f1) == dir(f2)
        assert f1.__doc__ == f2.__doc__
        assert type(f1.f_back) is type(f2.f_back)
        assert f1.f_builtins is f2.f_builtins
        assert f1.f_code == f2.f_code
        assert f1.f_exc_traceback is f2.f_exc_traceback
        assert f1.f_exc_type is f2.f_exc_type
        assert f1.f_exc_value is f2.f_exc_value
        assert f1.f_lasti == f2.f_lasti
        assert f1.f_lineno == f2.f_lineno
        assert f1.f_restricted is f2.f_restricted
        assert f1.f_trace is f2.f_trace

    def test_pickle_traceback(self):
        skip("in-progress")
        def f():
            try:
                raise Exception()
            except:
                from sys import exc_info
                exc_type, exc, tb = exc_info()
                return tb
        import pickle
        tb     = f()
        pckl   = pickle.dumps(tb)
        result = pickle.loads(pckl)

        assert type(tb) is type(result)
        assert tb.tb_lasti == result.tb_lasti
        assert tb.tb_lineno == result.tb_lineno
        assert tb.tb_next == result.tb_next

        #XXX silly code duplication from frame pickling test
        f1 = tb.tb_frame
        f2 = result.tb_frame
        assert type(f1) is type(f2)
        assert dir(f1) == dir(f2)
        assert f1.__doc__ == f2.__doc__
        assert type(f1.f_back) is type(f2.f_back)
        assert f1.f_builtins is f2.f_builtins
        assert f1.f_code == f2.f_code
        assert f1.f_exc_traceback is f2.f_exc_traceback
        assert f1.f_exc_type is f2.f_exc_type
        assert f1.f_exc_value is f2.f_exc_value

        #print 'f1.f_globals =', f1.f_globals #f1.f_globals = {'__builtins__': <module object at 0x0167dc70>, '__name__': '__builtin__', 'test_pickle_frame': <function test_pickle_frame at 0x0237adb0>}
        #print 'f2.f_globals=', f2.f_globals  #f2.f_globals= {'__builtins__': <module object at 0x0167dc70>, '__name__': '__builtin__', 'test_pickle_frame': <function test_pickle_frame at 0x02c346f0>}
        #assert f1.f_globals == f2.f_globals  #XXX test_pickle_frame function not same identity (see pickle func tests, we don't compare by identity there!)?

        assert f1.f_lasti == f2.f_lasti
        assert f1.f_lineno == f2.f_lineno

        #print 'f1.f_locals=', f1.f_locals     #['exc_info', 'tb', 'exc_type', 'exc']
        #print 'f2.f_locals=', f2.f_locals   #[]
        #assert list(f1.f_locals) == list(f2.f_locals)

        assert f1.f_restricted is f2.f_restricted
        assert f1.f_trace is f2.f_trace

    def test_pickle_module(self):
        import pickle
        mod    = pickle
        pckl   = pickle.dumps(mod)
        result = pickle.loads(pckl)
        assert mod is result
    
    def test_pickle_moduledict(self):
        import pickle
        moddict  = pickle.__dict__
        pckl     = pickle.dumps(moddict)
        result   = pickle.loads(pckl)
        assert moddict is result
    
    def test_pickle_bltins_module(self):
        import pickle
        mod  = __builtins__
        pckl     = pickle.dumps(mod)
        result   = pickle.loads(pckl)
        assert mod is result
    
    def test_pickle_buffer(self):
        import pickle
        a = buffer('ABCDEF')
        pckl     = pickle.dumps(a)
        result   = pickle.loads(pckl)
        assert a == result
    
    def test_pickle_complex(self):
        import pickle
        a = complex(1.23,4.567)
        pckl     = pickle.dumps(a)
        result   = pickle.loads(pckl)
        assert a == result
    
    def test_pickle_method(self):
        class myclass(object):
            def f(self):
                return 42
            def __reduce__(self):
                return (myclass, ())
        import pickle, sys, new
        myclass.__module__ = 'mod'
        myclass_inst = myclass()
        mod = new.module('mod')
        mod.myclass = myclass
        sys.modules['mod'] = mod
        try:
            method   = myclass_inst.f
            pckl     = pickle.dumps(method)
            result   = pickle.loads(pckl)
            # we cannot compare the objects, because the method will be a fresh one
            assert method() == result()
        finally:
            del sys.modules['mod']
    
    def test_pickle_staticmethod(self):
        class myclass(object):
            def f():
                return 42
            f = staticmethod(f)
        import pickle
        method   = myclass.f
        pckl     = pickle.dumps(method)
        result   = pickle.loads(pckl)
        assert method() == result()
    
    def test_pickle_classmethod(self):
        class myclass(object):
            def f(cls):
                return cls
            f = classmethod(f)
        import pickle, sys, new
        myclass.__module__ = 'mod'
        mod = new.module('mod')
        mod.myclass = myclass
        sys.modules['mod'] = mod
        try:
            method   = myclass.f
            pckl     = pickle.dumps(method)
            result   = pickle.loads(pckl)
            assert method() == result()
        finally:
            del sys.modules['mod']
    
    def test_pickle_sequenceiter(self):
        '''
        In PyPy there is no distinction here between listiterator and
        tupleiterator that is why you will find no test_pickle_listiter nor
        test_pickle_tupleiter here, just this test.
        '''
        import pickle
        liter  = iter([3,9,6,12,15,17,19,111])
        liter.next()
        pckl   = pickle.dumps(liter)
        result = pickle.loads(pckl)
        liter.next()
        result.next()
        assert type(liter) is type(result)
        assert len(liter) == 6
        assert list(liter) == list(result)

    def test_pickle_reversesequenceiter(self):
        import pickle
        liter  = reversed([3,9,6,12,15,17,19,111])
        liter.next()
        pckl   = pickle.dumps(liter)
        result = pickle.loads(pckl)
        liter.next()
        result.next()
        assert type(liter) is type(result)
        assert len(liter) == 6
        assert list(liter) == list(result)

    def test_pickle_dictiter(self):
        import pickle
        tdict = {'2':2, '3':3, '5':5}
        diter  = iter(tdict)
        diter.next()
        pckl   = pickle.dumps(diter)
        result = pickle.loads(pckl)
        assert len(diter) == 2
        assert list(diter) == list(result)
    
    def test_pickle_enum(self):
        import pickle
        e      = enumerate(range(10))
        e.next()
        e.next()
        pckl   = pickle.dumps(e)
        result = pickle.loads(pckl)
        e.next()
        result.next()
        assert type(e) is type(result)
        assert list(e) == list(result)

    def test_pickle_xrangeiter(self):
        import pickle
        riter  = iter(xrange(5))
        riter.next()
        riter.next()
        pckl   = pickle.dumps(riter)
        result = pickle.loads(pckl)
        assert type(riter) is type(result)
        assert list(result) == [2,3,4]
    
    def test_pickle_generator(self):
        import new
        mod = new.module('mod')
        import sys
        sys.modules['mod'] = mod
        try:
            def giveme(n):
                x = 0
                while x < n:
                    yield x
                    x += 1
            import pickle
            mod.giveme = giveme
            giveme.__module__ = mod
            g1   = mod.giveme(10)
            #g1.next()
            #g1.next()
            pckl = pickle.dumps(g1)
            g2   = pickle.loads(pckl)
            assert list(g1) == list(g2)
        finally:
            del sys.modules['mod']
