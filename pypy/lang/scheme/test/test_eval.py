import py
from pypy.lang.scheme.ssparser import parse
from pypy.lang.scheme.object import *

def test_eval_obj():
    w_num = W_Pair(W_Identifier("+"),
                   W_Pair(W_Fixnum(4), W_Pair(W_Fixnum(5), W_Nil())))
    assert w_num.eval(None).to_number() == 9 

def eval_expr(ctx, expr):
    return parse(expr).eval(ctx)

def eval_noctx(expr):
    return parse(expr).eval(None)

def test_numerical():
    w_num = eval_noctx("(+ 4)")
    assert w_num.to_number() == 4
    w_num = eval_noctx("(+ 4 -5)")
    assert w_num.to_number() == -1
    w_num = eval_noctx("(+ 4 -5 6.1)")
    assert w_num.to_number() == 5.1

    w_num = eval_noctx("(* 4)")
    assert w_num.to_number() == 4
    w_num = eval_noctx("(* 4 -5)")
    assert w_num.to_number() == -20
    w_num = eval_noctx("(* 4 -5 6.1)")
    assert w_num.to_number() == (4 * -5 * 6.1)

    w_num = eval_noctx("(- 4)")
    assert w_num.to_number() == -4
    w_num = eval_noctx("(- 4 5)")
    assert w_num.to_number() == -1
    w_num = eval_noctx("(- 4 -5 6.1)")
    assert w_num.to_number() == 4 - (-5) - 6.1

def test_numerical_nested():
    w_num = eval_noctx("(+ 4 (* (+ 5) 6) (+ 1 2))")
    assert w_num.to_number() == 37

def test_ctx_simple():
    ctx = ExecutionContext()
    ctx.put("v1", W_Fixnum(4))
    ctx.put("v2", W_Fixnum(5))

    w_num = eval_expr(ctx, "(+ 1 v1 v2)")
    assert w_num.to_number() == 10

    ctx.put("v2", W_Float(3.2))
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
    w_bool = eval_noctx("(= 1 2)")
    assert w_bool.to_boolean() is False

    w_bool = eval_noctx("(= 2 2)")
    assert w_bool.to_boolean() is True

    w_bool = eval_noctx("(= 2.1 1.2)")
    assert w_bool.to_boolean() is False

    w_bool = eval_noctx("(= 2.1 2.1)")
    assert w_bool.to_boolean() is True

def test_comparison_heteronums():
    w_bool = eval_noctx("(= 1 2.2)")
    assert w_bool.to_boolean() is False

    w_bool = eval_noctx("(= 2.0 2)")
    assert w_bool.to_boolean() is True

def test_lambda_noargs():
    ctx = ExecutionContext()
    w_lambda = eval_expr(ctx, "(lambda () 12)")
    assert isinstance(w_lambda, W_Procedure)
    assert isinstance(w_lambda, W_Lambda)

    ctx.put("f1", w_lambda)
    w_result = eval_expr(ctx, "(f1)")
    assert isinstance(w_result, W_Fixnum)
    assert w_result.to_number() == 12

def test_lambda_args():
    ctx = ExecutionContext()
    eval_expr(ctx, "(define f1 (lambda (n) n))")

    w_result = eval_expr(ctx, "(f1 42)")
    assert isinstance(w_result, W_Fixnum)
    assert w_result.to_number() == 42

    w_result = eval_expr(ctx, "((lambda (n m) (+ n m)) 42 -42)")
    assert isinstance(w_result, W_Fixnum)
    assert w_result.to_number() == 0

def test_lambda_top_ctx():
    ctx = ExecutionContext()
    eval_expr(ctx, "(define n 42)")
    eval_expr(ctx, "(define f1 (lambda (m) (+ n m)))")
    w_result = eval_expr(ctx, "(f1 -42)")
    assert isinstance(w_result, W_Fixnum)
    assert w_result.to_number() == 0

    eval_expr(ctx, "(define n 84)")
    w_result = eval_expr(ctx, "(f1 -42)")
    assert isinstance(w_result, W_Fixnum)
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
    assert isinstance(w_result, W_Fixnum)
    assert w_result.to_number() == 11

    w_result = eval_expr(ctx, "((adder 6) 5)")
    assert isinstance(w_result, W_Fixnum)
    assert w_result.to_number() == 11

def test_lambda_long_body():
    ctx = ExecutionContext()
    eval_expr(ctx, """(define long_body (lambda () (define x 42) (+ x 1)))""")
    w_result = eval_expr(ctx, "(long_body)")
    assert w_result.to_number() == 43
    assert ctx.get("x") is None

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

def test_quote():
    w_fnum = eval_noctx("(quote 42)")
    assert isinstance(w_fnum, W_Fixnum)
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
    assert isinstance(w_fnum, W_Fixnum)
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
    ctx.put("var", W_Fixnum(42))
    w_lst = eval_expr(ctx, "(list 1 var (+ 2 1) 'a)")
    assert isinstance(w_lst, W_Pair)
    assert w_lst.car.to_number() == 1
    assert w_lst.cdr.car.to_number() == 42
    assert w_lst.cdr.cdr.car.to_number() == 3
    assert w_lst.cdr.cdr.cdr.car.to_string() == "a"
    assert isinstance(w_lst.cdr.cdr.cdr.cdr, W_Nil)

def test_let():
    ctx = ExecutionContext()
    w_global = W_Fixnum(0)
    ctx.put("var", w_global)
    w_result = eval_expr(ctx, "(let ((var 42) (x (+ 2 var))) (+ var x))")
    assert w_result.to_number() == 44
    assert ctx.get("var") is w_global

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
                (even? 12))""")
    assert w_result.to_boolean() is True
