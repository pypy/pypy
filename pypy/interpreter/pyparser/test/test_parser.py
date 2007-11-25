from pypy.interpreter.pyparser.asthelper import get_atoms
from pypy.interpreter.pyparser.grammar import Parser
from pypy.interpreter.pyparser import error
from fakes import FakeSpace


def test_symbols():
    p = Parser()
    x1 = p.add_symbol('sym')
    x2 = p.add_token('tok')
    x3 = p.add_anon_symbol(':sym')
    x4 = p.add_anon_symbol(':sym1')
    # test basic numbering assumption
    # symbols and tokens are attributed sequentially
    # using the same counter
    assert x2 == x1 + 1
    # anon symbols have negative value
    assert x3 != x2 + 1
    assert x4 == x3 - 1
    assert x3 < 0
    y1 = p.add_symbol('sym')
    assert y1 == x1
    y2 = p.add_token('tok')
    assert y2 == x2
    y3 = p.add_symbol(':sym')
    assert y3 == x3
    y4 = p.add_symbol(':sym1')
    assert y4 == x4


def test_load():
    d = { 5 : 'sym1',
          6 : 'sym2',
          9 : 'sym3',
          }
    p = Parser()
    p.load_symbols( d )
    v = p.add_symbol('sym4')
    # check that we avoid numbering conflicts
    assert v>9
    v = p.add_symbol( 'sym1' )
    assert v == 5
    v = p.add_symbol( 'sym2' )
    assert v == 6
    v = p.add_symbol( 'sym3' )
    assert v == 9


