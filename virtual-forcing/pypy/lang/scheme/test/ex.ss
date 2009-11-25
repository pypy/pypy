(define fac
  (lambda (n)
    (if (= n 1)
      n
      (* n (fac (- n 1))))))
(fac 4)

(define adder (lambda (x) (lambda (y) (+ x y))))
((adder 4) 3)

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
  (even? 12))

(+ 1 2 3)
(- 2)
(- 2.1)
(- 1 2.9 2)
(* 1 2 2)
(/ 1 2.9 2)
(/ 1)
(/ 2 1)
(/ 2 1 7)
(/ 2.1)
;(quit)

