from pypy.lang.scheme.ssparser import parse
from pypy.lang.scheme.astbuilder import ASTBuilder
from pypy.rlib.parsing.parsing import Symbol, Nonterminal

def test_simple_sexpr():
    #parse simple sexpr
    t = parse(r'''(+ 1 2)''')
    assert isinstance(t, Nonterminal)
    assert len(t.children) == 3

def test_string():
    #parse string
    t = parse(r'''"don't beleive \"them\""''')
    assert isinstance(t, Symbol)

def test_complex_sexpr():
    #parse more complex sexpr
    t = parse(r'''
        (define (fac n) ; comment
            (if (< n 2) n
                (* (fac (- n 1)) n)))
        ''')
    assert isinstance(t, Nonterminal)
    assert len(t.children) == 3
    assert isinstance(t.children[0], Symbol)
    assert isinstance(t.children[1], Nonterminal)
    assert isinstance(t.children[2], Nonterminal)

def test_ident_gen():
    ch_list = "+-*/azAZ09<=>-_~!$%&:?^"
    for char in ch_list:
        yield check_ident_ch, char

def check_ident_ch(char):
    t = parse("(" + char + ")")
    assert isinstance(t, Nonterminal)
    assert isinstance(t.children[0], Symbol)

def eval_expr(expr):
    t = parse(expr)
    astb = ASTBuilder()
    ast = astb.dispatch(t)
    # evaluate with no context
    return ast.eval(None)

def test_eval_obj():
    w_num = eval_expr(r'''1''')
    assert w_num.to_number() == 1 
