from pypy.lang.scheme.ssparser import parse
from pypy.lang.scheme.object import W_Boolean, W_Fixnum, W_Float, W_String
from pypy.lang.scheme.object import W_Nil, W_Pair, W_Symbol, W_Identifier
from pypy.lang.scheme.object import ExecutionContext
from pypy.lang.scheme.operation import mul, add

def test_operations_simple():
    w_num1 = W_Fixnum(4)
    w_num2 = W_Fixnum(5)
    w_num3 = W_Float(6.1)

    w_num = mul(None, [w_num1])
    assert w_num.to_number() == w_num1.to_number()
    w_num = mul(None, [w_num1, w_num2])
    assert w_num.to_number() == w_num1.to_number() * w_num2.to_number()
    w_num = mul(None, [w_num1, w_num2, w_num3])
    assert w_num.to_number() == (w_num1.to_number() * w_num2.to_number()
            * w_num3.to_number())

    w_num = add(None, [w_num1])
    assert w_num.to_number() == w_num1.to_number()
    w_num = add(None, [w_num1, w_num2])
    assert w_num.to_number() == w_num1.to_number() + w_num2.to_number()
    w_num = add(None, [w_num1, w_num2, w_num3])
    assert w_num.to_number() == (w_num1.to_number() + w_num2.to_number()
            + w_num3.to_number())

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
    eval_expr(ctx, "(define v2 2.1)")
    assert ctx.get("v2").to_number() == 2.1

    w_num = eval_expr(ctx, "(+ 1 v1 v2)")
    assert w_num.to_number() == 45.1

    eval_expr(ctx, "(define v2 3.1)")
    w_num = eval_expr(ctx, "(+ 1 v1 v2)")
    assert w_num.to_number() == 46.1
