import py
from pypy.lang.scheme.ssparser import parse
from pypy.lang.scheme.execution import ExecutionContext
from pypy.lang.scheme.object import *

def eval_(ctx, expr):
    return parse(expr)[0].eval(ctx)

def eval_noctx(expr):
    return parse(expr)[0].eval(ExecutionContext())

def parse_(expr):
    return parse(expr)[0]

def test_syntax_rules_match():
    ctx = ExecutionContext()
    py.test.raises(SchemeSyntaxError, eval_noctx, "(syntax-rules 1)")
    py.test.raises(SchemeSyntaxError, eval_noctx, "(syntax-rules () 1)")

    w_transformer = eval_noctx("(syntax-rules ())")
    w_expr = parse_("(foo)")
    py.test.raises(MatchError, w_transformer.match, ctx, w_expr)

    w_transformer = eval_noctx("(syntax-rules () ((foo) #t))")
    w_expr = parse_("(bar)")
    assert w_transformer.match(ctx, w_expr)[0].to_boolean()
    w_expr = parse_("(foo bar)")
    py.test.raises(MatchError, w_transformer.match, ctx, w_expr)

    w_transformer = eval_noctx("""(syntax-rules () ((_) #t)
                                                   ((_ foo) foo))""")
    w_expr = parse_("(foo)")
    assert w_transformer.match(ctx, w_expr)[0].to_boolean()
    w_expr = parse_("(foo bar)")
    (template, match_dict) = w_transformer.match(ctx, w_expr)
    assert template.to_string() == "foo"
    assert match_dict["foo"].to_string() == "bar"

    w_expr = parse_("(foo bar boo)")
    py.test.raises(MatchError, w_transformer.match, ctx, w_expr)

    w_transformer = eval_noctx("(syntax-rules () ((foo (bar)) bar))")
    w_expr = parse_("(_ fuzz)")
    py.test.raises(MatchError, w_transformer.match, ctx, w_expr)
    w_expr = parse_("(_ (fuzz))")
    (template, match_dict) = w_transformer.match(ctx, w_expr)
    assert template.to_string() == "bar"
    assert match_dict["bar"].to_string() == "fuzz"

def test_syntax_rules_literals():
    ctx = ExecutionContext()

    # => is literal, should be matched exactly
    # w_transformer created in ctx
    w_transformer = eval_(ctx, "(syntax-rules (=>) ((foo => bar) #t))")

    w_expr = parse_("(foo bar boo)")
    py.test.raises(MatchError, w_transformer.match, ctx, w_expr)

    # exact match
    w_expr = parse_("(foo => boo)")

    # within the same context
    assert w_transformer.match(ctx, w_expr)[0].to_boolean()

    w_42 = W_Number(42)

    # different lexical scope, not the same bindings for => in ctx and closure
    closure = ctx.copy()
    closure.put("=>", w_42)
    w_transformer = eval_(ctx, "(syntax-rules (=>) ((foo => bar) #t))")
    py.test.raises(MatchError, w_transformer.match, closure, w_expr)

    # different lexical scope, not the same bindings for => in ctx and closure
    ctx.put("=>", W_Number(12))
    assert ctx.get("=>") is not closure.get("=>")
    w_transformer = eval_(ctx, "(syntax-rules (=>) ((foo => bar) #t))")
    py.test.raises(MatchError, w_transformer.match, closure, w_expr)

    # the same binding for => in ctx and closure
    ctx.put("=>", w_42)
    assert ctx.get("=>") is closure.get("=>")
    w_transformer = eval_(ctx, "(syntax-rules (=>) ((foo => bar) #t))")
    assert w_transformer.match(closure, w_expr)[0].to_boolean()

def test_syntax_rules_expand_simple():
    ctx = ExecutionContext()

    w_transformer = eval_(ctx, """(syntax-rules () ((_) #t)
                                                   ((_ foo) foo))""")

    w_expr = parse_("(foo)")
    w_expanded = w_transformer.expand(ctx, w_expr)
    assert isinstance(w_expanded, W_Boolean)
    assert w_expanded.to_boolean() == True

    w_expr = parse_("(foo bar)")
    w_expanded = w_transformer.expand(ctx, w_expr)
    assert w_expanded.to_string() == "bar"

    w_transformer = eval_(ctx, """(syntax-rules ()
                                        ((let1 var val body)
                                         (let ((var val)) body)))""")

    w_expr = parse_("(let1 var 12 (+ 1 var))")
    w_expanded = w_transformer.expand(ctx, w_expr)
    assert isinstance(w_expanded, W_Pair)
    assert w_expanded.to_string() == "(let ((var 12)) (+ 1 var))"

    w_transformer = eval_(ctx, """(syntax-rules ()
                                        ((let1 (var val) body)
                                         (let ((var val)) body)))""")

    w_expr = parse_("(let1 (var 12) (+ 1 var))")
    w_expanded = w_transformer.expand(ctx, w_expr)
    assert isinstance(w_expanded, W_Pair)
    assert w_expanded.to_string() == "(let ((var 12)) (+ 1 var))"

def test_syntax_rules_expand():
    ctx = ExecutionContext()

    w_transformer = eval_(ctx, """(syntax-rules ()
                                       ((_ var)
                                        (let ((temp 1)) (+ var temp))))""")

    w_expr = parse_("(_ 12)")
    w_expanded = w_transformer.expand(ctx, w_expr)
    assert w_expanded.to_string() == "(let ((temp 1)) (+ 12 temp))"
    assert w_transformer.expand_eval(ctx, w_expr).to_number() == 13

    #transparency
    eval_(ctx, "(define temp 12)")
    w_expr = parse_("(_ temp)")
    w_expanded = w_transformer.expand(ctx, w_expr)
    assert w_expanded.to_string() == "(let ((temp 1)) (+ temp temp))"
    assert w_transformer.expand_eval(ctx, w_expr).to_number() == 13

    #define in closure, should not affect macro eval
    closure = ctx.copy()
    eval_(closure, "(define + -)")
    assert w_transformer.expand_eval(closure, w_expr).to_number() == 13

    #define in top level - should affect macro eval
    eval_(ctx, "(define + -)")
    assert w_transformer.expand_eval(ctx, w_expr).to_number() == 11

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

    w_expr = parse_("(dotimes 5 (set! counter (+ counter 1)))")
    py.test.raises(UnboundVariable, w_transformer.expand_eval, ctx, w_expr)

    eval_(ctx, "(define counter 0)")
    w_expr = parse_("(dotimes 5 (set! counter (+ counter 1)))")
    w_transformer.expand_eval(ctx, w_expr)
    assert ctx.get("counter").to_number() == 5

def test_shadow():
    ctx = ExecutionContext()

    w_transformer = eval_(ctx, """(syntax-rules ()
                                     ((shadow used-arg body)
                                      (let ((used-arg 5)) body)))""")

    w_expr = parse_("(shadow test test)")
    assert w_transformer.expand_eval(ctx, w_expr).to_number() == 5

    eval_(ctx, "(define test 7)")
    assert w_transformer.expand_eval(ctx, w_expr).to_number() == 5

    w_transformer = eval_(ctx, """(syntax-rules ()
                                     ((shadow used-arg body)
                                      (letrec ((used-arg 5)) body)))""")

    w_expr = parse_("(shadow test test)")
    assert w_transformer.expand_eval(ctx, w_expr).to_number() == 5

    eval_(ctx, "(define test 7)")
    assert w_transformer.expand_eval(ctx, w_expr).to_number() == 5

def test_transformer_eval():
    ctx = ExecutionContext()
    eval_(ctx, """(define foo (syntax-rules ()
                                     ((_) #t)
                                     ((_ bar) bar)))""")

    assert eval_(ctx, "(foo '(_))").to_boolean()
    assert eval_(ctx, "(foo '(_ 42))").to_number() == 42

def test_define_syntax():
    ctx = ExecutionContext()
    eval_(ctx, """(define-syntax foo
                                 (syntax-rules ()
                                    ((_) #t)
                                    ((_ bar) bar)))""")

    assert eval_(ctx, "(foo)").to_boolean()
    assert eval_(ctx, "(foo 42)").to_number() == 42

def test_recursive_macro():
    ctx = ExecutionContext()
    eval_(ctx, """(define-syntax my-or
                                 (syntax-rules ()
                                    ((my-or) #f)
                                    ((my-or arg) arg)
                                    ((my-or arg1 arg2)
                                     (if arg1
                                         arg1
                                         (my-or arg2)))
                                    ((my-or arg1 arg2 arg3)
                                     (if arg1
                                         arg1
                                         (my-or arg2 arg3)))))""")

    assert eval_(ctx, "(my-or)").to_boolean() is False
    assert eval_(ctx, "(my-or 12)").to_number() == 12

    #should expand recursively and after that eval
    w_expr = parse_("(my-or 12 42)")
    assert ctx.get("my-or").expand(ctx, w_expr).to_string() == \
            "(if 12 12 42)"
    w_expr = parse_("(my-or 12 42 82)")
    assert ctx.get("my-or").expand(ctx, w_expr).to_string() == \
            "(if 12 12 (if 42 42 82))"
    assert eval_(ctx, "(my-or 12 42)").to_number() == 12
    assert eval_(ctx, "(my-or #f 42)").to_number() == 42
    assert eval_(ctx, "(my-or #f #f 82)").to_number() == 82

def test_macro_expand():
    ctx = ExecutionContext()
    eval_(ctx, """(define-syntax foo (syntax-rules ()
                                          ((foo) #t)
                                          ((foo arg) arg)))""")
    eval_(ctx, """(define-syntax bar (syntax-rules ()
                                          ((bar) (foo))
                                          ((bar arg) (foo arg))))""")

    w_expr = parse_("(bar 42)")
    #should expand directly (recursively) to 42
    assert ctx.get("bar").expand(ctx, w_expr).to_string() == "42"

def test_let_syntax():
    ctx = ExecutionContext()
    w_result = \
        eval_(ctx, """(let-syntax ((foo (syntax-rules ()
                                          ((foo) #t)
                                          ((foo arg) arg)))
                                   (bar (syntax-rules ()
                                          ((bar) #f)
                                          ((bar arg) arg))))
                        (foo (bar (foo))))""")

    assert w_result.to_boolean() is True
    py.test.raises(UnboundVariable, ctx.get, "foo")
    py.test.raises(UnboundVariable, ctx.get, "bar")

def test_sete():
    ctx = ExecutionContext()
    eval_(ctx, "(define a 42)")
    eval_(ctx, """(let-syntax ((foo (syntax-rules ()
                                      ((foo var val) (set! var val)))))
                      (foo a 0))""")

    assert eval_(ctx, "a").to_number() == 0

def test_reverse():
    ctx = ExecutionContext()
    eval_(ctx, """(define-syntax reverse-order
                                 (syntax-rules () 
                                   ((_ e) (reverse-order e ())) 
                                   ((_ (e . rest) r)
                                    (reverse-order rest (e . r))) 
                                   ((_ () r) r)))""")

    w_result = eval_(ctx, "(reverse-order (2 3 -))")
    assert w_result.to_number() == 1

def test_ellipsis_symbol():
    ctx = ExecutionContext()
    eval_(ctx, """(define-syntax or (syntax-rules ()
                                      ((or) #f)
                                      ((or e) e)
                                      ((or e1 e2 ...)
                                       (let ((temp e1))
                                         (if temp
                                             temp
                                             (or e2 ...))))))""")

    assert eval_(ctx, "(or 12)").to_number() == 12
    assert eval_(ctx, "(or 12 42)").to_number() == 12
    
    assert eval_(ctx, "(or #f #f 82)").to_number() == 82
    assert eval_(ctx, "(or #f #f #f 162)").to_number() == 162

def test_ellipsis_list_template():
    ctx = ExecutionContext()
    eval_(ctx, """(define-syntax letzero
                                 (syntax-rules ()
                                    ((_ (sym ...) body ...)
                                     (let ((sym 0) ...) body ...))))""")

    assert eval_(ctx, "(letzero (x) x)").to_number() == 0
    assert eval_(ctx, "(letzero (x) (set! x 1) x)").to_number() == 1

    assert eval_(ctx, "(letzero (x y z) (+ x y z))").to_number() == 0
    assert eval_(ctx, """(letzero (x y z) (set! x 1)
                                          (set! y 1)
                                          (set! z 1)
                                          (+ x y z))""").to_number() == 3

def test_ellipsis_expr_template():
    ctx = ExecutionContext()
    eval_(ctx, """(define-syntax zero-if-true
                                 (syntax-rules ()
                                    ((_ sym ...)
                                     (begin
                                       (if sym (set! sym 0)) ...))))""")

    eval_(ctx, "(define x #t)")
    eval_(ctx, "(define y #f)")
    eval_(ctx, "(define z #t)")
    eval_(ctx, "(zero-if-true x y z)")
    assert eval_(ctx, "x").to_number() == 0
    assert eval_(ctx, "y").to_boolean() is False
    assert eval_(ctx, "z").to_number() == 0

def test_ellipsis_list_pattern():
    ctx = ExecutionContext()
    eval_(ctx, """(define-syntax rlet
                                 (syntax-rules ()
                                    ((_ ((val sym) ...) body ...)
                                     (let ((sym val) ...) body ...))))""")

    assert eval_(ctx, "(rlet ((0 x)) x)").to_number() == 0
    assert eval_(ctx, "(rlet ((0 x)) (set! x 1) x)").to_number() == 1

    assert eval_(ctx, """(rlet ((0 x) (0 y) (0 z))
                               (+ x y z))""").to_number() == 0
    assert eval_(ctx, """(rlet ((0 x) (0 y) (0 z))
                               (set! x 1)
                               (set! y 1)
                               (set! z 1)
                               (+ x y z))""").to_number() == 3

