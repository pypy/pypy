class AppTestInterpObjectPickling:

    def test_pickle_code(self):
        def f():
            return 42
        import pickle
        code = f.func_code
        pckl = pickle.dumps(code)
        result = pickle.loads(pckl)
        assert code == result

    def test_pickle_func(self):
        skip("work in progress")
        def func():
            return 42
        import pickle
        pckl = pickle.dumps(func)
        result = pickle.loads(pckl)
        assert func == result
        
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

    def test_pickle_module(self): #XXX this passes for the wrong reason!
        skip("work in progress")
        def f():
            pass
        import pickle
        mod    = f.__module__ #XXX returns a string?
        pckl   = pickle.dumps(mod)
        result = pickle.loads(pckl)
        assert mod == result

    def test_pickle_moduledict(self): #XXX this test is not correct!
        skip("work in progress")
        def f():
            pass
        import pickle
        modedict = f.__module__.__dict__ 
        pckl     = pickle.dumps(moddict)
        result   = pickle.loads(pckl)
        assert mod == result

    def test_pickle_iter(self):
        skip("work in progress")

    def test_pickle_method(self):
        skip("work in progress")
        class C(object):
            def f(self):
                pass
        import pickle
        method   = C.f
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

    def test_pickle_enumfactory(self):
        skip("work in progress")
        
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

    def test_pickle_rangeiter(self):
        skip("work in progress")
        import pickle
        riter  = iter(xrange(5))
        pckl   = pickle.dumps(riter)
        result = pickle.loads(pckl)
        assert riter == result

    def test_pickle_generator(self):
        skip("work in progress")
        import pickle        
        def giveme(n):
            x = 0
            while x < n:
                yield x
        generator = giveme(10)
        print pickle.dumps(generator)
