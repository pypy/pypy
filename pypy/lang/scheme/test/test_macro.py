import py
from pypy.lang.scheme.ssparser import parse
from pypy.lang.scheme.execution import ExecutionContext
from pypy.lang.scheme.object import *

def eval_(ctx, expr):
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
    assert w_transformer.match_dict["foo"].to_string() == "bar"

    w_expr = parse("(foo bar boo)")[0]
    assert not w_transformer.match(w_expr)
    assert w_transformer.match_dict == {}

    w_transformer = eval_noctx("(syntax-rules () ((foo (bar)) bar))")
    w_expr = parse("(_ fuzz)")[0]
    assert not w_transformer.match(w_expr)
    w_expr = parse("(_ (fuzz))")[0]
    assert w_transformer.match(w_expr)
    assert w_transformer.match_dict["bar"].to_string() == "fuzz"

def test_syntax_rules_literals():
    ctx = ExecutionContext()

    # => is literal, should be matched exactly
    # w_transformer created in ctx
    w_transformer = eval_(ctx, "(syntax-rules (=>) ((foo => bar) #t))")

    w_expr = parse("(foo bar boo)")[0]
    assert not w_transformer.match(w_expr, ctx)

    # exact match
    w_expr = parse("(foo => boo)")[0]

    # within the same context
    assert w_transformer.match(w_expr, ctx)

    w_42 = W_Number(42)

    # different lexical scope, not the same bindings for => in ctx and closure
    closure = ctx.copy()
    closure.put("=>", w_42)
    w_transformer = eval_(ctx, "(syntax-rules (=>) ((foo => bar) #t))")
    assert not w_transformer.match(w_expr, closure)

    # different lexical scope, not the same bindings for => in ctx and closure
    ctx.put("=>", W_Number(12))
    assert ctx.get("=>") is not closure.get("=>")
    w_transformer = eval_(ctx, "(syntax-rules (=>) ((foo => bar) #t))")
    assert not w_transformer.match(w_expr, closure)

    # the same binding for => in ctx and closure
    ctx.put("=>", w_42)
    assert ctx.get("=>") is closure.get("=>")
    w_transformer = eval_(ctx, "(syntax-rules (=>) ((foo => bar) #t))")
    assert w_transformer.match(w_expr, closure)

def test_syntax_rules_expand_simple():
    ctx = ExecutionContext()

    w_transformer = eval_(ctx, """(syntax-rules () ((_) #t)
                                                   ((_ foo) foo))""")

    w_expr = parse("(foo)")[0]
    w_expanded = w_transformer.expand(w_expr, ctx)
    assert isinstance(w_expanded, W_Boolean)
    assert w_expanded.to_boolean() == True

    w_expr = parse("(foo bar)")[0]
    w_expanded = w_transformer.expand(w_expr, ctx)
    assert w_expanded.to_string() == "bar"

    w_transformer = eval_(ctx, """(syntax-rules ()
                                        ((let1 var val body)
                                         (let ((var val)) body)))""")

    w_expr = parse("(let1 var 12 (+ 1 var))")[0]
    w_expanded = w_transformer.expand(w_expr, ctx)
    assert isinstance(w_expanded, W_Pair)
    assert w_expanded.to_string() == "(let ((var 12)) (+ 1 var))"

    w_transformer = eval_(ctx, """(syntax-rules ()
                                        ((let1 (var val) body)
                                         (let ((var val)) body)))""")

    w_expr = parse("(let1 (var 12) (+ 1 var))")[0]
    w_expanded = w_transformer.expand(w_expr, ctx)
    assert isinstance(w_expanded, W_Pair)
    assert w_expanded.to_string() == "(let ((var 12)) (+ 1 var))"

def test_syntax_rules_expand():
    ctx = ExecutionContext()

    w_transformer = eval_(ctx, """(syntax-rules ()
                                       ((_ var)
                                        (let ((temp 1)) (+ var temp))))""")

    w_expr = parse("(_ 12)")[0]
    w_expanded = w_transformer.expand(w_expr, ctx)
    assert w_expanded.to_string() == "(let ((temp 1)) (+ 12 temp))"
    assert w_transformer.expand_eval(w_expr, ctx).to_number() == 13

    #transparency
    eval_(ctx, "(define temp 12)")
    w_expr = parse("(_ temp)")[0]
    w_expanded = w_transformer.expand(w_expr, ctx)
    assert w_expanded.to_string() == "(let ((temp 1)) (+ temp temp))"
    assert w_transformer.expand_eval(w_expr, ctx).to_number() == 13

    #define in closure, should not affect macro eval
    closure = ctx.copy()
    eval_(closure, "(define + -)")
    assert w_transformer.expand_eval(w_expr, closure).to_number() == 13

    #define in top level - should affect macro eval
    eval_(ctx, "(define + -)")
    assert w_transformer.expand_eval(w_expr, ctx).to_number() == 11

def test_syntax_rules_hygenic_expansion():
    ctx = ExecutionContext()

    w_transformer = eval_(ctx, """(syntax-rules ()
                                     ((dotimes count body)
                                      (letrec ((loop
                                       (lambda (counter)
                                         (if (= counter 0)
                                             #f
                                             (begin
                                                body
                                                (loop (- counter 1)))))))
                                        (loop count))))""")

    w_expr = parse("(dotimes 5 (set! counter (+ counter 1)))")[0]
    py.test.raises(UnboundVariable, w_transformer.expand_eval, w_expr, ctx)

    eval_(ctx, "(define counter 0)")
    w_expr = parse("(dotimes 5 (set! counter (+ counter 1)))")[0]
    w_transformer.expand_eval(w_expr, ctx)
    assert ctx.get("counter").to_number() == 5

def test_shadow():
    ctx = ExecutionContext()

    w_transformer = eval_(ctx, """(syntax-rules ()
                                     ((shadow used-arg body)
                                      (let ((used-arg 5)) body)))""")

    w_expr = parse("(shadow test test)")[0]
    assert w_transformer.expand_eval(w_expr, ctx).to_number() == 5

    eval_(ctx, "(define test 7)")
    assert w_transformer.expand_eval(w_expr, ctx).to_number() == 5

def test_transformer_eval():
    ctx = ExecutionContext()
    eval_(ctx, """(define foo (syntax-rules ()
                                     ((_) #t)
                                     ((_ bar) bar)))""")

    w_foo = eval_(ctx, "(foo '(_))")
    assert w_foo.to_boolean()

    w_foobar = eval_(ctx, """(foo '(_ 42))""")
    assert w_foobar.to_number() == 42

def test_define_syntax():
    ctx = ExecutionContext()
    eval_(ctx, """(define-syntax foo (syntax-rules ()
                                     ((_) #t)
                                     ((_ bar) bar)))""")
    w_foo = eval_(ctx, """(foo)""")
    assert w_foo.to_boolean()

    w_foobar = eval_(ctx, """(foo 42)""")
    assert w_foobar.to_number() == 42

