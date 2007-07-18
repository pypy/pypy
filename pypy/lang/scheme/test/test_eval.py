import py
from pypy.lang.scheme.ssparser import parse
from pypy.lang.scheme.execution import ExecutionContext
from pypy.lang.scheme.object import *

def test_eval_obj():
    w_num = W_Pair(W_Identifier("+"),
                   W_Pair(W_Integer(4), W_Pair(W_Integer(5), W_Nil())))
    assert w_num.eval(ExecutionContext()).to_number() == 9 

def eval_expr(ctx, expr):
    return parse(expr)[0].eval(ctx)

def eval_noctx(expr):
    return parse(expr)[0].eval(ExecutionContext())

def test_numerical():
    w_num = eval_noctx("(+)")
    assert w_num.to_number() == 0
    w_num = eval_noctx("(+ 4)")
    assert w_num.to_number() == 4
    w_num = eval_noctx("(+ 4 -5)")
    assert w_num.to_number() == -1
    w_num = eval_noctx("(+ 4 -5 6.1)")
    assert w_num.to_number() == 5.1

    w_num = eval_noctx("(*)")
    assert w_num.to_number() == 1
    w_num = eval_noctx("(* 4)")
    assert w_num.to_number() == 4
    w_num = eval_noctx("(* 4 -5)")
    assert w_num.to_number() == -20
    w_num = eval_noctx("(* 4 -5 6.1)")
    assert w_num.to_number() == (4 * -5 * 6.1)

    py.test.raises(WrongArgsNumber, eval_noctx, "(/)")
    w_num = eval_noctx("(/ 4)")
    assert w_num.to_number() == 1 / 4
    w_num = eval_noctx("(/ 4 -5)")
    assert w_num.to_number() == 4 / -5
    w_num = eval_noctx("(/ 4 -5 6.1)")
    assert w_num.to_number() == (4 / -5 / 6.1)

    py.test.raises(WrongArgsNumber, eval_noctx, "(-)")
    w_num = eval_noctx("(- 4)")
    assert w_num.to_number() == -4
    w_num = eval_noctx("(- 4 5)")
    assert w_num.to_number() == -1
    w_num = eval_noctx("(- 4 -5 6.1)")
    assert w_num.to_number() == 4 - (-5) - 6.1

    py.test.raises(WrongArgType, eval_noctx, "(+ 'a)")
    py.test.raises(WrongArgType, eval_noctx, "(+ 1 'a)")
    py.test.raises(WrongArgType, eval_noctx, "(- 'a)")
    py.test.raises(WrongArgType, eval_noctx, "(- 1 'a)")
    py.test.raises(WrongArgType, eval_noctx, "(* 'a)")
    py.test.raises(WrongArgType, eval_noctx, "(* 1 'a)")
    py.test.raises(WrongArgType, eval_noctx, "(/ 'a)")
    py.test.raises(WrongArgType, eval_noctx, "(/ 1 'a)")

def test_numerical_nested():
    w_num = eval_noctx("(+ 4 (* (+ 5) 6) (+ 1 2))")
    assert w_num.to_number() == 37

def test_ctx_simple():
    ctx = ExecutionContext()
    ctx.put("v1", W_Integer(4))
    ctx.put("v2", W_Integer(5))

    w_num = eval_expr(ctx, "(+ 1 v1 v2)")
    assert w_num.to_number() == 10

    ctx.put("v2", W_Real(3.2))
    w_num = eval_expr(ctx, "(+ 1 v1 v2)")
    assert w_num.to_number() == 8.2

def test_ctx_define():
    ctx = ExecutionContext()
    eval_expr(ctx, "(define v1 42)")
    assert ctx.get("v1").to_number() == 42
    w_num = eval_expr(ctx, "v1")
    assert w_num.to_number() == 42

    eval_expr(ctx, "(define v2 2.1)")
    assert ctx.get("v2").to_number() == 2.1

    w_num = eval_expr(ctx, "(+ 1 v1 v2)")
    assert w_num.to_number() == 45.1

    eval_expr(ctx, "(define v2 3.1)")
    w_num = eval_expr(ctx, "(+ 1 v1 v2)")
    assert w_num.to_number() == 46.1

def text_unbound():
    ctx = ExecutionContext()
    py.test.raises(UnboundVariable, eval_expr, ctx, "y")

def test_sete():
    ctx = ExecutionContext()
    eval_expr(ctx, "(define x 42)")
    loc1 = ctx.get_location("x")
    eval_expr(ctx, "(set! x 43)")
    loc2 = ctx.get_location("x")
    assert ctx.get("x").to_number() == 43
    assert loc1 is loc2
    py.test.raises(UnboundVariable, eval_expr, ctx, "(set! y 42)")

def test_func():
    ctx = ExecutionContext()
    w_func = eval_expr(ctx, "+")
    assert isinstance(w_func, W_Procedure)

def test_if_simple():
    ctx = ExecutionContext()
    w_t = eval_expr(ctx, "(if #t #t #f)")
    assert w_t.to_boolean() is True
    w_f = eval_expr(ctx, "(if #f #t #f)")
    assert w_f.to_boolean() is False
    w_f = eval_expr(ctx, "(if 1 #f #t)")
    assert w_f.to_boolean() is False
    w_f = eval_expr(ctx, "(if #t #t)")
    assert w_f.to_boolean() is True
    w_f = eval_expr(ctx, "(if #f #t)")
    assert w_f.to_boolean() is False

def test_if_evaluation():
    ctx = ExecutionContext()
    eval_expr(ctx, "(define then #f)")
    eval_expr(ctx, "(define else #f)")
    eval_expr(ctx, "(if #t (define then #t) (define else #t))")
    assert ctx.get("then").to_boolean() is True
    assert ctx.get("else").to_boolean() is False

    eval_expr(ctx, "(define then #f)")
    eval_expr(ctx, "(define else #f)")
    eval_expr(ctx, "(if #f (define then #t) (define else #t))")
    assert ctx.get("then").to_boolean() is False
    assert ctx.get("else").to_boolean() is True

def test_cons_simple():
    w_pair = eval_noctx("(cons 1 2)")
    assert isinstance(w_pair, W_Pair)
    assert w_pair.car.to_number() == 1
    assert w_pair.cdr.to_number() == 2

    w_pair = eval_noctx("(cons 1 (cons 2 3))")
    assert isinstance(w_pair, W_Pair)
    assert isinstance(w_pair.cdr, W_Pair)
    assert w_pair.car.to_number() == 1
    assert w_pair.cdr.car.to_number() == 2
    assert w_pair.cdr.cdr.to_number() == 3

def test_car_simple():
    w_car = eval_noctx("(car (cons 1 2))")
    assert w_car.to_number() == 1

    w_cdr = eval_noctx("(cdr (cons 1 2))")
    assert w_cdr.to_number() == 2

    w_cadr = eval_noctx("(car (cdr (cons 1 (cons 2 3))))")
    assert w_cadr.to_number() == 2

    w_cddr = eval_noctx("(cdr (cdr (cons 1 (cons 2 3))))")
    assert w_cddr.to_number() == 3

def test_comparison_homonums():
    w_bool = eval_noctx("(=)")
    assert w_bool.to_boolean() is True

    w_bool = eval_noctx("(= 1)")
    assert w_bool.to_boolean() is True

    w_bool = eval_noctx("(= 1 2)")
    assert w_bool.to_boolean() is False

    w_bool = eval_noctx("(= 2 2)")
    assert w_bool.to_boolean() is True

    w_bool = eval_noctx("(= 2 2 2 2)")
    assert w_bool.to_boolean() is True

    w_bool = eval_noctx("(= 2 2 3 2)")
    assert w_bool.to_boolean() is False

    w_bool = eval_noctx("(= 2.1 1.2)")
    assert w_bool.to_boolean() is False

    w_bool = eval_noctx("(= 2.1 2.1)")
    assert w_bool.to_boolean() is True

    w_bool = eval_noctx("(= 2.1 2.1 2.1 2.1)")
    assert w_bool.to_boolean() is True

    w_bool = eval_noctx("(= 2.1 2.1 2.1 2)")
    assert w_bool.to_boolean() is False

    py.test.raises(WrongArgType, eval_noctx, "(= 'a 1)")

def test_comparison_heteronums():
    w_bool = eval_noctx("(= 1 1.0 1.1)")
    assert w_bool.to_boolean() is False

    w_bool = eval_noctx("(= 2.0 2 2.0)")
    assert w_bool.to_boolean() is True

def test_lambda_noargs():
    ctx = ExecutionContext()
    w_lambda = eval_expr(ctx, "(lambda () 12)")
    assert isinstance(w_lambda, W_Procedure)
    assert isinstance(w_lambda, W_Lambda)

    ctx.put("f1", w_lambda)
    w_result = eval_expr(ctx, "(f1)")
    assert isinstance(w_result, W_Integer)
    assert w_result.to_number() == 12

def test_lambda_args():
    ctx = ExecutionContext()
    w_lam = eval_expr(ctx, "(define f1 (lambda (n) n))")
    assert isinstance(w_lam, W_Lambda)

    w_result = eval_expr(ctx, "(f1 42)")
    assert isinstance(w_result, W_Integer)
    assert w_result.to_number() == 42

    w_result = eval_expr(ctx, "((lambda (n m) (+ n m)) 42 -42)")
    assert isinstance(w_result, W_Integer)
    assert w_result.to_number() == 0

def test_lambda_top_ctx():
    ctx = ExecutionContext()
    eval_expr(ctx, "(define n 42)")
    eval_expr(ctx, "(define f1 (lambda (m) (+ n m)))")
    w_result = eval_expr(ctx, "(f1 -42)")
    assert isinstance(w_result, W_Integer)
    assert w_result.to_number() == 0

    eval_expr(ctx, "(define n 84)")
    w_result = eval_expr(ctx, "(f1 -42)")
    assert isinstance(w_result, W_Integer)
    assert w_result.to_number() == 42

def test_lambda_fac():
    ctx = ExecutionContext()
    eval_expr(ctx, """
        (define fac
            (lambda (n)
                (if (= n 1)
                    n
                    (* (fac (- n 1)) n))))""")
    assert isinstance(ctx.get("fac"), W_Lambda)
    w_result = eval_expr(ctx, "(fac 4)")
    assert w_result.to_number() == 24

    w_result = eval_expr(ctx, "(fac 5)")
    assert w_result.to_number() == 120

def test_lambda2():
    ctx = ExecutionContext()
    eval_expr(ctx, """(define adder (lambda (x) (lambda (y) (+ x y))))""")
    w_lambda = eval_expr(ctx, "(adder 6)")
    assert isinstance(w_lambda, W_Lambda)

    eval_expr(ctx, """(define add6 (adder 6))""")
    w_result = eval_expr(ctx, "(add6 5)")
    assert isinstance(w_result, W_Integer)
    assert w_result.to_number() == 11

    w_result = eval_expr(ctx, "((adder 6) 5)")
    assert isinstance(w_result, W_Integer)
    assert w_result.to_number() == 11

def test_lambda_long_body():
    ctx = ExecutionContext()
    eval_expr(ctx, """(define long_body (lambda () (define x 42) (+ x 1)))""")
    w_result = eval_expr(ctx, "(long_body)")
    assert w_result.to_number() == 43
    py.test.raises(UnboundVariable, ctx.get, "x")

def test_lambda_lstarg():
    ctx = ExecutionContext()
    w_result = eval_expr(ctx, """((lambda x x) 1 2 3)""")
    assert isinstance(w_result, W_Pair)
    assert w_result.car.to_number() == 1
    assert w_result.cdr.car.to_number() == 2
    assert w_result.cdr.cdr.car.to_number() == 3

def test_lambda_dotted_lstarg():
    ctx = ExecutionContext()
    w_result = eval_expr(ctx, """((lambda (x y . z) z) 3 4)""")
    assert isinstance(w_result, W_Nil)

    w_result = eval_expr(ctx, """((lambda (x y . z) z) 3 4 5 6)""")
    assert isinstance(w_result, W_Pair)
    assert w_result.car.to_number() == 5
    assert w_result.cdr.car.to_number() == 6
    assert isinstance(w_result.cdr.cdr, W_Nil)

def test_define_lambda_sugar():
    ctx = ExecutionContext()
    eval_expr(ctx, """(define (f x) (+ x 1))""")
    w_result = eval_expr(ctx, "(f 1)")
    assert isinstance(w_result, W_Integer)
    assert w_result.to_number() == 2

    eval_expr(ctx, """(define (f2) (+ 1 1))""")
    w_result = eval_expr(ctx, "(f2)")
    assert isinstance(w_result, W_Integer)
    assert w_result.to_number() == 2

    eval_expr(ctx, """(define (f3 . x) x)""")
    w_result = eval_expr(ctx, "(f3 1 2)")
    assert isinstance(w_result, W_Pair)
    assert w_result.car.to_number() == 1
    assert w_result.cdr.car.to_number() == 2

    eval_expr(ctx, """(define (f4 x . y) x y)""")
    w_result = eval_expr(ctx, "(f4 1 2)")
    assert isinstance(w_result, W_Pair)
    assert w_result.car.to_number() == 2
    assert isinstance(w_result.cdr, W_Nil)

def test_quote():
    w_fnum = eval_noctx("(quote 42)")
    assert isinstance(w_fnum, W_Integer)
    assert w_fnum.to_number() == 42

    w_sym = eval_noctx("(quote symbol)")
    assert isinstance(w_sym, W_Symbol)
    assert w_sym.to_string() == "symbol"

    w_lst = eval_noctx("(quote (1 2 3))")
    assert isinstance(w_lst, W_Pair)
    assert w_lst.car.to_number() == 1
    assert w_lst.cdr.car.to_number() == 2
    assert w_lst.cdr.cdr.car.to_number() == 3

    w_lst = eval_noctx("(quote (a (x y) c))")
    assert isinstance(w_lst, W_Pair)
    assert isinstance(w_lst.car, W_Symbol)
    assert w_lst.car.to_string() == "a"
    w_pair = w_lst.cdr.car
    assert isinstance(w_lst.cdr.cdr.car, W_Symbol)
    assert w_lst.cdr.cdr.car.to_string() == "c"

    assert isinstance(w_pair.car, W_Symbol)
    assert w_pair.car.to_string() == "x"
    assert isinstance(w_pair.cdr.car, W_Symbol)
    assert w_pair.cdr.car.to_string() == "y"

def test_quote_parse():
    w_fnum = eval_noctx("'42")
    assert isinstance(w_fnum, W_Integer)
    assert w_fnum.to_number() == 42

    w_sym = eval_noctx("'symbol")
    assert isinstance(w_sym, W_Symbol)
    assert w_sym.to_string() == "symbol"

    w_lst = eval_noctx("'(1 2 3)")
    assert isinstance(w_lst, W_Pair)
    assert w_lst.car.to_number() == 1
    assert w_lst.cdr.car.to_number() == 2
    assert w_lst.cdr.cdr.car.to_number() == 3

    w_lst = eval_noctx("'(a (x y) c)")
    assert isinstance(w_lst, W_Pair)
    assert isinstance(w_lst.car, W_Symbol)
    assert w_lst.car.to_string() == "a"
    w_pair = w_lst.cdr.car
    assert isinstance(w_lst.cdr.cdr.car, W_Symbol)
    assert w_lst.cdr.cdr.car.to_string() == "c"

    assert isinstance(w_pair.car, W_Symbol)
    assert w_pair.car.to_string() == "x"
    assert isinstance(w_pair.cdr.car, W_Symbol)
    assert w_pair.cdr.car.to_string() == "y"

def test_list():
    ctx = ExecutionContext()
    ctx.put("var", W_Integer(42))
    w_lst = eval_expr(ctx, "(list 1 var (+ 2 1) 'a)")
    assert isinstance(w_lst, W_Pair)
    assert w_lst.car.to_number() == 1
    assert w_lst.cdr.car.to_number() == 42
    assert w_lst.cdr.cdr.car.to_number() == 3
    assert w_lst.cdr.cdr.cdr.car.to_string() == "a"
    assert isinstance(w_lst.cdr.cdr.cdr.cdr, W_Nil)

def test_let():
    ctx = ExecutionContext()
    w_global = W_Integer(0)
    ctx.put("var", w_global)
    w_result = eval_expr(ctx, "(let ((var 42) (x (+ 2 var))) (+ var x))")
    assert w_result.to_number() == 44
    assert ctx.get("var") is w_global

    w_result = eval_expr(ctx, """
        (let ((x (lambda () 1)))
            (let ((y (lambda () (x)))
                  (x (lambda () 2))) (y)))""")
    assert w_result.to_number() == 1

    py.test.raises(UnboundVariable, eval_noctx, "(let ((y 0) (x y)) x)")

def test_letrec():
    ctx = ExecutionContext()
    w_result = eval_expr(ctx, """
        (letrec ((even?
                    (lambda (n)
                        (if (= n 0)
                            #t
                            (odd? (- n 1)))))
                 (odd?
                    (lambda (n)
                        (if (= n 0)
                            #f
                            (even? (- n 1))))))
                (even? 2000))""")
    assert w_result.to_boolean() is True

    w_result = eval_expr(ctx, """
        (let ((x (lambda () 1)))
            (letrec ((y (lambda () (x)))
                     (x (lambda () 2))) (y)))""")
    assert w_result.to_number() == 2

    py.test.raises(UnboundVariable, eval_noctx, "(letrec ((y 0) (x y)) x)")

def test_letstar():
    #test for (let* ...)
    w_result = eval_noctx("""
        (let* ((x 42)
                (y (- x 42))
                (z (+ x y)))
                z)""")
    assert w_result.to_number() == 42

    py.test.raises(UnboundVariable, eval_noctx, "(let* ((x (+ 1 y)) (y 0)) x)")

def test_quit():
    py.test.raises(SchemeQuit, eval_noctx, "(quit)")

def test_numbers():
    assert eval_noctx("(integer? 42)").to_boolean()
    assert eval_noctx("(integer? 42.0)").to_boolean()
    assert not eval_noctx("(integer? 42.1)").to_boolean()

    assert eval_noctx("(rational? 42)").to_boolean()
    assert eval_noctx("(rational? 42.1)").to_boolean()

    assert eval_noctx("(real? 42)").to_boolean()
    assert eval_noctx("(real? 42.1)").to_boolean()

    assert eval_noctx("(complex? 42)").to_boolean()
    assert eval_noctx("(complex? 42.1)").to_boolean()

    assert eval_noctx("(number? 42)").to_boolean()
    assert eval_noctx("(number? 42.1)").to_boolean()

    py.test.raises(WrongArgType, eval_noctx, "(number? 'a)" )

def test_exactness():
    assert eval_noctx("(exact? 42)").to_boolean()
    assert not eval_noctx("(exact? 42.0)").to_boolean()
    py.test.raises(WrongArgType, eval_noctx, "(exact? 'a)" )

    assert not eval_noctx("(inexact? 42)").to_boolean()
    assert eval_noctx("(inexact? 42.0)").to_boolean()
    py.test.raises(WrongArgType, eval_noctx, "(inexact? 'a)" )

def test_number_predicates():
    assert eval_noctx("(zero? 0)").to_boolean()
    assert eval_noctx("(zero? 0.0)").to_boolean()
    assert not eval_noctx("(zero? 1.0)").to_boolean()
    py.test.raises(WrongArgType, eval_noctx, "(zero? 'a)" )

    assert not eval_noctx("(odd? 0)").to_boolean()
    assert eval_noctx("(odd? 1)").to_boolean()
    py.test.raises(WrongArgType, eval_noctx, "(odd? 1.1)" )

    assert eval_noctx("(even? 0)").to_boolean()
    assert not eval_noctx("(even? 1)").to_boolean()
    py.test.raises(WrongArgType, eval_noctx, "(even? 1.1)" )

def test_delay_promise_force():
    ctx = ExecutionContext()
    w_promise = eval_expr(ctx, "(delay (+ 1 2))")
    assert isinstance(w_promise, W_Promise)
    ctx.put("d", w_promise)
    w_promise2 = eval_expr(ctx, "d")
    assert w_promise2 is w_promise
    py.test.raises(NotCallable, eval_expr, ctx, "(d)")

    w_value = eval_expr(ctx, "(force d)")
    assert w_value.to_number() == 3
    py.test.raises(WrongArgType, eval_noctx, "(force 'a)")

    eval_expr(ctx, "(define d2 (delay (+ 1 x)))")
    eval_expr(ctx, "(define x 42)")
    w_result = eval_expr(ctx, "(force d2)")
    assert w_result.to_number() == 43
    eval_expr(ctx, "(set! x 0)")
    w_result = eval_expr(ctx, "(force d2)")
    assert w_result.to_number() == 43

def test_lambda_context():
    ctx = ExecutionContext()
    eval_expr(ctx, """
            (define b (lambda ()
                        (define lam (lambda () (set! a 42)))
                        (define a 12)
                        (lam)
                        a))
                        """)
    w_num = eval_expr(ctx, "(b)")
    assert w_num.to_number() == 42

def test_evaluator():
    ctx = ExecutionContext()
    eval_expr(ctx, "(define a 0)")
    w_obj = parse("(let () (set! a 42) a)")[0]
    (w_expr, new_ctx) = w_obj.eval_tr(ctx)
    assert ctx.get("a").to_number() == 42
    assert isinstance(w_expr, W_Identifier)
    assert new_ctx is not ctx
    assert isinstance(new_ctx, ExecutionContext)
    (w_obj, newer_ctx) = w_expr.eval_tr(new_ctx)
    assert isinstance(w_obj, W_Number)
    assert w_obj.to_number() == 42
    assert newer_ctx is None

def test_deep_recursion():
    ctx = ExecutionContext()
    eval_expr(ctx, "(define a 0)")
    eval_expr(ctx, """
        (define loop (lambda (n)
                        (set! a (+ a 1))
                        (if (= n 0)
                            n
                            (loop (- n 1)))))""")

    eval_expr(ctx, "(loop 2000)")
    assert ctx.get("a").to_number() == 2001

def test_setcar():
    ctx = ExecutionContext()
    w_pair = eval_expr(ctx, "(define lst '(1 2 3 4))")
    eval_expr(ctx, "(set-car! lst 11)")
    assert w_pair is eval_expr(ctx, "lst")
    assert eval_expr(ctx, "(car lst)").to_number() == 11

    eval_expr(ctx, "(set-car! (cdr lst) 12)")
    assert eval_expr(ctx, "(car (cdr lst))").to_number() == 12

def test_setcdr():
    ctx = ExecutionContext()
    w_pair = eval_expr(ctx, "(define lst '(1 2 3 4))")
    eval_expr(ctx, "(set-cdr! lst (cdr (cdr lst)))")
    w_lst = eval_expr(ctx, "lst")
    assert w_pair is w_lst
    assert w_lst.to_string() == "(1 3 4)"

    eval_expr(ctx, "(set-cdr! (cdr lst) '(12))")
    w_lst = eval_expr(ctx, "lst")
    assert w_lst.to_string() == "(1 3 12)"

    #warning circural list
    eval_expr(ctx, "(set-cdr! (cdr (cdr lst)) lst)")
    w_lst = eval_expr(ctx, "lst")
    assert w_lst is eval_expr(ctx, "(cdr (cdr (cdr lst)))")

def test_quasiquote():
    w_res = eval_noctx("(quasiquote (list (unquote (+ 1 2)) 4))")
    assert w_res.to_string() == "(list 3 4)"

    w_res = eval_noctx("""
                (let ((name 'a))
                    (quasiquote (list (unquote name)
                                      (quote (unquote name)))))""")
    assert w_res.to_string() == "(list a (quote a))"

def test_quasiquote_nested():
    w_res = eval_noctx("""
                (quasiquote
                    (a (quasiquote
                           (b (unquote (+ 1 2))
                              (unquote (foo
                                       (unquote (+ 1 3))
                                       d))
                                e))
                            f))""")
    assert w_res.to_string() == \
            "(a (quasiquote (b (unquote (+ 1 2)) (unquote (foo 4 d)) e)) f)"

    w_res = eval_noctx("""
                (let ((name1 'x)
                      (name2 'y))
                    (quasiquote (a
                                (quasiquote (b
                                             (unquote (unquote name1))
                                             (unquote (quote
                                                        (unquote name2)))
                                             d))
                                 e)))""")
    assert w_res.to_string() == "(a (quasiquote (b (unquote x) (unquote (quote y)) d)) e)"

