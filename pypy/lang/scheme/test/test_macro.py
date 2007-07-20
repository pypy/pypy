import py
from pypy.lang.scheme.ssparser import parse
from pypy.lang.scheme.execution import ExecutionContext
from pypy.lang.scheme.object import *

def eval_expr(ctx, expr):
    return parse(expr)[0].eval(ctx)

def eval_noctx(expr):
    return parse(expr)[0].eval(ExecutionContext())

def test_syntax_rules_match():
    py.test.raises(SchemeSyntaxError, eval_noctx, "(syntax-rules 1)")
    py.test.raises(SchemeSyntaxError, eval_noctx, "(syntax-rules () 1)")

    w_transformer = eval_noctx("(syntax-rules ())")
    w_expr = parse("(foo)")[0]
    assert not w_transformer.match(w_expr)

    w_transformer = eval_noctx("(syntax-rules () ((foo) #t))")
    w_expr = parse("(bar)")[0]
    assert w_transformer.match(w_expr)
    w_expr = parse("(foo bar)")[0]
    assert not w_transformer.match(w_expr)

    w_transformer = eval_noctx("""(syntax-rules () ((_) #t)
                                                   ((_ foo) foo))""")
    w_expr = parse("(foo)")[0]
    assert w_transformer.match(w_expr).to_boolean()
    w_expr = parse("(foo bar)")[0]
    assert w_transformer.match(w_expr).to_string() == "foo"

