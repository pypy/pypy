from pypy.translator.interactive import Translation
import py

def test_simple_annotate():

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    assert t.context is t.driver.translator
    assert t.config is t.driver.config is t.context.config
    
    s = t.annotate([int, int])
    assert s.knowntype == int

    t = Translation(f, [int, int])
    s = t.annotate()
    assert s.knowntype == int

    t = Translation(f)
    s = t.annotate([int, int])
    assert s.knowntype == int

    t = Translation(f, [int, int])
    py.test.raises(Exception, "t.annotate([int, float])")


def test_simple_rtype():

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    s = t.annotate()
    t.rtype()

    assert 'rtype_lltype' in t.driver.done    

    t = Translation(f)
    s = t.annotate([int, int])
    t.rtype()

    assert 'rtype_lltype' in t.driver.done        

def test_simple_backendopt():
    def f(x, y):
        return x,y

    t = Translation(f, [int, int], backend='c')
    t.backendopt()
    
    assert 'backendopt_lltype' in t.driver.done

    t = Translation(f, [int, int])
    t.backendopt()

    assert 'backendopt_lltype' in t.driver.done

def test_simple_source():
    def f(x, y):
        return x,y

    t = Translation(f, backend='c')
    t.annotate([int, int])
    t.source()
    assert 'source_c' in t.driver.done

    t = Translation(f, [int, int])
    t.source_c()
    assert 'source_c' in t.driver.done

    t = Translation(f, [int, int])
    py.test.raises(Exception, "t.source()")

def test_simple_source_llvm():
    from pypy.translator.llvm.test.runtest import llvm_test
    llvm_test()

    def f(x,y):
        return x+y

    t = Translation(f, [int, int], backend='llvm')
    t.source(gc='boehm')
    assert 'source_llvm' in t.driver.done
    
    t = Translation(f, [int, int])
    t.source_llvm()
    assert 'source_llvm' in t.driver.done
    
def test_disable_logic():

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    t.disable(['backendopt'])
    t.source_c()

    assert 'backendopt' not in t.driver.done

def test_simple_compile_c():
    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    t.source(backend='c')
    t_f = t.compile()

    res = t_f(2,3)
    assert res == 5

    t = Translation(f, [int, int])
    t_f = t.compile_c()

    res = t_f(2,3)
    assert res == 5

def test_simple_rtype_with_type_system():

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    s = t.annotate()
    t.rtype(type_system='lltype')

    assert 'rtype_lltype' in t.driver.done    

    t = Translation(f, [int, int])
    s = t.annotate()
    t.rtype(type_system='ootype')
    assert 'rtype_ootype' in t.driver.done        

    t = Translation(f, type_system='ootype')
    s = t.annotate([int, int])
    t.rtype()
    assert 'rtype_ootype' in t.driver.done    

    t = Translation(f)
    s = t.annotate([int, int])
    t.rtype(backend='cli')
    assert 'rtype_ootype' in t.driver.done


    t = Translation(f, backend='cli', type_system='ootype')
    s = t.annotate([int, int])
    t.rtype()
    assert 'rtype_ootype' in t.driver.done        

    t = Translation(f, type_system='lltype')
    s = t.annotate([int, int])
    py.test.raises(Exception, "t.rtype(backend='cli')")

    t = Translation(f, backend='cli')
    s = t.annotate([int, int])
    py.test.raises(Exception, "t.rtype(type_system='lltype')")

