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
        assert frame == result
        
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

    def test_pickle_method(self):
        skip("work in progress")
        class myclass(object):
            def f(self):
                pass
        import pickle
        method   = myclass.f
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

    def test_pickle_dictiter(self):
        skip("work in progress")
        import pickle
        diter  = iter({})
        pckl   = pickle.dumps(diter)
        result = pickle.loads(pckl)
        assert diter == result

    def test_pickle_enum(self):
        skip("work in progress")
        import pickle
        e      = enumerate([])
        pckl   = pickle.dumps(e)
        result = pickle.loads(pckl)
        assert e == result
        
    #def test_pickle_enumfactory(self):
    #    skip("work in progress")

    def test_pickle_sequenceiter(self):
        '''
        In PyPy there is no distinction here between listiterator and
        tupleiterator that is why you will find no test_pickle_listiter nor
        test_pickle_tupleiter here, just this test.
        '''
        skip("work in progress")
        import pickle
        liter  = iter([])
        pckl   = pickle.dumps(liter)
        result = pickle.loads(pckl)
        assert liter == result

    def test_pickle_xrangeiter(self):
        import pickle
        riter  = iter(xrange(5))
        riter.next()
        riter.next()
        pckl   = pickle.dumps(riter)
        result = pickle.loads(pckl)
        assert type(riter) is type(result)
        assert list(result) == [2,3,4]

    def test_pickle_reversed_iterator(self):
        import pickle
        i = reversed(xrange(5))
        i.next()
        i.next()
        pckl   = pickle.dumps(i)
        result = pickle.loads(pckl)
        assert type(i) is type(result)
        assert list(result) == [2,1,0]

    def test_pickle_generator(self):
        skip("work in progress")
        import pickle        
        def giveme(n):
            x = 0
            while x < n:
                yield x
        generator = giveme(10)
        print pickle.dumps(generator)
