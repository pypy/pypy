class AppTestInterpObjectPickling:
 
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

    #def test_pickle_generator(self):
    #    import pickle        
    #    def giveme(n):
    #        x = 0
    #        while x < n:
    #            yield x
    #    generator = giveme(10)
    #    print pickle.dumps(generator)
    
#TODO: test pickling of code objects
#TODO: test pickling of function objects
#TODO: test pickling of frame objects
#TODO: test pickling of tracebacks
#TODO: test pickling of modules

'''
etc. etc. etc.
init_codetype()
init_functype()
init_celltype()
init_frametype()
init_tracebacktype()
init_moduletype()
init_moduledicttype()
init_itertype()
init_methodtype()
init_dictitertype()
init_enumtype()
init_enumfactorytype()
init_listitertype()
init_rangeitertype()
init_tupleitertype()
'''
