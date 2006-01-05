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
