import math

# from the excessive effort department, routines for printing floating
# point numbers from

# "Printing Floating-Point Numbers Quickly and Accurately" by Burger &
# Dybvig, Proceedings of the SIGPLAN '96 Conference on Programming
# Language Design and Implementation.

# The paper contains scheme code which has been specialized for IEEE
# doubles and converted into (still somewhat scheme-like) Python by
# Michael Hudson.

# XXX unfortunately, we need the fixed-format output routines, the source
# for which is not included in the paper... for now, just put up with
# occasionally incorrectly rounded final digits.  I'll get to it.

# XXX should run this at interpreter level, really....


## (define flonum->digits
##   (lambda (v f e min-e p b B)
##     (if (>= e 0)
##         (if (not (= f (expt b (- p 1))))
##             (let ([be (expt b e)])
##               (scale (* f be 2) 2 be be 0 B v))
##             (let* ([be (expt b e)] [be1 (* be b)])
##                   (scale (* f be1 2) (* b 2) be1 be 0 B v)))
##         (if (or (= e min-e) (not (= f (expt b (- p 1)))))
##             (scale (* f 2) (* (expt b (- e)) 2) 1 1 0 B v)
##             (scale (* f b 2) (* (expt b (- 1 e)) 2) b 1 0 B v)))))

# I reject generality in the extreme: we're working with
# ieee 754 64 bit doubles on any platform I care about.
# This means b == 2, min-e = -1074, p = 53 above.  Also,
# specialize for B = 10.

# in:
# v = f * 2**e
# out:
# [d0, d1, ..., dn], k
# st 0.[d1][d2]...[dn] * 10**k is the "best" representation of v

def flonum2digits(v, f, e):
    if e >= 0:
        if not f != 2**52:
            be = 2**e
            return scale(f*be*2, 2, be, be, 0, v)
        else:
            be = 2**e
            be1 = 2*be
            return scale(f*be1*2, 4, be1, be, 0, v)
    else:
        if e == -1075 or f != 2**52:
            return scale(f*2, 2*2**(-e), 1, 1, 0, v)
        else:
            return scale(f*4, 2*2**(1-e), 2, 1, 0, v)


## (define generate
##   (lambda (r s m+ m- B low-ok? high-ok?)
##     (let ([q-r (quotient-remainder (* r B) s)]
##           [m+ (* m+ B)]
##           [m- (* m- B)])
##       (let ([d (car q-r)]
##             [r (cdr q-r)])
##         (let ([tc1 ((if low-ok? <= <) r m-)]
##               [tc2 ((if high-ok? >= >) (+ r m+) s)])
##           (if (not tc1)
##               (if (not tc2)
##                   (cons d (generate r s m+ m- B low-ok? high-ok?))
##                   (list (+ d 1)))
##               (if (not tc2)
##                   (list d)
##                   (if (< (* r 2) s)
##                       (list d)
##                       (list (+ d 1))))))))))

# now the above is an example of a pointlessly recursive algorithm if
# ever i saw one...

def generate(r, s, m_plus, m_minus):
    rr = []
    while 1:
        d, r = divmod(r*10, s)
        m_plus *= 10
        m_minus *= 10
        tc1 = r < m_minus
        tc2 = (r + m_plus) > s
        if tc2:
            rr.append(d+1)
        else:
            rr.append(d)
        if tc1 or tc2:
            break
    return rr


## (define scale
##   (lambda (r s m+ m- k B low-ok? high-ok? v)
##     (let ([est (inexact->exact (ceiling (- (logB B v) 1e-10)))])
##       (if (>= est 0)
##           (fixup r (* s (exptt B est)) m+ m- est B low-ok? high-ok? )
##           (let ([scale (exptt B (- est))])
##             (fixup (* r scale) s (* m+ scale) (* m- scale)
##                    est B low-ok? high-ok? ))))))

def scale(r, s, m_plus, m_minus, k, v):
    est = long(math.ceil(math.log(v, 10) - 1e-10))
    if est >= 0:
        return fixup(r, s * 10 ** est, m_plus, m_minus, est)
    else:
        scale = 10 ** -est
        return fixup(r*scale, s, m_plus*scale, m_minus*scale, est)


## (define fixup
##   (lambda (r s m+ m- k B low-ok? high-ok? )
##     (if ((if high-ok? >= >) (+ r m+) s) ; too low?
##         (cons (+ k 1) (generate r (* s B) m+ m- B low-ok? high-ok? ))
##         (cons k (generate r s m+ m- B low-ok? high-ok? )))))

def fixup(r, s, m_plus, m_minus, k):
    if r + m_plus > s:
        return generate(r, s*10, m_plus, m_minus), k + 1
    else:
        return generate(r, s, m_plus, m_minus), k


def float_digits(f):
    assert f >= 0
    if f == 0.0:
        return ['0'], 1
    m, e = math.frexp(f)
    m = long(m*2.0**53)
    e -= 53
    ds, k = flonum2digits(f, m, e)
    ds = map(str, ds)
    return ds, k
