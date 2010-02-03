# minimal test: just checks that (parts of) rsre can be translated

from pypy.rpython.test.test_llinterp import gengraph
from pypy.rlib.rsre.test import targetrsre

def main(n):
    state = targetrsre.rsre.SimpleStringState(str(n))
    return state.search(targetrsre.r_code1)


def test_gengraph():
    t, typer, graph = gengraph(main, [int])
