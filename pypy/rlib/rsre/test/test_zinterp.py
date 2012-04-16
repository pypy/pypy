# minimal test: just checks that (parts of) rsre can be translated

from pypy.rpython.test.test_llinterp import gengraph, interpret
from pypy.rlib.rsre import rsre_core
from pypy.rlib.rsre.rsre_re import compile

def main(n):
    assert n >= 0
    pattern = [n] * n
    string = chr(n) * n
    rsre_core.search(pattern, string)
    #
    unicodestr = unichr(n) * n
    ctx = rsre_core.UnicodeMatchContext(pattern, unicodestr,
                                        0, len(unicodestr), 0)
    rsre_core.search_context(ctx)
    #
    return 0


def test_gengraph():
    t, typer, graph = gengraph(main, [int])

m = compile("(a|b)aaaaa")

def test_match():
    def f(i):
        if i:
            s = "aaaaaa"
        else:
            s = "caaaaa"
        g = m.match(s)
        if g is None:
            return 3
        return int("aaaaaa" == g.group(0))
    assert interpret(f, [3]) == 1
    assert interpret(f, [0]) == 3
