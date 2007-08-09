import py
from pypy.lang.scheme.ssparser import parse
from pypy.lang.scheme.execution import ExecutionContext
from pypy.lang.scheme.object import *

def eval_(ctx, expr):
    try:
        return parse(expr)[0].eval(ctx)
    except ContinuationReturn, e:
        return e.result

def test_callcc():
    ctx = ExecutionContext()

    eval_(ctx, "(define cont #f)")
    w_result = eval_(ctx, """(call/cc (lambda (k) (set! cont k) 3))""")

    w_result = eval_(ctx, "(cont 3)")
    assert w_result.to_number() == 3
    w_result = eval_(ctx, "(cont #f)")
    assert w_result.to_boolean() is False

    #this (+ 1 [...]) should be ingored
    w_result = eval_(ctx, "(+ 1 (cont 3))")
    assert w_result.to_number() == 3
    w_result = eval_(ctx, "(+ 1 (cont #t))")
    assert w_result.to_boolean() is True

def test_callcc_callcc():
    ctx = ExecutionContext()
    w_procedure = eval_(ctx, "(call/cc call/cc)")
    assert isinstance(w_procedure, W_Procedure)
    print w_procedure

    eval_(ctx, "(define cont 'none)")
    w_result = eval_(ctx, """((call/cc call/cc) (lambda (k)
                                                     (set! cont k)
                                                     'done))""")
    assert w_result.to_string() == "done"
    assert isinstance(eval_(ctx, "cont"), W_Procedure)
    eval_(ctx, "(cont +)")
    assert eval_(ctx, "cont") is ctx.get("+")

def test_simple_multi_shot():
    ctx = ExecutionContext()

    eval_(ctx, "(define cont #f)")
    w_result = eval_(ctx, """
        (+ 1 2 (call/cc (lambda (k) (set! cont k) 3)) 4)""")

    assert w_result.to_number() == 10
    assert isinstance(eval_(ctx, "cont"), W_Procedure)
    w_result = eval_(ctx, "(cont 0)")
    assert w_result.to_number() == 7
    w_result = eval_(ctx, "(cont 3)")
    assert w_result.to_number() == 10

def test_nested_multi_shot():
    ctx = ExecutionContext()

    eval_(ctx, "(define cont #f)")
    w_result = eval_(ctx, """
        (* 2 (+ 1 2 (call/cc (lambda (k) (set! cont k) 3)) 4) 1)""")
    assert w_result.to_number() == 20
    w_result = eval_(ctx, "(cont 0)")
    assert w_result.to_number() == 14
    w_result = eval_(ctx, "(cont 3)")
    assert w_result.to_number() == 20

def test_as_lambda_arg():
    ctx = ExecutionContext()

    eval_(ctx, "(define cont #f)")
    eval_(ctx, "(define (add3 a1 a2 a3) (+ a3 a2 a1))")
    w_result = eval_(ctx, """
            (add3 (call/cc (lambda (k) (set! cont k) 3)) 2 1)""")
    assert w_result.to_number() == 6
    w_result = eval_(ctx, "(cont 0)")
    assert w_result.to_number() == 3
    w_result = eval_(ctx, "(cont 3)")
    assert w_result.to_number() == 6

def test_the_continuation():
    ctx = ExecutionContext()

    eval_(ctx, "(define con #f)")
    eval_(ctx, """
        (define (test)
          (let ((i 0))
            (call/cc (lambda (k) (set! con k)))
            ; The next time tc is called, we start here.
            (set! i (+ i 1))
            i))""")

    assert eval_(ctx, "(test)").to_number() == 1
    assert eval_(ctx, "(con)").to_number() == 2
    assert eval_(ctx, "(con)").to_number() == 3
    eval_(ctx, "(define con2 con)")
    assert eval_(ctx, "(test)").to_number() == 1
    assert eval_(ctx, "(con)").to_number() == 2
    assert eval_(ctx, "(con2)").to_number() == 4
    assert eval_(ctx, "(+ 1 (con2))").to_number() == 5

def test_the_continuation_x2():
    ctx = ExecutionContext()

    eval_(ctx, "(define con #f)")
    eval_(ctx, """
        (define (test)
           (* 2 
              (let ((i 0))
                (call/cc (lambda (k) (set! con k)))
                (set! i (+ i 1))
                i)))""")

    assert eval_(ctx, "(test)").to_number() == 2
    assert eval_(ctx, "(con)").to_number() == 4
    assert eval_(ctx, "(con)").to_number() == 6
    eval_(ctx, "(define con2 con)")
    assert eval_(ctx, "(test)").to_number() == 2
    assert eval_(ctx, "(con)").to_number() == 4
    assert eval_(ctx, "(con2)").to_number() == 8
    assert eval_(ctx, "(+ 1 (con2))").to_number() == 10

def test_escape_continuation():
    ctx = ExecutionContext()

    eval_(ctx, "(define ret-failed #f)")
    w_result = eval_(ctx, """
        (let ((test 17))
          (call/cc (lambda (return)
                     (if (odd? test) (return 'odd))
                     (set! ret-failed #t)
                     'even)))""")

    assert w_result.to_string() == "odd"
    assert eval_(ctx, "ret-failed").to_boolean() == False

