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
        def func():
            return 42
        mod.__dict__['func'] = func
        func.__module__ = 'mod'
        import pickle
        pckl = pickle.dumps(func)
        result = pickle.loads(pckl)
        assert func is result
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
        #print mod.__dict__
    
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
        '''
        >>>> dir(frame)
        ['__class__', '__delattr__', '__doc__', '__getattribute__', '__hash__', '__init__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__str__', 'f_back', 'f_builtins', 'f_code', 'f_exc_traceback', 'f_exc_type', 'f_exc_value', 'f_globals', 'f_lasti', 'f_lineno', 'f_locals', 'f_restricted', 'f_trace']
        '''
        skip("work in progress")
        from sys import exc_info
        def f():
            try:
                raise Exception()
            except:
                exc_type, exc, tb = exc_info()
                return tb.tb_frame
        import pickle
        frame  = f()
        pckl   = pickle.dumps(frame)
        result = pickle.loads(pckl)
        assert type(frame) is type(result)
        assert dir(frame) == dir(result)
        assert frame.__doc__ == result.__doc__
        assert type(frame.f_back) is type(result.f_back)
        assert frame.f_builtins is result.f_builtins
        assert frame.f_code is result.f_code
        assert frame.f_exc_traceback is result.f_exc_traceback
        assert frame.f_exc_type is result.f_exc_type
        assert frame.f_exc_value is result.f_exc_value
        assert frame.f_globals is result.f_globals
        assert frame.f_lasti == result.f_lasti
        assert frame.f_lineno == result.f_lineno
        assert list(frame.f_locals) == list(result.f_locals)
        assert frame.f_restricted is result.f_restricted
        assert frame.f_trace is result.f_trace

    def test_pickle_traceback(self):
        skip("work in progress")
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
        assert tb == result
    
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
        skip("work in progress")
        class myclass(object):
            def f(self):
                pass
            def __reduce__(self):
                return (myclass,())
        import pickle
        myclass_inst = myclass()
        method   = myclass_inst.f
        pckl     = pickle.dumps(method)
        result   = pickle.loads(pckl)
        assert method == result
        
    
    def test_pickle_staticmethod(self):
        skip("work in progress")
        class myclass(object):
            def f(self):
                pass
            f = staticmethod(f)
        import pickle
        method   = myclass.f
        pckl     = pickle.dumps(method)
        result   = pickle.loads(pckl)
        assert method == result
    
    def test_pickle_classmethod(self):
        skip("work in progress")
        class myclass(object):
            def f(self):
                pass
            f = classmethod(f)
        import pickle
        method   = myclass.f
        pckl     = pickle.dumps(method)
        result   = pickle.loads(pckl)
        assert method == result
    
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
        skip("work in progress (implement after frame pickling)")
        import pickle
        def giveme(n):
            x = 0
            while x < n:
                yield x
        generator = giveme(10)
        print pickle.dumps(generator)
