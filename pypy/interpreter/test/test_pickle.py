class AppTestInterpObjectPickling:

    def test_pickle_code(self):
        import pickle
        def f():
            return 42
        code = f.func_code
        pckl = pickle.dumps(code)
        result = pickle.loads(pckl)
        assert code == result

    def DONTtest_pickle_func(self):
        pass
    
    def test_pickle_cell(self):
        import pickle       
        def g():
            x = [42]
            def f():
                x[0] += 1
                return x
            return f.func_closure[0]
        cell = g()
        pckl = pickle.dumps(g())
        result = pickle.loads(pckl)
        assert cell == result
        assert not (cell != result)

    def DONTtest_pickle_frame(self):
        pass

    def DONTtest_pickle_traceback(self):
        pass

    def DONTtest_pickle_module(self):
        pass

    def DONTtest_pickle_moduledict(self):
        pass

    def DONTtest_pickle_iter(self):
        pass

    def DONTtest_pickle_method(self):
        pass

    def DONTtest_pickle_dictiter(self):
        pass

    def DONTtest_pickle_enum(self):
        pass

    def DONTtest_pickle_enumfactory(self):
        pass

    def DONTtest_pickle_listiter(self):
        pass

    def DONTtest_pickle_rangeiter(self):
        pass

    def DONTtest_pickle_tupleiter(self):
        pass

    #def test_pickle_generator(self):
    #    import pickle        
    #    def giveme(n):
    #        x = 0
    #        while x < n:
    #            yield x
    #    generator = giveme(10)
    #    print pickle.dumps(generator)
