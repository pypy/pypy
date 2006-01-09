from pypy.translator.interactive import Translation
import py

def test_simple_annotate():

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
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

    t = Translation(f)
    s = t.annotate([int, int])
    t.rtype()

    t = Translation(f, [int, int])
    t.annotate()
    py.test.raises(Exception, "t.rtype([int, int],debug=False)")

def test_simple_backendopt():
    def f(x, y):
        return x,y

    t = Translation(f, [int, int], backend='c')
    t.backendopt()

    t = Translation(f, [int, int])
    t.backendopt_c()

    t = Translation(f, [int, int])
    py.test.raises(Exception, "t.backendopt()")

def test_simple_source():
    def f(x, y):
        return x,y

    t = Translation(f, backend='c')
    t.annotate([int, int])
    t.source()

    t = Translation(f, [int, int])
    t.source_c()

    t = Translation(f, [int, int])
    py.test.raises(Exception, "t.source()")

def test_simple_source_llvm():
    from pypy.translator.llvm.test.runtest import llvm_test
    llvm_test()

    def f(x,y):
        return x+y


    t = Translation(f, [int, int], backend='llvm')
    t.source(gc='boehm')
    
    t = Translation(f, [int, int])
    t.source_llvm()
    
