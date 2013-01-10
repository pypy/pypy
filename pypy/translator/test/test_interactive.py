from pypy.translator.interactive import Translation
import py

def test_simple_annotate():

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    assert t.context is t.driver.translator
    assert t.config is t.driver.config is t.context.config
    
    s = t.annotate()
    assert s.knowntype == int

    t = Translation(f, [int, int])
    s = t.annotate()
    assert s.knowntype == int


def test_simple_rtype():

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    t.annotate()
    t.rtype()

    assert 'rtype_lltype' in t.driver.done    

def test_simple_backendopt():
    def f(x, y):
        return x,y

    t = Translation(f, [int, int], backend='c')
    t.backendopt()
    
    assert 'backendopt_lltype' in t.driver.done

def test_simple_source():
    def f(x, y):
        return x,y

    t = Translation(f, [int, int], backend='c')
    t.annotate()
    t.source()
    assert 'source_c' in t.driver.done

    t = Translation(f, [int, int])
    t.source_c()
    assert 'source_c' in t.driver.done

    t = Translation(f, [int, int])
    py.test.raises(Exception, "t.source()")
    
def test_disable_logic():

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    t.disable(['backendopt'])
    t.source_c()

    assert 'backendopt' not in t.driver.done

def test_simple_compile_c():
    import ctypes
    
    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    t.source(backend='c')
    t.compile()

    dll = ctypes.CDLL(str(t.driver.c_entryp))
    f = dll.pypy_g_f
    assert f(2, 3) == 5

def test_simple_rtype_with_type_system():

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    t.rtype(type_system='lltype')

    assert 'rtype_lltype' in t.driver.done    

    t = Translation(f, [int, int])
    t.rtype(type_system='ootype')
    assert 'rtype_ootype' in t.driver.done        

    t = Translation(f, [int, int], type_system='ootype')
    t.rtype()
    assert 'rtype_ootype' in t.driver.done    

    t = Translation(f, [int, int])
    t.rtype(backend='cli')
    assert 'rtype_ootype' in t.driver.done


    t = Translation(f, [int, int], backend='cli', type_system='ootype')
    t.rtype()
    assert 'rtype_ootype' in t.driver.done        

    t = Translation(f, [int, int], type_system='lltype')
    t.annotate()
    py.test.raises(Exception, "t.rtype(backend='cli')")

    t = Translation(f, [int, int], backend='cli')
    t.annotate()
    py.test.raises(Exception, "t.rtype(type_system='lltype')")

