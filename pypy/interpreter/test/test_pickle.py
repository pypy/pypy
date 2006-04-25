import py
import pickle

def test_pickle_cell():
    py.test.skip("cell pickling is work in progress")
    def g():
        x = None
        def f():
            return x
        return f.func_closure[0]
    try:
        cell = g()
        pickle.dumps(cell)
    except IndexError, e:
        raise

def test_pickle_generator():
    py.test.skip("generator pickling is work in progress")
    def giveme(n):
        x = 0
        while x < n:
            yield x
    generator = giveme(10)
    pickle.dumps(generator)
    
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
