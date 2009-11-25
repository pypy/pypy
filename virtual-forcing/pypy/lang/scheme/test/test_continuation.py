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
            ; The next time con is called, we start here.
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

def test_loop():
    ctx = ExecutionContext()

    eval_(ctx, "(define k 'none)")
    eval_(ctx, "(define num 'none)")
    w_result = eval_(ctx, """
        (call/cc
            (lambda (return)
                (letrec ((loop
                          (lambda (n)
                            (if (zero? n)
                                0
                                (begin
                                  (call/cc (lambda (cc)
                                             (set! k cc)
                                             (return n)))
                                  (set! num n)
                                  (loop (- n 1)))))))
                      (loop 10))))""")

    assert w_result.to_number() == 10
    assert isinstance(ctx.get("k"), Continuation)
    assert ctx.get("num").to_string() == "none"

    for i in range(9, -1, -1):
        w_result = eval_(ctx, "(k)")
        assert w_result.to_number() == i
        assert ctx.get("num").to_number() == i+1

    w_result = eval_(ctx, "(k)")
    assert w_result.to_number() == 0
    assert ctx.get("num").to_number() == 1

def test_let_define():
    ctx = ExecutionContext()
    
    eval_(ctx, """(define oo
                          (let ((cont (call/cc (lambda (k) k))))
                               cont))""")
    assert isinstance(ctx.get("oo"), Continuation)
    eval_(ctx, "(oo +)")
    assert ctx.get("oo") is ctx.get("+")

def test_lambda_call():
    ctx = ExecutionContext()

    eval_(ctx, "(define c1 'none)")
    eval_(ctx, "(define c2 'none)")
    eval_(ctx, """(define fun (lambda (x y z)
                                (call/cc (lambda (k)
                                           (set! c1 k)))
                                (+ x y z)))""")

    assert ctx.get("c1").to_string() == "none"
    assert ctx.get("c2").to_string() == "none"

    eval_(ctx, """(fun (call/cc (lambda (k)
                                  (set! c2 k)
                                  1))
                       2 3)""")

    w_result = eval_(ctx, "(c1)")
    assert w_result.to_number() == 6

    w_result = eval_(ctx, "(c2 0)")
    assert w_result.to_number() == 5
    w_result = eval_(ctx, "(c1)")
    assert w_result.to_number() == 5

    w_result = eval_(ctx, "(c2 5)")
    assert w_result.to_number() == 10
    w_result = eval_(ctx, "(c1)")
    assert w_result.to_number() == 10

def test_pitfall_1_1():
    ctx = ExecutionContext()
    w_result = eval_(ctx, """
        (let ((cont #f))
           (letrec ((x (call/cc (lambda (c) (set! cont c) 0)))
                    (y (call/cc (lambda (c) (set! cont c) 0))))
             (if cont
                 (let ((c cont))
                   (set! cont #f)
                   (set! x 1)
                   (set! y 1)
                   (c 0))
                 (+ x y 1))))""")

    assert w_result.to_number() == 1

def test_pitfall_1_2():
    #py.test.skip("(cond ...), (and ...) not implemented")
    ctx = ExecutionContext()

    w_result = eval_(ctx, """
      (letrec ((x (call/cc list)) (y (call/cc list)))
        (cond ((procedure? x) (x (pair? y)))
              ((procedure? y) (y (pair? x))))
        (let ((x (car x)) (y (car y)))
          (and (call/cc x) (call/cc y) (call/cc x))))""")

    assert isinstance(w_result, W_Boolean)
    assert w_result.to_boolean() is True

def test_pitfall_1_3():
    ctx = ExecutionContext()
    w_result = eval_(ctx, """
      (letrec ((x (call/cc
                    (lambda (c)
                        (list #t c)))))
          (if (car x)
              ((car (cdr x)) (list #f (lambda () x)))
              (eq? x ((car (cdr x))))))""")

    assert isinstance(w_result, W_Boolean)
    assert w_result.to_boolean() is True

def test_pitfall_7_4():
    ctx = ExecutionContext()
    w_result = eval_(ctx, """
        (let ((x '())
              (y 0))
            (call/cc 
             (lambda (escape)
               (let* ((yin ((lambda (foo) 
                              (set! x (cons y x))
                              (if (= y 10)
                                  (escape x)
                                  (begin
                                    (set! y 0)
                                    foo)))
                            (call/cc (lambda (bar) bar))))
                      (yang ((lambda (foo) 
                               (set! y (+ y 1))
                               foo)
                             (call/cc (lambda (baz) baz)))))
                 (yin yang)))))""")

    assert isinstance(w_result, W_Pair)
    assert w_result.to_string() == "(10 9 8 7 6 5 4 3 2 1 0)"

def test_hefty1_computation():
    ctx = ExecutionContext()

    eval_(ctx, "(define side-effects '())")
    eval_(ctx, """
        (define (hefty-computation do-other-stuff)
            (letrec
              ((loop (lambda (n)
                  (set! side-effects (cons (list 'hefty-a n) side-effects))
                  (set! do-other-stuff (call/cc do-other-stuff))
                  (set! side-effects (cons (list 'hefty-b n) side-effects))
                  (set! do-other-stuff (call/cc do-other-stuff))
                  (set! side-effects (cons (list 'hefty-c n) side-effects))
                  (set! do-other-stuff (call/cc do-other-stuff))
                  (if (zero? n)
                      '()
                      (loop (- n 1))))))
               (loop 1)))""")

    eval_(ctx, """
        (define (superfluous-computation do-other-stuff)
            (letrec
              ((loop (lambda ()
                        (set! side-effects (cons 'break side-effects))
                        (set! do-other-stuff (call/cc do-other-stuff))
                        (loop))))
              (loop)))""")

    eval_(ctx, "(hefty-computation superfluous-computation)")

    assert ctx.get("side-effects").to_string() == \
            """(break (hefty-c 0) break (hefty-b 0) break (hefty-a 0) break (hefty-c 1) break (hefty-b 1) break (hefty-a 1))"""

def test_hefty2_computation():
    ctx = ExecutionContext()

    eval_(ctx, "(define side-effects '())")
    eval_(ctx, """
        (define (hefty-computation do-other-stuff)
            (letrec
              ((loop (lambda (n)
                  (set! side-effects (cons (list 'hefty-a n) side-effects))
                  (set! do-other-stuff (call/cc do-other-stuff))
                  (set! side-effects (cons (list 'hefty-b n) side-effects))
                  (set! do-other-stuff (call/cc do-other-stuff))
                  (set! side-effects (cons (list 'hefty-c n) side-effects))
                  (set! do-other-stuff (call/cc do-other-stuff))
                  (if (zero? n)
                      '()
                      (loop (- n 1))))))
               (loop 1)))""")

    eval_(ctx, """
        (define (superfluous-computation do-other-stuff)
            (letrec
              ((loop (lambda ()
                  (lst-loop '(straight quarter-past half quarter-til))
                  (loop)))
               (lst-loop (lambda (lst) 
                  (if (pair? lst)
                      (let ((graphic (car lst)))
                        (set! side-effects (cons graphic side-effects))
                        (set! do-other-stuff (call/cc do-other-stuff))
                        (lst-loop (cdr lst)))))))
              (loop)))""")


    eval_(ctx, "(hefty-computation superfluous-computation)")
    assert ctx.get("side-effects").to_string() == \
            """(quarter-past (hefty-c 0) straight (hefty-b 0) quarter-til (hefty-a 0) half (hefty-c 1) quarter-past (hefty-b 1) straight (hefty-a 1))"""

